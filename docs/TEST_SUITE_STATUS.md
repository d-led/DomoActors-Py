# DomoActors-Py Test Suite Status

## Overview

The TypeScript version has **220+ tests** across 15 test files. This document tracks the Python port progress.

## Completed Test Files ✅

### 1. test_actor.py - **30 tests** ✅
**Status**: Complete
**Coverage**: Core actor protocol, lifecycle, parent-child relationships
**Test Groups**:
- Operational Methods (6 tests)
- State Management (2 tests)
- Lifecycle Methods (3 tests)
- Parent/Child Relationships (4 tests)
- Object Methods (4 tests)
- Message Processing (3 tests)
- Additional integration tests (8 tests)

### 2. test_bounded_mailbox.py - **13 tests** ✅
**Status**: Complete
**Coverage**: Message queue capacity, overflow policies
**Test Groups**:
- Constructor and Basic Properties (2 tests)
- DropOldest Policy (3 tests)
- DropNewest Policy (1 test)
- Reject Policy (1 test)
- Suspension and Resumption (1 test)
- Size and Capacity Tracking (2 tests)
- Additional edge cases (3 tests)

### 3. test_scheduler.py - **15 tests** ✅
**Status**: Complete
**Coverage**: Task scheduling, cancellation, timing
**Test Groups**:
- scheduleOnce - One-time Execution (4 tests)
- schedule - Repeating Execution (3 tests)
- close - Cleanup (2 tests)
- Error Handling (1 test)
- Timing Accuracy (2 tests)
- Async Action Support (1 test)
- Additional tests (2 tests)

### 4. test_basic.py - **3 tests** ✅
**Status**: Complete (smoke tests)
**Coverage**: Basic counter functionality
**Tests**:
- Basic counter operations
- Counter initialization
- Multiple independent counters

### 5. test_counter.py - **8 tests** ✅
**Status**: PyTest version (needs async update)
**Coverage**: Stateful actor operations

## Test Files To Create 📝

### Priority 1: Core Functionality

#### 6. test_array_mailbox.py - **~10 tests**
**From**: ArrayMailbox.test.ts
**Coverage**: Unbounded FIFO mailbox behavior
**Key Tests**:
- Basic send/receive
- Suspension/resumption
- FIFO ordering
- Self-draining dispatch
- Close behavior

```python
# Template structure:
@pytest.mark.asyncio
async def test_array_mailbox_basic_operations(stage):
    """Test basic send and receive."""
    # Create actor with array mailbox
    # Send messages
    # Verify FIFO processing

@pytest.mark.asyncio
async def test_array_mailbox_suspension(stage):
    """Test suspension prevents processing."""
    # Suspend mailbox
    # Send messages
    # Verify not processed
    # Resume
    # Verify processed
```

#### 7. test_directory.py - **~18 tests**
**From**: Directory.test.ts
**Coverage**: Actor registry/lookup, sharding
**Key Tests**:
- Set and get operations
- Size tracking
- Distribution statistics
- Configuration options (DEFAULT, HIGH_CAPACITY, SMALL)
- Large scale operations (10,000+ actors)
- Hash distribution

```python
# Template structure:
@pytest.mark.asyncio
async def test_directory_basic_operations():
    """Test set and get."""
    directory = Directory()
    address = Uuid7Address()
    actor = create_mock_actor()
    directory.register(address, actor)
    assert directory.get(address) == actor

@pytest.mark.asyncio
async def test_directory_distribution():
    """Test actor distribution across buckets."""
    # Create 1000 actors
    # Verify good distribution
    # Check stats
```

#### 8. test_supervision_lifecycle.py - **~6 tests**
**From**: SupervisionLifeCycle.test.ts
**Coverage**: Supervision directives and strategies
**Key Tests**:
- Restart directive
- Resume directive
- Stop directive
- Escalate directive
- SupervisionStrategy (intensity/period/scope)
- beforeRestart/afterRestart hooks

```python
# Template structure:
class RestartingSupervisor(DefaultSupervisor):
    def decide_directive(self, error, supervised, strategy):
        return SupervisionDirective.RESTART

@pytest.mark.asyncio
async def test_restart_directive():
    """Test that restart directive restarts actor."""
    # Create supervised actor
    # Cause failure
    # Verify beforeRestart called
    # Verify afterRestart called
    # Verify state reset
```

#### 9. test_supervision_message_delivery_failure.py - **~13 tests**
**From**: SupervisionMessageDeliveryFailure.test.ts
**Coverage**: Message processing failures and supervision
**Key Tests**:
- Message error triggers supervision
- Promise rejection on failure
- Mailbox suspension during supervision
- State handling (restart vs resume)
- Multiple failures
- Restart intensity limits

```python
# Template structure:
@pytest.mark.asyncio
async def test_message_error_triggers_supervision():
    """Test that message processing error triggers supervisor."""
    # Create actor with supervisor
    # Send message that throws
    # Verify supervisor.inform() called
    # Verify mailbox suspended
    # Verify promise rejected
```

### Priority 2: Lifecycle and Integration

#### 10. test_lifecycle_error_handling.py - **~10 tests**
**From**: LifecycleErrorHandling.test.ts
**Coverage**: Errors in lifecycle hooks
**Key Tests**:
- beforeStart() errors
- start() errors
- afterStop() errors
- Error isolation between actors
- Error logging
- Normal lifecycle execution

```python
# Template structure:
class BeforeStartErrorActor(Actor):
    async def before_start(self):
        raise ValueError("beforeStart error")

@pytest.mark.asyncio
async def test_before_start_error_handling(stage):
    """Test that beforeStart errors are caught and logged."""
    # Create actor that fails in beforeStart
    # Verify error logged
    # Verify actor creation succeeds
```

#### 11. test_stage_close.py - **~14 tests**
**From**: StageClose.test.ts
**Coverage**: Stage shutdown sequencing
**Key Tests**:
- Basic shutdown
- Hierarchical shutdown order (children → parents → root)
- Supervisor shutdown
- Multiple close() calls (idempotent)
- Actors stop in correct order

```python
# Template structure:
global_stop_order = []

class TrackingActor(Actor):
    async def before_stop(self):
        global_stop_order.append(f"{self._id}-beforeStop")

@pytest.mark.asyncio
async def test_hierarchical_shutdown_order(stage):
    """Test that children stop before parents."""
    # Create parent with children
    # Close stage
    # Verify stop order correct
```

#### 12. test_mailbox_suspension.py - **~9 tests**
**From**: MailboxSuspension.test.ts
**Coverage**: Mailbox suspension behavior
**Key Tests**:
- Suspension state
- Message queuing during suspension
- Processing on resume
- Idempotent suspend/resume
- Integration with supervision

```python
# Template structure:
@pytest.mark.asyncio
async def test_mailbox_suspension_state():
    """Test suspension state transitions."""
    # Create actor
    # Get mailbox
    # Suspend
    # Verify isSuspended() == True
    # Resume
    # Verify isSuspended() == False
```

### Priority 3: Advanced Features

#### 13. test_actor_selection.py - **~8 tests**
**From**: ActorSelection.test.ts
**Coverage**: Actor lookup and discovery
**Key Tests**:
- Lookup by address
- Actor not found scenarios
- Directory integration

#### 14. test_root_actors.py - **~5 tests**
**From**: RootActors.test.ts
**Coverage**: PrivateRootActor and PublicRootActor
**Key Tests**:
- Root actor initialization
- Default parent behavior
- Root actor hierarchy

#### 15. test_observable_state.py - **~6 tests**
**From**: ObservableState.test.ts
**Coverage**: Test state observation
**Key Tests**:
- State snapshots
- awaitObservableState utility
- State value assertions

#### 16. test_enhanced_stop_sequence.py - **~8 tests**
**From**: EnhancedStopSequence.test.ts
**Coverage**: Graceful shutdown sequencing
**Key Tests**:
- Stop propagation
- Cleanup ordering
- Resource release

## Test Count Summary

| Category | Completed | Remaining | Total |
|----------|-----------|-----------|-------|
| Core Actor Tests | 30 | 0 | 30 |
| Mailbox Tests | 13 | 10 | 23 |
| Scheduler Tests | 15 | 0 | 15 |
| Supervision Tests | 0 | 19 | 19 |
| Lifecycle Tests | 0 | 10 | 10 |
| Directory Tests | 0 | 18 | 18 |
| Stage Tests | 0 | 14 | 14 |
| Integration Tests | 3 | 26 | 29 |
| **TOTAL** | **61** | **97** | **~158** |

Note: The TypeScript suite has 220+ tests, but some are duplicated across files or are integration tests. The Python suite aims for equivalent coverage with ~150-180 comprehensive tests.

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/actors/test_actor.py -v
```

### Run With Coverage
```bash
pytest tests/ --cov=domo_actors --cov-report=html
```

### Run Tests Matching Pattern
```bash
pytest tests/ -k "mailbox" -v
```

## Test Template

Use this template for new test files:

```python
"""
[Test File Name] - [Description]

Tests based on DomoActors-TS [TS File Name]
[N] test cases covering [coverage areas].
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


# Global storage for test actors
test_actors: Dict[str, 'TestActorImpl'] = {}


# ============================================================================
# Test Protocols and Implementations
# ============================================================================

class TestProtocol(ActorProtocol):
    """Test protocol interface."""
    async def test_method(self) -> None: ...


class TestActorImpl(Actor):
    """Test actor implementation."""

    def __init__(self):
        super().__init__()
        self._state = None

    async def test_method(self) -> None:
        self._state = "tested"


class TestInstantiator(ProtocolInstantiator):
    def instantiate(self, definition: Definition) -> Actor:
        actor = TestActorImpl()
        test_actors[definition.address().value_as_string()] = actor
        return actor


class TestProtocolImpl(Protocol):
    def type(self) -> str:
        return "TestActor"

    def instantiator(self) -> ProtocolInstantiator:
        return TestInstantiator()


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
    test_actors.clear()


# ============================================================================
# Tests
# ============================================================================

@pytest.mark.asyncio
async def test_example(stage):
    """Test description."""
    # Arrange
    actor: TestProtocol = stage.actor_for(
        TestProtocolImpl(),
        Definition("Test", Uuid7Address(), ())
    )
    await asyncio.sleep(0.05)

    # Act
    await actor.test_method()

    # Assert
    raw_actor = test_actors[actor.address().value_as_string()]
    assert raw_actor._state == "tested"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

## Next Steps

1. ✅ Complete core actor tests (30 tests)
2. ✅ Complete bounded mailbox tests (13 tests)
3. ✅ Complete scheduler tests (15 tests)
4. 📝 Create array mailbox tests (10 tests)
5. 📝 Create directory tests (18 tests)
6. 📝 Create supervision tests (19 tests)
7. 📝 Create lifecycle error handling tests (10 tests)
8. 📝 Create stage close tests (14 tests)
9. 📝 Create remaining integration tests

## Coverage Goals

- **Unit Tests**: 100% coverage of core classes
- **Integration Tests**: All major workflows tested
- **Edge Cases**: Error conditions and boundary cases
- **Performance**: Basic timing and load tests
- **Documentation**: All tests have clear descriptions

## Notes

- All test files follow the same structure as TypeScript tests
- Global dictionaries track actors for verification (like TS Maps)
- Async/await patterns match TypeScript behavior
- Test naming follows pytest conventions (test_*)
- Each test is isolated with fixtures
