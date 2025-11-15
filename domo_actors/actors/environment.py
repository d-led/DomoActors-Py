"""
 Copyright © 2012-2025 Vaughn Vernon. All rights reserved.
 Copyright © 2012-2025 Kalele, Inc. All rights reserved.

 Licensed under the Reciprocal Public License 1.5

 See: LICENSE.md in repository root directory
 See: https://opensource.org/license/rpl-1-5
"""

"""
Environment - Runtime context for actors.

Provides access to actor's address, mailbox, parent, logger, supervisor, etc.
"""

from typing import TYPE_CHECKING, Optional
from domo_actors.actors.execution_context import ExecutionContext, EmptyExecutionContext

if TYPE_CHECKING:
    from domo_actors.actors.address import Address
    from domo_actors.actors.mailbox import Mailbox
    from domo_actors.actors.actor import Actor
    from domo_actors.actors.logger import Logger
    from domo_actors.actors.stage import Stage
    from domo_actors.actors.supervisor import Supervisor
    from domo_actors.actors.scheduler import Scheduler
    from domo_actors.actors.definition import Definition
    from domo_actors.actors.dead_letters import DeadLetters


class Environment:
    """Actor runtime environment providing access to system services."""

    def __init__(
        self,
        address: 'Address',
        definition: 'Definition',
        mailbox: 'Mailbox',
        parent: Optional['Actor'],
        stage: 'Stage',
        logger: 'Logger',
        supervisor: Optional['Supervisor'] = None,
    ) -> None:
        """
        Initialize the environment.

        Args:
            address: Actor's unique address
            definition: Actor definition metadata
            mailbox: Actor's mailbox for message delivery
            parent: Parent actor (None for root actors)
            stage: The actor stage/system
            logger: Logger instance
            supervisor: Optional supervisor for fault tolerance
        """
        self._address = address
        self._definition = definition
        self._mailbox = mailbox
        self._parent = parent
        self._stage = stage
        self._logger = logger
        self._supervisor = supervisor
        self._current_message_execution_context: ExecutionContext = EmptyExecutionContext

    def address(self) -> 'Address':
        """Get the actor's address."""
        return self._address

    def definition(self) -> 'Definition':
        """Get the actor's definition."""
        return self._definition

    def mailbox(self) -> 'Mailbox':
        """Get the actor's mailbox."""
        return self._mailbox

    def parent(self) -> Optional['Actor']:
        """Get the parent actor."""
        return self._parent

    def stage(self) -> 'Stage':
        """Get the actor stage."""
        return self._stage

    def logger(self) -> 'Logger':
        """Get the logger."""
        return self._logger

    def supervisor(self) -> Optional['Supervisor']:
        """Get the supervisor."""
        return self._supervisor

    def set_supervisor(self, supervisor: 'Supervisor') -> None:
        """Set the supervisor."""
        self._supervisor = supervisor

    def scheduler(self) -> 'Scheduler':
        """Get the scheduler from the stage."""
        return self._stage.scheduler()

    def dead_letters(self) -> 'DeadLetters':
        """Get the dead letters facility from the stage."""
        return self._stage.dead_letters()

    def current_message_execution_context(self) -> ExecutionContext:
        """Get the current message execution context."""
        return self._current_message_execution_context

    def set_current_message_execution_context(self, context: ExecutionContext) -> None:
        """Set the current message execution context."""
        self._current_message_execution_context = context

    def __str__(self) -> str:
        """String representation."""
        return f"Environment(address={self._address}, parent={self._parent is not None})"
