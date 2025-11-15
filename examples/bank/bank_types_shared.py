"""
Shared types for the bank example.

Defines data structures used across the bank application.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class AccountType(Enum):
    """Type of bank account."""
    CHECKING = "checking"
    SAVINGS = "savings"


class TransferStatus(Enum):
    """Status of a transfer operation."""
    WITHDRAWN = "withdrawn"
    COMPLETED = "completed"
    FAILED_DEPOSIT = "failed-deposit"
    REFUNDED = "refunded"


@dataclass
class AccountInfo:
    """Information about a bank account."""
    account_number: str
    owner: str
    type: AccountType
    balance: float
    created_at: datetime


@dataclass
class Transaction:
    """Transaction record for audit trail."""
    id: str
    type: str  # 'deposit', 'withdrawal', 'transfer-in', 'transfer-out', 'refund'
    amount: float
    balance: float
    timestamp: datetime
    description: str
    refund_reason: Optional[str] = None


@dataclass
class PendingTransfer:
    """Pending transfer state."""
    transaction_id: str
    from_account_number: str
    to_account_number: str
    amount: float
    status: str
    withdrawn_at: datetime
    attempts: int = 0


@dataclass
class TransferResult:
    """Result of a transfer operation."""
    success: bool
    transaction_id: Optional[str] = None
    error: Optional[str] = None


# Request types for Teller

@dataclass
class OpenAccountRequest:
    """Request to open a new account."""
    owner: str
    account_type: str
    initial_balance: str


@dataclass
class DepositRequest:
    """Request to deposit funds."""
    account_number: str
    amount: str


@dataclass
class WithdrawalRequest:
    """Request to withdraw funds."""
    account_number: str
    amount: str


@dataclass
class TransferRequest:
    """Request to transfer funds."""
    from_account_number: str
    to_account_number: str
    amount: str


@dataclass
class AccountSummaryRequest:
    """Request for account summary."""
    account_number: str


@dataclass
class TransactionHistoryRequest:
    """Request for transaction history."""
    account_number: str
    limit: Optional[int] = None


# Request type enum
class RequestType(Enum):
    """Types of requests that can be made."""
    OPEN_ACCOUNT = "OpenAccount"
    DEPOSIT = "Deposit"
    WITHDRAW = "Withdraw"
    TRANSFER = "Transfer"
    ACCOUNT_SUMMARY = "AccountSummary"
    TRANSACTION_HISTORY = "TransactionHistory"
    ALL_ACCOUNTS = "AllAccounts"
    PENDING_TRANSFERS = "PendingTransfers"
