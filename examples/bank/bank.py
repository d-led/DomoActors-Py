"""
Interactive Banking System - CLI Menu.

Demonstrates DomoActors with supervision, hierarchy, and real-world patterns.
"""

import asyncio
import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from domo_actors.actors.stage import Stage, stage
from domo_actors.actors.protocol import Protocol, ProtocolInstantiator
from domo_actors.actors.definition import Definition
from domo_actors.actors.address import Uuid7Address

# Local imports
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
from supervisors.account_supervisor import AccountSupervisor
from supervisors.bank_supervisor import BankSupervisor
from supervisors.transfer_supervisor import TransferSupervisor


# Global references
teller: Teller = None


def print_menu():
    """Print the main menu."""
    print("\n" + "="*60)
    print(" DomoActors-Py Bank Example")
    print("="*60)
    print("1. Open Account")
    print("2. Deposit Funds")
    print("3. Withdraw Funds")
    print("4. Transfer Funds")
    print("5. Account Summary")
    print("6. Transaction History")
    print("7. List All Accounts")
    print("8. Pending Transfers")
    print("0. Exit")
    print("="*60)


async def prompt(message: str) -> str:
    """Async input prompt."""
    return input(message)


async def open_account():
    """Open a new account."""
    owner = await prompt('Owner name: ')
    account_type = await prompt('Account type (checking/savings): ')
    initial_balance = await prompt('Initial balance: $')

    request = OpenAccountRequest(owner, account_type, initial_balance)

    # Set execution context
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.OPEN_ACCOUNT.value) \
        .set_value('request', request)

    try:
        result = await teller.open_account(request)
        print(result)
    except Exception as e:
        # Error already handled by supervision
        pass

    await asyncio.sleep(0.1)  # Allow async messages to process


async def deposit():
    """Deposit funds."""
    account_number = await prompt('Account number: ')
    amount = await prompt('Amount: $')

    request = DepositRequest(account_number, amount)

    # Set execution context
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.DEPOSIT.value) \
        .set_value('request', request)

    try:
        new_balance = await teller.deposit(request)
        print(f"✅ Deposit successful. New balance: ${new_balance:.2f}")
    except Exception as e:
        # Error already handled by supervision
        pass

    await asyncio.sleep(0.1)


async def withdraw():
    """Withdraw funds."""
    account_number = await prompt('Account number: ')
    amount = await prompt('Amount: $')

    request = WithdrawalRequest(account_number, amount)

    # Set execution context
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.WITHDRAW.value) \
        .set_value('request', request)

    try:
        new_balance = await teller.withdraw(request)
        print(f"✅ Withdrawal successful. New balance: ${new_balance:.2f}")
    except Exception as e:
        # Error already handled by supervision
        pass

    await asyncio.sleep(0.1)


async def transfer():
    """Transfer funds."""
    from_account_number = await prompt('From account number: ')
    to_account_number = await prompt('To account number: ')
    amount = await prompt('Amount: $')

    request = TransferRequest(from_account_number, to_account_number, amount)

    # Set execution context
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.TRANSFER.value) \
        .set_value('request', request)

    try:
        result = await teller.transfer(request)
        if result['success']:
            print(f"✅ Transfer initiated. Transaction ID: {result['transactionId']}")
            print("   (Check 'Pending Transfers' to monitor progress)")
        else:
            print(f"❌ Transfer failed: {result['error']}")
    except Exception as e:
        # Error already handled by supervision
        pass

    await asyncio.sleep(0.1)


async def account_summary():
    """Show account summary."""
    account_number = await prompt('Account number: ')

    request = AccountSummaryRequest(account_number)

    # Set execution context
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.ACCOUNT_SUMMARY.value) \
        .set_value('request', request)

    try:
        summary = await teller.account_summary(request)
        print(summary)
    except Exception as e:
        # Error already handled by supervision
        pass

    await asyncio.sleep(0.1)


async def transaction_history():
    """Show transaction history."""
    account_number = await prompt('Account number: ')
    limit_str = await prompt('Limit (press Enter for all): ')

    limit = int(limit_str) if limit_str.strip() else None
    request = TransactionHistoryRequest(account_number, limit)

    # Set execution context
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.TRANSACTION_HISTORY.value) \
        .set_value('request', request)

    try:
        history = await teller.transaction_history(request)
        print(history)
    except Exception as e:
        # Error already handled by supervision
        pass

    await asyncio.sleep(0.1)


async def all_accounts():
    """List all accounts."""
    # Set execution context
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.ALL_ACCOUNTS.value)

    try:
        accounts = await teller.all_accounts()
        print(accounts)
    except Exception as e:
        # Error already handled by supervision
        pass

    await asyncio.sleep(0.1)


async def pending_transfers():
    """Show pending transfers."""
    # Set execution context
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.PENDING_TRANSFERS.value)

    try:
        transfers = await teller.pending_transfers()
        print(transfers)
    except Exception as e:
        # Error already handled by supervision
        pass

    await asyncio.sleep(0.1)


async def initialize_system():
    """Initialize the banking system."""
    global teller

    print("\nInitializing DomoActors-Py Bank Actor System...")

    # Create and register supervisors as actors
    account_sup_protocol: Protocol = type('AccountSupervisorProtocol', (), {
        'type': lambda self: 'AccountSupervisor',
        'instantiator': lambda self: type('Instantiator', (), {
            'instantiate': lambda self, definition: AccountSupervisor()
        })()
    })()
    account_sup = stage().actor_for(account_sup_protocol, Definition('AccountSupervisor', Uuid7Address(), ()))
    stage().register_supervisor('account-supervisor', account_sup)

    bank_sup_protocol: Protocol = type('BankSupervisorProtocol', (), {
        'type': lambda self: 'BankSupervisor',
        'instantiator': lambda self: type('Instantiator', (), {
            'instantiate': lambda self, definition: BankSupervisor()
        })()
    })()
    bank_sup = stage().actor_for(bank_sup_protocol, Definition('BankSupervisor', Uuid7Address(), ()))
    stage().register_supervisor('bank-supervisor', bank_sup)

    transfer_sup_protocol: Protocol = type('TransferSupervisorProtocol', (), {
        'type': lambda self: 'TransferSupervisor',
        'instantiator': lambda self: type('Instantiator', (), {
            'instantiate': lambda self, definition: TransferSupervisor()
        })()
    })()
    transfer_sup = stage().actor_for(transfer_sup_protocol, Definition('TransferSupervisor', Uuid7Address(), ()))
    stage().register_supervisor('transfer-supervisor', transfer_sup)

    # Create Bank actor
    bank_protocol: Protocol = type('BankProtocol', (), {
        'type': lambda self: 'Bank',
        'instantiator': lambda self: type('Instantiator', (), {
            'instantiate': lambda self, definition: BankActor()
        })()
    })()

    bank_definition = Definition('Bank', Uuid7Address(), ())
    bank: Bank = stage().actor_for(bank_protocol, bank_definition, supervisor_name='bank-supervisor')

    await asyncio.sleep(0.05)  # Allow bank to initialize

    # Create Teller actor
    teller_protocol: Protocol = type('TellerProtocol', (), {
        'type': lambda self: 'Teller',
        'instantiator': lambda self: type('Instantiator', (), {
            'instantiate': lambda self, definition: TellerActor(bank)
        })()
    })()

    teller_definition = Definition('Teller', Uuid7Address(), ())
    teller = stage().actor_for(teller_protocol, teller_definition, supervisor_name='bank-supervisor')

    await asyncio.sleep(0.05)  # Allow teller to initialize

    print("✅ Bank system initialized successfully!")
    print("   - Bank actor created")
    print("   - Teller actor created")
    print("   - Supervisors registered")


async def shutdown_system():
    """Shutdown the banking system."""
    print("\nShutting down DomoActors-Py Bank...")
    await stage().close()
    print("✅ Bank system shutdown complete.")


async def main_loop():
    """Main interactive loop."""
    while True:
        print_menu()
        choice = await prompt("\nEnter your choice: ")

        try:
            if choice == '0':
                break
            elif choice == '1':
                await open_account()
            elif choice == '2':
                await deposit()
            elif choice == '3':
                await withdraw()
            elif choice == '4':
                await transfer()
            elif choice == '5':
                await account_summary()
            elif choice == '6':
                await transaction_history()
            elif choice == '7':
                await all_accounts()
            elif choice == '8':
                await pending_transfers()
            else:
                print("❌ Invalid choice. Please select 0-8.")
        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")


async def main():
    """Main entry point."""
    try:
        await initialize_system()
        await main_loop()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    finally:
        await shutdown_system()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
