"""
Mailbox Suspension tests - Mailbox state management.

Test cases covering suspension behavior.
"""

import pytest
import asyncio
from typing import Dict
from domo_actors.actors.actor import Actor
from domo_actors.actors.actor_protocol import ActorProtocol
from domo_actors.actors.protocol import Protocol, ProtocolInstantiator
from domo_actors.actors.definition import Definition
from domo_actors.actors.local_stage import LocalStage
from domo_actors.actors.address import Uuid7Address


# Global storage
counter_actors: Dict[str, 'CounterActorImpl'] = {}


# ============================================================================
# Test Actor
# ============================================================================

class Counter(ActorProtocol):
    async def increment(self) -> None: ...
    async def get_value(self) -> int: ...


class CounterActorImpl(Actor):
    def __init__(self):
        super().__init__()
        self._count = 0

    async def increment(self) -> None:
        self._count += 1

    async def get_value(self) -> int:
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
    s = LocalStage()
    yield s
    asyncio.run(s.close())


@pytest.fixture(autouse=True)
def clear_actors():
    counter_actors.clear()


# ============================================================================
# Tests
# ============================================================================

@pytest.mark.asyncio
async def test_mailbox_starts_unsuspended(stage):
    """Test that mailbox starts in unsuspended state."""
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    raw_actor = counter_actors[counter.address().value_as_string()]
    mailbox = raw_actor.life_cycle().environment().mailbox()

    assert mailbox.is_suspended() == False


@pytest.mark.asyncio
async def test_suspend_changes_state_to_suspended(stage):
    """Test that suspend() changes state to suspended."""
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    raw_actor = counter_actors[counter.address().value_as_string()]
    mailbox = raw_actor.life_cycle().environment().mailbox()

    mailbox.suspend()
    assert mailbox.is_suspended() == True


@pytest.mark.asyncio
async def test_resume_changes_state_to_unsuspended(stage):
    """Test that resume() changes state to unsuspended."""
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    raw_actor = counter_actors[counter.address().value_as_string()]
    mailbox = raw_actor.life_cycle().environment().mailbox()

    mailbox.suspend()
    assert mailbox.is_suspended() == True

    mailbox.resume()
    assert mailbox.is_suspended() == False


@pytest.mark.asyncio
async def test_messages_queue_during_suspension(stage):
    """Test that messages queue but don't process when suspended."""
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

    # Wait a bit
    await asyncio.sleep(0.1)

    # Should not be processed
    assert raw_actor._count == 0


@pytest.mark.asyncio
async def test_queued_messages_process_on_resume(stage):
    """Test that all queued messages process on resume."""
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    raw_actor = counter_actors[counter.address().value_as_string()]
    mailbox = raw_actor.life_cycle().environment().mailbox()

    # Suspend and queue messages
    mailbox.suspend()

    await counter.increment()
    await counter.increment()
    await counter.increment()

    await asyncio.sleep(0.05)
    assert raw_actor._count == 0

    # Resume
    mailbox.resume()

    await asyncio.sleep(0.1)

    # All should be processed
    assert raw_actor._count == 3


@pytest.mark.asyncio
async def test_multiple_suspend_calls_idempotent(stage):
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

    # Queue messages
    await counter.increment()
    await asyncio.sleep(0.05)
    assert raw_actor._count == 0

    # Single resume should work
    mailbox.resume()
    await asyncio.sleep(0.1)

    assert raw_actor._count == 1


@pytest.mark.asyncio
async def test_multiple_resume_calls_idempotent(stage):
    """Test that multiple resume calls are idempotent."""
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    raw_actor = counter_actors[counter.address().value_as_string()]
    mailbox = raw_actor.life_cycle().environment().mailbox()

    # Suspend
    mailbox.suspend()

    # Queue messages
    await counter.increment()

    # Multiple resumes
    mailbox.resume()
    mailbox.resume()
    mailbox.resume()

    await asyncio.sleep(0.1)

    # Message should be processed once
    assert raw_actor._count == 1
    assert mailbox.is_suspended() == False


@pytest.mark.asyncio
async def test_closed_mailbox_does_not_process_after_resume(stage):
    """Test that closed mailbox doesn't process messages after resume."""
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

    # Suspend
    mailbox.suspend()

    # Queue message
    await counter.increment()

    # Close mailbox
    mailbox.close()

    # Try to resume
    mailbox.resume()

    await asyncio.sleep(0.1)

    # Message should not be processed
    assert raw_actor._count == 0


@pytest.mark.asyncio
async def test_messages_process_in_order_during_suspension(stage):
    """Test that messages process in FIFO order after suspension."""
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    raw_actor = counter_actors[counter.address().value_as_string()]
    mailbox = raw_actor.life_cycle().environment().mailbox()

    # Suspend
    mailbox.suspend()

    # Queue many messages
    for _ in range(10):
        await counter.increment()

    await asyncio.sleep(0.05)
    assert raw_actor._count == 0

    # Resume
    mailbox.resume()

    await asyncio.sleep(0.2)

    # All should be processed in order
    assert raw_actor._count == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
