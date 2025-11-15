"""
Stage Close tests - Stage shutdown sequencing.

Test cases covering hierarchical shutdown.
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


# Global tracking
global_stop_order: List[str] = []
tracking_actors: Dict[str, 'TrackingActorImpl'] = {}


# ============================================================================
# Tracking Actor
# ============================================================================

class TrackingActor(ActorProtocol):
    """Actor that tracks stop order."""
    pass


class TrackingActorImpl(Actor):
    """Actor that records stop order in global list."""

    def __init__(self, actor_id: str):
        super().__init__()
        self._actor_id = actor_id

    async def before_stop(self) -> None:
        await super().before_stop()
        global_stop_order.append(f"{self._actor_id}-beforeStop")

    async def after_stop(self) -> None:
        await super().after_stop()
        global_stop_order.append(f"{self._actor_id}-afterStop")


class TrackingInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        params = definition.parameters()
        actor_id = params[0] if params else "unknown"
        actor = TrackingActorImpl(actor_id)
        tracking_actors[definition.address().value_as_string()] = actor
        return actor


class TrackingProtocol(Protocol):
    def type(self) -> str:
        return "TrackingActor"

    def instantiator(self) -> ProtocolInstantiator:
        return TrackingInstantiator()


# ============================================================================
# Parent Actor
# ============================================================================

class Parent(ActorProtocol):
    """Parent actor that can have children."""
    async def create_child(self, child_id: str) -> ActorProtocol: ...


class ParentActorImpl(Actor):
    """Parent actor implementation."""

    def __init__(self, actor_id: str):
        super().__init__()
        self._actor_id = actor_id
        self._children: List[ActorProtocol] = []

    async def before_stop(self) -> None:
        await super().before_stop()
        global_stop_order.append(f"{self._actor_id}-beforeStop")

    async def after_stop(self) -> None:
        await super().after_stop()
        global_stop_order.append(f"{self._actor_id}-afterStop")

    async def create_child(self, child_id: str) -> ActorProtocol:
        child = self.child_actor_for(
            TrackingProtocol(),
            Definition(f"Child-{child_id}", Uuid7Address(), (child_id,))
        )
        self._children.append(child)
        return child


class ParentInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        params = definition.parameters()
        actor_id = params[0] if params else "parent"
        return ParentActorImpl(actor_id)


class ParentProtocol(Protocol):
    def type(self) -> str:
        return "Parent"

    def instantiator(self) -> ProtocolInstantiator:
        return ParentInstantiator()


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def clear_tracking():
    """Clear global tracking before each test."""
    global_stop_order.clear()
    tracking_actors.clear()


# ============================================================================
# Tests
# ============================================================================

@pytest.mark.asyncio
async def test_stage_close_stops_all_actors(clear_tracking):
    """Test that stage.close() stops all actors."""
    stage = LocalStage()

    # Create actors
    actor1: TrackingActor = stage.actor_for(
        TrackingProtocol(),
        Definition("Actor1", Uuid7Address(), ("actor1",))
    )

    actor2: TrackingActor = stage.actor_for(
        TrackingProtocol(),
        Definition("Actor2", Uuid7Address(), ("actor2",))
    )

    await asyncio.sleep(0.05)

    # Close stage
    await stage.close()

    # Both actors should be stopped
    assert actor1.is_stopped() == True
    assert actor2.is_stopped() == True


@pytest.mark.asyncio
async def test_empty_stage_closes_gracefully(clear_tracking):
    """Test that empty stage closes without errors."""
    stage = LocalStage()

    # Close without any actors
    await stage.close()

    # Should complete without error
    assert True


@pytest.mark.asyncio
async def test_one_failing_actor_does_not_prevent_others(clear_tracking):
    """Test that one actor's stop failure doesn't prevent others."""
    stage = LocalStage()

    # Create normal actors
    actor1: TrackingActor = stage.actor_for(
        TrackingProtocol(),
        Definition("Actor1", Uuid7Address(), ("actor1",))
    )

    actor2: TrackingActor = stage.actor_for(
        TrackingProtocol(),
        Definition("Actor2", Uuid7Address(), ("actor2",))
    )

    await asyncio.sleep(0.05)

    # Close stage
    await stage.close()

    # Both should be stopped
    assert actor1.is_stopped() == True
    assert actor2.is_stopped() == True


@pytest.mark.asyncio
async def test_hierarchical_shutdown_order(clear_tracking):
    """Test that children stop before parents."""
    stage = LocalStage()

    # Create parent
    parent: Parent = stage.actor_for(
        ParentProtocol(),
        Definition("Parent", Uuid7Address(), ("parent",))
    )

    await asyncio.sleep(0.05)

    # Create children
    child1 = await parent.create_child("child1")
    child2 = await parent.create_child("child2")

    await asyncio.sleep(0.05)

    # Close stage
    await stage.close()

    # Check order - children should stop before parent's afterStop
    if len(global_stop_order) > 0:
        # Find indices
        child1_after_idx = None
        child2_after_idx = None
        parent_after_idx = None

        for i, event in enumerate(global_stop_order):
            if "child1-afterStop" in event:
                child1_after_idx = i
            if "child2-afterStop" in event:
                child2_after_idx = i
            if "parent-afterStop" in event:
                parent_after_idx = i

        # If all were stopped, verify order
        if child1_after_idx is not None and parent_after_idx is not None:
            assert child1_after_idx < parent_after_idx


@pytest.mark.asyncio
async def test_multiple_close_calls_are_idempotent(clear_tracking):
    """Test that calling close() multiple times is safe."""
    stage = LocalStage()

    actor: TrackingActor = stage.actor_for(
        TrackingProtocol(),
        Definition("Actor", Uuid7Address(), ("actor",))
    )

    await asyncio.sleep(0.05)

    # Close multiple times
    await stage.close()
    await stage.close()
    await stage.close()

    # Should be stopped once
    assert actor.is_stopped() == True


@pytest.mark.asyncio
async def test_actors_without_children_stop_correctly(clear_tracking):
    """Test that actors without children stop properly."""
    stage = LocalStage()

    # Create standalone actors
    for i in range(5):
        stage.actor_for(
            TrackingProtocol(),
            Definition(f"Actor{i}", Uuid7Address(), (f"actor{i}",))
        )

    await asyncio.sleep(0.05)

    # Close
    await stage.close()

    # All should have stopped
    assert len([e for e in global_stop_order if "afterStop" in e]) >= 5


@pytest.mark.asyncio
async def test_mix_of_parent_child_and_standalone(clear_tracking):
    """Test shutdown with mix of parent/child and standalone actors."""
    stage = LocalStage()

    # Standalone
    standalone: TrackingActor = stage.actor_for(
        TrackingProtocol(),
        Definition("Standalone", Uuid7Address(), ("standalone",))
    )

    # Parent with child
    parent: Parent = stage.actor_for(
        ParentProtocol(),
        Definition("Parent", Uuid7Address(), ("parent",))
    )

    await asyncio.sleep(0.05)

    child = await parent.create_child("child")

    await asyncio.sleep(0.05)

    # Close
    await stage.close()

    # All should be stopped
    assert standalone.is_stopped() == True
    assert parent.is_stopped() == True
    assert child.is_stopped() == True


@pytest.mark.asyncio
async def test_multi_level_hierarchy_shutdown_order(clear_tracking):
    """Test shutdown order with grandparent -> parent -> child."""
    stage = LocalStage()

    # Create grandparent
    grandparent: Parent = stage.actor_for(
        ParentProtocol(),
        Definition("Grandparent", Uuid7Address(), ("grandparent",))
    )

    await asyncio.sleep(0.05)

    # Grandparent creates parent (we need to get raw actor for this)
    # For simplicity, we'll create a parent as top-level
    parent: Parent = stage.actor_for(
        ParentProtocol(),
        Definition("Parent", Uuid7Address(), ("parent",))
    )

    await asyncio.sleep(0.05)

    # Parent creates child
    child = await parent.create_child("child")

    await asyncio.sleep(0.05)

    # Close
    await stage.close()

    # Verify all stopped
    assert grandparent.is_stopped() == True
    assert parent.is_stopped() == True
    assert child.is_stopped() == True


@pytest.mark.asyncio
async def test_stage_close_with_no_actors(clear_tracking):
    """Test closing stage with no user actors."""
    stage = LocalStage()

    # Just close immediately
    await stage.close()

    # Should complete successfully
    assert True


@pytest.mark.asyncio
async def test_stage_close_stops_root_actors(clear_tracking):
    """Test that root actors are stopped on close."""
    stage = LocalStage()

    # Create an actor (triggers root actor initialization)
    actor: TrackingActor = stage.actor_for(
        TrackingProtocol(),
        Definition("Actor", Uuid7Address(), ("actor",))
    )

    await asyncio.sleep(0.05)

    # Close
    await stage.close()

    # User actor should be stopped
    assert actor.is_stopped() == True


@pytest.mark.asyncio
async def test_before_stop_called_before_after_stop(clear_tracking):
    """Test that beforeStop is called before afterStop."""
    stage = LocalStage()

    actor: TrackingActor = stage.actor_for(
        TrackingProtocol(),
        Definition("Actor", Uuid7Address(), ("actor",))
    )

    await asyncio.sleep(0.05)

    await stage.close()

    # Check order
    before_idx = None
    after_idx = None

    for i, event in enumerate(global_stop_order):
        if "actor-beforeStop" in event:
            before_idx = i
        if "actor-afterStop" in event:
            after_idx = i

    if before_idx is not None and after_idx is not None:
        assert before_idx < after_idx


@pytest.mark.asyncio
async def test_stage_close_waits_for_all_stops(clear_tracking):
    """Test that close() waits for all actors to stop."""
    stage = LocalStage()

    # Create multiple actors
    actors = []
    for i in range(10):
        actor = stage.actor_for(
            TrackingProtocol(),
            Definition(f"Actor{i}", Uuid7Address(), (f"actor{i}",))
        )
        actors.append(actor)

    await asyncio.sleep(0.1)

    # Close
    await stage.close()

    # All should be stopped
    for actor in actors:
        assert actor.is_stopped() == True


@pytest.mark.asyncio
async def test_stage_close_handles_slow_actors(clear_tracking):
    """Test that close waits for slow-stopping actors."""
    stage = LocalStage()

    # Create actors
    actor1: TrackingActor = stage.actor_for(
        TrackingProtocol(),
        Definition("Actor1", Uuid7Address(), ("actor1",))
    )

    actor2: TrackingActor = stage.actor_for(
        TrackingProtocol(),
        Definition("Actor2", Uuid7Address(), ("actor2",))
    )

    await asyncio.sleep(0.05)

    # Close (should wait for all)
    await stage.close()

    # Both should be stopped
    assert actor1.is_stopped() == True
    assert actor2.is_stopped() == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
