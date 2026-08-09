"""
Handles MULLIGAN_CHOICE PDUs
"""

import logging

logger = logging.getLogger(__name__)

async def handle_mulligan_choice(pdu: dict, player_id: str, game_server) -> None:
    state = game_server.state
    player = state.get_player(player_id)

    if player_id is None:
        return