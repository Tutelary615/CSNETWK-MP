"""
Handles routing of client PDUs to the correct handler
"""

import logging
from shared.constants import PDU

logger = logging.getLogger(__name__)

class Dispatcher:
    def __init__(self):
        self._handlers: dict = {}

    def register(self, pdu_type: str, handler) -> None:
        self._handlers[pdu_type] = handler