"""
Contains game state data as an object
This is stored by the game_server
"""

from dataclasses import dataclass, field
from typing import Optional

from server.state.player_state import PlayerState
from shared.constants import Phase

@dataclass
class GameState:
    player_ids: list[str] = field(default_factory=list)
    players: dict[str, PlayerState] = field(default_factory=dict)

    active_player_id: Optional[str] = None
    phase: str = Phase.LOBBY

    # For sequence counter (increments every PDU server sends)
    seq_counter: int = 0

    def next_seq(self) -> int:
        self.seq_counter += 1
        return self.seq_counter