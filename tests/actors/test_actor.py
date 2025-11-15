"""
Actor tests - Core actor protocol testing.

Test cases covering actor protocol, lifecycle, and parent-child relationships.
"""

import pytest
import asyncio
from typing import Optional, Dict
from domo_actors.actors.actor import Actor
from domo_actors.actors.actor_protocol import ActorProtocol
from domo_actors.actors.protocol import Protocol, ProtocolInstantiator
from domo_actors.actors.definition import Definition
from domo_actors.actors.local_stage import LocalStage
from domo_actors.actors.address import Uuid7Address


# Global storage for test actors
named_actors: Dict[str, 'NamedActorImpl'] = {}
stateful_actors: Dict[str, 'StatefulActorImpl'] = {}
child_actors: Dict[str, 'ChildActorImpl'] = {}


# ============================================================================
# Test Protocols and Implementations
# ============================================================================

class Named(ActorProtocol):
    """Simple actor with name storage."""
    async def set_name(self, name: str) -> None: ...
    async def name(self) -> str: ...


class NamedActorImpl(Actor):
    """Named actor implementation."""

    def __init__(self):
        super().__init__()
        self._name: str = ""

    async def set_name(self, name: str) -> None:
        self._name = name

    async def name(self) -> str:
        return self._name


class NamedInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        actor = NamedActorImpl()
        named_actors[definition.address().value_as_string()] = actor
        return actor


class NamedProtocol(Protocol):
    def type(self) -> str:
        return "Named"

    def instantiator(self) -> ProtocolInstantiator:
        return NamedInstantiator()


# ============================================================================
# Stateful Actor for State Management Tests
# ============================================================================

class Stateful(ActorProtocol):
    """Actor with state snapshot."""
    async def get_state(self) -> str: ...
    async def set_state(self, state: str) -> None: ...


class StatefulActorImpl(Actor):
    """Stateful actor implementation."""

    def __init__(self):
        super().__init__()
        self._state: str = ""

    async def get_state(self) -> str:
        return self._state

    async def set_state(self, state: str) -> None:
        self._state = state


class StatefulInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        actor = StatefulActorImpl()
        stateful_actors[definition.address().value_as_string()] = actor
        return actor


class StatefulProtocol(Protocol):
    def type(self) -> str:
        return "Stateful"

    def instantiator(self) -> ProtocolInstantiator:
        return StatefulInstantiator()


# ============================================================================
# Child Actor for Parent-Child Tests
# ============================================================================

class Child(ActorProtocol):
    """Child actor with constructor parameters."""
    async def get_param(self) -> str: ...
    async def get_default_param(self) -> str: ...


class ChildActorImpl(Actor):
    """Child actor implementation."""

    def __init__(self, param: str, default_param: str = "default"):
        super().__init__()
        self._param = param
        self._default_param = default_param

    async def get_param(self) -> str:
        return self._param

    async def get_default_param(self) -> str:
        return self._default_param


class ChildInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        params = definition.parameters()
        actor = ChildActorImpl(*params)
        child_actors[definition.address().value_as_string()] = actor
        return actor


class ChildProtocol(Protocol):
    def type(self) -> str:
        return "Child"

    def instantiator(self) -> ProtocolInstantiator:
        return ChildInstantiator()


# ============================================================================
# Tests
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
    named_actors.clear()
    stateful_actors.clear()
    child_actors.clear()


# Test Group 1: Actor Protocol - Operational Methods
# ============================================================================

@pytest.mark.asyncio
async def test_actor_creation_and_retrieval(stage):
    """Test actor creation and raw actor retrieval."""
    named: Named = stage.actor_for(NamedProtocol(), Definition("Named", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    # Verify actor was stored
    raw_actor = named_actors.get(named.address().value_as_string())
    assert raw_actor is not None
    assert isinstance(raw_actor, NamedActorImpl)


@pytest.mark.asyncio
async def test_unique_addresses(stage):
    """Test that each actor gets a unique address."""
    named1: Named = stage.actor_for(NamedProtocol(), Definition("Named1", Uuid7Address(), ()))
    named2: Named = stage.actor_for(NamedProtocol(), Definition("Named2", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    assert named1.address() != named2.address()
    assert hash(named1.address()) != hash(named2.address())


@pytest.mark.asyncio
async def test_synchronous_stage_access(stage):
    """Test synchronous access to stage through proxy."""
    named: Named = stage.actor_for(NamedProtocol(), Definition("Named", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    # These should be synchronous (no await needed)
    actor_stage = named.stage()
    assert actor_stage is stage


@pytest.mark.asyncio
async def test_synchronous_address_access(stage):
    """Test synchronous access to address through proxy."""
    named: Named = stage.actor_for(NamedProtocol(), Definition("Named", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    # Synchronous access
    address = named.address()
    assert address is not None
    assert address.value_as_string() != ""


@pytest.mark.asyncio
async def test_synchronous_is_stopped_access(stage):
    """Test synchronous access to isStopped through proxy."""
    named: Named = stage.actor_for(NamedProtocol(), Definition("Named", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    # Synchronous access
    assert named.is_stopped() == False


@pytest.mark.asyncio
async def test_logger_scheduler_dead_letters_access(stage):
    """Test access to logger, scheduler, and dead letters through proxy."""
    named: Named = stage.actor_for(NamedProtocol(), Definition("Named", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    # Synchronous access to system services
    logger = named.logger()
    dead_letters = named.dead_letters()

    assert logger is not None
    assert dead_letters is not None


# Test Group 2: Actor Protocol - State Management
# ============================================================================

@pytest.mark.asyncio
async def test_state_persistence(stage):
    """Test that state persists across message calls."""
    named: Named = stage.actor_for(NamedProtocol(), Definition("Named", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    await named.set_name("Alice")

    name1 = await named.name()
    name2 = await named.name()

    assert name1 == "Alice"
    assert name2 == "Alice"
    assert name1 == name2


@pytest.mark.asyncio
async def test_state_isolation(stage):
    """Test that each actor has isolated state."""
    named1: Named = stage.actor_for(NamedProtocol(), Definition("Named1", Uuid7Address(), ()))
    named2: Named = stage.actor_for(NamedProtocol(), Definition("Named2", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    await named1.set_name("Alice")
    await named2.set_name("Bob")

    assert await named1.name() == "Alice"
    assert await named2.name() == "Bob"


# Test Group 3: Actor Protocol - Lifecycle Methods
# ============================================================================

@pytest.mark.asyncio
async def test_not_stopped_on_creation(stage):
    """Test that actors are not stopped when created."""
    named: Named = stage.actor_for(NamedProtocol(), Definition("Named", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    assert named.is_stopped() == False


@pytest.mark.asyncio
async def test_stop_changes_state(stage):
    """Test that stop() changes stopped state."""
    named: Named = stage.actor_for(NamedProtocol(), Definition("Named", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    assert named.is_stopped() == False

    # Stop returns a coroutine
    await named.stop()
    await asyncio.sleep(0.05)

    assert named.is_stopped() == True


@pytest.mark.asyncio
async def test_messages_rejected_after_stop(stage):
    """Test that messages are rejected after actor stops."""
    from domo_actors.actors.testkit.test_dead_letters_listener import TestDeadLettersListener

    # Register dead letter listener
    listener = TestDeadLettersListener()
    stage.dead_letters().register_listener(listener)

    named: Named = stage.actor_for(NamedProtocol(), Definition("Named", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    await named.stop()
    await asyncio.sleep(0.05)

    # Try to send message after stop
    await named.set_name("Alice")
    await asyncio.sleep(0.05)

    # Should go to dead letters
    assert listener.count() > 0


# Test Group 4: Actor Protocol - Parent/Child Relationships
# ============================================================================

@pytest.mark.asyncio
async def test_child_creation_with_parameters(stage):
    """Test creating child actor with constructor parameters."""
    parent: Named = stage.actor_for(NamedProtocol(), Definition("Parent", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    # Access raw actor to create child
    raw_parent = named_actors[parent.address().value_as_string()]

    child: Child = raw_parent.child_actor_for(
        ChildProtocol(),
        Definition("Child", Uuid7Address(), ("test_param",))
    )

    await asyncio.sleep(0.05)

    param = await child.get_param()
    assert param == "test_param"


@pytest.mark.asyncio
async def test_parent_child_relationship(stage):
    """Test parent-child relationship verification."""
    parent: Named = stage.actor_for(NamedProtocol(), Definition("Parent", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    raw_parent = named_actors[parent.address().value_as_string()]

    child: Child = raw_parent.child_actor_for(
        ChildProtocol(),
        Definition("Child", Uuid7Address(), ("test",))
    )

    await asyncio.sleep(0.05)

    # Access raw child to check parent
    raw_child = child_actors[child.address().value_as_string()]
    child_parent = raw_child.parent()

    # Parent should match
    assert child_parent is not None
    assert child_parent.address() == parent.address()


@pytest.mark.asyncio
async def test_multiple_children(stage):
    """Test creating multiple children from same parent."""
    parent: Named = stage.actor_for(NamedProtocol(), Definition("Parent", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    raw_parent = named_actors[parent.address().value_as_string()]

    child1: Child = raw_parent.child_actor_for(
        ChildProtocol(),
        Definition("Child1", Uuid7Address(), ("param1",))
    )

    child2: Child = raw_parent.child_actor_for(
        ChildProtocol(),
        Definition("Child2", Uuid7Address(), ("param2",))
    )

    await asyncio.sleep(0.05)

    assert await child1.get_param() == "param1"
    assert await child2.get_param() == "param2"
    assert child1.address() != child2.address()


@pytest.mark.asyncio
async def test_child_default_parameters(stage):
    """Test that child actors handle default parameters."""
    parent: Named = stage.actor_for(NamedProtocol(), Definition("Parent", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    raw_parent = named_actors[parent.address().value_as_string()]

    child: Child = raw_parent.child_actor_for(
        ChildProtocol(),
        Definition("Child", Uuid7Address(), ("required",))
    )

    await asyncio.sleep(0.05)

    assert await child.get_param() == "required"
    assert await child.get_default_param() == "default"


# Test Group 5: Actor Protocol - Object Methods
# ============================================================================

@pytest.mark.asyncio
async def test_equality_by_address(stage):
    """Test that actors are equal if addresses match."""
    named1: Named = stage.actor_for(NamedProtocol(), Definition("Named", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    # Same actor through proxy should be equal
    raw_actor = named_actors[named1.address().value_as_string()]

    # Equality based on address
    assert named1.address() == raw_actor.address()


@pytest.mark.asyncio
async def test_hash_code_consistency(stage):
    """Test that hash codes are consistent."""
    named: Named = stage.actor_for(NamedProtocol(), Definition("Named", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    hash1 = hash(named)
    hash2 = hash(named)

    assert hash1 == hash2


@pytest.mark.asyncio
async def test_string_representation(stage):
    """Test string representation shows type."""
    named: Named = stage.actor_for(NamedProtocol(), Definition("Named", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    string_rep = str(named)

    # Should contain type name
    assert "Named" in string_rep or "ActorProxy" in string_rep


@pytest.mark.asyncio
async def test_hash_code_different_actors(stage):
    """Test that different actors have different hash codes."""
    named1: Named = stage.actor_for(NamedProtocol(), Definition("Named1", Uuid7Address(), ()))
    named2: Named = stage.actor_for(NamedProtocol(), Definition("Named2", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    # Different actors should have different hashes (based on address)
    assert hash(named1) != hash(named2)


# Test Group 6: Actor Protocol - Message Processing
# ============================================================================

@pytest.mark.asyncio
async def test_fifo_message_ordering(stage):
    """Test that messages are processed in FIFO order."""
    named: Named = stage.actor_for(NamedProtocol(), Definition("Named", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    # Send multiple messages
    await named.set_name("First")
    await named.set_name("Second")
    await named.set_name("Third")

    # Final value should be last message
    assert await named.name() == "Third"


@pytest.mark.asyncio
async def test_async_operation_handling(stage):
    """Test handling of async operations."""
    named: Named = stage.actor_for(NamedProtocol(), Definition("Named", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    # Set name and immediately retrieve
    await named.set_name("AsyncTest")
    result = await named.name()

    assert result == "AsyncTest"


@pytest.mark.asyncio
async def test_concurrent_message_sends(stage):
    """Test concurrent message sends maintain state consistency."""
    named: Named = stage.actor_for(NamedProtocol(), Definition("Named", Uuid7Address(), ()))

    await asyncio.sleep(0.05)

    # Send messages concurrently (but they'll be processed sequentially)
    await asyncio.gather(
        named.set_name("First"),
        named.set_name("Second"),
        named.set_name("Third")
    )

    # Last one wins (order may vary with gather)
    result = await named.name()
    assert result in ["First", "Second", "Third"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
