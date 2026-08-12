"""
Handles and contains game server logic, holds all component references and implements it
"""

import asyncio
import logging
import random # for randomizing deck
from pathlib import Path

from shared.cards import load_catalog
from shared.constants import PDU, Phase, STARTING_LIFE
from shared.framing import write_pdu
from server.pdu import builder
from server.phases.lobby import lobby_state
from server.phases.mulligan import handle_mulligan_choice
from server.phases.priority_manager import PriorityManager
from server.phases.turn_manager import TurnManager
from server.phases.combat import CombatManager
from server.rules.engine import RulesEngine
from server.state.game_state import GameState
from server.state.player_state import PlayerState
from server.pdu.dispatcher import Dispatcher
from server.actions.handlers import (
    handle_cast_spell, handle_concede, handle_discard,
    handle_ping, handle_play_land
)

CATALOG_PATH = Path(__file__).parent.parent / "data" / "card-set.json"

# Holds all component references, manages connection
logger = logging.getLogger(__name__)

class GameServer:
    def __init__(self):
        self.state = GameState()
        self.card_catalog = load_catalog(CATALOG_PATH)
        
        self._writers: dict[str, asyncio.StreamWriter] = {}
        
        self.ready_players: set[str] = set()

        # Used for mulligan seq validation
        self.last_sent_seq: dict[str, int] = {}

        # Used by cleanup discard loop
        self.discard_event = asyncio.Event()

        # Components
        self.priority_manager = PriorityManager(self)
        self.turn_manager = TurnManager(self)
        self.combat_manager = CombatManager(self)
        self.rules_engine = RulesEngine(self)

        self.turn_manager.pm = self.priority_manager

        # PDU dispatcher
        self.dispatcher = Dispatcher()
        self._register_handlers()

    def _register_handlers(self) -> None:
        d = self.dispatcher
        d.register(PDU.PLAYER_READY, lobby_state)
        d.register(PDU.MULLIGAN_CHOICE, handle_mulligan_choice)
        d.register(PDU.DECLARE_ATTACKERS, self.combat_manager.handle_declare_attackers)
        d.register(PDU.DECLARE_BLOCKERS, self.combat_manager.handle_declare_blockers)
        d.register(PDU.ASSIGN_DAMAGE_ORDER, self.combat_manager.handle_assign_damage_order)
        d.register(PDU.PRIORITY_PASS, self.priority_manager.handle_pass)
        d.register(PDU.CAST_SPELL, handle_cast_spell)
        d.register(PDU.PLAY_LAND, handle_play_land)
        d.register(PDU.CONCEDE, handle_concede)
        d.register(PDU.DISCARD, handle_discard)
        d.register(PDU.PING, handle_ping)
        #d.register(PDU.ACTIVATE_ABILITY, handler)
        #d.register(PDU.TRIGGER_ORDER_RESPONSE, handler)
        #d.register(PDU.TRIGGER_CHOICE_RESPONSE, handler)

    def register_connection(self, player_id: str, writer: asyncio.StreamWriter) -> None:
        self._writers[player_id] = writer
        if player_id not in self.state.players:
            self.state.players[player_id] = PlayerState(player_id=player_id)
            self.state.player_ids.append(player_id)
        logger.info("Player %s connected", player_id)

    def remove_connection(self, player_id: str, purge_state: bool = False) -> None:
        self._writers.pop(player_id, None)
        # Remove player info in game state
        if purge_state:
            self.state.players.pop(player_id, None)
            if player_id in self.state.player_ids:
                self.state.player_ids.remove(player_id)
        logger.info("Player %s disconnected.", player_id)


    async def send_to(self, player_id: str, pdu: dict) -> None:
        writer = self._writers.get(player_id)
        if writer:
            try:
                await write_pdu(writer, pdu)
                self.last_sent_seq[player_id] = pdu.get("seq_num", 0)
            except (ConnectionResetError, BrokenPipeError):
                logger.warning("Failed to send to '%s'. Connection lost.", player_id)

    async def broadcast(self, pdu: dict) -> None:
        for pid in self.state.player_ids:
            await self.send_to(pid, pdu)


    async def handle_pdu(self, pdu: dict, player_id: str) -> None:
        await self.dispatcher.dispatch(pdu, player_id, self)


    async def start_game_setup(self) -> None:
        self.state.phase = Phase.MULLIGAN # immediately transition to MULLIGAN phase

        for pid, player in self.state.players.items():
            player.life = STARTING_LIFE
            player.hand = []
            player.graveyard = []
            player.battlefield = []
            player.mulligan_count = 0
            player.has_kept = False
            player.land_played_this_turn = False
            player.shuffle_library()
            player.draw_opening_hand(7)

        # Coin flip: select random 1st player
        self.state.active_player_id = random.choice(self.state.player_ids)
        self.state.turn = 0

        logger.info("First player: %s", self.state.active_player_id)

        for pid in self.state.player_ids:
            seq = self.state.next_seq()
            view = self.state.to_visible_dict(pid) # personalized view
            self.last_sent_seq[pid] = seq
            await self.send_to(pid, builder.game_state_update(seq, view))

    async def start_in_game(self) -> None:
        self.state.phase = Phase.UNTAP
        await self.turn_manager.begin_turn()

    async def end_game(self, winner_id: str, loser_id: str, reason: str) -> None:
        logger.info("Game over. Winner: %s, Reason: %s", winner_id, reason)
        self.state.phase = Phase.GAME_OVER

        seq = self.state.next_seq()
        await self.broadcast(builder.game_over(seq, winner_id, loser_id, reason))

        await self._reset_for_lobby()

    async def _reset_for_lobby(self) -> None:
        # Tear down in-game state and return to LOBBY
        self.state.phase = Phase.LOBBY
        self.state.turn = 0
        self.state.active_player_id = None
        self.state.priority_holder_id = None
        self.state.last_passer_id = None
        self.state.seq_counter = 0
        self.last_sent_seq.clear()
        self.state.stack.clear()
        self.ready_players.clear()

        # Reset per-player state but keep the connections
        for pid in list(self.state.player_ids):
            self.state.players[pid] = PlayerState(player_id=pid)

        logger.info("Returned to LOBBY. Awaiting PLAYER_READY PDUs.")
