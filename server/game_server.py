import asyncio
import logging

from server.state.game_state import GameState
from server.state.player_state import PlayerState

# Holds all component references, manages connection
logger = logging.getLogger(__name__)

class GameServer:
    def __init__(self):
        state = GameState()
        self._writers: dict[str, asyncio.StreamWriter] = {}

def register_connection(self, player_id: str, writer: asyncio.StreamWriter) -> None:
    self._writers[player_id] = writer
    if player_id not in self.state.players:
        self.state.players[player_id] = PlayerState(player_id=player_id)
        self.state.player_ids.append(player_id)
    logger.info("Player %s connected", player_id)

def remove_connection(self, player_id: str) -> None:
    self._writers.pop(player_id, None)
    logger.info("Player %s disconnected.", player_id)