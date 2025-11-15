"""
Actor Selection tests - Actor lookup and discovery.

Test cases covering actor_of lookup functionality.
"""

import pytest
import asyncio
from typing import Optional
from domo_actors.actors.actor import Actor
from domo_actors.actors.actor_protocol import ActorProtocol
from domo_actors.actors.protocol import Protocol, ProtocolInstantiator
from domo_actors.actors.definition import Definition
from domo_actors.actors.local_stage import LocalStage
from domo_actors.actors.address import Uuid7Address


# ============================================================================
# Test Actor
# ============================================================================

class SimpleActor(ActorProtocol):
    """Simple actor for testing selection."""
    async def get_value(self) -> str: ...
    async def set_value(self, value: str) -> None: ...


class SimpleActorImpl(Actor):
    """Simple actor implementation."""

    def __init__(self):
        super().__init__()
        self._value = "initial"

    async def get_value(self) -> str:
        return self._value

    async def set_value(self, value: str) -> None:
        self._value = value


class SimpleActorInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        return SimpleActorImpl()


class SimpleActorProtocol(Protocol):
    def type(self) -> str:
        return "SimpleActor"

    def instantiator(self) -> ProtocolInstantiator:
        return SimpleActorInstantiator()


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def stage():
    s = LocalStage()
    yield s
    asyncio.run(s.close())


# ============================================================================
# Tests - actorOf Basic Lookup
# ============================================================================

@pytest.mark.asyncio
async def test_find_actor_by_address(stage):
    """Test that actorOf finds an actor by its address."""
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )
    address = actor.address()

    await asyncio.sleep(0.01)

    # Look up the actor by address
    found_actor = await stage.actor_of(address)

    assert found_actor is not None
    assert found_actor.address().equals(address) == True


@pytest.mark.asyncio
async def test_return_none_for_nonexistent_address(stage):
    """Test that actorOf returns None for non-existent address."""
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )

    await asyncio.sleep(0.01)

    # Create a different address (won't exist in directory)
    non_existent_address = Uuid7Address()

    found_actor = await stage.actor_of(non_existent_address)

    assert found_actor is None


@pytest.mark.asyncio
async def test_find_multiple_actors_by_addresses(stage):
    """Test that actorOf can find multiple actors."""
    actor1: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor1", Uuid7Address(), ())
    )
    actor2: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor2", Uuid7Address(), ())
    )
    actor3: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor3", Uuid7Address(), ())
    )

    address1 = actor1.address()
    address2 = actor2.address()
    address3 = actor3.address()

    await asyncio.sleep(0.01)

    # Look up all actors
    found1 = await stage.actor_of(address1)
    found2 = await stage.actor_of(address2)
    found3 = await stage.actor_of(address3)

    assert found1 is not None
    assert found2 is not None
    assert found3 is not None

    assert found1.address().equals(address1) == True
    assert found2.address().equals(address2) == True
    assert found3.address().equals(address3) == True


@pytest.mark.asyncio
async def test_return_same_proxy_for_same_address(stage):
    """Test that actorOf returns the same proxy instance."""
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )
    address = actor.address()

    await asyncio.sleep(0.01)

    # Look up the actor twice
    found1 = await stage.actor_of(address)
    found2 = await stage.actor_of(address)

    # Should be the exact same object reference
    assert found1 is found2


# ============================================================================
# Tests - actorOf Functional Proxy
# ============================================================================

@pytest.mark.asyncio
async def test_functional_proxy_receives_messages(stage):
    """Test that looked-up proxy can receive messages."""
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )
    address = actor.address()

    # Set a value through the original reference
    await actor.set_value("test-value")

    await asyncio.sleep(0.02)

    # Look up the actor and read the value
    found_actor = await stage.actor_of(address)
    assert found_actor is not None

    value = await found_actor.get_value()
    assert value == "test-value"


@pytest.mark.asyncio
async def test_send_messages_through_looked_up_proxy(stage):
    """Test sending messages through looked-up proxy."""
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )
    address = actor.address()

    await asyncio.sleep(0.01)

    # Look up the actor and send a message
    found_actor = await stage.actor_of(address)
    assert found_actor is not None

    await found_actor.set_value("new-value")
    await asyncio.sleep(0.02)

    # Verify through original reference
    value = await actor.get_value()
    assert value == "new-value"


# ============================================================================
# Tests - actorOf Lifecycle Integration
# ============================================================================

@pytest.mark.asyncio
async def test_not_find_stopped_actors(stage):
    """Test that stopped actors are not found."""
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )
    address = actor.address()

    await asyncio.sleep(0.01)

    # Verify actor can be found
    found1 = await stage.actor_of(address)
    assert found1 is not None

    # Stop the actor
    await actor.stop()
    assert actor.is_stopped() == True

    await asyncio.sleep(0.01)

    # Should no longer be in directory
    found2 = await stage.actor_of(address)
    assert found2 is None


@pytest.mark.asyncio
async def test_remove_child_actors_when_parent_stops(stage):
    """Test that child actors are removed when parent stops."""
    parent: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("Parent", Uuid7Address(), ())
    )

    await asyncio.sleep(0.01)

    # Create child through parent
    child: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("Child", Uuid7Address(), ()),
        parent=parent
    )

    parent_address = parent.address()
    child_address = child.address()

    await asyncio.sleep(0.01)

    # Both should be in directory
    found_parent = await stage.actor_of(parent_address)
    found_child = await stage.actor_of(child_address)
    assert found_parent is not None
    assert found_child is not None

    # Stop parent (should cascade to child)
    await parent.stop()

    await asyncio.sleep(0.02)

    # Neither should be in directory
    found_parent2 = await stage.actor_of(parent_address)
    found_child2 = await stage.actor_of(child_address)
    assert found_parent2 is None
    assert found_child2 is None


@pytest.mark.asyncio
async def test_handle_lookup_of_stopping_actor(stage):
    """Test lookup of actor that is stopping."""
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )
    address = actor.address()

    await asyncio.sleep(0.01)

    # Start stopping the actor (don't await)
    stop_task = asyncio.create_task(actor.stop())

    # Try to look up during stop (may or may not be found depending on timing)
    found = await stage.actor_of(address)
    # No assertion - timing dependent

    # Wait for stop to complete
    await stop_task
    await asyncio.sleep(0.01)

    # Should definitely not be found after stop completes
    found2 = await stage.actor_of(address)
    assert found2 is None


# ============================================================================
# Tests - actorOf Address Equality
# ============================================================================

@pytest.mark.asyncio
async def test_find_actor_using_address_from_proxy(stage):
    """Test finding actor using address from proxy."""
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )
    address = actor.address()

    await asyncio.sleep(0.01)

    # Look up using the address we got from the proxy
    found = await stage.actor_of(address)
    assert found is not None
    assert found.address().equals(address) == True


@pytest.mark.asyncio
async def test_use_address_value_as_string_for_lookup(stage):
    """Test that lookup uses address.value_as_string()."""
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )
    address = actor.address()
    address_string = address.value_as_string()

    await asyncio.sleep(0.01)

    # Look up the actor
    found = await stage.actor_of(address)
    assert found is not None

    # Verify the address string matches
    assert found.address().value_as_string() == address_string


# ============================================================================
# Tests - actorOf Concurrent Access
# ============================================================================

@pytest.mark.asyncio
async def test_concurrent_lookups_of_same_actor(stage):
    """Test concurrent lookups of the same actor."""
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )
    address = actor.address()

    await asyncio.sleep(0.01)

    # Perform multiple concurrent lookups
    lookups = await asyncio.gather(
        stage.actor_of(address),
        stage.actor_of(address),
        stage.actor_of(address),
        stage.actor_of(address),
        stage.actor_of(address)
    )

    # All should find the actor
    for found in lookups:
        assert found is not None
        assert found.address().equals(address) == True

    # All should be the same instance
    first = lookups[0]
    for found in lookups:
        assert found is first


@pytest.mark.asyncio
async def test_concurrent_creation_and_lookup(stage):
    """Test concurrent creation and lookup of actors."""
    # Create multiple actors concurrently
    actors = await asyncio.gather(
        asyncio.coroutine(lambda: stage.actor_for(
            SimpleActorProtocol(),
            Definition("SimpleActor1", Uuid7Address(), ())
        ))(),
        asyncio.coroutine(lambda: stage.actor_for(
            SimpleActorProtocol(),
            Definition("SimpleActor2", Uuid7Address(), ())
        ))(),
        asyncio.coroutine(lambda: stage.actor_for(
            SimpleActorProtocol(),
            Definition("SimpleActor3", Uuid7Address(), ())
        ))()
    )

    addresses = [a.address() for a in actors]

    await asyncio.sleep(0.01)

    # Look up all actors concurrently
    found = await asyncio.gather(
        *[stage.actor_of(addr) for addr in addresses]
    )

    # All should be found
    for i, f in enumerate(found):
        assert f is not None
        assert f.address().equals(addresses[i]) == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
