"""
 Copyright © 2012-2025 Vaughn Vernon. All rights reserved.
 Copyright © 2012-2025 Kalele, Inc. All rights reserved.

 Licensed under the Reciprocal Public License 1.5

 See: LICENSE.md in repository root directory
 See: https://opensource.org/license/rpl-1-5
"""

"""
StageInternal - Internal stage interface with failure handling.
"""

from abc import ABC, abstractmethod
from domo_actors.actors.stage import Stage
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domo_actors.actors.directory import Directory
    from domo_actors.actors.supervised import Supervised


class StageInternal(Stage, ABC):
    """Internal stage interface with additional methods for actor system internals."""

    @abstractmethod
    def directory(self) -> 'Directory':
        """
        Get the actor directory.

        Returns:
            The directory for actor lookup
        """
        pass

    @abstractmethod
    async def handle_failure_of(self, supervised: 'Supervised') -> None:
        """
        Handle a failed actor.

        Args:
            supervised: The supervised actor that failed
        """
        pass
