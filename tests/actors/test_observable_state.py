"""
Observable State tests - State observation pattern for testing.

Test cases covering ObservableState and ObservableStateProvider.
"""

import pytest
import asyncio
from domo_actors.actors.actor import Actor
from domo_actors.actors.actor_protocol import ActorProtocol
from domo_actors.actors.protocol import Protocol, ProtocolInstantiator
from domo_actors.actors.definition import Definition
from domo_actors.actors.local_stage import LocalStage
from domo_actors.actors.address import Uuid7Address
from domo_actors.actors.observable_state import ObservableState, ObservableStateProvider
from domo_actors.actors.testkit.test_await_assist import (
    await_observable_state,
    await_state_value,
    await_assert
)


# ============================================================================
# Worker Actor
# ============================================================================

class Worker(ActorProtocol):
    """Worker protocol."""
    async def process(self, id: int) -> None: ...
    async def reset(self) -> None: ...
    async def get_processed_count(self) -> int: ...


class WorkerActor(Actor):
    """Example actor demonstrating ObservableStateProvider pattern."""

    def __init__(self):
        super().__init__()
        self._processed_ids = []
        self._processed_count = 0
        self._status = "idle"

    async def process(self, id: int) -> None:
        self._status = "busy"
        # Simulate async work
        await asyncio.sleep(0.01)
        self._processed_ids.append(id)
        self._processed_count += 1
        self._status = "idle"

    async def reset(self) -> None:
        self._processed_ids = []
        self._processed_count = 0
        self._status = "idle"

    async def get_processed_count(self) -> int:
        return self._processed_count

    async def observable_state(self) -> ObservableState:
        """
        Exposes internal state for testing.
        Returns a snapshot - not mutable internal references!
        """
        last_processed = self._processed_ids[-1] if self._processed_ids else None
        return (ObservableState()
                .put_value('processedCount', self._processed_count)
                .put_value('processedIds', list(self._processed_ids))  # Copy list
                .put_value('status', self._status)
                .put_value('lastProcessed', last_processed))


class WorkerInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        return WorkerActor()


class WorkerProtocol(Protocol):
    def type(self) -> str:
        return "Worker"

    def instantiator(self) -> ProtocolInstantiator:
        return WorkerInstantiator()


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def stage():
    s = LocalStage()
    yield s
    asyncio.run(s.close())


# ============================================================================
# Tests - ObservableState Class
# ============================================================================

def test_store_and_retrieve_values():
    """Test that ObservableState stores and retrieves values."""
    state = ObservableState()
    state.put_value('count', 42)
    state.put_value('status', 'active')

    assert state.value_of('count') == 42
    assert state.value_of('status') == 'active'
    assert state.value_of('missing') is None


def test_fluent_chaining():
    """Test fluent chaining of put_value."""
    state = (ObservableState()
             .put_value('a', 1)
             .put_value('b', 2)
             .put_value('c', 3))

    assert state.value_of('a') == 1
    assert state.value_of('b') == 2
    assert state.value_of('c') == 3


def test_typed_value_of():
    """Test typed valueOf."""
    state = (ObservableState()
             .put_value('count', 42)
             .put_value('items', [1, 2, 3]))

    count = state.value_of('count')
    items = state.value_of('items')

    assert count == 42
    assert items == [1, 2, 3]


def test_value_of_or_default():
    """Test value_of_or_default."""
    state = ObservableState().put_value('count', 10)

    assert state.value_of_or_default('count', 0) == 10
    assert state.value_of_or_default('missing', 0) == 0
    assert state.value_of_or_default('missing', 'default') == 'default'


def test_check_value_existence():
    """Test has_value."""
    state = ObservableState().put_value('exists', 'yes')

    assert state.has_value('exists') == True
    assert state.has_value('missing') == False


def test_size_and_keys():
    """Test size and keys."""
    state = (ObservableState()
             .put_value('a', 1)
             .put_value('b', 2)
             .put_value('c', 3))

    assert state.size() == 3
    assert state.keys() == ['a', 'b', 'c']


def test_snapshot():
    """Test snapshot."""
    state = (ObservableState()
             .put_value('count', 42)
             .put_value('status', 'active'))

    snapshot = state.snapshot()

    assert snapshot == {
        'count': 42,
        'status': 'active'
    }


def test_clear_all_values():
    """Test clear."""
    state = (ObservableState()
             .put_value('a', 1)
             .put_value('b', 2))

    assert state.size() == 2

    state.clear()

    assert state.size() == 0
    assert state.has_value('a') == False


# ============================================================================
# Tests - ObservableStateProvider Usage
# ============================================================================

@pytest.mark.asyncio
async def test_expose_internal_state_for_testing(stage):
    """Test exposing internal state for testing."""
    worker: Worker = stage.actor_for(
        WorkerProtocol(),
        Definition("Worker", Uuid7Address(), ())
    )

    await worker.process(1)
    await worker.process(2)
    await worker.process(3)

    await asyncio.sleep(0.05)

    state = await worker.observable_state()

    assert state.value_of('processedCount') == 3
    assert state.value_of('processedIds') == [1, 2, 3]
    assert state.value_of('lastProcessed') == 3
    assert state.value_of('status') == 'idle'


@pytest.mark.asyncio
async def test_provide_snapshot_not_mutable_references(stage):
    """Test that snapshot doesn't provide mutable references."""
    worker: Worker = stage.actor_for(
        WorkerProtocol(),
        Definition("Worker", Uuid7Address(), ())
    )

    await worker.process(1)
    await asyncio.sleep(0.02)

    state1 = await worker.observable_state()
    ids1 = state1.value_of('processedIds')

    await worker.process(2)
    await asyncio.sleep(0.02)

    state2 = await worker.observable_state()
    ids2 = state2.value_of('processedIds')

    # Different snapshots - modifications don't affect actor
    assert ids1 == [1]
    assert ids2 == [1, 2]

    ids1.append(999)  # Mutate snapshot

    state3 = await worker.observable_state()
    assert state3.value_of('processedIds') == [1, 2]  # Unaffected


@pytest.mark.asyncio
async def test_work_alongside_normal_protocol_methods(stage):
    """Test that observable state works alongside normal methods."""
    worker: Worker = stage.actor_for(
        WorkerProtocol(),
        Definition("Worker", Uuid7Address(), ())
    )

    await worker.process(1)
    await worker.process(2)
    await asyncio.sleep(0.05)

    # Traditional query method
    count = await worker.get_processed_count()
    assert count == 2

    # Observable state (more detailed)
    state = await worker.observable_state()
    assert state.value_of('processedCount') == 2
    assert state.value_of('processedIds') == [1, 2]
    assert state.value_of('status') == 'idle'


# ============================================================================
# Tests - Test Utilities
# ============================================================================

@pytest.mark.asyncio
async def test_await_observable_state_condition(stage):
    """Test await_observable_state utility."""
    worker: Worker = stage.actor_for(
        WorkerProtocol(),
        Definition("Worker", Uuid7Address(), ())
    )

    # Start async processing
    await worker.process(1)
    await worker.process(2)
    await worker.process(3)

    # Wait for condition to be satisfied
    state = await await_observable_state(
        worker,
        lambda s: s.value_of('processedCount') == 3,
        {'timeout': 1.0}
    )

    assert state.value_of('processedCount') == 3
    assert len(state.value_of('processedIds')) == 3


@pytest.mark.asyncio
async def test_await_specific_state_value(stage):
    """Test await_state_value utility."""
    worker: Worker = stage.actor_for(
        WorkerProtocol(),
        Definition("Worker", Uuid7Address(), ())
    )

    await worker.process(1)
    await worker.process(2)
    await worker.process(3)

    await await_state_value(worker, 'processedCount', 3, {'timeout': 1.0})

    state = await worker.observable_state()
    assert state.value_of('processedCount') == 3


@pytest.mark.asyncio
async def test_throw_if_condition_not_met_within_timeout(stage):
    """Test that timeout is enforced."""
    worker: Worker = stage.actor_for(
        WorkerProtocol(),
        Definition("Worker", Uuid7Address(), ())
    )

    await worker.process(1)
    await asyncio.sleep(0.05)

    with pytest.raises(asyncio.TimeoutError) as exc_info:
        await await_observable_state(
            worker,
            lambda s: s.value_of('processedCount') == 999,
            {'timeout': 0.1, 'interval': 0.01}
        )

    assert "not satisfied within 100ms" in str(exc_info.value)


@pytest.mark.asyncio
async def test_await_assertion_to_pass(stage):
    """Test await_assert utility."""
    worker: Worker = stage.actor_for(
        WorkerProtocol(),
        Definition("Worker", Uuid7Address(), ())
    )

    await worker.process(1)
    await worker.process(2)
    await worker.process(3)

    async def check():
        state = await worker.observable_state()
        assert state.value_of('processedCount') == 3
        assert state.value_of('status') == 'idle'

    await await_assert(check, timeout=1.0)


@pytest.mark.asyncio
async def test_throw_last_assertion_error_on_timeout(stage):
    """Test that assertion error is propagated on timeout."""
    worker: Worker = stage.actor_for(
        WorkerProtocol(),
        Definition("Worker", Uuid7Address(), ())
    )

    await worker.process(1)
    await asyncio.sleep(0.05)

    async def check():
        state = await worker.observable_state()
        assert state.value_of('processedCount') == 999

    with pytest.raises(AssertionError) as exc_info:
        await await_assert(check, timeout=0.1, interval=0.01)

    assert "999" in str(exc_info.value)


# ============================================================================
# Tests - Real-World Testing Patterns
# ============================================================================

@pytest.mark.asyncio
async def test_verify_async_processing_completes(stage):
    """Test verifying async processing completes."""
    worker: Worker = stage.actor_for(
        WorkerProtocol(),
        Definition("Worker", Uuid7Address(), ())
    )

    # Fire off multiple async operations
    for i in range(1, 11):
        await worker.process(i)

    # Wait for all to complete
    state = await await_observable_state(
        worker,
        lambda s: s.value_of('processedCount') == 10,
        {'timeout': 2.0}
    )

    assert len(state.value_of('processedIds')) == 10
    assert state.value_of('status') == 'idle'


@pytest.mark.asyncio
async def test_verify_intermediate_state_during_processing(stage):
    """Test verifying intermediate state."""
    worker: Worker = stage.actor_for(
        WorkerProtocol(),
        Definition("Worker", Uuid7Address(), ())
    )

    await worker.process(1)
    await worker.process(2)

    # Wait for partial completion
    await await_state_value(worker, 'processedCount', 2, {'timeout': 1.0})

    # Continue processing
    await worker.process(3)
    await worker.process(4)

    # Wait for full completion
    await await_state_value(worker, 'processedCount', 4, {'timeout': 1.0})


@pytest.mark.asyncio
async def test_verify_state_after_reset(stage):
    """Test verifying state after reset."""
    worker: Worker = stage.actor_for(
        WorkerProtocol(),
        Definition("Worker", Uuid7Address(), ())
    )

    await worker.process(1)
    await worker.process(2)
    await asyncio.sleep(0.05)

    state = await worker.observable_state()
    assert state.value_of('processedCount') == 2

    await worker.reset()
    await asyncio.sleep(0.02)

    state = await worker.observable_state()
    assert state.value_of('processedCount') == 0
    assert state.value_of('processedIds') == []
    assert state.value_of('status') == 'idle'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
