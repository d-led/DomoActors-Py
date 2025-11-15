"""
Transaction History Actor - Immutable transaction log.

Demonstrates self-messaging pattern for state consistency.
"""

from __future__ import annotations
from typing import List, Optional
from domo_actors.actors.actor import Actor
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bank_types_shared import Transaction
from model.bank_types import TransactionHistory


class TransactionHistoryActor(Actor):
    """
    Transaction history actor implementation.

    Uses self-messaging pattern to ensure all state changes
    go through the mailbox for consistency.
    """

    def __init__(self):
        super().__init__()
        self._transactions: List[Transaction] = []
        self._self: Optional[TransactionHistory] = None

    async def before_start(self) -> None:
        """Initialize self-proxy for self-messaging."""
        await super().before_start()
        self._self = self.self_as()

    async def record_transaction(self, transaction: Transaction) -> None:
        """
        Record a transaction by self-sending to append.

        This ensures the append goes through the mailbox,
        preventing race conditions.
        """
        await self._self.append_transaction(transaction)

    async def append_transaction(self, transaction: Transaction) -> None:
        """
        Append transaction to history (self-send only).

        This method should only be called via self-messaging
        to ensure serialization through the mailbox.
        """
        self._transactions.append(transaction)
        self.logger().info(
            f"Transaction recorded: {transaction.type} ${transaction.amount:.2f}, "
            f"Balance: ${transaction.balance:.2f}"
        )

    async def get_history(self, limit: Optional[int] = None) -> List[Transaction]:
        """Get transaction history, optionally limited. Returns newest first."""
        # Return newest first (reverse chronological order)
        sorted_transactions = list(reversed(self._transactions))
        if limit:
            return sorted_transactions[:limit]
        return sorted_transactions

    async def get_balance(self) -> float:
        """Get current balance from last transaction."""
        if not self._transactions:
            return 0.0
        return self._transactions[-1].balance
