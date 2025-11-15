"""
Bank Actor - Root coordinator managing accounts and transfers.

Demonstrates parent-child relationships and actor creation.
"""

from __future__ import annotations
from typing import Dict, List, Optional
import random
from domo_actors.actors.actor import Actor
from domo_actors.actors.protocol import Protocol, ProtocolInstantiator
from domo_actors.actors.definition import Definition
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bank_types_shared import AccountType, AccountInfo, Transaction, TransferResult, PendingTransfer
from model.bank_types import Bank, Account, TransferCoordinator
from model.account_actor import AccountActor
from model.transfer_coordinator_actor import TransferCoordinatorActor


class BankActor(Actor):
    """
    Bank actor implementation.

    Root coordinator that manages all accounts and transfers.
    Creates child Account actors and a single TransferCoordinator.
    """

    def __init__(self):
        super().__init__()
        self._accounts: Dict[str, Account] = {}
        self._transfer_coordinator: Optional[TransferCoordinator] = None

    async def before_start(self) -> None:
        """Create transfer coordinator child actor."""
        await super().before_start()

        # Create transfer coordinator as a child actor
        coordinator_protocol: Protocol = type('TransferCoordinatorProtocol', (), {
            'type': lambda self: 'TransferCoordinator',
            'instantiator': lambda self: type('Instantiator', (), {
                'instantiate': lambda self, definition: TransferCoordinatorActor()
            })()
        })()

        coordinator_definition = Definition(
            'TransferCoordinator',
            self.address(),
            ()
        )

        self._transfer_coordinator = self.child_actor_for(
            coordinator_protocol,
            coordinator_definition,
            'transfer-supervisor'
        )

        self.logger().info("Bank: Initialized with transfer coordinator")

    async def open_account(self, owner: str, account_type: AccountType, initial_balance: float) -> str:
        """Open a new account and return account number."""
        # Validation
        if not owner or not owner.strip():
            raise ValueError("Account owner name cannot be empty")

        if initial_balance < 0:
            raise ValueError(f"Initial balance cannot be negative, got ${initial_balance:.2f}")

        # Generate account number
        account_number = f"ACC{random.randint(100000, 999999)}"

        # Create account actor as a child
        account_protocol: Protocol = type('AccountProtocol', (), {
            'type': lambda self: 'Account',
            'instantiator': lambda self: type('Instantiator', (), {
                'instantiate': lambda self, definition: AccountActor(
                    account_number,
                    owner.strip(),
                    account_type,
                    initial_balance
                )
            })()
        })()

        account_definition = Definition(
            f'Account-{account_number}',
            self.address(),
            ()
        )

        account = self.child_actor_for(
            account_protocol,
            account_definition,
            'account-supervisor'
        )

        self._accounts[account_number] = account

        # Register account with transfer coordinator
        await self._transfer_coordinator.register_account(account_number, account)

        self.logger().info(
            f"Bank: Opened {account_type.value} account {account_number} "
            f"for {owner} with balance ${initial_balance:.2f}"
        )

        return account_number

    async def deposit(self, account_number: str, amount: float) -> float:
        """Deposit funds to an account."""
        account = self._accounts.get(account_number)
        if not account:
            raise ValueError(f"Account not found: {account_number}")

        return await account.deposit(amount)

    async def withdraw(self, account_number: str, amount: float) -> float:
        """Withdraw funds from an account."""
        account = self._accounts.get(account_number)
        if not account:
            raise ValueError(f"Account not found: {account_number}")

        return await account.withdraw(amount)

    async def account(self, account_number: str) -> Optional[Account]:
        """Get account actor by account number."""
        return self._accounts.get(account_number)

    async def account_summary(self, account_number: str) -> Optional[AccountInfo]:
        """Get account summary information."""
        account = self._accounts.get(account_number)
        if not account:
            return None

        return await account.get_info()

    async def account_balance(self, account_number: str) -> Optional[float]:
        """Get account balance."""
        account = self._accounts.get(account_number)
        if not account:
            return None

        return await account.get_balance()

    async def all_accounts(self) -> List[AccountInfo]:
        """Get all account summaries."""
        summaries = []
        for account in self._accounts.values():
            info = await account.get_info()
            summaries.append(info)

        # Sort by account number
        summaries.sort(key=lambda x: x.account_number)
        return summaries

    async def transfer(self, from_account_number: str, to_account_number: str, amount: float) -> TransferResult:
        """Transfer funds between accounts."""
        try:
            transaction_id = await self._transfer_coordinator.initiate_transfer(
                from_account_number,
                to_account_number,
                amount
            )

            return TransferResult(
                success=True,
                transaction_id=transaction_id
            )
        except Exception as error:
            return TransferResult(
                success=False,
                error=str(error)
            )

    async def transaction_history(self, account_number: str, limit: Optional[int] = None) -> List[Transaction]:
        """Get transaction history for an account."""
        account = self._accounts.get(account_number)
        if not account:
            raise ValueError(f"Account not found: {account_number}")

        return await account.get_history(limit)

    async def pending_transfers(self) -> List[PendingTransfer]:
        """Get list of pending transfers."""
        return await self._transfer_coordinator.get_pending_transfers()
