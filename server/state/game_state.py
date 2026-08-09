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

    # Turn tracking
    turn: int = 0
    active_player_id: Optional[str] = None
    phase: str = Phase.LOBBY

    # TODO: Add priority tracking variables here

    # For sequence counter (increments every PDU server sends)
    seq_counter: int = 0

    def next_seq(self) -> int:
        self.seq_counter += 1
        return self.seq_counter

    def get_player(self, player_id: str) -> Optional[PlayerState]:
        return self.players.get(player_id)

    # Set visible state for each player
    def to_visible_dict(self, viewer_id: str) -> dict:
        state = {
            "turn": self.turn,
            "active_player": self.active_player_id,
            "phase": self.phase,
            "life_totals": {pid: p.life for pid, p in self.players.items()},
            #"stack": self.stack.to_list(),
            "battlefield": {},
            "graveyard": {},
            "hand": {},
            "hand_counts": {},
            "library_counts": {},
        }

        for pid, player in self.players.items():
            pass

        return state