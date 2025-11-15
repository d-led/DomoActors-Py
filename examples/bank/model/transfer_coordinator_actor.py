"""
Transfer Coordinator Actor - Multi-step transfer orchestration.

Demonstrates retry logic, exponential backoff, and refund handling.
"""

from __future__ import annotations
from typing import Dict, List, Optional
import time
import random
from datetime import datetime
from domo_actors.actors.actor import Actor
from domo_actors.actors.scheduler import Scheduled
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bank_types_shared import PendingTransfer, TransferStatus
from model.bank_types import Account, TransferCoordinator


# Transfer retry configuration
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_MS = 1000  # 1 second base delay


class TransferCoordinatorActor(Actor):
    """
    Transfer coordinator actor implementation.

    Orchestrates multi-step transfers with retry logic and refund handling.
    Uses self-messaging for state machine transitions.
    """

    def __init__(self):
        super().__init__()
        self._accounts: Dict[str, Account] = {}
        self._pending_transfers: Dict[str, PendingTransfer] = {}
        self._self: Optional[TransferCoordinator] = None

    async def before_start(self) -> None:
        """Initialize self-proxy for state machine."""
        await super().before_start()
        self._self = self.self_as()

    async def register_account(self, account_number: str, account: Account) -> None:
        """Register an account for transfers."""
        self._accounts[account_number] = account
        self.logger().info(f"TransferCoordinator: Registered account {account_number}")

    async def initiate_transfer(self, from_account_number: str, to_account_number: str, amount: float) -> str:
        """
        Initiate a transfer and return transaction ID.

        Phase 1: Immediate withdrawal (synchronous, must succeed)
        Phase 2-5: Async state machine via self-messaging
        """
        # Validation
        if from_account_number == to_account_number:
            raise ValueError("Transfer must be between different accounts")

        from_account = self._accounts.get(from_account_number)
        if not from_account:
            raise ValueError(f"Account not found: {from_account_number}")

        to_account = self._accounts.get(to_account_number)
        if not to_account:
            raise ValueError(f"Account not found: {to_account_number}")

        # Generate transaction ID
        transaction_id = f"txn-{int(time.time() * 1000)}-{random.randint(10000, 99999)}"

        # Phase 1: Withdraw immediately (if fails, transfer stops)
        try:
            await from_account.withdraw(amount)
            self.logger().info(
                f"Transfer {transaction_id}: Withdrew ${amount:.2f} from {from_account_number}"
            )
        except Exception as error:
            self.logger().info(
                f"Transfer {transaction_id}: Withdrawal failed - {error}"
            )
            raise

        # Phase 2: Record pending transfer (async via self-send)
        pending = PendingTransfer(
            transaction_id=transaction_id,
            from_account_number=from_account_number,
            to_account_number=to_account_number,
            amount=amount,
            status=TransferStatus.WITHDRAWN.value,
            withdrawn_at=datetime.now(),
            attempts=0
        )
        await self._self.record_pending_transfer(pending)

        # Phase 3: Attempt deposit (async via self-send)
        await self._self.attempt_deposit(transaction_id)

        return transaction_id

    async def record_pending_transfer(self, transfer: PendingTransfer) -> None:
        """Record pending transfer (self-send only)."""
        self._pending_transfers[transfer.transaction_id] = transfer
        self.logger().info(
            f"Transfer {transfer.transaction_id}: Recorded as pending "
            f"({transfer.from_account_number} → {transfer.to_account_number})"
        )

    async def attempt_deposit(self, transaction_id: str) -> None:
        """Attempt deposit to target account (self-send only)."""
        transfer = self._pending_transfers.get(transaction_id)
        if not transfer:
            self.logger().info(f"Transfer {transaction_id}: Not found in pending")
            return

        to_account = self._accounts.get(transfer.to_account_number)
        if not to_account:
            await self._self.handle_deposit_failure(
                transaction_id,
                f"Account not found: {transfer.to_account_number}"
            )
            return

        try:
            await to_account.deposit(transfer.amount)
            self.logger().info(
                f"Transfer {transaction_id}: Deposit successful "
                f"(${transfer.amount:.2f} to {transfer.to_account_number})"
            )
            await self._self.complete_transfer(transaction_id)
        except Exception as error:
            self.logger().info(
                f"Transfer {transaction_id}: Deposit failed - {error}"
            )
            await self._self.handle_deposit_failure(transaction_id, str(error))

    async def handle_deposit_failure(self, transaction_id: str, reason: str) -> None:
        """Handle deposit failure with retry (self-send only)."""
        transfer = self._pending_transfers.get(transaction_id)
        if not transfer:
            return

        transfer.attempts += 1

        if transfer.attempts < MAX_RETRY_ATTEMPTS:
            # Exponential backoff: 1s, 2s, 4s
            delay_ms = RETRY_DELAY_MS * (2 ** (transfer.attempts - 1))

            self.logger().info(
                f"Transfer {transaction_id}: Retry attempt {transfer.attempts}/{MAX_RETRY_ATTEMPTS} "
                f"in {delay_ms}ms"
            )

            # Schedule retry
            class RetryTask(Scheduled):
                def __init__(self, coordinator_self, txn_id):
                    self.coordinator_self = coordinator_self
                    self.txn_id = txn_id

                def interval_signal(self, scheduled):
                    import asyncio
                    asyncio.create_task(self.coordinator_self.attempt_deposit(self.txn_id))

            retry_task = RetryTask(self._self, transaction_id)
            self.scheduler().schedule_once(retry_task, delay_ms, 0)
        else:
            # Max retries exceeded - refund
            self.logger().info(
                f"Transfer {transaction_id}: Max retries exceeded, processing refund"
            )
            await self._self.process_refund(transaction_id, reason)

    async def process_refund(self, transaction_id: str, reason: str) -> None:
        """Process refund after max retries (self-send only)."""
        transfer = self._pending_transfers.get(transaction_id)
        if not transfer:
            return

        from_account = self._accounts.get(transfer.from_account_number)
        if not from_account:
            self.logger().info(
                f"Transfer {transaction_id}: Cannot refund - from account not found"
            )
            return

        refund_reason = (
            f"Transfer to {transfer.to_account_number} failed: {reason}. "
            f"Attempted {MAX_RETRY_ATTEMPTS} times."
        )

        try:
            await from_account.refund(transfer.amount, transaction_id, refund_reason)
            self.logger().info(
                f"Transfer {transaction_id}: Refunded ${transfer.amount:.2f} "
                f"to {transfer.from_account_number}"
            )
        except Exception as error:
            self.logger().info(
                f"Transfer {transaction_id}: Refund failed - {error}"
            )

        transfer.status = TransferStatus.REFUNDED.value
        await self._self.complete_transfer(transaction_id)

    async def complete_transfer(self, transaction_id: str) -> None:
        """Complete transfer and remove from pending (self-send only)."""
        transfer = self._pending_transfers.pop(transaction_id, None)
        if transfer:
            if transfer.status == TransferStatus.WITHDRAWN.value:
                transfer.status = TransferStatus.COMPLETED.value

            self.logger().info(
                f"Transfer {transaction_id}: Completed with status '{transfer.status}'"
            )

    async def get_transfer_status(self, transaction_id: str) -> Optional[str]:
        """Get status of a transfer."""
        transfer = self._pending_transfers.get(transaction_id)
        return transfer.status if transfer else None

    async def get_pending_transfers(self) -> List[PendingTransfer]:
        """Get all pending transfers."""
        return list(self._pending_transfers.values())
