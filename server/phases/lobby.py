"""
Handles PLAYER_READY and LOBBY state, then transitions to GAME_SETUP
"""

import asyncio 
import logging
from server.game_server import GameServer
from shared.framing import read_pdu
from shared.constants import PDU
from shared.constants import MIN_DECK_SIZE, MAX_DECK_SIZE
from shared.constants import ErrorCode as ec
from server.pdu import builder

logger = logging.getLogger(__name__)

# This will be called by the dispatcher already -> see handler(pdu, player_id, game_server)
async def lobby_state(pdu: dict, player_id: str, game_server : GameServer):
    state = game_server.state

    # TODO: Add handling for empty id code?
    
    # Duplicate ID check
    if len(player_id) == 0:
        await game_server.send_to(
            player_id,
            builder.error(
                seq = state.next_seq(),
                code = '', # ADD CODE FOR THIS
                message = 'player_id is an empty string'
            )
        )
        return
    
    elif player_id not in state.player_ids and pdu.get('player_id') in state.player_ids:
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
        
    deck_size = len(pdu['deck'])
    if deck_size < MIN_DECK_SIZE:
        await game_server.send_to(
            player_id, 
            builder.error(
                seq = state.next_seq(),
                code = ec.ILLEGAL_DECK,
                message = f'Deck contains {deck_size} cards; minimum is {MIN_DECK_SIZE}.'
            ))
    elif deck_size > MAX_DECK_SIZE:
        await game_server.send_to(
            player_id, 
            builder.error(
                seq = state.next_seq(),
                code = ec.ILLEGAL_DECK,
                message = f'Deck contains {deck_size} cards; maximum is {MAX_DECK_SIZE}.'
            ))  
    else:    
        game_server.state.players[player_id].deck = pdu['deck'] 
        game_server.ready_players.add(player_id)
        game_server.send_to(
            player_id,
            builder.game_state_update(
                seq = state.next_seq(),
                state = builder.lobby_state(
                    players_ready = len(game_server.ready_players),
                    waiting_for = [] # TODO
                )
            ))      
        
    # TODO: Update lobby state (not yet implemented)
    
    if len(game_server.ready_players) == 2:
        logger.info("Both players ready. Starting GAME_SETUP.")
        await game_server.start_game_setup()
    