import asyncio
import logging

# Holds all component references, manages connection
logger = logging.getLogger(__name__)

def register_connection(self, player_id: str, writer: asyncio.StreamWriter) -> None:
    #self._writers[player_id] = writer
    #if player_id not in self.state.players:
        #self.state.players[player_id] = PlayerState(player_id=player_id)
        #self.state.player_ids.append(player_id)
    logger.info("Player %s connected", player_id)

def remove_connection(self, player_id: str) -> None:
    self._writers.pop(player_id, None)
    logger.info("Player %s disconnected.", player_id)