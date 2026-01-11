"""
 Copyright © 2012-2025 Vaughn Vernon. All rights reserved.
 Copyright © 2012-2025 Kalele, Inc. All rights reserved.

 Licensed under the Reciprocal Public License 1.5

 See: LICENSE.md in repository root directory
 See: https://opensource.org/license/rpl-1-5
"""

"""
ArrayMailbox - Unbounded FIFO mailbox implementation.

Inspired by phony's efficient mailbox design:
- Only one dispatch task runs at a time (tracked by _dispatching flag)
- Dispatch task processes all queued messages until empty
- Prevents task explosion when sending many messages rapidly
"""

import asyncio
from collections import deque
from typing import Deque
from domo_actors.actors.mailbox import Mailbox
from domo_actors.actors.message import Message, EmptyMessage


class ArrayMailbox(Mailbox):
    """
    Unbounded FIFO mailbox using a deque for message storage.
    
    Uses a single dispatch task pattern (inspired by phony):
    - Only creates one dispatch task at a time
    - Dispatch task processes all queued messages until empty
    - Thread-safe for asyncio's single-threaded event loop
    
    Why deque instead of list?
    - deque provides O(1) append and popleft operations (optimal for FIFO)
    - list would require O(n) popleft (shifting all elements)
    - deque's block allocation reduces memory allocations for high-throughput scenarios
    - For asyncio (single event loop), thread-safety is not needed
    """

    def __init__(self) -> None:
        """Initialize an empty mailbox."""
        self._queue: Deque[Message] = deque()  # deque is optimal for FIFO: O(1) append/popleft
        self._closed: bool = False
        self._suspended: bool = False
        self._dispatching: bool = False  # Track if dispatch task is running

    def send(self, message: Message) -> None:
        """
        Send a message to the mailbox.

        Args:
            message: The message to enqueue
        """
        if not self._closed:
            self._queue.append(message)

            # Only start dispatch if not already dispatching and not suspended
            # This prevents creating thousands of tasks when sending rapidly
            # (inspired by phony's single-worker pattern)
            if not self._suspended and not self._dispatching:
                self._dispatching = True
                asyncio.create_task(self._dispatch_all())
        else:
            # Mailbox is closed - send to dead letters
            from domo_actors.actors.dead_letters import DeadLetter

            dead_letter = DeadLetter(message.to(), message.representation())
            message.to().stage().dead_letters().failed_delivery(dead_letter)
            message.deferred().resolve(None)  # Resolve with None to indicate actor stopped

    def receive(self) -> Message:
        """
        Receive the next message from the queue.

        Returns:
            The next message or EmptyMessage if queue is empty
        """
        if self._queue:
            return self._queue.popleft()
        return EmptyMessage

    async def _dispatch_all(self) -> None:
        """
        Dispatch all messages from the queue until empty.
        
        This is the main dispatch loop that processes all queued messages.
        Only one instance of this coroutine runs at a time (enforced by _dispatching flag).
        
        Inspired by phony's worker pattern: single worker processes all messages
        until queue is empty, then exits. New messages trigger a new worker.
        """
        try:
            # Process all messages until queue is empty
            while True:
                # Check if we should stop dispatching
                if self._suspended or self._closed:
                    break

                # Receive next message
                message = self.receive()

                # If no message available, we're done
                if not message.is_deliverable():
                    break

                # Deliver the message
                await message.deliver()

                # Continue loop to process next message (if any)
        finally:
            # Always clear dispatching flag when done
            self._dispatching = False
            
            # If more messages arrived while we were processing, start a new dispatch
            # This handles the case where messages arrive during message delivery
            if not self._suspended and not self._closed and self.is_receivable():
                self._dispatching = True
                asyncio.create_task(self._dispatch_all())

    async def dispatch(self) -> None:
        """
        Dispatch messages from the queue (legacy method for compatibility).
        
        This method is kept for backward compatibility but delegates to _dispatch_all().
        The new implementation uses _dispatch_all() which processes all messages efficiently.
        """
        # If already dispatching, don't start another task
        if self._dispatching:
            return
        
        # Start dispatch if not suspended/closed and have messages
        if not self._suspended and not self._closed and self.is_receivable():
            self._dispatching = True
            asyncio.create_task(self._dispatch_all())

    def suspend(self) -> None:
        """Suspend message processing."""
        self._suspended = True

    def resume(self) -> None:
        """Resume message processing and trigger dispatch."""
        self._suspended = False

        # Trigger dispatch if there are pending messages and not already dispatching
        if self.is_receivable() and not self._dispatching:
            self._dispatching = True
            asyncio.create_task(self._dispatch_all())

    def close(self) -> None:
        """Close the mailbox - no further message delivery."""
        self._closed = True

    def is_suspended(self) -> bool:
        """
        Check if the mailbox is suspended.

        Returns:
            True if suspended
        """
        return self._suspended

    def is_closed(self) -> bool:
        """
        Check if the mailbox is closed.

        Returns:
            True if closed
        """
        return self._closed

    def is_receivable(self) -> bool:
        """
        Check if there are messages available to receive.

        Returns:
            True if queue has messages
        """
        return len(self._queue) > 0

    def size(self) -> int:
        """
        Get the current queue size.

        Returns:
            Number of messages in the queue
        """
        return len(self._queue)

    def __str__(self) -> str:
        """String representation."""
        return f"ArrayMailbox(size={len(self._queue)}, suspended={self._suspended}, closed={self._closed}, dispatching={self._dispatching})"
