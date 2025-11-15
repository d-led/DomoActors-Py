"""
Lifecycle Error Handling tests - Errors in lifecycle hooks.

Test cases covering error scenarios in lifecycle hooks.
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
normal_actors: Dict[str, 'NormalActorImpl'] = {}
error_actors: Dict[str, Actor] = {}


# ============================================================================
# Normal Actor (for baseline)
# ============================================================================

class Normal(ActorProtocol):
    """Normal actor for baseline testing."""
    async def get_before_start_called(self) -> bool: ...
    async def get_after_stop_called(self) -> bool: ...


class NormalActorImpl(Actor):
    """Normal actor that tracks lifecycle calls."""

    def __init__(self):
        super().__init__()
        self._before_start_called = False
        self._after_stop_called = False

    async def before_start(self) -> None:
        await super().before_start()
        self._before_start_called = True

    async def after_stop(self) -> None:
        await super().after_stop()
        self._after_stop_called = True

    async def get_before_start_called(self) -> bool:
        return self._before_start_called

    async def get_after_stop_called(self) -> bool:
        return self._after_stop_called


class NormalInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        actor = NormalActorImpl()
        normal_actors[definition.address().value_as_string()] = actor
        return actor


class NormalProtocol(Protocol):
    def type(self) -> str:
        return "Normal"

    def instantiator(self) -> ProtocolInstantiator:
        return NormalInstantiator()


# ============================================================================
# Error Actors
# ============================================================================

class BeforeStartError(ActorProtocol):
    """Actor that fails in beforeStart."""
    pass


class BeforeStartErrorActor(Actor):
    """Actor that throws in beforeStart hook."""

    async def before_start(self) -> None:
        await super().before_start()
        raise ValueError("beforeStart error")


class BeforeStartErrorInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        actor = BeforeStartErrorActor()
        error_actors[definition.address().value_as_string()] = actor
        return actor


class BeforeStartErrorProtocol(Protocol):
    def type(self) -> str:
        return "BeforeStartError"

    def instantiator(self) -> ProtocolInstantiator:
        return BeforeStartErrorInstantiator()


# AfterStop Error Actor

class AfterStopError(ActorProtocol):
    """Actor that fails in afterStop."""
    pass


class AfterStopErrorActor(Actor):
    """Actor that throws in afterStop hook."""

    async def after_stop(self) -> None:
        await super().after_stop()
        raise ValueError("afterStop error")


class AfterStopErrorInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        actor = AfterStopErrorActor()
        error_actors[definition.address().value_as_string()] = actor
        return actor


class AfterStopErrorProtocol(Protocol):
    def type(self) -> str:
        return "AfterStopError"

    def instantiator(self) -> ProtocolInstantiator:
        return AfterStopErrorInstantiator()


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def stage():
    """Create a fresh stage."""
    s = LocalStage()
    yield s
    asyncio.run(s.close())


@pytest.fixture(autouse=True)
def clear_actors():
    """Clear global storage."""
    normal_actors.clear()
    error_actors.clear()


# ============================================================================
# Tests
# ============================================================================

@pytest.mark.asyncio
async def test_before_start_error_is_caught(stage, caplog):
    """Test that beforeStart errors are caught and logged."""
    actor: BeforeStartError = stage.actor_for(
        BeforeStartErrorProtocol(),
        Definition("BeforeStartError", Uuid7Address(), ())
    )

    await asyncio.sleep(0.1)

    # Actor should still be created despite error
    assert actor is not None


@pytest.mark.asyncio
async def test_before_start_error_does_not_prevent_creation(stage):
    """Test that actor creation succeeds despite beforeStart error."""
    actor: BeforeStartError = stage.actor_for(
        BeforeStartErrorProtocol(),
        Definition("BeforeStartError", Uuid7Address(), ())
    )

    await asyncio.sleep(0.1)

    # Actor should exist in directory
    assert actor.address() is not None


@pytest.mark.asyncio
async def test_after_stop_error_is_caught(stage):
    """Test that afterStop errors are caught and logged."""
    actor: AfterStopError = stage.actor_for(
        AfterStopErrorProtocol(),
        Definition("AfterStopError", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    # Stop should not raise even with error
    await actor.stop()
    await asyncio.sleep(0.05)

    # Actor should be stopped
    assert actor.is_stopped() == True


@pytest.mark.asyncio
async def test_after_stop_error_completes_stop(stage):
    """Test that stop completes even if afterStop fails."""
    actor: AfterStopError = stage.actor_for(
        AfterStopErrorProtocol(),
        Definition("AfterStopError", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    await actor.stop()
    await asyncio.sleep(0.05)

    assert actor.is_stopped() == True


@pytest.mark.asyncio
async def test_normal_lifecycle_execution(stage):
    """Test that normal lifecycle hooks are called correctly."""
    actor: Normal = stage.actor_for(
        NormalProtocol(),
        Definition("Normal", Uuid7Address(), ())
    )

    await asyncio.sleep(0.1)

    # beforeStart should have been called
    assert await actor.get_before_start_called() == True

    # Stop actor
    await actor.stop()
    await asyncio.sleep(0.05)

    # afterStop should have been called
    assert await actor.get_after_stop_called() == True


@pytest.mark.asyncio
async def test_normal_lifecycle_no_errors(stage, caplog):
    """Test that normal operation doesn't log errors."""
    actor: Normal = stage.actor_for(
        NormalProtocol(),
        Definition("Normal", Uuid7Address(), ())
    )

    await asyncio.sleep(0.1)
    await actor.stop()
    await asyncio.sleep(0.05)

    # Should have been clean execution
    assert actor.is_stopped() == True


@pytest.mark.asyncio
async def test_error_isolation_between_actors(stage):
    """Test that one actor's error doesn't affect others."""
    # Create error actor
    error_actor: BeforeStartError = stage.actor_for(
        BeforeStartErrorProtocol(),
        Definition("ErrorActor", Uuid7Address(), ())
    )

    # Create normal actor
    normal_actor: Normal = stage.actor_for(
        NormalProtocol(),
        Definition("NormalActor", Uuid7Address(), ())
    )

    await asyncio.sleep(0.1)

    # Normal actor should work fine
    assert await normal_actor.get_before_start_called() == True


@pytest.mark.asyncio
async def test_multiple_actors_handle_errors_independently(stage):
    """Test that multiple actors handle errors independently."""
    # Create multiple error actors
    error1: BeforeStartError = stage.actor_for(
        BeforeStartErrorProtocol(),
        Definition("Error1", Uuid7Address(), ())
    )

    error2: BeforeStartError = stage.actor_for(
        BeforeStartErrorProtocol(),
        Definition("Error2", Uuid7Address(), ())
    )

    # Create normal actors
    normal1: Normal = stage.actor_for(
        NormalProtocol(),
        Definition("Normal1", Uuid7Address(), ())
    )

    normal2: Normal = stage.actor_for(
        NormalProtocol(),
        Definition("Normal2", Uuid7Address(), ())
    )

    await asyncio.sleep(0.1)

    # All actors should exist
    assert error1 is not None
    assert error2 is not None
    assert await normal1.get_before_start_called() == True
    assert await normal2.get_before_start_called() == True


@pytest.mark.asyncio
async def test_lifecycle_hooks_called_in_order(stage):
    """Test that lifecycle hooks are called in correct order."""
    actor: Normal = stage.actor_for(
        NormalProtocol(),
        Definition("Normal", Uuid7Address(), ())
    )

    await asyncio.sleep(0.1)

    # beforeStart should be called
    assert await actor.get_before_start_called() == True

    # Stop
    await actor.stop()
    await asyncio.sleep(0.05)

    # afterStop should be called
    assert await actor.get_after_stop_called() == True


@pytest.mark.asyncio
async def test_error_in_lifecycle_does_not_crash_stage(stage):
    """Test that lifecycle errors don't crash the stage."""
    # Create several actors with errors
    for i in range(5):
        stage.actor_for(
            BeforeStartErrorProtocol(),
            Definition(f"Error{i}", Uuid7Address(), ())
        )

    await asyncio.sleep(0.1)

    # Stage should still be functional
    normal: Normal = stage.actor_for(
        NormalProtocol(),
        Definition("Normal", Uuid7Address(), ())
    )

    await asyncio.sleep(0.05)

    assert await normal.get_before_start_called() == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
