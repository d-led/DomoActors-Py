"""
Scheduler tests - Task scheduling and timing.

Test cases covering scheduling, cancellation, and timing.
"""

import pytest
import asyncio
from datetime import timedelta
import time
from domo_actors.actors.scheduler import DefaultScheduler, Cancellable


# ============================================================================
# Helper Classes
# ============================================================================

class CounterHolder:
    """Helper class for tracking scheduled task executions."""

    def __init__(self, target: int = 1):
        self._count = 0
        self._target = target
        self._event = asyncio.Event()

    def increment(self):
        """Increment the counter."""
        self._count += 1
        if self._count >= self._target:
            self._event.set()

    def get_count(self) -> int:
        """Get current count."""
        return self._count

    async def wait_for_target(self, timeout: float = 2.0):
        """Wait until count reaches target."""
        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def scheduler():
    """Create a scheduler for testing."""
    s = DefaultScheduler()
    yield s
    s.close()


# ============================================================================
# Tests
# ============================================================================

# Test Group 1: scheduleOnce - One-time Execution
# ============================================================================

@pytest.mark.asyncio
async def test_schedule_once_executes_after_delay(scheduler):
    """Test that scheduleOnce executes after the specified delay."""
    holder = CounterHolder(target=1)

    start_time = time.time()

    scheduler.schedule_once(
        delay=timedelta(milliseconds=100),
        action=holder.increment
    )

    await holder.wait_for_target()

    elapsed = (time.time() - start_time) * 1000  # Convert to ms

    assert holder.get_count() == 1
    assert 80 <= elapsed <= 200  # Allow some tolerance


@pytest.mark.asyncio
async def test_schedule_once_immediate_execution(scheduler):
    """Test that scheduleOnce with zero delay executes immediately."""
    holder = CounterHolder(target=1)

    scheduler.schedule_once(
        delay=timedelta(milliseconds=0),
        action=holder.increment
    )

    await holder.wait_for_target(timeout=0.2)

    assert holder.get_count() == 1


@pytest.mark.asyncio
async def test_schedule_once_cancellation(scheduler):
    """Test that cancelling scheduleOnce prevents execution."""
    holder = CounterHolder(target=1)

    cancellable = scheduler.schedule_once(
        delay=timedelta(milliseconds=100),
        action=holder.increment
    )

    # Cancel immediately
    result = cancellable.cancel()

    assert result == True  # Successfully cancelled

    # Wait to ensure it doesn't execute
    await asyncio.sleep(0.2)

    assert holder.get_count() == 0


@pytest.mark.asyncio
async def test_cancellable_returns_false_when_already_cancelled(scheduler):
    """Test that cancel() returns false if already cancelled."""
    holder = CounterHolder(target=1)

    cancellable = scheduler.schedule_once(
        delay=timedelta(milliseconds=100),
        action=holder.increment
    )

    # First cancellation
    result1 = cancellable.cancel()
    assert result1 == True

    # Second cancellation
    result2 = cancellable.cancel()
    assert result2 == False  # Already cancelled


# Test Group 2: schedule - Repeating Execution
# ============================================================================

@pytest.mark.asyncio
async def test_schedule_repeat_multiple_executions(scheduler):
    """Test that schedule executes multiple times."""
    holder = CounterHolder(target=3)

    scheduler.schedule_repeat(
        initial_delay=timedelta(milliseconds=10),
        interval=timedelta(milliseconds=50),
        action=holder.increment
    )

    await holder.wait_for_target(timeout=1.0)

    assert holder.get_count() >= 3


@pytest.mark.asyncio
async def test_schedule_repeat_with_initial_delay(scheduler):
    """Test that repeating schedule respects initial delay."""
    holder = CounterHolder(target=2)

    start_time = time.time()

    scheduler.schedule_repeat(
        initial_delay=timedelta(milliseconds=100),
        interval=timedelta(milliseconds=50),
        action=holder.increment
    )

    await holder.wait_for_target(timeout=1.0)

    elapsed = (time.time() - start_time) * 1000

    assert holder.get_count() >= 2
    # First execution after 100ms, second after 150ms total
    assert elapsed >= 100


@pytest.mark.asyncio
async def test_schedule_repeat_stops_when_cancelled(scheduler):
    """Test that cancelling stops repeating execution."""
    holder = CounterHolder(target=2)

    cancellable = scheduler.schedule_repeat(
        initial_delay=timedelta(milliseconds=10),
        interval=timedelta(milliseconds=30),
        action=holder.increment
    )

    # Wait for 2 executions
    await holder.wait_for_target(timeout=0.5)

    count_at_cancel = holder.get_count()

    # Cancel
    cancellable.cancel()

    # Wait more and verify no additional executions
    await asyncio.sleep(0.2)

    assert holder.get_count() == count_at_cancel


# Test Group 3: close - Cleanup
# ============================================================================

@pytest.mark.asyncio
async def test_close_cancels_all_tasks():
    """Test that close() cancels all pending tasks."""
    scheduler = DefaultScheduler()
    holder = CounterHolder(target=1)

    # Schedule multiple tasks
    scheduler.schedule_once(
        delay=timedelta(milliseconds=100),
        action=holder.increment
    )

    scheduler.schedule_once(
        delay=timedelta(milliseconds=200),
        action=holder.increment
    )

    # Close immediately
    scheduler.close()

    # Wait and verify nothing executed
    await asyncio.sleep(0.3)

    assert holder.get_count() == 0


@pytest.mark.asyncio
async def test_close_is_idempotent():
    """Test that close() can be called multiple times safely."""
    scheduler = DefaultScheduler()

    scheduler.close()
    scheduler.close()  # Should not raise

    # No assertion needed - just shouldn't raise


# Test Group 4: Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_errors_in_callbacks_are_caught(scheduler):
    """Test that errors in scheduled callbacks are caught and logged."""
    holder = CounterHolder(target=1)

    def failing_action():
        holder.increment()
        raise ValueError("Intentional error")

    scheduler.schedule_once(
        delay=timedelta(milliseconds=10),
        action=failing_action
    )

    await holder.wait_for_target(timeout=0.2)

    # Should have executed despite error
    assert holder.get_count() == 1


# Test Group 5: Timing Accuracy
# ============================================================================

@pytest.mark.asyncio
async def test_delay_timing_accuracy(scheduler):
    """Test that delays are reasonably accurate."""
    holder = CounterHolder(target=1)
    delay_ms = 150

    start_time = time.time()

    scheduler.schedule_once(
        delay=timedelta(milliseconds=delay_ms),
        action=holder.increment
    )

    await holder.wait_for_target(timeout=1.0)

    elapsed_ms = (time.time() - start_time) * 1000

    # Allow ±50ms tolerance
    assert delay_ms - 50 <= elapsed_ms <= delay_ms + 100


@pytest.mark.asyncio
async def test_interval_timing_accuracy(scheduler):
    """Test that interval timing is reasonably accurate."""
    holder = CounterHolder(target=3)
    interval_ms = 60

    start_time = time.time()

    scheduler.schedule_repeat(
        initial_delay=timedelta(milliseconds=10),
        interval=timedelta(milliseconds=interval_ms),
        action=holder.increment
    )

    await holder.wait_for_target(timeout=1.0)

    elapsed_ms = (time.time() - start_time) * 1000

    # 3 executions: ~10ms + 60ms + 60ms = ~130ms
    # Allow some tolerance
    expected_min = 100
    expected_max = 250

    assert expected_min <= elapsed_ms <= expected_max


# Test Group 6: Data Passing (async callbacks)
# ============================================================================

@pytest.mark.asyncio
async def test_async_action_support(scheduler):
    """Test that async actions are supported."""
    holder = CounterHolder(target=1)

    async def async_action():
        await asyncio.sleep(0.01)
        holder.increment()

    scheduler.schedule_once(
        delay=timedelta(milliseconds=10),
        action=async_action
    )

    await holder.wait_for_target(timeout=0.5)

    assert holder.get_count() == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
