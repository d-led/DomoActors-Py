"""
 Copyright © 2012-2025 Vaughn Vernon. All rights reserved.
 Copyright © 2012-2025 Kalele, Inc. All rights reserved.

 Licensed under the Reciprocal Public License 1.5

 See: LICENSE.md in repository root directory
 See: https://opensource.org/license/rpl-1-5
"""

"""
Test dead letters listener for collecting undeliverable messages in tests.
"""

from typing import List
from domo_actors.actors.dead_letters import DeadLetter, DeadLettersListener


class TestDeadLettersListener:
    """
    Dead letters listener implementation for testing.

    Collects dead letters for test assertions.
    """

    def __init__(self) -> None:
        """Initialize the test listener."""
        self._dead_letters: List[DeadLetter] = []

    def handle(self, dead_letter: DeadLetter) -> None:
        """
        Handle a dead letter by collecting it.

        Args:
            dead_letter: The dead letter to collect
        """
        self._dead_letters.append(dead_letter)

    def dead_letters(self) -> List[DeadLetter]:
        """
        Get collected dead letters.

        Returns:
            List of collected dead letters
        """
        return self._dead_letters

    def count(self) -> int:
        """
        Get count of collected dead letters.

        Returns:
            Number of dead letters
        """
        return len(self._dead_letters)

    def clear(self) -> None:
        """Clear collected dead letters."""
        self._dead_letters.clear()
