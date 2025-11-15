"""
State Snapshot tests - Actor state persistence pattern.

Test cases covering state snapshot storage and retrieval.
"""

import pytest
import asyncio
import time
from typing import Dict, Optional
from domo_actors.actors.actor import Actor
from domo_actors.actors.actor_protocol import ActorProtocol
from domo_actors.actors.protocol import Protocol, ProtocolInstantiator
from domo_actors.actors.definition import Definition
from domo_actors.actors.local_stage import LocalStage
from domo_actors.actors.address import Uuid7Address


# ============================================================================
# Stateful Actor (Custom Implementation)
# ============================================================================

class Stateful(ActorProtocol):
    """Stateful actor protocol."""
    async def set_value(self, value: str) -> None: ...
    async def get_value(self) -> str: ...
    async def save_snapshot(self) -> None: ...
    async def restore_snapshot(self) -> None: ...


class StatefulSnapshot:
    """Snapshot data structure."""
    def __init__(self, value: str, timestamp: float):
        self.value = value
        self.timestamp = timestamp


class StatefulActor(Actor):
    """Actor with custom state snapshot implementation."""

    def __init__(self):
        super().__init__()
        self._value = ""
        self._snapshot: Optional[StatefulSnapshot] = None

    async def set_value(self, value: str) -> None:
        self._value = value

    async def get_value(self) -> str:
        return self._value

    async def save_snapshot(self) -> None:
        snapshot = StatefulSnapshot(self._value, time.time())
        self.state_snapshot(snapshot)

    async def restore_snapshot(self) -> None:
        snapshot = self.state_snapshot()
        if snapshot:
            self._value = snapshot.value

    def state_snapshot(self, snapshot: Optional[StatefulSnapshot] = None) -> Optional[StatefulSnapshot]:
        """Override stateSnapshot to store/retrieve snapshots."""
        if snapshot is not None:
            self._snapshot = snapshot
            return None
        return self._snapshot


stateful_actors: Dict[str, StatefulActor] = {}


class StatefulInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        actor = StatefulActor()
        stateful_actors[definition.address().value_as_string()] = actor
        return actor


class StatefulProtocol(Protocol):
    def type(self) -> str:
        return "Stateful"

    def instantiator(self) -> ProtocolInstantiator:
        return StatefulInstantiator()


# ============================================================================
# Simple Actor (Default Implementation)
# ============================================================================

class Simple(ActorProtocol):
    """Simple actor protocol."""
    async def do_something(self) -> None: ...


class SimpleActor(Actor):
    """Actor with default state snapshot behavior."""

    def __init__(self):
        super().__init__()

    async def do_something(self) -> None:
        pass


simple_actors: Dict[str, SimpleActor] = {}


class SimpleInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        actor = SimpleActor()
        simple_actors[definition.address().value_as_string()] = actor
        return actor


class SimpleProtocol(Protocol):
    def type(self) -> str:
        return "Simple"

    def instantiator(self) -> ProtocolInstantiator:
        return SimpleInstantiator()


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
    """Clear actor maps before each test."""
    stateful_actors.clear()
    simple_actors.clear()


# ============================================================================
# Tests - Custom stateSnapshot Implementation
# ============================================================================

@pytest.mark.asyncio
async def test_store_and_retrieve_state_snapshot(stage):
    """Test storing and retrieving state snapshot."""
    proxy: Stateful = stage.actor_for(
        StatefulProtocol(),
        Definition("Stateful", Uuid7Address(), ())
    )

    # Set a value
    await proxy.set_value("test-value")

    # Save snapshot
    await proxy.save_snapshot()

    await asyncio.sleep(0.02)

    # Get the underlying actor to access state_snapshot directly
    actor = stateful_actors[proxy.address().value_as_string()]

    # Retrieve snapshot and verify
    snapshot = actor.state_snapshot()
    assert snapshot is not None
    assert snapshot.value == "test-value"
    assert snapshot.timestamp > 0


@pytest.mark.asyncio
async def test_restore_state_from_snapshot(stage):
    """Test restoring state from snapshot."""
    proxy: Stateful = stage.actor_for(
        StatefulProtocol(),
        Definition("Stateful", Uuid7Address(), ())
    )

    # Set initial value and save snapshot
    await proxy.set_value("initial")
    await proxy.save_snapshot()
    await asyncio.sleep(0.02)

    # Change the value
    await proxy.set_value("changed")
    value = await proxy.get_value()
    assert value == "changed"

    # Restore from snapshot
    await proxy.restore_snapshot()
    await asyncio.sleep(0.02)

    value = await proxy.get_value()
    assert value == "initial"


@pytest.mark.asyncio
async def test_update_snapshot_when_saved_multiple_times(stage):
    """Test that snapshot updates on multiple saves."""
    proxy: Stateful = stage.actor_for(
        StatefulProtocol(),
        Definition("Stateful", Uuid7Address(), ())
    )

    actor = stateful_actors[proxy.address().value_as_string()]

    # First snapshot
    await proxy.set_value("first")
    await proxy.save_snapshot()
    await asyncio.sleep(0.02)

    snapshot1 = actor.state_snapshot()
    assert snapshot1.value == "first"
    timestamp1 = snapshot1.timestamp

    # Wait a bit to ensure different timestamp
    await asyncio.sleep(0.01)

    # Second snapshot
    await proxy.set_value("second")
    await proxy.save_snapshot()
    await asyncio.sleep(0.02)

    snapshot2 = actor.state_snapshot()
    assert snapshot2.value == "second"
    assert snapshot2.timestamp > timestamp1


@pytest.mark.asyncio
async def test_return_none_before_any_snapshot_saved(stage):
    """Test that state_snapshot returns None initially."""
    proxy: Stateful = stage.actor_for(
        StatefulProtocol(),
        Definition("Stateful", Uuid7Address(), ())
    )

    await asyncio.sleep(0.01)

    actor = stateful_actors[proxy.address().value_as_string()]

    # No snapshot saved yet
    snapshot = actor.state_snapshot()
    assert snapshot is None


@pytest.mark.asyncio
async def test_preserve_snapshot_after_state_changes(stage):
    """Test that snapshot is preserved after state changes."""
    proxy: Stateful = stage.actor_for(
        StatefulProtocol(),
        Definition("Stateful", Uuid7Address(), ())
    )

    actor = stateful_actors[proxy.address().value_as_string()]

    # Save snapshot
    await proxy.set_value("snapshot-value")
    await proxy.save_snapshot()
    await asyncio.sleep(0.02)

    # Change state without saving
    await proxy.set_value("new-value")
    await asyncio.sleep(0.02)

    # Snapshot should still have old value
    snapshot = actor.state_snapshot()
    assert snapshot.value == "snapshot-value"

    # But current value is different
    current_value = await proxy.get_value()
    assert current_value == "new-value"


# ============================================================================
# Tests - Default stateSnapshot Behavior
# ============================================================================

@pytest.mark.asyncio
async def test_return_none_for_actors_without_custom_implementation(stage):
    """Test default implementation returns None."""
    proxy: Simple = stage.actor_for(
        SimpleProtocol(),
        Definition("Simple", Uuid7Address(), ())
    )

    await asyncio.sleep(0.01)

    actor = simple_actors[proxy.address().value_as_string()]

    # Default implementation returns None
    snapshot = actor.state_snapshot()
    assert snapshot is None


@pytest.mark.asyncio
async def test_not_throw_when_setting_snapshot_on_default_implementation(stage):
    """Test that default implementation doesn't throw on setter."""
    proxy: Simple = stage.actor_for(
        SimpleProtocol(),
        Definition("Simple", Uuid7Address(), ())
    )

    await asyncio.sleep(0.01)

    actor = simple_actors[proxy.address().value_as_string()]

    # Default implementation is a no-op for setter
    try:
        actor.state_snapshot({"some": "data"})
    except Exception as e:
        pytest.fail(f"Setting snapshot should not throw: {e}")

    # But getter still returns None
    snapshot = actor.state_snapshot()
    assert snapshot is None


# ============================================================================
# Tests - Snapshot Isolation Between Actors
# ============================================================================

@pytest.mark.asyncio
async def test_maintain_separate_snapshots_for_different_actors(stage):
    """Test that snapshots are isolated between actors."""
    proxy1: Stateful = stage.actor_for(
        StatefulProtocol(),
        Definition("Stateful1", Uuid7Address(), ())
    )
    proxy2: Stateful = stage.actor_for(
        StatefulProtocol(),
        Definition("Stateful2", Uuid7Address(), ())
    )

    actor1 = stateful_actors[proxy1.address().value_as_string()]
    actor2 = stateful_actors[proxy2.address().value_as_string()]

    # Set different values and save snapshots
    await proxy1.set_value("actor1-value")
    await proxy1.save_snapshot()

    await proxy2.set_value("actor2-value")
    await proxy2.save_snapshot()

    await asyncio.sleep(0.02)

    # Verify snapshots are isolated
    snapshot1 = actor1.state_snapshot()
    snapshot2 = actor2.state_snapshot()

    assert snapshot1.value == "actor1-value"
    assert snapshot2.value == "actor2-value"


@pytest.mark.asyncio
async def test_not_share_snapshot_state_between_actor_instances(stage):
    """Test that snapshot state is not shared between instances."""
    proxy1: Stateful = stage.actor_for(
        StatefulProtocol(),
        Definition("Stateful1", Uuid7Address(), ())
    )
    proxy2: Stateful = stage.actor_for(
        StatefulProtocol(),
        Definition("Stateful2", Uuid7Address(), ())
    )

    actor1 = stateful_actors[proxy1.address().value_as_string()]
    actor2 = stateful_actors[proxy2.address().value_as_string()]

    # Save snapshot only for actor1
    await proxy1.set_value("has-snapshot")
    await proxy1.save_snapshot()

    await asyncio.sleep(0.02)

    # Actor2 should not have a snapshot
    snapshot1 = actor1.state_snapshot()
    snapshot2 = actor2.state_snapshot()

    assert snapshot1 is not None
    assert snapshot2 is None


# ============================================================================
# Tests - Complex Snapshot Scenarios
# ============================================================================

@pytest.mark.asyncio
async def test_handle_multiple_save_and_restore_cycles(stage):
    """Test multiple save and restore cycles."""
    proxy: Stateful = stage.actor_for(
        StatefulProtocol(),
        Definition("Stateful", Uuid7Address(), ())
    )

    # Cycle 1
    await proxy.set_value("v1")
    await proxy.save_snapshot()
    await proxy.set_value("temp1")
    await proxy.restore_snapshot()
    await asyncio.sleep(0.02)

    assert await proxy.get_value() == "v1"

    # Cycle 2
    await proxy.set_value("v2")
    await proxy.save_snapshot()
    await proxy.set_value("temp2")
    await proxy.restore_snapshot()
    await asyncio.sleep(0.02)

    assert await proxy.get_value() == "v2"


@pytest.mark.asyncio
async def test_restore_from_latest_snapshot_after_multiple_saves(stage):
    """Test that restore uses latest snapshot."""
    proxy: Stateful = stage.actor_for(
        StatefulProtocol(),
        Definition("Stateful", Uuid7Address(), ())
    )

    # Multiple snapshots - only latest should be kept
    await proxy.set_value("v1")
    await proxy.save_snapshot()

    await proxy.set_value("v2")
    await proxy.save_snapshot()

    await proxy.set_value("v3")
    await proxy.save_snapshot()

    await asyncio.sleep(0.02)

    # Restore should use latest (v3)
    await proxy.set_value("current")
    await proxy.restore_snapshot()
    await asyncio.sleep(0.02)

    assert await proxy.get_value() == "v3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
