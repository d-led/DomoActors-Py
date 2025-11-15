"""
 Copyright © 2012-2025 Vaughn Vernon. All rights reserved.
 Copyright © 2012-2025 Kalele, Inc. All rights reserved.

 Licensed under the Reciprocal Public License 1.5

 See: LICENSE.md in repository root directory
 See: https://opensource.org/license/rpl-1-5
"""

"""
Execution Context - Request-scoped context for message processing.

Provides key-value storage that propagates across collaborating actors.
"""

from typing import TypeVar, Generic, Dict, Any, Optional

T = TypeVar('T')


class ExecutionContext:
    """Request-scoped context that can be copied and propagated."""

    def __init__(self, values: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the execution context.

        Args:
            values: Optional dictionary of initial values
        """
        self._values: Dict[str, Any] = values.copy() if values else {}

    def set_value(self, key: str, value: Any) -> 'ExecutionContext':
        """
        Set a value in the context.

        Args:
            key: The key to set
            value: The value to store

        Returns:
            Self for method chaining
        """
        self._values[key] = value
        return self

    def get_value(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        Get a value from the context.

        Args:
            key: The key to retrieve
            default: Default value if key not found

        Returns:
            The value or default
        """
        return self._values.get(key, default)

    def has_value(self, key: str) -> bool:
        """
        Check if a key exists in the context.

        Args:
            key: The key to check

        Returns:
            True if the key exists
        """
        return key in self._values

    def copy(self) -> 'ExecutionContext':
        """
        Create a copy of this context.

        Returns:
            A new ExecutionContext with copied values
        """
        return ExecutionContext(self._values)

    def propagate(self) -> None:
        """Propagate context to collaborators (hook for extensions)."""
        pass

    def clear(self) -> None:
        """Clear all values from the context."""
        self._values.clear()

    def __str__(self) -> str:
        """
        String representation.

        Returns:
            String showing the context values
        """
        return f"ExecutionContext({self._values})"


# Singleton empty context
EmptyExecutionContext = ExecutionContext()
