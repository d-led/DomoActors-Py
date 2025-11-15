"""
Basic test without pytest - verifies core functionality works.
"""

import asyncio
import sys
sys.path.insert(0, '.')

from domo_actors.actors.actor import Actor
from domo_actors.actors.actor_protocol import ActorProtocol
from domo_actors.actors.protocol import Protocol, ProtocolInstantiator
from domo_actors.actors.definition import Definition
from domo_actors.actors.local_stage import LocalStage
from domo_actors.actors.address import Uuid7Address


# Protocol interface
class Counter(ActorProtocol):
    """Counter protocol interface."""

    async def increment(self) -> None:
        """Increment the counter."""
        pass

    async def get_value(self) -> int:
        """Get the current count."""
        pass


# Actor implementation
class CounterActor(Actor):
    """Counter actor implementation."""

    def __init__(self) -> None:
        """Initialize the counter."""
        super().__init__()
        self._count = 0

    async def increment(self) -> None:
        """Increment the counter."""
        self._count += 1

    async def get_value(self) -> int:
        """Get the current count."""
        return self._count


# Protocol instantiator
class CounterInstantiator(ProtocolInstantiator):
    """Instantiator for Counter protocol."""

    def instantiate(self, definition: Definition) -> Actor:
        """Create a CounterActor instance."""
        return CounterActor()


# Protocol implementation
class CounterProtocol(Protocol):
    """Counter protocol."""

    def type(self) -> str:
        """Get the protocol type."""
        return "Counter"

    def instantiator(self) -> ProtocolInstantiator:
        """Get the instantiator."""
        return CounterInstantiator()


async def test_basic_counter():
    """Test basic counter actor functionality."""
    print("Testing basic counter...")

    # Create stage
    stage = LocalStage()

    # Create counter actor
    address = Uuid7Address()
    definition = Definition("Counter", address, ())
    counter: Counter = stage.actor_for(CounterProtocol(), definition)

    # Give actor time to start
    await asyncio.sleep(0.1)

    # Increment counter
    await counter.increment()
    await counter.increment()
    await counter.increment()

    # Get value
    value = await counter.get_value()

    # Assert
    assert value == 3, f"Expected count=3, got {value}"
    print(f"✓ Counter value is correct: {value}")

    # Cleanup
    await stage.close()
    print("✓ test_basic_counter passed")


async def test_counter_initialization():
    """Test counter starts at zero."""
    print("\nTesting counter initialization...")

    stage = LocalStage()

    address = Uuid7Address()
    definition = Definition("Counter", address, ())
    counter: Counter = stage.actor_for(CounterProtocol(), definition)

    await asyncio.sleep(0.1)

    value = await counter.get_value()
    assert value == 0, f"Expected initial count=0, got {value}"
    print(f"✓ Counter initialized correctly: {value}")

    await stage.close()
    print("✓ test_counter_initialization passed")


async def test_multiple_counters():
    """Test multiple independent counter actors."""
    print("\nTesting multiple counters...")

    stage = LocalStage()

    # Create two counters
    counter1: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter1", Uuid7Address(), ())
    )

    counter2: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter2", Uuid7Address(), ())
    )

    await asyncio.sleep(0.1)

    # Increment counter1 twice
    await counter1.increment()
    await counter1.increment()

    # Increment counter2 three times
    await counter2.increment()
    await counter2.increment()
    await counter2.increment()

    # Check values
    value1 = await counter1.get_value()
    value2 = await counter2.get_value()

    assert value1 == 2, f"Expected counter1=2, got {value1}"
    assert value2 == 3, f"Expected counter2=3, got {value2}"

    print(f"✓ Counter1: {value1}, Counter2: {value2}")

    await stage.close()
    print("✓ test_multiple_counters passed")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("DomoActors-Py - Basic Test Suite")
    print("=" * 60)

    try:
        await test_basic_counter()
        await test_counter_initialization()
        await test_multiple_counters()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
