"""
Handles routing of client PDUs to the correct handler
"""

import logging
from shared.constants import PDU, ErrorCode
from server.pdu import builder
from server.rules.engine import GameEngineError

logger = logging.getLogger(__name__)

class Dispatcher:
    def __init__(self):
        self._handlers: dict = {}

    def register(self, pdu_type: str, handler) -> None:
        self._handlers[pdu_type] = handler

    async def dispatch(self, pdu: dict, player_id: str, game_server) -> None:
        pdu_type = pdu.get("type")

        if pdu_type is None:
            await game_server.send_to(
                player_id,
                builder.error(
                    seq = game_server.state.next_seq(),
                    code = ErrorCode.INVALID_JSON,
                    message = "PDU is missing the required 'type' field.",
                    rejected_action = pdu
                )
            )
            return

        handler = self._handlers.get(pdu_type)
        if handler is None:
            logger.warning("Unknown PDU type '%s' from %s", pdu_type, player_id)
            await game_server.send_to(
                player_id,
                builder.error(
                    seq = game_server.state.next_seq(),
                    code = ErrorCode.UNKNOWN_TYPE,
                    message = f"Unknown PDU type: '{pdu_type}'.",
                    rejected_action = pdu
                )
            )
            return

        logger.debug("Dispatching %s from %s", pdu_type, player_id)
        await handler(pdu, player_id, game_server)

        try:
            await handler(pdu, player_id, game_server)
        except GameEngineError as e:
            logger.warning("Engine rule violation by '%s': [%s] %s", player_id, e.code, e.message)
            await game_server.send_to(
                player_id,
                builder.error(
                    seq=game_server.state.next_seq(),
                    code=e.code,
                    message=e.message,
                    rejected_action=pdu
                )
            )
        except Exception as e:
            logger.exception("Unexpected server error dispatching '%s' from '%s'", pdu_type, player_id)
            await game_server.send_to(
                player_id,
                builder.error(
                    seq=game_server.state.next_seq(),
                    code=ErrorCode.ILLEGAL_ACTION,
                    message="An unexpected internal error occurred.",
                    rejected_action=pdu
                )
            )