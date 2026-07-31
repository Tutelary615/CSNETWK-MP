"""
Contains game state data
"""

from dataclasses import dataclass, field

from server.state.player_state import PlayerState

@dataclass
class GameState:
    player_ids: list[str] = field(default_factory=list)
    players: dict[str, PlayerState] = field(default_factory=dict)
