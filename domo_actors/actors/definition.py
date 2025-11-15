"""
 Copyright © 2012-2025 Vaughn Vernon. All rights reserved.
 Copyright © 2012-2025 Kalele, Inc. All rights reserved.

 Licensed under the Reciprocal Public License 1.5

 See: LICENSE.md in repository root directory
 See: https://opensource.org/license/rpl-1-5
"""

"""
Definition - Metadata bundle for actor instantiation.
"""

from typing import Any, Tuple
from domo_actors.actors.address import Address


class Definition:
    """Encapsulates actor type, address, and constructor parameters."""

    def __init__(self, actor_type: str, address: Address, parameters: Tuple[Any, ...] = ()) -> None:
        """
        Initialize an actor definition.

        Args:
            actor_type: String identifier for the actor type
            address: Unique address for the actor
            parameters: Tuple of constructor parameters
        """
        self._type = actor_type
        self._address = address
        self._parameters = parameters

    def type(self) -> str:
        """
        Get the actor type.

        Returns:
            The actor type string
        """
        return self._type

    def address(self) -> Address:
        """
        Get the actor address.

        Returns:
            The actor's address
        """
        return self._address

    def parameters(self) -> Tuple[Any, ...]:
        """
        Get the constructor parameters.

        Returns:
            Tuple of parameters
        """
        return self._parameters

    def __str__(self) -> str:
        """
        String representation.

        Returns:
            String describing the definition
        """
        return f"Definition(type={self._type}, address={self._address}, parameters={len(self._parameters)})"
