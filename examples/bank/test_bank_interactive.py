"""
Test script to verify bank example functionality.

Tests the basic operations without user interaction.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from domo_actors.actors.local_stage import LocalStage
from domo_actors.actors.protocol import Protocol
from domo_actors.actors.definition import Definition
from domo_actors.actors.address import Uuid7Address

from bank_types_shared import (
    RequestType,
    OpenAccountRequest,
    DepositRequest,
    WithdrawalRequest,
    TransferRequest,
    AccountSummaryRequest,
    TransactionHistoryRequest,
)
from model.bank_types import Bank, Teller
from model.bank_actor import BankActor
from model.teller_actor import TellerActor


async def test_bank_operations():
    """Test basic bank operations."""
    print("\n" + "="*60)
    print("Testing DomoActors-Py Bank Actor System")
    print("="*60)

    # Create stage
    stage = LocalStage()

    # Create Bank actor
    bank_protocol: Protocol = type('BankProtocol', (), {
        'type': lambda self: 'Bank',
        'instantiator': lambda self: type('Instantiator', (), {
            'instantiate': lambda self, definition: BankActor()
        })()
    })()

    bank_definition = Definition('Bank', Uuid7Address(), ())
    bank: Bank = stage.actor_for(bank_protocol, bank_definition)

    await asyncio.sleep(0.1)

    # Create Teller actor
    teller_protocol: Protocol = type('TellerProtocol', (), {
        'type': lambda self: 'Teller',
        'instantiator': lambda self: type('Instantiator', (), {
            'instantiate': lambda self, definition: TellerActor(bank)
        })()
    })()

    teller_definition = Definition('Teller', Uuid7Address(), ())
    teller: Teller = stage.actor_for(teller_protocol, teller_definition)

    await asyncio.sleep(0.1)

    print("✅ Stage and actors created\n")

    # Test 1: Open account
    print("Test 1: Opening account...")
    request = OpenAccountRequest("Alice", "checking", "1000.00")
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.OPEN_ACCOUNT.value) \
        .set_value('request', request)

    result = await teller.open_account(request)
    print(f"  {result}")
    account_number = result.split(":")[-1].strip()

    await asyncio.sleep(0.1)

    # Test 2: Deposit
    print("\nTest 2: Depositing funds...")
    deposit_req = DepositRequest(account_number, "500.00")
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.DEPOSIT.value) \
        .set_value('request', deposit_req)

    new_balance = await teller.deposit(deposit_req)
    print(f"  ✅ Deposit successful. New balance: ${new_balance:.2f}")

    await asyncio.sleep(0.1)

    # Test 3: Withdraw
    print("\nTest 3: Withdrawing funds...")
    withdraw_req = WithdrawalRequest(account_number, "200.00")
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.WITHDRAW.value) \
        .set_value('request', withdraw_req)

    new_balance = await teller.withdraw(withdraw_req)
    print(f"  ✅ Withdrawal successful. New balance: ${new_balance:.2f}")

    await asyncio.sleep(0.1)

    # Test 4: Account summary
    print("\nTest 4: Getting account summary...")
    summary_req = AccountSummaryRequest(account_number)
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.ACCOUNT_SUMMARY.value) \
        .set_value('request', summary_req)

    summary = await teller.account_summary(summary_req)
    print(summary)

    await asyncio.sleep(0.1)

    # Test 5: Transaction history
    print("\nTest 5: Getting transaction history...")
    history_req = TransactionHistoryRequest(account_number, None)
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.TRANSACTION_HISTORY.value) \
        .set_value('request', history_req)

    history = await teller.transaction_history(history_req)
    print(history)

    await asyncio.sleep(0.1)

    # Test 6: All accounts
    print("\nTest 6: Listing all accounts...")
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.ALL_ACCOUNTS.value)

    accounts = await teller.all_accounts()
    print(accounts)

    await asyncio.sleep(0.1)

    print("\n" + "="*60)
    print("All tests completed successfully!")
    print("="*60)

    # Cleanup
    await stage.close()


if __name__ == '__main__':
    asyncio.run(test_bank_operations())
