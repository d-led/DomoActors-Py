"""
Array Mailbox tests - Unbounded FIFO mailbox behavior.

Test cases covering unbounded queue operations.
"""

import pytest
import asyncio
from typing import List, Dict
from domo_actors.actors.actor import Actor
from domo_actors.actors.actor_protocol import ActorProtocol
from domo_actors.actors.protocol import Protocol, ProtocolInstantiator
from domo_actors.actors.definition import Definition
from domo_actors.actors.local_stage import LocalStage
from domo_actors.actors.address import Uuid7Address
from domo_actors.actors.array_mailbox import ArrayMailbox


# Global storage
counter_actors: Dict[str, 'CounterActorImpl'] = {}


# ============================================================================
# Test Actor
# ============================================================================

class Counter(ActorProtocol):
    """Counter actor for testing."""
    async def increment(self) -> None: ...
    async def get_value(self) -> int: ...
    async def add(self, amount: int) -> int: ...


class CounterActorImpl(Actor):
    """Counter implementation."""

    def __init__(self):
        super().__init__()
        self._count = 0

    async def increment(self) -> None:
        self._count += 1

    async def get_value(self) -> int:
        return self._count

    async def add(self, amount: int) -> int:
        self._count += amount
        return self._count


class CounterInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        actor = CounterActorImpl()
        counter_actors[definition.address().value_as_string()] = actor
        return actor


class CounterProtocol(Protocol):
    def type(self) -> str:
        return "Counter"

    def instantiator(self) -> ProtocolInstantiator:
        return CounterInstantiator()


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def stage():
    """Create a fresh stage for each test."""
    s = LocalStage()
    yield s
    asyncio.run(s.close())


@pytest.fixture(autouse=True)
def clear_actors():
    """Clear global actor storage."""
    counter_actors.clear()


# ============================================================================
# Tests
# ============================================================================

@pytest.mark.asyncio
async def test_array_mailbox_basic_send_receive(stage):
    """Test basic send and receive operations."""
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    # Send messages
    await counter.increment()
    await counter.increment()
    await counter.increment()

    # Verify processed
    value = await counter.get_value()
    assert value == 3


@pytest.mark.asyncio
async def test_array_mailbox_fifo_ordering(stage):
    """Test that messages are processed in FIFO order."""
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    # Send messages that set specific values
    result1 = await counter.add(10)  # 10
    result2 = await counter.add(5)   # 15
    result3 = await counter.add(3)   # 18

    # Results should reflect FIFO processing
    assert result1 == 10
    assert result2 == 15
    assert result3 == 18


@pytest.mark.asyncio
async def test_array_mailbox_suspension(stage):
    """Test that suspension prevents message processing."""
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    # Get raw actor and mailbox
    raw_actor = counter_actors[counter.address().value_as_string()]
    mailbox = raw_actor.life_cycle().environment().mailbox()

    # Suspend mailbox
    mailbox.suspend()
    assert mailbox.is_suspended() == True

    # Send messages while suspended
    await counter.increment()
    await counter.increment()

    await asyncio.sleep(0.1)

    # Should not be processed yet
    assert raw_actor._count == 0

    # Resume
    mailbox.resume()
    assert mailbox.is_suspended() == False

    await asyncio.sleep(0.1)

    # Now should be processed
    assert raw_actor._count == 2


@pytest.mark.asyncio
async def test_array_mailbox_resumption_processes_queued(stage):
    """Test that resumption processes all queued messages."""
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    raw_actor = counter_actors[counter.address().value_as_string()]
    mailbox = raw_actor.life_cycle().environment().mailbox()

    # Suspend and queue many messages
    mailbox.suspend()

    for _ in range(10):
        await counter.increment()

    await asyncio.sleep(0.05)
    assert raw_actor._count == 0

    # Resume
    mailbox.resume()
    await asyncio.sleep(0.2)

    # All should be processed
    assert raw_actor._count == 10


@pytest.mark.asyncio
async def test_array_mailbox_is_receivable(stage):
    """Test is_receivable reflects queue state."""
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    raw_actor = counter_actors[counter.address().value_as_string()]
    mailbox = raw_actor.life_cycle().environment().mailbox()

    # Suspend to prevent processing
    mailbox.suspend()

    # Should be empty
    assert mailbox.is_receivable() == False

    # Send message
    await counter.increment()
    await asyncio.sleep(0.05)

    # Should have message
    assert mailbox.is_receivable() == True

    # Resume and wait for processing
    mailbox.resume()
    await asyncio.sleep(0.1)

    # Should be empty again
    assert mailbox.is_receivable() == False


@pytest.mark.asyncio
async def test_array_mailbox_size(stage):
    """Test size tracking."""
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    raw_actor = counter_actors[counter.address().value_as_string()]
    mailbox = raw_actor.life_cycle().environment().mailbox()

    # Suspend
    mailbox.suspend()

    # Send messages
    await counter.increment()
    await counter.increment()
    await counter.increment()

    await asyncio.sleep(0.05)

    # Check size
    assert mailbox.size() == 3

    # Resume and wait
    mailbox.resume()
    await asyncio.sleep(0.1)

    # Should be empty
    assert mailbox.size() == 0


@pytest.mark.asyncio
async def test_array_mailbox_close_prevents_delivery(stage):
    """Test that closing mailbox prevents message delivery."""
    from domo_actors.actors.testkit.test_dead_letters_listener import TestDeadLettersListener

    listener = TestDeadLettersListener()
    stage.dead_letters().register_listener(listener)

    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    raw_actor = counter_actors[counter.address().value_as_string()]
    mailbox = raw_actor.life_cycle().environment().mailbox()

    # Close mailbox
    mailbox.close()
    assert mailbox.is_closed() == True

    # Try to send message
    await counter.increment()
    await asyncio.sleep(0.1)

    # Should go to dead letters
    assert listener.count() > 0


@pytest.mark.asyncio
async def test_array_mailbox_multiple_suspend_resume(stage):
    """Test multiple suspend/resume cycles."""
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    raw_actor = counter_actors[counter.address().value_as_string()]
    mailbox = raw_actor.life_cycle().environment().mailbox()

    # First cycle
    mailbox.suspend()
    await counter.increment()
    mailbox.resume()
    await asyncio.sleep(0.1)
    assert raw_actor._count == 1

    # Second cycle
    mailbox.suspend()
    await counter.increment()
    await counter.increment()
    mailbox.resume()
    await asyncio.sleep(0.1)
    assert raw_actor._count == 3


@pytest.mark.asyncio
async def test_array_mailbox_idempotent_suspend(stage):
    """Test that multiple suspend calls are idempotent."""
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    raw_actor = counter_actors[counter.address().value_as_string()]
    mailbox = raw_actor.life_cycle().environment().mailbox()

    # Multiple suspends
    mailbox.suspend()
    mailbox.suspend()
    mailbox.suspend()

    assert mailbox.is_suspended() == True

    # Single resume should work
    mailbox.resume()
    assert mailbox.is_suspended() == False


@pytest.mark.asyncio
async def test_array_mailbox_concurrent_sends(stage):
    """Test handling of concurrent message sends."""
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    # Send many messages concurrently
    tasks = []
    for _ in range(20):
        tasks.append(counter.increment())

    await asyncio.gather(*tasks)
    await asyncio.sleep(0.2)

    # All should be processed
    value = await counter.get_value()
    assert value == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
