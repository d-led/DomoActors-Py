"""Quick test for deposit functionality."""

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
    RequestType,
)
from model.bank_types import Bank, Teller
from model.bank_actor import BankActor
from model.teller_actor import TellerActor


async def test():
    print("Creating stage...")
    stage = LocalStage()

    # Create Bank
    bank_protocol: Protocol = type('BankProtocol', (), {
        'type': lambda self: 'Bank',
        'instantiator': lambda self: type('Instantiator', (), {
            'instantiate': lambda self, definition: BankActor()
        })()
    })()
    bank_definition = Definition('Bank', Uuid7Address(), ())
    bank: Bank = stage.actor_for(bank_protocol, bank_definition)
    await asyncio.sleep(0.1)

    # Create Teller
    teller_protocol: Protocol = type('TellerProtocol', (), {
        'type': lambda self: 'Teller',
        'instantiator': lambda self: type('Instantiator', (), {
            'instantiate': lambda self, definition: TellerActor(bank)
        })()
    })()
    teller_definition = Definition('Teller', Uuid7Address(), ())
    teller: Teller = stage.actor_for(teller_protocol, teller_definition)
    await asyncio.sleep(0.1)

    print("Opening account...")
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.OPEN_ACCOUNT.value) \
        .set_value('request', OpenAccountRequest("Test", "checking", "1000"))

    result = await teller.open_account(OpenAccountRequest("Test", "checking", "1000"))
    print(f"Result: {result}")
    account_number = result.split(":")[-1].strip()

    await asyncio.sleep(0.2)

    print(f"\nDepositing to account {account_number}...")
    teller.execution_context().clear(); teller.execution_context() \
        .set_value('command', RequestType.DEPOSIT.value) \
        .set_value('request', DepositRequest(account_number, "500"))

    balance = await teller.deposit(DepositRequest(account_number, "500"))
    print(f"New balance: ${balance:.2f}")

    await asyncio.sleep(0.2)

    print("\nTest completed!")
    await stage.close()


if __name__ == '__main__':
    asyncio.run(test())
