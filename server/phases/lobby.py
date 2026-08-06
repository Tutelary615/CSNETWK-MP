"""
Handles PLAYER_READY and LOBBY state, then transitions to GAME_SETUP
"""

import asyncio 
import logging
from server.state.game_state import GameState
from shared.framing import read_pdu
from shared.constants import PDU
from shared.constants import MIN_DECK_SIZE, MAX_DECK_SIZE
from shared.constants import ErrorCode as ec
from server.pdu import builder

logger = logging.getLogger(__name__)

# This will be called by the dispatcher already -> see handler(pdu, player_id, game_server)
async def lobby_state(pdu: dict, player_id: str, game_server):
    state = game_server.state

    # TODO: Add handling for empty id code?

    # Duplicate ID check
    for existing_id in state.player_ids:
        if existing_id != player_id and pdu.get("player_id") == existing_id:
            await game_server.send_to(
                player_id,
                builder.error(
                    seq = state.next_seq(),
                    code = ec.DUPLICATE_ID,
                    message = f"Player ID '{pdu.get('player_id')} is already taken.",
                    rejected_action = pdu
                )
            )
            return

    # TODO: Change this implementation
    """
    elif deck_size > MAX_DECK_SIZE:
        await game_server.dispatcher.dispatch(error(seq, ec.ILLEGAL_DECK, f'Deck contains {deck_size} cards; maximum is {MAX_DECK_SIZE}'))
    elif deck_size < MIN_DECK_SIZE:
        await game_server.dispatcher.dispatch(error(seq, ec.ILLEGAL_DECK, f'Deck contains {deck_size} cards; minimum is {MIN_DECK_SIZE}'))
    
    elif seq_nums.get(player_id) != None and seq != seq_nums.get(player_id) + 1: 
        await game_server.dispatcher.dispatch(error(seq, ec.DUPLICATE_ID, f'ID {player_id} is taken'))
    else:
        seq_nums[player_id] = seq
        # await game_server.dispatcher.dispatch() GAME STATE UPDATE
    """

    # TODO: Update player's deck in player_state

    game_server.ready_players.add(player_id)
    
    # TODO: Update lobby state (not yet implemented)

    if len(game_server.ready_players) == 2:
        logger.info("Both players ready. Starting GAME_SETUP.")
        await game_server.start_game_setup()
    