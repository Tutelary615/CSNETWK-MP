"""
Handles PLAYER_READY and LOBBY state, then transitions to GAME_SETUP
"""

import asyncio 
from ..game_server import GameServer
from ...shared.framing import read_pdu
from shared.constants import PDU
from shared.constants import MIN_DECK_SIZE, MAX_DECK_SIZE
from shared.constants import ErrorCode as ec
from pdu.builder import error

async def lobby_state(game_server: GameServer, reader : asyncio.StreamReader):
    seq_nums = {}
    while True:
        pdu = await read_pdu(reader)
        player_id = pdu['player_id']
        seq = pdu['seq_num']
        deck_size = len(pdu['deck'])
        ready_players = game_server.ready_players
        
        if len(player_id) == 0:
            # change to empty id code
            await game_server.dispatcher.dispatch(error(seq, ec.DUPLICATE_ID, f'ID {player_id} is taken'))
        elif deck_size > MAX_DECK_SIZE:
            await game_server.dispatcher.dispatch(error(seq, ec.ILLEGAL_DECK, f'Deck contains {deck_size} cards; maximum is {MAX_DECK_SIZE}'))
        elif deck_size < MIN_DECK_SIZE:
            await game_server.dispatcher.dispatch(error(seq, ec.ILLEGAL_DECK, f'Deck contains {deck_size} cards; minimum is {MIN_DECK_SIZE}'))
    
        elif seq_nums.get(player_id) != None and seq != seq_nums.get(player_id) + 1: 
              await game_server.dispatcher.dispatch(error(seq, ec.DUPLICATE_ID, f'ID {player_id} is taken'))
        else:
            seq_nums[player_id] = seq
            # await game_server.dispatcher.dispatch() GAME STATE UPDATE
              
        if len(ready_players) == 2:
            # await game_server.dispatcher.dispatch() TRANSISTION TO  GAME SETUP
            return
    