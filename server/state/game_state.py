"""
Contains game state data as an object
This is stored by the game_server
"""

from dataclasses import dataclass, field

from server.state.player_state import PlayerState

@dataclass
class GameState:
    player_ids: list[str] = field(default_factory=list)
    players: dict[str, PlayerState] = field(default_factory=dict)

    # For sequence counter (increments every PDU server sends)
    seq_counter: int

    def next_seq(self) -> int:
        self.seq_counter += 1
        return self.seq_counter