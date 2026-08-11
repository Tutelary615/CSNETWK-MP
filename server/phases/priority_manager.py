"""
Manages priority based from the priority state machine (Section 8.2 of the RFC):
  - AP gets priority at the start of each step
  - On PRIORITY_PASS: give priority to the other player
  - When both pass consecutively:
      - Stack non-empty: resolve top item, AP gets priority again
      - Stack empty: step ends
"""

from enum import Enum, auto
from typing import Optional
from server.state.game_state import GameState


class PriorityResult(Enum):
    PRIORITY_PASSED = auto()
    RESOLVED_STACK_ITEM = auto()
    STEP_ENDED = auto()


class PriorityManager:
    @staticmethod
    def grant_initial_priority(game_state: GameState) -> None:
        game_state.priority_holder_id = game_state.active_player_id
        game_state.last_passer_id = None
        game_state.current_priority_seq = game_state.next_seq()

    @staticmethod
    def reset_pass_tracker(game_state: GameState) -> None:
        game_state.last_passer_id = None

    @staticmethod
    def _get_next_player_id(game_state: GameState, current_player_id: str) -> Optional[str]:
        if not game_state.player_ids or current_player_id not in game_state.player_ids:
            return None
        idx = game_state.player_ids.index(current_player_id)
        next_idx = (idx + 1) % len(game_state.player_ids)
        return game_state.player_ids[next_idx]

    @classmethod
    def handle_pass(cls, game_state: GameState, player_id: str, engine) -> PriorityResult:
        if game_state.priority_holder_id != player_id:
            raise ValueError(f"Player '{player_id}' does not hold priority.")

        # Check if another player previously passed without any actions in between
        if game_state.last_passer_id is not None and game_state.last_passer_id != player_id:
            # Both/all players have passed consecutively!
            game_state.last_passer_id = None

            if not game_state.stack.is_empty():
                # Stack non-empty: resolve top item, AP gets priority again
                engine.resolve_top_stack_item(game_state)
                game_state.priority_holder_id = game_state.active_player_id
                game_state.current_priority_seq = game_state.next_seq()
                return PriorityResult.RESOLVED_STACK_ITEM
            else:
                # Stack empty: step ends
                game_state.priority_holder_id = None
                game_state.current_priority_seq = game_state.next_seq()
                return PriorityResult.STEP_ENDED
        else:
            # First pass in sequence: pass priority to the next player
            next_player = cls._get_next_player_id(game_state, player_id)
            game_state.last_passer_id = player_id
            game_state.priority_holder_id = next_player
            game_state.current_priority_seq = game_state.next_seq()
            return PriorityResult.PRIORITY_PASSED