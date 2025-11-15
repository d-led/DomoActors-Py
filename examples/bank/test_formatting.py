"""Test transaction history and supervisor formatting."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from domo_actors.actors.local_stage import LocalStage
from domo_actors.actors.protocol import Protocol
from domo_actors.actors.definition import Definition
from domo_actors.actors.address import Uuid7Address

from bank_types_shared import (
    OpenAccountRequest,
    DepositRequest,
    WithdrawalRequest,
    TransactionHistoryRequest,
    RequestType,
)
from model.bank_types import Bank, Teller
from model.bank_actor import BankActor
from model.teller_actor import TellerActor
from supervisors.account_supervisor import AccountSupervisor
from supervisors.bank_supervisor import BankSupervisor
from supervisors.transfer_supervisor import TransferSupervisor


async def test():
    print("Creating stage and registering supervisors...")
    stage = LocalStage()

    # Create and register supervisors as actors
    account_sup_protocol: Protocol = type('AccountSupervisorProtocol', (), {
        'type': lambda self: 'AccountSupervisor',
        'instantiator': lambda self: type('Instantiator', (), {
            'instantiate': lambda self, definition: AccountSupervisor()
        })()
    })()
    account_sup = stage.actor_for(account_sup_protocol, Definition('AccountSupervisor', Uuid7Address(), ()))
    stage.register_supervisor('account-supervisor', account_sup)

    bank_sup_protocol: Protocol = type('BankSupervisorProtocol', (), {
        'type': lambda self: 'BankSupervisor',
        'instantiator': lambda self: type('Instantiator', (), {
            'instantiate': lambda self, definition: BankSupervisor()
        })()
    })()
    bank_sup = stage.actor_for(bank_sup_protocol, Definition('BankSupervisor', Uuid7Address(), ()))
    stage.register_supervisor('bank-supervisor', bank_sup)

    transfer_sup_protocol: Protocol = type('TransferSupervisorProtocol', (), {
        'type': lambda self: 'TransferSupervisor',
        'instantiator': lambda self: type('Instantiator', (), {
            'instantiate': lambda self, definition: TransferSupervisor()
        })()
    })()
    transfer_sup = stage.actor_for(transfer_sup_protocol, Definition('TransferSupervisor', Uuid7Address(), ()))
    stage.register_supervisor('transfer-supervisor', transfer_sup)

    await asyncio.sleep(0.1)

    # Create Bank
    bank_protocol: Protocol = type('BankProtocol', (), {
        'type': lambda self: 'Bank',
        'instantiator': lambda self: type('Instantiator', (), {
            'instantiate': lambda self, definition: BankActor()
        })()
    })()
    bank_definition = Definition('Bank', Uuid7Address(), ())
    bank: Bank = stage.actor_for(bank_protocol, bank_definition, supervisor_name='bank-supervisor')
    await asyncio.sleep(0.1)

    # Create Teller
    teller_protocol: Protocol = type('TellerProtocol', (), {
        'type': lambda self: 'Teller',
        'instantiator': lambda self: type('Instantiator', (), {
            'instantiate': lambda self, definition: TellerActor(bank)
        })()
    })()
    teller_definition = Definition('Teller', Uuid7Address(), ())
    teller: Teller = stage.actor_for(teller_protocol, teller_definition, supervisor_name='bank-supervisor')
    await asyncio.sleep(0.1)

    print("Opening account and making transactions...")
    result = await teller.open_account(OpenAccountRequest("Alice", "checking", "1000"))
    account_number = result.split(":")[-1].strip()
    print(f"Account: {account_number}")

    await asyncio.sleep(0.2)

    # Make some transactions
    await teller.deposit(DepositRequest(account_number, "500"))
    await asyncio.sleep(0.1)
    await teller.withdraw(WithdrawalRequest(account_number, "200"))
    await asyncio.sleep(0.1)
    await teller.deposit(DepositRequest(account_number, "100"))
    await asyncio.sleep(0.1)

    print("\n=== Transaction History (should show newest first) ===")
    history_req = TransactionHistoryRequest(account_number, None)
    history = await teller.transaction_history(history_req)
    print(history)

    await asyncio.sleep(0.2)
    await stage.close()


if __name__ == '__main__':
    asyncio.run(test())
