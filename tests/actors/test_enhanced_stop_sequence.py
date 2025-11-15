"""
Enhanced Stop Sequence tests - Detailed actor shutdown behavior.

Test cases covering beforeStop/afterStop hooks and child stopping coordination.
"""

import pytest
import asyncio
from typing import Dict, List
from domo_actors.actors.actor import Actor
from domo_actors.actors.actor_protocol import ActorProtocol
from domo_actors.actors.protocol import Protocol, ProtocolInstantiator
from domo_actors.actors.definition import Definition
from domo_actors.actors.local_stage import LocalStage
from domo_actors.actors.address import Uuid7Address


# ============================================================================
# Test Actors
# ============================================================================

class Trackable(ActorProtocol):
    """Trackable actor protocol."""
    async def do_something(self) -> None: ...


class TrackingActor(Actor):
    """Actor that tracks lifecycle hook calls."""

    def __init__(self):
        super().__init__()
        self._before_stop_called = False
        self._after_stop_called = False
        self._stop_order: List[str] = []

    async def before_stop(self) -> None:
        await super().before_stop()
        self._before_stop_called = True
        self._stop_order.append("beforeStop")

    async def after_stop(self) -> None:
        await super().after_stop()
        self._after_stop_called = True
        self._stop_order.append("afterStop")

    async def do_something(self) -> None:
        pass

    def was_before_stop_called(self) -> bool:
        return self._before_stop_called

    def was_after_stop_called(self) -> bool:
        return self._after_stop_called

    def get_stop_order(self) -> List[str]:
        return list(self._stop_order)


class BeforeStopErrorActor(Actor):
    """Actor that throws error in beforeStop."""

    def __init__(self):
        super().__init__()

    async def before_stop(self) -> None:
        raise ValueError("beforeStop failed intentionally")

    async def do_something(self) -> None:
        pass


class ParentActor(Actor):
    """Parent actor that tracks child stop ordering."""

    def __init__(self):
        super().__init__()
        self._stop_order: List[str] = []

    async def before_stop(self) -> None:
        await super().before_stop()
        self._stop_order.append("parent-beforeStop")

    async def after_stop(self) -> None:
        await super().after_stop()
        self._stop_order.append("parent-afterStop")

    async def do_something(self) -> None:
        pass

    def get_stop_order(self) -> List[str]:
        return list(self._stop_order)


# ============================================================================
# Global Storage
# ============================================================================

tracking_actors: Dict[str, TrackingActor] = {}
parent_actors: Dict[str, ParentActor] = {}


# ============================================================================
# Protocols
# ============================================================================

class TrackingInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        actor = TrackingActor()
        tracking_actors[definition.address().value_as_string()] = actor
        return actor


class TrackingProtocol(Protocol):
    def type(self) -> str:
        return "Tracking"

    def instantiator(self) -> ProtocolInstantiator:
        return TrackingInstantiator()


class BeforeStopErrorInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        return BeforeStopErrorActor()


class BeforeStopErrorProtocol(Protocol):
    def type(self) -> str:
        return "BeforeStopError"

    def instantiator(self) -> ProtocolInstantiator:
        return BeforeStopErrorInstantiator()


class ParentInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        actor = ParentActor()
        parent_actors[definition.address().value_as_string()] = actor
        return actor


class ParentProtocol(Protocol):
    def type(self) -> str:
        return "Parent"

    def instantiator(self) -> ProtocolInstantiator:
        return ParentInstantiator()


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
    tracking_actors.clear()
    parent_actors.clear()


# ============================================================================
# Tests - beforeStop() Lifecycle Hook
# ============================================================================

@pytest.mark.asyncio
async def test_call_before_stop_before_closing_mailbox(stage):
    """Test that beforeStop() is called before mailbox closes."""
    proxy: Trackable = stage.actor_for(
        TrackingProtocol(),
        Definition("Tracking", Uuid7Address(), ())
    )

    actor = tracking_actors[proxy.address().value_as_string()]

    await asyncio.sleep(0.01)

    # Stop the actor
    await proxy.stop()

    # beforeStop should have been called
    assert actor.was_before_stop_called() == True
    assert proxy.is_stopped() == True


@pytest.mark.asyncio
async def test_call_before_stop_before_after_stop(stage):
    """Test that beforeStop() is called before afterStop()."""
    proxy: Trackable = stage.actor_for(
        TrackingProtocol(),
        Definition("Tracking", Uuid7Address(), ())
    )

    actor = tracking_actors[proxy.address().value_as_string()]

    await asyncio.sleep(0.01)

    # Stop the actor
    await proxy.stop()

    # Check order
    stop_order = actor.get_stop_order()
    assert stop_order == ["beforeStop", "afterStop"]


@pytest.mark.asyncio
async def test_handle_errors_in_before_stop_gracefully(stage):
    """Test that errors in beforeStop() are handled gracefully."""
    proxy: Trackable = stage.actor_for(
        BeforeStopErrorProtocol(),
        Definition("BeforeStopError", Uuid7Address(), ())
    )

    await asyncio.sleep(0.01)

    # Stop should complete despite error
    await proxy.stop()
    assert proxy.is_stopped() == True


@pytest.mark.asyncio
async def test_not_prevent_stop_if_before_stop_throws(stage):
    """Test that stop proceeds even if beforeStop() throws."""
    proxy: Trackable = stage.actor_for(
        BeforeStopErrorProtocol(),
        Definition("BeforeStopError", Uuid7Address(), ())
    )

    await asyncio.sleep(0.01)

    # Should be able to send messages before stop
    await proxy.do_something()

    # Stop should work despite beforeStop error
    await proxy.stop()

    # Actor should be stopped
    assert proxy.is_stopped() == True


# ============================================================================
# Tests - Child Actor Stopping Coordination
# ============================================================================

@pytest.mark.asyncio
async def test_stop_child_actors_before_parent(stage):
    """Test that child actors stop before parent."""
    parent_proxy: Trackable = stage.actor_for(
        ParentProtocol(),
        Definition("Parent", Uuid7Address(), ())
    )

    parent_actor = parent_actors[parent_proxy.address().value_as_string()]

    await asyncio.sleep(0.01)

    # Create child actors
    child1_proxy: Trackable = stage.actor_for(
        TrackingProtocol(),
        Definition("Child1", Uuid7Address(), ()),
        parent=parent_proxy
    )

    child2_proxy: Trackable = stage.actor_for(
        TrackingProtocol(),
        Definition("Child2", Uuid7Address(), ()),
        parent=parent_proxy
    )

    await asyncio.sleep(0.01)

    # Stop the parent
    await parent_proxy.stop()

    # Children should be stopped before parent completes
    assert child1_proxy.is_stopped() == True
    assert child2_proxy.is_stopped() == True
    assert parent_proxy.is_stopped() == True

    # Check stop order
    stop_order = parent_actor.get_stop_order()
    assert stop_order[0] == "parent-beforeStop"
    assert stop_order[-1] == "parent-afterStop"


@pytest.mark.asyncio
async def test_continue_stopping_other_children_if_one_fails(stage):
    """Test that one failing child doesn't prevent others from stopping."""
    parent_proxy: Trackable = stage.actor_for(
        ParentProtocol(),
        Definition("Parent", Uuid7Address(), ())
    )

    await asyncio.sleep(0.01)

    # Create children - one that fails, one normal
    error_child: Trackable = stage.actor_for(
        BeforeStopErrorProtocol(),
        Definition("ErrorChild", Uuid7Address(), ()),
        parent=parent_proxy
    )

    normal_child: Trackable = stage.actor_for(
        TrackingProtocol(),
        Definition("NormalChild", Uuid7Address(), ()),
        parent=parent_proxy
    )

    await asyncio.sleep(0.01)

    # Stop parent
    await parent_proxy.stop()

    # All should be stopped despite one child failing
    assert error_child.is_stopped() == True
    assert normal_child.is_stopped() == True
    assert parent_proxy.is_stopped() == True


# ============================================================================
# Tests - Stop Sequence Integration
# ============================================================================

@pytest.mark.asyncio
async def test_execute_full_stop_sequence_in_correct_order(stage):
    """Test that full stop sequence executes in correct order."""
    proxy: Trackable = stage.actor_for(
        TrackingProtocol(),
        Definition("Tracking", Uuid7Address(), ())
    )

    actor = tracking_actors[proxy.address().value_as_string()]

    await asyncio.sleep(0.01)

    # Process some messages
    await proxy.do_something()
    await proxy.do_something()

    # Stop the actor
    await proxy.stop()

    # Verify complete sequence
    assert actor.was_before_stop_called() == True
    assert actor.was_after_stop_called() == True
    assert proxy.is_stopped() == True

    # Verify order
    stop_order = actor.get_stop_order()
    assert stop_order[0] == "beforeStop"
    assert stop_order[1] == "afterStop"


@pytest.mark.asyncio
async def test_handle_stop_being_called_multiple_times(stage):
    """Test that calling stop() multiple times is idempotent."""
    proxy: Trackable = stage.actor_for(
        TrackingProtocol(),
        Definition("Tracking", Uuid7Address(), ())
    )

    actor = tracking_actors[proxy.address().value_as_string()]

    await asyncio.sleep(0.01)

    # Stop multiple times
    await proxy.stop()
    await proxy.stop()
    await proxy.stop()

    # Should only execute stop sequence once
    stop_order = actor.get_stop_order()
    assert len(stop_order) == 2  # beforeStop, afterStop
    assert stop_order == ["beforeStop", "afterStop"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
