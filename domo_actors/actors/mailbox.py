"""
 Copyright © 2012-2025 Vaughn Vernon. All rights reserved.
 Copyright © 2012-2025 Kalele, Inc. All rights reserved.

 Licensed under the Reciprocal Public License 1.5

 See: LICENSE.md in repository root directory
 See: https://opensource.org/license/rpl-1-5
"""

"""
Mailbox - FIFO message queue interface for actors.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domo_actors.actors.message import Message


class OverflowPolicy(Enum):
    """Policy for handling mailbox overflow in bounded mailboxes."""

    DROP_OLDEST = "DROP_OLDEST"  # Remove oldest message when full
    DROP_NEWEST = "DROP_NEWEST"  # Reject newest message when full
    REJECT = "REJECT"  # Send to dead letters when full


class Mailbox(ABC):
    """Abstract mailbox interface for message queuing and delivery."""

    @abstractmethod
    def send(self, message: 'Message') -> None:
        """
        Send a message to the mailbox.

        Args:
            message: The message to enqueue
        """
        pass

    @abstractmethod
    def receive(self) -> 'Message':
        """
        Receive the next message from the queue.

        Returns:
            The next message or EmptyMessage if queue is empty
        """
        pass

    @abstractmethod
    async def dispatch(self) -> None:
        """Dispatch messages from the queue asynchronously."""
        pass

    @abstractmethod
    def suspend(self) -> None:
        """Suspend message processing (queue still accepts messages)."""
        pass

    @abstractmethod
    def resume(self) -> None:
        """Resume message processing."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the mailbox (no further message delivery)."""
        pass

    @abstractmethod
    def is_suspended(self) -> bool:
        """Check if the mailbox is suspended."""
        pass

    @abstractmethod
    def is_closed(self) -> bool:
        """Check if the mailbox is closed."""
        pass

    @abstractmethod
    def is_receivable(self) -> bool:
        """Check if there are messages available to receive."""
        pass
