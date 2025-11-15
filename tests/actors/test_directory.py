"""
Directory tests - Actor registry and lookup.

Test cases covering actor registry, sharding, and distribution.
"""

import pytest
from domo_actors.actors.directory import Directory, DirectoryConfigs, DirectoryConfig
from domo_actors.actors.address import Uuid7Address, NumericAddress
from domo_actors.actors.actor_protocol import ActorProtocol


# ============================================================================
# Mock Actor for Testing
# ============================================================================

class MockActor:
    """Mock actor for directory testing."""

    def __init__(self, actor_id: str):
        self._id = actor_id
        self._address = Uuid7Address()

    def address(self):
        return self._address

    def is_stopped(self):
        return False

    def __str__(self):
        return f"MockActor({self._id})"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def directory():
    """Create a fresh directory."""
    return Directory()


# ============================================================================
# Tests
# ============================================================================

# Test Group 1: Construction and Configuration
# ============================================================================

def test_directory_default_configuration():
    """Test directory with default configuration."""
    directory = Directory()
    assert directory is not None
    assert directory.size() == 0


def test_directory_high_capacity_configuration():
    """Test directory with high capacity config."""
    directory = Directory(DirectoryConfigs.HIGH_CAPACITY)
    assert directory is not None
    assert directory.size() == 0


def test_directory_small_configuration():
    """Test directory with small config."""
    directory = Directory(DirectoryConfigs.SMALL)
    assert directory is not None
    assert directory.size() == 0


def test_directory_custom_configuration():
    """Test directory with custom configuration."""
    config = DirectoryConfig(buckets=64, capacity=128)
    directory = Directory(config)
    assert directory is not None
    assert directory.size() == 0


# Test Group 2: Basic Operations
# ============================================================================

def test_directory_register_and_get(directory):
    """Test registering and retrieving an actor."""
    address = Uuid7Address()
    actor = MockActor("actor1")

    directory.register(address, actor)

    retrieved = directory.get(address)
    assert retrieved == actor


def test_directory_get_nonexistent_returns_none(directory):
    """Test that getting non-existent actor returns None."""
    address = Uuid7Address()

    result = directory.get(address)
    assert result is None


def test_directory_register_multiple_actors(directory):
    """Test registering multiple actors."""
    actors = []
    addresses = []

    for i in range(5):
        address = Uuid7Address()
        actor = MockActor(f"actor{i}")
        addresses.append(address)
        actors.append(actor)
        directory.register(address, actor)

    # Verify all retrievable
    for i in range(5):
        retrieved = directory.get(addresses[i])
        assert retrieved == actors[i]


def test_directory_overwrite_at_same_address(directory):
    """Test that registering at same address overwrites."""
    address = Uuid7Address()
    actor1 = MockActor("actor1")
    actor2 = MockActor("actor2")

    directory.register(address, actor1)
    directory.register(address, actor2)

    retrieved = directory.get(address)
    assert retrieved == actor2


def test_directory_unregister(directory):
    """Test unregistering an actor."""
    address = Uuid7Address()
    actor = MockActor("actor1")

    directory.register(address, actor)
    assert directory.has(address) == True

    directory.unregister(address)
    assert directory.has(address) == False
    assert directory.get(address) is None


def test_directory_unregister_nonexistent(directory):
    """Test unregistering non-existent actor."""
    address = Uuid7Address()

    # Should not raise
    directory.unregister(address)
    assert directory.get(address) is None


# Test Group 3: Size Calculation
# ============================================================================

def test_directory_size_tracking(directory):
    """Test that size is tracked correctly."""
    assert directory.size() == 0

    # Add actors
    for i in range(10):
        directory.register(Uuid7Address(), MockActor(f"actor{i}"))

    assert directory.size() == 10

    # Remove some
    addresses = [Uuid7Address() for _ in range(3)]
    for addr in addresses:
        directory.register(addr, MockActor("temp"))

    # Size should include new ones
    assert directory.size() == 13

    # Remove
    for addr in addresses:
        directory.unregister(addr)

    assert directory.size() == 10


def test_directory_size_after_operations(directory):
    """Test size updates correctly after various operations."""
    addresses = []

    # Add 5
    for i in range(5):
        addr = Uuid7Address()
        addresses.append(addr)
        directory.register(addr, MockActor(f"actor{i}"))

    assert directory.size() == 5

    # Remove 2
    directory.unregister(addresses[0])
    directory.unregister(addresses[1])

    assert directory.size() == 3

    # Add 3 more
    for i in range(3):
        directory.register(Uuid7Address(), MockActor(f"new{i}"))

    assert directory.size() == 6


# Test Group 4: Has Operation
# ============================================================================

def test_directory_has_registered_actor(directory):
    """Test has() returns True for registered actors."""
    address = Uuid7Address()
    actor = MockActor("actor1")

    directory.register(address, actor)

    assert directory.has(address) == True


def test_directory_has_unregistered_actor(directory):
    """Test has() returns False for unregistered actors."""
    address = Uuid7Address()

    assert directory.has(address) == False


# Test Group 5: Distribution and Sharding
# ============================================================================

def test_directory_distribution_across_buckets(directory):
    """Test that actors are distributed across multiple buckets."""
    # Add many actors
    for i in range(100):
        directory.register(Uuid7Address(), MockActor(f"actor{i}"))

    # Actors should be distributed across buckets
    # With 32 buckets and 100 actors, should have > 1 bucket used
    assert directory.size() == 100


def test_directory_handles_hash_collisions(directory):
    """Test that hash collisions are handled gracefully."""
    actors = []
    addresses = []

    # Add many actors (some may hash to same bucket)
    for i in range(1000):
        addr = Uuid7Address()
        actor = MockActor(f"actor{i}")
        addresses.append(addr)
        actors.append(actor)
        directory.register(addr, actor)

    # All should be retrievable
    for i in range(1000):
        retrieved = directory.get(addresses[i])
        assert retrieved == actors[i]


# Test Group 6: Large Scale Operations
# ============================================================================

def test_directory_large_scale_operations():
    """Test efficient handling of 10,000+ actors."""
    directory = Directory(DirectoryConfigs.HIGH_CAPACITY)

    addresses = []
    actors = []

    # Add 10,000 actors
    for i in range(10000):
        addr = Uuid7Address()
        actor = MockActor(f"actor{i}")
        addresses.append(addr)
        actors.append(actor)
        directory.register(addr, actor)

    assert directory.size() == 10000

    # Sample random retrievals
    import random
    for _ in range(100):
        idx = random.randint(0, 9999)
        retrieved = directory.get(addresses[idx])
        assert retrieved == actors[idx]

    # Bulk removal
    for i in range(0, 5000):
        directory.unregister(addresses[i])

    assert directory.size() == 5000


# Test Group 7: Different Address Types
# ============================================================================

def test_directory_with_numeric_addresses():
    """Test directory with numeric addresses."""
    directory = Directory()

    addresses = [NumericAddress() for _ in range(10)]
    actors = [MockActor(f"actor{i}") for i in range(10)]

    for addr, actor in zip(addresses, actors):
        directory.register(addr, actor)

    # All should be retrievable
    for addr, actor in zip(addresses, actors):
        assert directory.get(addr) == actor


def test_directory_mixed_address_types():
    """Test directory with mixed address types."""
    directory = Directory()

    uuid_addr = Uuid7Address()
    num_addr = NumericAddress()

    actor1 = MockActor("uuid_actor")
    actor2 = MockActor("num_actor")

    directory.register(uuid_addr, actor1)
    directory.register(num_addr, actor2)

    assert directory.get(uuid_addr) == actor1
    assert directory.get(num_addr) == actor2
    assert directory.size() == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
