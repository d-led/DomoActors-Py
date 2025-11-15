"""
Failure Informant - Context-aware error message formatter.

Provides detailed, user-friendly error messages based on command type and request data.
"""

from __future__ import annotations
from typing import Any, Optional
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bank_types_shared import RequestType


def failure_explanation(
    cause: Exception,
    command: str,
    request: Optional[Any],
    more_details: str,
    highlight: str
) -> str:
    """
    Format context-aware error message with highlight prefix on every line.

    Args:
        cause: The exception that occurred
        command: The command type (e.g., 'OpenAccount')
        request: The request data
        more_details: Additional context-specific details
        highlight: Highlight character (e.g., '***')

    Returns:
        Formatted error message with highlight prefix on every line
    """
    lines = []

    # Start with error info (prefixed with highlight)
    lines.append(f"{highlight}")
    lines.append(f"{highlight}         Command: {command}")
    lines.append(f"{highlight}           Error: {str(cause)}")
    lines.append(f"{highlight}")

    # Command-specific formatting (all lines prefixed with highlight)
    try:
        req_type = RequestType(command)

        if req_type == RequestType.OPEN_ACCOUNT and request:
            lines.append(f"{highlight}           Owner: {request.owner if hasattr(request, 'owner') else 'N/A'}")
            lines.append(f"{highlight}    Account Type: {request.account_type if hasattr(request, 'account_type') else 'N/A'}")
            lines.append(f"{highlight} Initial Balance: {request.initial_balance if hasattr(request, 'initial_balance') else 'N/A'}")
            lines.append(f"{highlight}")
            lines.append(f"{highlight}      Suggestion: Ensure initial balance is a valid monetary value (e.g., '100.00')")

        elif req_type in (RequestType.DEPOSIT, RequestType.WITHDRAW) and request:
            lines.append(f"{highlight}  Account Number: {request.account_number if hasattr(request, 'account_number') else 'N/A'}")
            lines.append(f"{highlight}          Amount: {request.amount if hasattr(request, 'amount') else 'N/A'}")
            lines.append(f"{highlight}")
            lines.append(f"{highlight}      Suggestion: Ensure amount is a valid positive number and account exists")

        elif req_type == RequestType.TRANSFER and request:
            lines.append(f"{highlight}    From Account: {request.from_account_number if hasattr(request, 'from_account_number') else 'N/A'}")
            lines.append(f"{highlight}      To Account: {request.to_account_number if hasattr(request, 'to_account_number') else 'N/A'}")
            lines.append(f"{highlight}          Amount: {request.amount if hasattr(request, 'amount') else 'N/A'}")
            lines.append(f"{highlight}")
            if more_details and more_details != 'None':
                lines.append(f"{highlight}            More: {more_details}")
            lines.append(f"{highlight}      Suggestion: Ensure both accounts exist, are different, and amount is valid")

        elif req_type == RequestType.ACCOUNT_SUMMARY and request:
            lines.append(f"{highlight}  Account Number: {request.account_number if hasattr(request, 'account_number') else 'N/A'}")
            lines.append(f"{highlight}")
            lines.append(f"{highlight}      Suggestion: Ensure account number is valid and exists")

        elif req_type == RequestType.TRANSACTION_HISTORY and request:
            lines.append(f"{highlight}  Account Number: {request.account_number if hasattr(request, 'account_number') else 'N/A'}")
            limit = request.limit if hasattr(request, 'limit') else None
            if limit:
                lines.append(f"{highlight}           Limit: {limit}")
            lines.append(f"{highlight}")
            lines.append(f"{highlight}      Suggestion: Ensure account number is valid and exists")

    except ValueError:
        # Unknown command type - show basic error
        if more_details and more_details != 'None':
            lines.append(f"{highlight}            More: {more_details}")

    lines.append(f"{highlight}")

    return "\n".join(lines)
