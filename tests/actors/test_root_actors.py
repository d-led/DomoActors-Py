"""
Root Actors tests - Guardian actor behavior.

Test cases covering PrivateRootActor and PublicRootActor initialization and supervision.
"""

import pytest
import asyncio
from typing import List
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
    """Simple actor for testing root actors."""
    async def do_work(self) -> str: ...
    async def get_parent_address(self) -> str: ...
    async def fail(self) -> None: ...


class SimpleActorImpl(Actor):
    """Simple actor implementation."""

    def __init__(self):
        super().__init__()
        self._fail_count = 0

    async def do_work(self) -> str:
        return "work done"

    async def get_parent_address(self) -> str:
        parent = self.parent()
        return parent.address().value_as_string() if parent else "no parent"

    async def fail(self) -> None:
        self._fail_count += 1
        raise ValueError(f"Intentional failure {self._fail_count}")

    async def before_restart(self, reason: Exception) -> None:
        await super().before_restart(reason)
        self.logger().log(f"SimpleActor restarting after: {reason}")

    async def after_restart(self) -> None:
        await super().after_restart()
        self.logger().log("SimpleActor restarted")


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
# Tests - Root Actor Hierarchy
# ============================================================================

@pytest.mark.asyncio
async def test_initialize_root_actors_on_first_use(stage):
    """Test that root actors initialize on first use."""
    # Create a user actor to trigger root actor initialization
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )

    await asyncio.sleep(0.1)

    # User actor should be functional
    result = await actor.do_work()
    assert result == "work done"


@pytest.mark.asyncio
async def test_use_public_root_as_default_parent(stage):
    """Test that PublicRootActor is default parent for user actors."""
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )

    await asyncio.sleep(0.1)

    parent_address = await actor.get_parent_address()
    # Parent should be PublicRootActor (not "no parent")
    assert parent_address != "no parent"


@pytest.mark.asyncio
async def test_create_actors_without_explicit_parent(stage):
    """Test creating multiple actors without specifying parent."""
    # Create multiple actors without specifying parent
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

    await asyncio.sleep(0.05)

    # All should have the same parent (PublicRootActor)
    parent1 = await actor1.get_parent_address()
    parent2 = await actor2.get_parent_address()
    parent3 = await actor3.get_parent_address()

    assert parent1 == parent2
    assert parent2 == parent3
    assert parent1 != "no parent"


# ============================================================================
# Tests - PublicRootActor Supervision (Restart Forever)
# ============================================================================

@pytest.mark.asyncio
async def test_restart_failing_child_actors(stage):
    """Test that PublicRootActor restarts failing children."""
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    # Trigger a failure
    try:
        await actor.fail()
    except:
        pass  # Ignore rejection

    # Wait for restart
    await asyncio.sleep(0.1)

    # Actor should still be functional after restart
    result = await actor.do_work()
    assert result == "work done"


@pytest.mark.asyncio
async def test_restart_actors_multiple_times(stage):
    """Test forever restart strategy."""
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    # Trigger multiple failures
    try:
        await actor.fail()
    except:
        pass
    await asyncio.sleep(0.05)

    try:
        await actor.fail()
    except:
        pass
    await asyncio.sleep(0.05)

    try:
        await actor.fail()
    except:
        pass
    await asyncio.sleep(0.05)

    # Actor should still be functional after multiple restarts
    result = await actor.do_work()
    assert result == "work done"


@pytest.mark.asyncio
async def test_continue_normal_operation_after_restart(stage):
    """Test that actors continue normal operation after restart."""
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    # Do work before failure
    before = await actor.do_work()
    assert before == "work done"

    # Trigger failure
    try:
        await actor.fail()
    except:
        pass
    await asyncio.sleep(0.1)

    # Do work after restart
    after = await actor.do_work()
    assert after == "work done"


# ============================================================================
# Tests - Bulkhead Pattern
# ============================================================================

@pytest.mark.asyncio
async def test_isolate_failing_actors_from_system(stage):
    """Test that failing actors are isolated from the system."""
    actor1: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor1", Uuid7Address(), ())
    )
    actor2: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor2", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    # Fail actor1
    try:
        await actor1.fail()
    except:
        pass
    await asyncio.sleep(0.1)

    # actor2 should still work normally (not affected by actor1's failure)
    result = await actor2.do_work()
    assert result == "work done"

    # actor1 should also work after restart
    result1 = await actor1.do_work()
    assert result1 == "work done"


@pytest.mark.asyncio
async def test_prevent_cascading_failures(stage):
    """Test that failures don't cascade."""
    # Create multiple actors
    actors: List[SimpleActor] = []
    for i in range(5):
        actor = stage.actor_for(
            SimpleActorProtocol(),
            Definition(f"SimpleActor{i}", Uuid7Address(), ())
        )
        actors.append(actor)

    await asyncio.sleep(0.1)

    # Fail the first two actors
    try:
        await actors[0].fail()
    except:
        pass
    try:
        await actors[1].fail()
    except:
        pass

    await asyncio.sleep(0.15)

    # All actors should still be functional
    results = await asyncio.gather(*[a.do_work() for a in actors])
    for result in results:
        assert result == "work done"


# ============================================================================
# Tests - Actor Hierarchy with Root Actors
# ============================================================================

@pytest.mark.asyncio
async def test_parent_child_with_public_root_ancestor(stage):
    """Test parent-child relationships with PublicRootActor as ancestor."""
    parent: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("Parent", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    child: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("Child", Uuid7Address(), ()),
        parent=parent
    )

    await asyncio.sleep(0.05)

    # Child should have parent address (not PublicRootActor)
    child_parent_address = await child.get_parent_address()
    parent_address = parent.address().value_as_string()

    assert child_parent_address == parent_address

    # But parent should have PublicRootActor as its parent
    parent_parent_address = await parent.get_parent_address()
    assert parent_parent_address != "no parent"
    assert parent_parent_address != parent_address


@pytest.mark.asyncio
async def test_maintain_hierarchy_integrity(stage):
    """Test that actor hierarchy integrity is maintained."""
    grandparent: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("Grandparent", Uuid7Address(), ())
    )
    await asyncio.sleep(0.03)

    parent: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("Parent", Uuid7Address(), ()),
        parent=grandparent
    )
    await asyncio.sleep(0.03)

    child: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("Child", Uuid7Address(), ()),
        parent=parent
    )
    await asyncio.sleep(0.03)

    # Verify hierarchy
    child_parent = await child.get_parent_address()
    parent_parent = await parent.get_parent_address()
    grandparent_parent = await grandparent.get_parent_address()

    assert child_parent == parent.address().value_as_string()
    assert parent_parent == grandparent.address().value_as_string()
    assert grandparent_parent != "no parent"  # Should be PublicRootActor


# ============================================================================
# Tests - System Stability
# ============================================================================

@pytest.mark.asyncio
async def test_remain_stable_with_concurrent_creations(stage):
    """Test stability with multiple concurrent actor creations."""
    # Create many actors concurrently
    tasks = []
    for i in range(20):
        actor = stage.actor_for(
            SimpleActorProtocol(),
            Definition(f"SimpleActor{i}", Uuid7Address(), ())
        )
        tasks.append(actor)

    await asyncio.sleep(0.1)

    # All actors should be functional
    results = await asyncio.gather(*[a.do_work() for a in tasks[:10]])
    for result in results:
        assert result == "work done"


@pytest.mark.asyncio
async def test_handle_rapid_failure_and_recovery(stage):
    """Test handling rapid failure and recovery."""
    actor: SimpleActor = stage.actor_for(
        SimpleActorProtocol(),
        Definition("SimpleActor", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    # Rapid failures
    for i in range(5):
        try:
            await actor.fail()
        except:
            pass
        await asyncio.sleep(0.02)

    # Wait for recovery
    await asyncio.sleep(0.15)

    # Should still work
    result = await actor.do_work()
    assert result == "work done"


@pytest.mark.asyncio
async def test_maintain_system_integrity_under_stress(stage):
    """Test system integrity under stress."""
    # Create actors and cause some to fail
    actors: List[SimpleActor] = []
    for i in range(10):
        actor = stage.actor_for(
            SimpleActorProtocol(),
            Definition(f"SimpleActor{i}", Uuid7Address(), ())
        )
        actors.append(actor)

    await asyncio.sleep(0.1)

    # Cause half to fail
    for i in range(5):
        try:
            await actors[i].fail()
        except:
            pass

    await asyncio.sleep(0.15)

    # All should still be functional
    results = await asyncio.gather(*[a.do_work() for a in actors])
    for result in results:
        assert result == "work done"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
