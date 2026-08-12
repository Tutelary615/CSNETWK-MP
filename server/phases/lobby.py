"""
Handles PLAYER_READY and LOBBY state, then transitions to GAME_SETUP
"""

import asyncio 
import logging
from shared.framing import read_pdu
from shared.cards import is_valid_card_id
from shared.constants import PDU
from shared.constants import MIN_DECK_SIZE, MAX_DECK_SIZE
from shared.constants import ErrorCode as ec
from server.pdu import builder

logger = logging.getLogger(__name__)

# This will be called by the dispatcher already -> see handler(pdu, player_id, game_server)
async def lobby_state(pdu: dict, player_id: str, game_server):
    state = game_server.state

    # If player is empty
    if len(player_id) == 0:
        await game_server.send_to(
            player_id,
            builder.error(
                seq = state.next_seq(),
                code = ec.ILLEGAL_ACTION,
                message = 'player_id is an empty string'
            )
        )
        return

    # Duplicate ID check
    if player_id not in state.player_ids and pdu.get('player_id') in state.player_ids:
        await game_server.send_to(
            player_id,
            builder.error(
                seq = state.next_seq(),
                code = ec.DUPLICATE_ID,
                message = f"Player ID '{pdu.get('player_id')} is already taken.",
                rejected_action = pdu
            ))
        return        

    # Check if deck is within min and max size
    deck_list = pdu.get("deck_list", [])
    if len(deck_list) < MIN_DECK_SIZE or len(deck_list) > MAX_DECK_SIZE:
        await game_server.send_to(
            player_id, 
            builder.error(
                seq = state.next_seq(),
                code = ec.ILLEGAL_DECK,
                message = f'Deck must contain between {MIN_DECK_SIZE} and {MAX_DECK_SIZE} cards.',
                rejected_action = pdu
            ))
        return

    # Check if deck is empty or unknown
    illegal = [c for c in deck_list if not is_valid_card_id(c)]
    if illegal:
        await game_server.send_to(
            player_id,
            builder.error(
                seq = state.next_seq(),
                code = ec.ILLEGAL_DECK,
                message = f"Unknown card IDs in deck: {illegal}",
                rejected_action = pdu
            )
        )
        return

    # Additional check if player exists in game state
    player_state = state.get_player(player_id)
    if player_state is None:
        logger.error("PLAYER_READY from unregistered connection: %s", player_id)

    # Store deck to the game state player instance
    player_state.library = list(deck_list)
    game_server.ready_players.add(player_id)

    logger.info("Player %s is ready with %d cards.", player_id, len(deck_list))

    # Wait for next player
    waiting = [pid for pid in state.player_ids if pid not in game_server.ready_players]
    seq = state.next_seq()
    await game_server.send_to(
        player_id,
        builder.lobby_state(seq, len(game_server.ready_players), waiting)
        ) 

    # Transition to GAME_SETUP
    if len(game_server.ready_players) == 2:
        logger.info("Both players ready. Starting GAME_SETUP.")
        await game_server.start_game_setup()
    