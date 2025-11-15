"""
Bank Supervisor - Supervises Bank and Teller actors.

Uses Resume strategy with "let it crash" philosophy.
"""

from __future__ import annotations
from domo_actors.actors.supervisor import (
    DefaultSupervisor,
    SupervisionDirective,
    SupervisionStrategy,
    Supervised
)
from domo_actors.actors.logger import DefaultLogger
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from supervisors.failure_informant import failure_explanation


class BankSupervisor(DefaultSupervisor):
    """
    Bank supervisor implementation.

    Supervises Bank and Teller actors with Resume strategy.
    Implements "let it crash" - actors throw on invalid input,
    supervisor catches and reports.
    """

    async def inform(self, error: Exception, supervised: Supervised) -> None:
        """Inform of error with context-aware message."""
        # Get execution context
        execution_context = supervised.actor().life_cycle().environment().current_message_execution_context()
        command = execution_context.get_value('command') or 'unknown'
        request = execution_context.get_value('request')

        # Format error message
        explained = failure_explanation(error, command, request, 'None', '***')

        # Log the error with TypeScript-style formatting
        print('**********************************************************************', file=sys.stderr)
        print(f'*** Bank Supervisor on behalf of {supervised.actor().type()}', file=sys.stderr)
        print(explained, file=sys.stderr)
        print('***', file=sys.stderr)
        print('**********************************************************************', file=sys.stderr)

        # Call parent to handle supervision
        await super().inform(error, supervised)

    def decide_directive(
        self,
        error: Exception,
        supervised: Supervised,
        strategy: SupervisionStrategy
    ) -> SupervisionDirective:
        """Decide supervision directive - always Resume."""
        return SupervisionDirective.RESUME
