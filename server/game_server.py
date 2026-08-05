"""
Handles and contains game server logic, holds all component references and implements it
"""

import asyncio
import logging
import random # for randomizing deck
from pathlib import Path

from shared.constants import PDU
from shared.framing import write_pdu

from server.state.game_state import GameState
from server.state.player_state import PlayerState
from server.pdu.dispatcher import Dispatcher

CATALOG_PATH = Path(__file__).parent.parent / "data" / "card_set.json"

# Holds all component references, manages connection
logger = logging.getLogger(__name__)

class GameServer:
    def __init__(self):
        self.state = GameState()
        self.card_catalog = None #load_catalog(CATALOG_PATH)
        
        self._writers: dict[str, asyncio.StreamWriter] = {}
        
        self.ready_players: set[str] = set()

        # PDU dispatcher
        self.dispatcher = Dispatcher()
        self._register_handlers()

    def _register_handlers(self) -> None:
        d = self.dispatcher
        # TODO: Register PDUs here (currently placeholders)
        #d.register(PDU.PLAYER_READY, handle_player_ready)
        #d.register(PDU.MULLIGAN_CHOICE, handle_mulligan_choice)
        #d.register(PDU.PRIORITY_PASS, self.priority_manager.handle_pass)
        #d.register(PDU.CAST_SPELL, handle_cast_spell)
        #d.register(PDU.PLAY_LAND, handle_play_land)
        #d.register(PDU.CONCEDE, handle_concede)
        #d.register(PDU.DISCARD, handle_discard)
        #d.register(PDU.PING, handle_ping)
        #d.register(PDU.DECLARE_ATTACKERS, self.combat_manager.handle_declare_attackers)
        #d.register(PDU.DECLARE_BLOCKERS, self.combat_manager.handle_declare_blockers)
        #d.register(PDU.ASSIGN_DAMAGE_ORDER, self.combat_manager.handle_assign_damage_order)
    
    def register_connection(self, player_id: str, writer: asyncio.StreamWriter) -> None:
        self._writers[player_id] = writer
        if player_id not in self.state.players:
            self.state.players[player_id] = PlayerState(player_id=player_id)
            self.state.player_ids.append(player_id)
        logger.info("Player %s connected", player_id)

    def remove_connection(self, player_id: str) -> None:
        self._writers.pop(player_id, None)
        logger.info("Player %s disconnected.", player_id)


    async def send_to(self, player_id: str, pdu: dict) -> None:
        writer = self._writers.get(player_id)
        if writer:
            try:
                await write_pdu(writer, pdu)
            except (ConnectionResetError, BrokenPipeError):
                logger.warning("Failed to send to '%s'. Connection lost.", player_id)

    async def broadcast(self, pdu: dict) -> None:
        for pid in self.state.player_ids:
            await self.send_to(pid, pdu)


    async def handle_pdu(self, pdu: dict, player_id: str) -> None:
        await self.dispatcher.dispatch(pdu, player_id, self)


    async def start_game_setup(self) -> None:
        all_card_ids = list(self.card_catalog.keys())

        # TODO: Shuffling deck, game lifecycle transitions here