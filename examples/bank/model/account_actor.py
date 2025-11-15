"""
Account Actor - Individual bank account.

Demonstrates parent-child relationships and transaction history.
"""

from __future__ import annotations
from typing import List, Optional
import time
import random
from datetime import datetime
from domo_actors.actors.actor import Actor
from domo_actors.actors.protocol import Protocol, ProtocolInstantiator
from domo_actors.actors.definition import Definition
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bank_types_shared import AccountType, AccountInfo, Transaction
from model.bank_types import Account, TransactionHistory
from model.transaction_history_actor import TransactionHistoryActor


class AccountActor(Actor):
    """
    Account actor implementation.

    Manages account balance and creates child TransactionHistory actor.
    """

    def __init__(self, account_number: str, owner: str, account_type: AccountType, initial_balance: float):
        super().__init__()
        self._account_number = account_number
        self._owner = owner
        self._type = account_type
        self._balance = initial_balance
        self._created_at = datetime.now()
        self._transaction_history: Optional[TransactionHistory] = None

    async def before_start(self) -> None:
        """Create child TransactionHistory actor."""
        await super().before_start()

        # Create transaction history as a child actor
        history_protocol: Protocol = type('TransactionHistoryProtocol', (), {
            'type': lambda self: 'TransactionHistory',
            'instantiator': lambda self: type('Instantiator', (), {
                'instantiate': lambda self, definition: TransactionHistoryActor()
            })()
        })()

        history_definition = Definition(
            'TransactionHistory',
            self.address(),
            ()
        )

        self._transaction_history = self.child_actor_for(
            history_protocol,
            history_definition,
            'account-supervisor'
        )

        # Record initial deposit
        if self._balance > 0:
            await self._transaction_history.record_transaction(Transaction(
                id=f"init-{self._account_number}",
                type='deposit',
                amount=self._balance,
                balance=self._balance,
                timestamp=self._created_at,
                description=f"Initial deposit ${self._balance:.2f}"
            ))

    async def deposit(self, amount: float) -> float:
        """Deposit funds and return new balance."""
        if amount <= 0:
            raise ValueError(f"Deposit amount must be positive, got ${amount:.2f}")

        self._balance += amount

        # Record transaction
        await self._transaction_history.record_transaction(Transaction(
            id=f"dep-{int(time.time() * 1000)}-{random.randint(1000, 9999)}",
            type='deposit',
            amount=amount,
            balance=self._balance,
            timestamp=datetime.now(),
            description=f"Deposit ${amount:.2f}"
        ))

        self.logger().info(f"Account {self._account_number}: Deposited ${amount:.2f}, Balance: ${self._balance:.2f}")
        return self._balance

    async def withdraw(self, amount: float) -> float:
        """Withdraw funds and return new balance."""
        if amount <= 0:
            raise ValueError(f"Withdrawal amount must be positive, got ${amount:.2f}")

        if amount > self._balance:
            raise ValueError(
                f"Insufficient funds. Requested ${amount:.2f}, Available ${self._balance:.2f}"
            )

        self._balance -= amount

        # Record transaction
        await self._transaction_history.record_transaction(Transaction(
            id=f"wth-{int(time.time() * 1000)}-{random.randint(1000, 9999)}",
            type='withdrawal',
            amount=amount,
            balance=self._balance,
            timestamp=datetime.now(),
            description=f"Withdrawal ${amount:.2f}"
        ))

        self.logger().info(f"Account {self._account_number}: Withdrew ${amount:.2f}, Balance: ${self._balance:.2f}")
        return self._balance

    async def refund(self, amount: float, transaction_id: str, reason: str) -> float:
        """Refund funds with audit trail."""
        if amount <= 0:
            raise ValueError(f"Refund amount must be positive, got ${amount:.2f}")

        self._balance += amount

        # Record refund transaction
        await self._transaction_history.record_transaction(Transaction(
            id=f"refund-{transaction_id}",
            type='refund',
            amount=amount,
            balance=self._balance,
            timestamp=datetime.now(),
            description=f"Refund for transaction {transaction_id}",
            refund_reason=reason
        ))

        self.logger().info(
            f"Account {self._account_number}: Refunded ${amount:.2f} for {transaction_id}, "
            f"Balance: ${self._balance:.2f}"
        )
        return self._balance

    async def get_balance(self) -> float:
        """Get current balance."""
        return self._balance

    async def get_info(self) -> AccountInfo:
        """Get account information."""
        return AccountInfo(
            account_number=self._account_number,
            owner=self._owner,
            type=self._type,
            balance=self._balance,
            created_at=self._created_at
        )

    async def get_history(self, limit: Optional[int] = None) -> List[Transaction]:
        """Get transaction history."""
        return await self._transaction_history.get_history(limit)
