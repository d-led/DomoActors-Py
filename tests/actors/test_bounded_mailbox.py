"""
Bounded Mailbox tests - Message queue capacity and overflow policies.

Test cases covering capacity, overflow policies, and integration.
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
from domo_actors.actors.bounded_mailbox import BoundedMailbox
from domo_actors.actors.mailbox import OverflowPolicy
from domo_actors.actors.testkit.test_dead_letters_listener import TestDeadLettersListener


# Global storage for test actors
slow_actors: Dict[str, 'SlowActorImpl'] = {}


# ============================================================================
# Test Actor - Slow Processing Actor
# ============================================================================

class SlowActor(ActorProtocol):
    """Actor that processes messages slowly for queue testing."""
    async def process_message(self, value: int) -> None: ...
    async def get_processed_count(self) -> int: ...
    async def get_processed_values(self) -> List[int]: ...


class SlowActorImpl(Actor):
    """Slow actor implementation."""

    def __init__(self, delay_ms: int = 50):
        super().__init__()
        self._delay_ms = delay_ms
        self._processed_values: List[int] = []

    async def process_message(self, value: int) -> None:
        # Slow processing to allow queue buildup
        await asyncio.sleep(self._delay_ms / 1000.0)
        self._processed_values.append(value)

    async def get_processed_count(self) -> int:
        return len(self._processed_values)

    async def get_processed_values(self) -> List[int]:
        return self._processed_values.copy()


class SlowActorInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        params = definition.parameters()
        delay = params[0] if params else 50
        actor = SlowActorImpl(delay)
        slow_actors[definition.address().value_as_string()] = actor
        return actor


class SlowActorProtocol(Protocol):
    def type(self) -> str:
        return "SlowActor"

    def instantiator(self) -> ProtocolInstantiator:
        return SlowActorInstantiator()


# ============================================================================
# Helper Functions
# ============================================================================

def create_bounded_mailbox_actor(
    stage: LocalStage,
    capacity: int,
    policy: OverflowPolicy,
    delay_ms: int = 50
):
    """Create an actor with a bounded mailbox."""
    mailbox = BoundedMailbox(capacity, policy)
    address = Uuid7Address()
    definition = Definition("SlowActor", address, (delay_ms,))

    # Create actor with custom mailbox
    # We need to create the actor manually with the custom mailbox
    instantiator = SlowActorProtocol().instantiator()
    actor = instantiator.instantiate(definition)

    # Set up environment
    from domo_actors.actors.environment import Environment
    environment = Environment(
        address=address,
        definition=definition,
        mailbox=mailbox,
        parent=None,
        stage=stage,
        logger=stage.logger(),
        supervisor=None
    )
    actor.set_environment(environment)

    # Create proxy
    from domo_actors.actors.actor_proxy import create_actor_proxy
    proxy = create_actor_proxy(actor, mailbox)

    # Register and start
    stage.directory().register(address, proxy)
    asyncio.create_task(actor.start())

    return proxy, mailbox


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
    """Clear global actor storage before each test."""
    slow_actors.clear()


# ============================================================================
# Tests
# ============================================================================

# Test Group 1: Constructor and Basic Properties
# ============================================================================

@pytest.mark.asyncio
async def test_mailbox_capacity(stage):
    """Test that mailbox has correct capacity."""
    mailbox = BoundedMailbox(capacity=10, overflow_policy=OverflowPolicy.DROP_OLDEST)

    assert mailbox.capacity() == 10
    assert mailbox.size() == 0
    assert mailbox.is_full() == False


@pytest.mark.asyncio
async def test_mailbox_capacity_validation():
    """Test that mailbox validates capacity."""
    # Should work with valid capacity
    mailbox = BoundedMailbox(capacity=1, overflow_policy=OverflowPolicy.DROP_OLDEST)
    assert mailbox.capacity() == 1

    # Zero capacity should still work (though not practical)
    mailbox2 = BoundedMailbox(capacity=0, overflow_policy=OverflowPolicy.REJECT)
    assert mailbox2.capacity() == 0


# Test Group 2: DropOldest Policy
# ============================================================================

@pytest.mark.asyncio
async def test_drop_oldest_normal_processing(stage):
    """Test normal processing under capacity."""
    proxy, mailbox = create_bounded_mailbox_actor(
        stage, capacity=5, policy=OverflowPolicy.DROP_OLDEST
    )

    await asyncio.sleep(0.05)

    # Send 3 messages (under capacity)
    await proxy.process_message(1)
    await proxy.process_message(2)
    await proxy.process_message(3)

    # Wait for processing
    await asyncio.sleep(0.3)

    values = await proxy.get_processed_values()
    assert values == [1, 2, 3]
    assert mailbox.dropped_message_count() == 0


@pytest.mark.asyncio
async def test_drop_oldest_overflow(stage):
    """Test dropping oldest messages when at capacity."""
    proxy, mailbox = create_bounded_mailbox_actor(
        stage, capacity=3, policy=OverflowPolicy.DROP_OLDEST, delay_ms=100
    )

    await asyncio.sleep(0.05)

    # Suspend to build up queue
    mailbox.suspend()

    # Send 5 messages (exceeds capacity of 3)
    await proxy.process_message(1)
    await proxy.process_message(2)
    await proxy.process_message(3)
    await proxy.process_message(4)
    await proxy.process_message(5)

    await asyncio.sleep(0.05)

    # Should have dropped 2 oldest
    assert mailbox.dropped_message_count() == 2

    # Resume and process
    mailbox.resume()
    await asyncio.sleep(0.5)

    values = await proxy.get_processed_values()
    # Should have [3, 4, 5] (dropped 1 and 2)
    assert values == [3, 4, 5]


@pytest.mark.asyncio
async def test_drop_oldest_tracking(stage):
    """Test accurate tracking of dropped messages."""
    proxy, mailbox = create_bounded_mailbox_actor(
        stage, capacity=2, policy=OverflowPolicy.DROP_OLDEST
    )

    await asyncio.sleep(0.05)

    mailbox.suspend()

    # Send 10 messages with capacity 2
    for i in range(10):
        await proxy.process_message(i)

    await asyncio.sleep(0.05)

    # Should have dropped 8 messages
    assert mailbox.dropped_message_count() == 8

    mailbox.resume()
    await asyncio.sleep(0.3)

    values = await proxy.get_processed_values()
    # Should have last 2: [8, 9]
    assert values == [8, 9]


# Test Group 3: DropNewest Policy
# ============================================================================

@pytest.mark.asyncio
async def test_drop_newest_overflow(stage):
    """Test dropping newest messages when at capacity."""
    proxy, mailbox = create_bounded_mailbox_actor(
        stage, capacity=3, policy=OverflowPolicy.DROP_NEWEST, delay_ms=100
    )

    await asyncio.sleep(0.05)

    mailbox.suspend()

    # Send 5 messages (exceeds capacity of 3)
    await proxy.process_message(1)
    await proxy.process_message(2)
    await proxy.process_message(3)
    await proxy.process_message(4)  # Should be dropped
    await proxy.process_message(5)  # Should be dropped

    await asyncio.sleep(0.05)

    # Should have dropped 2 newest
    assert mailbox.dropped_message_count() == 2

    mailbox.resume()
    await asyncio.sleep(0.5)

    values = await proxy.get_processed_values()
    # Should have [1, 2, 3] (dropped 4 and 5)
    assert values == [1, 2, 3]


# Test Group 4: Reject Policy
# ============================================================================

@pytest.mark.asyncio
async def test_reject_overflow_to_dead_letters(stage):
    """Test that overflow messages go to dead letters with Reject policy."""
    listener = TestDeadLettersListener()
    stage.dead_letters().register_listener(listener)

    proxy, mailbox = create_bounded_mailbox_actor(
        stage, capacity=2, policy=OverflowPolicy.REJECT, delay_ms=100
    )

    await asyncio.sleep(0.05)

    mailbox.suspend()

    # Send 5 messages (exceeds capacity of 2)
    for i in range(5):
        await proxy.process_message(i)

    await asyncio.sleep(0.05)

    # Should have 3 messages in dead letters
    assert listener.count() >= 3
    assert mailbox.dropped_message_count() == 3

    mailbox.resume()
    await asyncio.sleep(0.3)

    values = await proxy.get_processed_values()
    # Should have first 2: [0, 1]
    assert values == [0, 1]


# Test Group 5: Suspension and Resumption
# ============================================================================

@pytest.mark.asyncio
async def test_suspension_and_resumption(stage):
    """Test mailbox suspension and resumption."""
    proxy, mailbox = create_bounded_mailbox_actor(
        stage, capacity=10, policy=OverflowPolicy.DROP_OLDEST
    )

    await asyncio.sleep(0.05)

    # Suspend mailbox
    mailbox.suspend()
    assert mailbox.is_suspended() == True

    # Send messages while suspended
    await proxy.process_message(1)
    await proxy.process_message(2)

    await asyncio.sleep(0.1)

    # Should not be processed yet
    count = await proxy.get_processed_count()
    assert count == 0

    # Resume
    mailbox.resume()
    assert mailbox.is_suspended() == False

    await asyncio.sleep(0.3)

    # Should be processed now
    values = await proxy.get_processed_values()
    assert values == [1, 2]


# Test Group 6: Size and Capacity Tracking
# ============================================================================

@pytest.mark.asyncio
async def test_size_tracking(stage):
    """Test that mailbox size is tracked correctly."""
    proxy, mailbox = create_bounded_mailbox_actor(
        stage, capacity=5, policy=OverflowPolicy.DROP_OLDEST, delay_ms=100
    )

    await asyncio.sleep(0.05)

    mailbox.suspend()

    # Send 3 messages
    await proxy.process_message(1)
    await proxy.process_message(2)
    await proxy.process_message(3)

    await asyncio.sleep(0.05)

    # Should have 3 in queue
    assert mailbox.size() == 3
    assert mailbox.is_full() == False

    mailbox.resume()
    await asyncio.sleep(0.4)

    # Should be empty after processing
    assert mailbox.size() == 0


@pytest.mark.asyncio
async def test_is_full_detection(stage):
    """Test that is_full() correctly detects capacity."""
    proxy, mailbox = create_bounded_mailbox_actor(
        stage, capacity=2, policy=OverflowPolicy.DROP_OLDEST
    )

    await asyncio.sleep(0.05)

    mailbox.suspend()

    await proxy.process_message(1)
    assert mailbox.is_full() == False

    await proxy.process_message(2)
    await asyncio.sleep(0.05)
    assert mailbox.is_full() == True

    mailbox.resume()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
