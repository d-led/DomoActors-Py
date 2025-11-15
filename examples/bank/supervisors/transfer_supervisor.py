"""
Transfer Supervisor - Supervises TransferCoordinator actor.

Uses Resume strategy with transfer-specific error analysis.
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


class TransferSupervisor(DefaultSupervisor):
    """
    Transfer supervisor implementation.

    Supervises TransferCoordinator with Resume strategy.
    Provides transfer-specific error analysis.
    """

    async def inform(self, error: Exception, supervised: Supervised) -> None:
        """Inform of error with transfer-specific context."""
        # Get execution context
        execution_context = supervised.actor().life_cycle().environment().current_message_execution_context()
        command = execution_context.get_value('command') or 'unknown'
        request = execution_context.get_value('request')

        # Transfer-specific error analysis
        additional_details = 'None'
        message = str(error).lower()

        if 'account not found' in message:
            additional_details = 'Non-existing account.'
        elif 'must be different accounts' in message or 'different accounts' in message:
            additional_details = 'The from-account and to-account are the same but must be different.'
        elif 'max retries' in message:
            additional_details = 'Transfer failed, bank will refund from account.'

        # Format error message
        explained = failure_explanation(error, command, request, additional_details, '***')

        # Log the error with TypeScript-style formatting
        print('**********************************************************************', file=sys.stderr)
        print(f'*** Transfer Supervisor on behalf of {supervised.actor().type()}', file=sys.stderr)
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
