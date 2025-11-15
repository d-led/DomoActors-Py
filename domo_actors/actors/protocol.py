"""
 Copyright © 2012-2025 Vaughn Vernon. All rights reserved.
 Copyright © 2012-2025 Kalele, Inc. All rights reserved.

 Licensed under the Reciprocal Public License 1.5

 See: LICENSE.md in repository root directory
 See: https://opensource.org/license/rpl-1-5
"""

"""
Protocol - Factory interface for actor instantiation.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domo_actors.actors.actor import Actor
    from domo_actors.actors.definition import Definition


class ProtocolInstantiator(ABC):
    """Factory interface for creating actor instances."""

    @abstractmethod
    def instantiate(self, definition: 'Definition') -> 'Actor':
        """
        Create an actor instance from a definition.

        Args:
            definition: The actor definition with parameters

        Returns:
            A new actor instance
        """
        pass


class Protocol(ABC):
    """Protocol interface defining actor type and instantiation."""

    @abstractmethod
    def type(self) -> str:
        """
        Get the protocol type name.

        Returns:
            String identifier for the protocol
        """
        pass

    @abstractmethod
    def instantiator(self) -> ProtocolInstantiator:
        """
        Get the protocol instantiator.

        Returns:
            A ProtocolInstantiator for creating actors
        """
        pass
