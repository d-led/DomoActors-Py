# DomoActors-Py Quick Start Guide

## Installation

```bash
pip install domo-actors
```

Or install from source:
```bash
git clone https://github.com/VaughnVernon/DomoActors-Py.git
cd DomoActors-Py
pip install -e .
```

## Your First Actor in 5 Minutes

### 1. Import Required Components

```python
import asyncio
from domo_actors import (
    Actor,
    ActorProtocol,
    Protocol,
    ProtocolInstantiator,
    Definition,
    LocalStage,
    Uuid7Address
)
```

### 2. Define the Protocol Interface

The protocol interface defines what messages your actor can receive:

```python
class Counter(ActorProtocol):
    """Counter protocol - defines the actor's interface."""

    async def increment(self) -> None:
        """Increment the counter."""
        pass

    async def get_value(self) -> int:
        """Get the current count."""
        pass
```

### 3. Implement the Actor

The actor implementation handles the actual logic:

```python
class CounterActor(Actor):
    """Counter actor implementation."""

    def __init__(self):
        super().__init__()
        self._count = 0

    async def increment(self) -> None:
        """Increment the counter."""
        self._count += 1

    async def get_value(self) -> int:
        """Get the current count."""
        return self._count
```

### 4. Create the Protocol and Instantiator

These wire up the actor creation:

```python
class CounterInstantiator(ProtocolInstantiator):
    """Creates Counter actors."""

    def instantiate(self, definition: Definition) -> Actor:
        return CounterActor()


class CounterProtocol(Protocol):
    """Counter protocol implementation."""

    def type(self) -> str:
        return "Counter"

    def instantiator(self) -> ProtocolInstantiator:
        return CounterInstantiator()
```

### 5. Use Your Actor

```python
async def main():
    # Create the actor system
    stage = LocalStage()

    # Create a counter actor
    counter: Counter = stage.actor_for(
        CounterProtocol(),
        Definition("Counter", Uuid7Address(), ())
    )

    # Use the actor (messages are async!)
    await counter.increment()
    await counter.increment()
    await counter.increment()

    # Get the value
    value = await counter.get_value()
    print(f"Count: {value}")  # Output: Count: 3

    # Cleanup
    await stage.close()


if __name__ == "__main__":
    asyncio.run(main())
```

## Key Concepts Explained

### Actors
- **Isolated state**: Each actor has its own private state
- **Message-based**: Actors communicate via async messages
- **Sequential processing**: Messages are processed one at a time

### Messages
- **Automatic**: Method calls are automatically converted to messages
- **Asynchronous**: All actor method calls return promises (are awaitable)
- **FIFO**: Messages are processed in order

### Lifecycle Hooks

Customize actor behavior with lifecycle hooks:

```python
class MyActor(Actor):
    async def before_start(self):
        """Called before actor starts - initialize state."""
        self.logger().info("Starting up!")

    async def before_stop(self):
        """Called before actor stops - cleanup."""
        self.logger().info("Shutting down!")
```

### Child Actors

Create actor hierarchies:

```python
class ParentActor(Actor):
    async def create_child(self):
        # Create a child actor
        child = self.child_actor_for(
            ChildProtocol(),
            Definition("Child", Uuid7Address(), (some, params))
        )
        # Child is now supervised by this actor
        return child
```

### Supervision

Handle failures gracefully:

```python
from domo_actors import DefaultSupervisor, SupervisionDirective

class MySupervisor(DefaultSupervisor):
    def decide_directive(self, error, supervised, strategy):
        if isinstance(error, ValueError):
            return SupervisionDirective.RESUME  # Continue
        else:
            return SupervisionDirective.RESTART  # Restart actor
```

## Common Patterns

### Request-Response

```python
class Calculator(ActorProtocol):
    async def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        pass

class CalculatorActor(Actor):
    async def add(self, a: int, b: int) -> int:
        return a + b

# Usage
calc: Calculator = stage.actor_for(CalculatorProtocol(), definition)
result = await calc.add(5, 3)  # Returns 8
```

### Actor State

```python
class BankAccount(ActorProtocol):
    async def deposit(self, amount: float) -> float:
        pass

class BankAccountActor(Actor):
    def __init__(self, initial_balance: float):
        super().__init__()
        self._balance = initial_balance  # Private state

    async def deposit(self, amount: float) -> float:
        self._balance += amount  # State changes are isolated
        return self._balance
```

### Scheduled Tasks

```python
from datetime import timedelta

class PeriodicActor(Actor):
    async def before_start(self):
        scheduler = self.environment().scheduler()

        # Run every 5 seconds
        scheduler.schedule_repeat(
            initial_delay=timedelta(seconds=1),
            interval=timedelta(seconds=5),
            action=self.periodic_task
        )

    def periodic_task(self):
        self.logger().info("Periodic task running!")
```

## Testing

Use the built-in test utilities:

```python
from domo_actors.actors.testkit import await_assert

async def test_counter():
    stage = LocalStage()
    counter = stage.actor_for(CounterProtocol(), definition)

    await counter.increment()

    # Wait for assertion to pass
    async def check():
        value = await counter.get_value()
        assert value == 1

    await await_assert(check, timeout=2.0)

    await stage.close()
```

## Next Steps

1. **Read the full README** for complete documentation
2. **Explore examples/** for real-world patterns
3. **Check tests/** for more usage examples
4. **Read the TypeScript docs** (patterns translate directly)

## Common Issues

### "Address already exists"
Each actor needs a unique address:
```python
# ✓ Good - new address each time
counter1 = stage.actor_for(CounterProtocol(), Definition("C1", Uuid7Address(), ()))
counter2 = stage.actor_for(CounterProtocol(), Definition("C2", Uuid7Address(), ()))
```

### "Actor not responding"
Remember to await actor methods:
```python
# ✗ Bad
counter.increment()  # Returns promise, doesn't execute

# ✓ Good
await counter.increment()  # Executes the message
```

### "Circular imports"
Use TYPE_CHECKING for type hints:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .other_module import OtherActor
```

## Help & Support

- **Issues**: https://github.com/VaughnVernon/DomoActors-Py/issues
- **Discussions**: https://github.com/VaughnVernon/DomoActors-Py/discussions
- **Examples**: See the `examples/` directory

Happy coding with DomoActors!
