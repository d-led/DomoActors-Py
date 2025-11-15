"""
 Copyright © 2012-2025 Vaughn Vernon. All rights reserved.
 Copyright © 2012-2025 Kalele, Inc. All rights reserved.

 Licensed under the Reciprocal Public License 1.5

 See: LICENSE.md in repository root directory
 See: https://opensource.org/license/rpl-1-5
"""

"""
LifeCycle - Actor lifecycle management interface and base class.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domo_actors.actors.environment import Environment


class LifeCycle(ABC):
    """Abstract lifecycle interface for actors."""

    @abstractmethod
    async def before_start(self) -> None:
        """Hook called before the actor starts."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the actor."""
        pass

    @abstractmethod
    async def before_restart(self, reason: Exception) -> None:
        """Hook called before the actor restarts."""
        pass

    @abstractmethod
    async def after_restart(self) -> None:
        """Hook called after the actor restarts."""
        pass

    @abstractmethod
    async def before_resume(self) -> None:
        """Hook called before the actor resumes after suspension."""
        pass

    @abstractmethod
    async def before_stop(self) -> None:
        """Hook called before the actor stops."""
        pass

    @abstractmethod
    async def after_stop(self) -> None:
        """Hook called after the actor stops."""
        pass

    @abstractmethod
    async def restart(self, reason: Exception) -> None:
        """Restart the actor due to a failure."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the actor."""
        pass

    @abstractmethod
    def is_stopped(self) -> bool:
        """Check if the actor is stopped."""
        pass

    @abstractmethod
    def environment(self) -> 'Environment':
        """Get the actor's environment."""
        pass
