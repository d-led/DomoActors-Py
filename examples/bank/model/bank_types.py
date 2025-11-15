"""
Actor protocol definitions for the bank example.

Defines the interfaces for all actor types in the banking system.
"""

from __future__ import annotations
from typing import List, Optional
from domo_actors.actors.actor_protocol import ActorProtocol
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bank_types_shared import (
    AccountInfo,
    Transaction,
    TransferResult,
    AccountType,
    PendingTransfer,
    OpenAccountRequest,
    DepositRequest,
    WithdrawalRequest,
    TransferRequest,
    AccountSummaryRequest,
    TransactionHistoryRequest,
)


class Account(ActorProtocol):
    """
    Account actor protocol.

    Represents a single bank account with deposit, withdrawal, and transfer capabilities.
    """

    async def deposit(self, amount: float) -> float:
        """Deposit funds and return new balance."""
        ...

    async def withdraw(self, amount: float) -> float:
        """Withdraw funds and return new balance."""
        ...

    async def get_balance(self) -> float:
        """Get current balance."""
        ...

    async def get_info(self) -> AccountInfo:
        """Get account information."""
        ...

    async def refund(self, amount: float, transaction_id: str, reason: str) -> float:
        """Refund funds with audit trail."""
        ...

    async def get_history(self, limit: Optional[int] = None) -> List[Transaction]:
        """Get transaction history."""
        ...


class Bank(ActorProtocol):
    """
    Bank actor protocol.

    Root coordinator managing all accounts and transfers.
    """

    async def open_account(self, owner: str, account_type: AccountType, initial_balance: float) -> str:
        """Open a new account and return account number."""
        ...

    async def deposit(self, account_number: str, amount: float) -> float:
        """Deposit funds to an account."""
        ...

    async def withdraw(self, account_number: str, amount: float) -> float:
        """Withdraw funds from an account."""
        ...

    async def account(self, account_number: str) -> Optional[Account]:
        """Get account actor by account number."""
        ...

    async def account_summary(self, account_number: str) -> Optional[AccountInfo]:
        """Get account summary information."""
        ...

    async def account_balance(self, account_number: str) -> Optional[float]:
        """Get account balance."""
        ...

    async def all_accounts(self) -> List[AccountInfo]:
        """Get all account summaries."""
        ...

    async def transfer(self, from_account_number: str, to_account_number: str, amount: float) -> TransferResult:
        """Transfer funds between accounts."""
        ...

    async def transaction_history(self, account_number: str, limit: Optional[int] = None) -> List[Transaction]:
        """Get transaction history for an account."""
        ...

    async def pending_transfers(self) -> List[PendingTransfer]:
        """Get list of pending transfers."""
        ...


class Teller(ActorProtocol):
    """
    Teller actor protocol.

    CLI validation layer implementing "let it crash" philosophy.
    Validates user input and delegates to Bank actor.
    """

    async def open_account(self, request: OpenAccountRequest) -> str:
        """Open account with validation."""
        ...

    async def deposit(self, request: DepositRequest) -> float:
        """Deposit with validation."""
        ...

    async def withdraw(self, request: WithdrawalRequest) -> float:
        """Withdraw with validation."""
        ...

    async def transfer(self, request: TransferRequest) -> dict:
        """Transfer with validation."""
        ...

    async def account_summary(self, request: AccountSummaryRequest) -> str:
        """Get formatted account summary."""
        ...

    async def transaction_history(self, request: TransactionHistoryRequest) -> str:
        """Get formatted transaction history."""
        ...

    async def all_accounts(self) -> str:
        """Get formatted list of all accounts."""
        ...

    async def pending_transfers(self) -> str:
        """Get formatted list of pending transfers."""
        ...


class TransactionHistory(ActorProtocol):
    """
    Transaction history actor protocol.

    Immutable transaction log using self-messaging pattern.
    """

    async def record_transaction(self, transaction: Transaction) -> None:
        """Record a transaction (self-send to append)."""
        ...

    async def get_history(self, limit: Optional[int] = None) -> List[Transaction]:
        """Get transaction history."""
        ...

    async def get_balance(self) -> float:
        """Get current balance from history."""
        ...

    async def append_transaction(self, transaction: Transaction) -> None:
        """Append transaction (self-send only)."""
        ...


class TransferCoordinator(ActorProtocol):
    """
    Transfer coordinator actor protocol.

    Multi-step transfer orchestration with retry logic.
    """

    async def register_account(self, account_number: str, account: Account) -> None:
        """Register an account for transfers."""
        ...

    async def initiate_transfer(self, from_account_number: str, to_account_number: str, amount: float) -> str:
        """Initiate a transfer and return transaction ID."""
        ...

    async def get_transfer_status(self, transaction_id: str) -> Optional[str]:
        """Get status of a transfer."""
        ...

    async def get_pending_transfers(self) -> List[PendingTransfer]:
        """Get all pending transfers."""
        ...

    # Self-send only methods (internal state machine)

    async def record_pending_transfer(self, transfer: PendingTransfer) -> None:
        """Record pending transfer (self-send only)."""
        ...

    async def attempt_deposit(self, transaction_id: str) -> None:
        """Attempt deposit to target account (self-send only)."""
        ...

    async def handle_deposit_failure(self, transaction_id: str, reason: str) -> None:
        """Handle deposit failure with retry (self-send only)."""
        ...

    async def process_refund(self, transaction_id: str, reason: str) -> None:
        """Process refund after max retries (self-send only)."""
        ...

    async def complete_transfer(self, transaction_id: str) -> None:
        """Complete transfer and remove from pending (self-send only)."""
        ...
