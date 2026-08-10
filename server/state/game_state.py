"""
Contains game state data as an object
This is stored by the game_server
"""

from dataclasses import dataclass, field
from typing import Optional

from server.state.player_state import PlayerState
from server.state.stack import Stack
from server.state.permanent import Permanent
from shared.constants import Phase

@dataclass
class GameState:
    player_ids: list[str] = field(default_factory=list)
    players: dict[str, PlayerState] = field(default_factory=dict)

    # Turn tracking
    turn: int = 0
    active_player_id: Optional[str] = None
    phase: str = Phase.LOBBY

    # Priority tracking
    priority_holder_id: Optional[str] = None
    last_passer_id: Optional[str] = None # tracks consecutive passes
    current_priority_seq: int = 0 # the seq_num of the latest PRIORITY_GRANT

    # Stack
    stack: Stack = field(default_factory=Stack)

    # For sequence counter (increments every PDU server sends)
    seq_counter: int = 0

    def next_seq(self) -> int:
        self.seq_counter += 1
        return self.seq_counter

    def get_player(self, player_id: str) -> Optional[PlayerState]:
        return self.players.get(player_id)

    # Set visible state for each player (will be called by game server in GAME_SETUP)
    def to_visible_dict(self, viewer_id: str) -> dict:
        state = {
            "turn": self.turn,
            "active_player": self.active_player_id,
            "phase": self.phase,
            "priority_holder": self.priority_holder_id,
            "life_totals": {pid: p.life for pid, p in self.players.items()},
            "stack": self.stack.to_list(),
            "battlefield": {},
            "graveyard": {},
            "hand": {},
            "hand_counts": {},
            "library_counts": {},
            "land_played_this_turn": (
                self.players[self.active_player_id].land_played_this_turn
                if self.active_player_id else False
            )
        }

        for pid, player in self.players.items():
            # Set battlefield visible to all
            state["battlefield"][pid] = [
                self._serialize_permanent(perm)
                for perm in player.battlefield
            ]

            # Set graveyard visible to all
            state["graveyard"][pid] = len(player.graveyard)

            # Set library counts visible
            #state["library_counts"][pid] = len(player.library)

            if pid == viewer_id:
                state["hand"][pid] = list(player.hand) # viewer sees ther own hand
            else:
                state["hand_counts"][pid] = len(player.hand) # opponent only sees hand count

        return state

    def _serialize_permanent(self, perm: Permanent) -> dict:
        base = {"id": perm.card_id, "tapped": perm.tapped}
        if perm.power is not None:
            base.update({
                "damage": perm.damage,
                "power": perm.power,
                "toughness": perm.toughness,
                "summoning_sick": perm.effective_summoning_sick
            })

        return base