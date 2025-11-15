"""
Teller Actor - CLI validation layer.

Implements "let it crash" philosophy - validates input and throws on errors.
Supervisors handle the errors and provide context-aware messages.
"""

from __future__ import annotations
from typing import Dict
from domo_actors.actors.actor import Actor
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bank_types_shared import (
    AccountType,
    OpenAccountRequest,
    DepositRequest,
    WithdrawalRequest,
    TransferRequest,
    AccountSummaryRequest,
    TransactionHistoryRequest,
)
from model.bank_types import Bank, Teller


class TellerActor(Actor):
    """
    Teller actor implementation.

    Validates user input and delegates to Bank actor.
    Throws on invalid input - supervision handles errors.
    """

    def __init__(self, bank: Bank):
        super().__init__()
        self._bank = bank

    async def open_account(self, request: OpenAccountRequest) -> str:
        """Open account with validation."""
        # Parse and validate
        initial_balance = float(request.initial_balance)

        account_type_str = request.account_type.lower().strip()
        if account_type_str == 'savings':
            account_type = AccountType.SAVINGS
        elif account_type_str == 'checking':
            account_type = AccountType.CHECKING
        else:
            raise ValueError(
                f"Invalid account type '{request.account_type}'. "
                f"Must be 'checking' or 'savings'"
            )

        # Delegate to bank
        account_number = await self._bank.open_account(
            request.owner.strip(),
            account_type,
            initial_balance
        )

        return f"✅ Account opened successfully with account id: {account_number}"

    async def deposit(self, request: DepositRequest) -> float:
        """Deposit with validation."""
        amount = float(request.amount)

        new_balance = await self._bank.deposit(
            request.account_number.strip(),
            amount
        )

        return new_balance

    async def withdraw(self, request: WithdrawalRequest) -> float:
        """Withdraw with validation."""
        amount = float(request.amount)

        new_balance = await self._bank.withdraw(
            request.account_number.strip(),
            amount
        )

        return new_balance

    async def transfer(self, request: TransferRequest) -> Dict[str, any]:
        """Transfer with validation."""
        amount = float(request.amount)

        result = await self._bank.transfer(
            request.from_account_number.strip(),
            request.to_account_number.strip(),
            amount
        )

        return {
            'success': result.success,
            'transactionId': result.transaction_id,
            'error': result.error
        }

    async def account_summary(self, request: AccountSummaryRequest) -> str:
        """Get formatted account summary."""
        info = await self._bank.account_summary(request.account_number.strip())

        if not info:
            return f"❌ Account not found: {request.account_number}"

        return f"""
┌─────────────────────────────────────────────────────────
│ Account: {info.account_number.ljust(24)}
├─────────────────────────────────────────────────────────
│ Owner:   {info.owner.ljust(24)}
│ Type:    {info.type.value.ljust(24)}
│ Balance: ${info.balance:.2f}
│ Created: {info.created_at.isoformat()[:19].ljust(23)}
└─────────────────────────────────────────────────────────"""

    async def transaction_history(self, request: TransactionHistoryRequest) -> str:
        """Get formatted transaction history."""
        transactions = await self._bank.transaction_history(
            request.account_number.strip(),
            request.limit
        )

        if not transactions:
            return f"No transactions found for account {request.account_number}"

        # Build formatted history with separate boxes for each transaction (TypeScript format)
        lines = []
        lines.append(f"\nShowing {len(transactions)} transaction(s):\n")

        for txn in transactions:
            timestamp_str = txn.timestamp.isoformat()[:19]

            # Each transaction gets its own box
            lines.append("┌─────────────────────────────────────────────────────────")
            lines.append(f"│ ID:          {txn.id.ljust(42)}")
            lines.append(f"│ Type:        {txn.type.ljust(42)}")
            lines.append(f"│ Amount:      ${txn.amount:.2f}".ljust(59))
            lines.append(f"│ Balance:     ${txn.balance:.2f}".ljust(59))
            lines.append(f"│ Timestamp:   {timestamp_str.ljust(42)}")
            lines.append(f"│ Description: {txn.description.ljust(42)}")
            if txn.refund_reason:
                lines.append(f"│ Refund:      {txn.refund_reason.ljust(42)}")
            lines.append("└─────────────────────────────────────────────────────────")
            lines.append("")  # Blank line between transactions

        return "\n".join(lines)

    async def all_accounts(self) -> str:
        """Get formatted list of all accounts."""
        accounts = await self._bank.all_accounts()

        if not accounts:
            return "No accounts found."

        # Build formatted list
        lines = []
        lines.append("\n┌─────────────────────────────────────────────────────────────────────────")
        lines.append("│ All Accounts")
        lines.append("├─────────────────────────────────────────────────────────────────────────")

        for info in accounts:
            lines.append(
                f"│ {info.account_number} │ {info.owner.ljust(20)} │ "
                f"{info.type.value.ljust(8)} │ ${info.balance:>10.2f}"
            )

        lines.append("└─────────────────────────────────────────────────────────────────────────")

        return "\n".join(lines)

    async def pending_transfers(self) -> str:
        """Get formatted list of pending transfers."""
        transfers = await self._bank.pending_transfers()

        if not transfers:
            return "No pending transfers."

        # Build formatted list
        lines = []
        lines.append("\n┌─────────────────────────────────────────────────────────────────────────────────")
        lines.append("│ Pending Transfers")
        lines.append("├─────────────────────────────────────────────────────────────────────────────────")

        for transfer in transfers:
            timestamp_str = transfer.withdrawn_at.isoformat()[:19]
            lines.append(
                f"│ {transfer.transaction_id} │ {transfer.from_account_number} → "
                f"{transfer.to_account_number} │ ${transfer.amount:.2f}"
            )
            lines.append(f"│   Status: {transfer.status} │ Withdrawn: {timestamp_str} │ Attempts: {transfer.attempts}")
            lines.append("│")

        lines.append("└─────────────────────────────────────────────────────────────────────────────────")

        return "\n".join(lines)
