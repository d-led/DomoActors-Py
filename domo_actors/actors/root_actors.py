"""
 Copyright © 2012-2025 Vaughn Vernon. All rights reserved.
 Copyright © 2012-2025 Kalele, Inc. All rights reserved.

 Licensed under the Reciprocal Public License 1.5

 See: LICENSE.md in repository root directory
 See: https://opensource.org/license/rpl-1-5
"""

"""
Root Actors - System infrastructure actors for the actor hierarchy.
"""

from domo_actors.actors.actor import Actor


class PrivateRootActor(Actor):
    """
    System root actor - supervises PublicRootActor.

    This is the top of the actor hierarchy and handles system-level supervision.
    """

    async def before_start(self) -> None:
        """Initialize the private root actor."""
        self.logger().debug("PrivateRootActor starting")

    async def before_stop(self) -> None:
        """Cleanup before stopping."""
        self.logger().debug("PrivateRootActor stopping")


class PublicRootActor(Actor):
    """
    Default parent for user-created actors.

    This actor serves as the default parent when no explicit parent is specified.
    It is supervised by PrivateRootActor.
    """

    async def before_start(self) -> None:
        """Initialize the public root actor."""
        self.logger().debug("PublicRootActor starting")

    async def before_stop(self) -> None:
        """Cleanup before stopping."""
        self.logger().debug("PublicRootActor stopping")
