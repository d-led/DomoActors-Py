"""
 Copyright © 2012-2025 Vaughn Vernon. All rights reserved.
 Copyright © 2012-2025 Kalele, Inc. All rights reserved.

 Licensed under the Reciprocal Public License 1.5

 See: LICENSE.md in repository root directory
 See: https://opensource.org/license/rpl-1-5
"""

"""
DomoActors - A Production-Ready Actor Model Toolkit for Python
"""

from domo_actors.actors.actor import Actor
from domo_actors.actors.actor_protocol import ActorProtocol
from domo_actors.actors.address import Address
from domo_actors.actors.definition import Definition
from domo_actors.actors.protocol import Protocol
from domo_actors.actors.stage import Stage, stage
from domo_actors.actors.local_stage import LocalStage
from domo_actors.actors.supervisor import Supervisor, SupervisionDirective, SupervisionScope
from domo_actors.actors.logger import Logger, ConsoleLogger
from domo_actors.actors.mailbox import Mailbox, OverflowPolicy
from domo_actors.actors.array_mailbox import ArrayMailbox
from domo_actors.actors.bounded_mailbox import BoundedMailbox

__version__ = "1.0.0"
__author__ = "Vaughn Vernon"
__license__ = "RPL-1.5"

__all__ = [
    "Actor",
    "ActorProtocol",
    "Address",
    "ArrayMailbox",
    "BoundedMailbox",
    "ConsoleLogger",
    "Definition",
    "LocalStage",
    "Logger",
    "Mailbox",
    "OverflowPolicy",
    "Protocol",
    "Stage",
    "stage",
    "Supervisor",
    "SupervisionDirective",
    "SupervisionScope",
]
