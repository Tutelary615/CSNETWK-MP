"""
Manages priority based from the priority state machine (Section 8.2 of the RFC):
  - AP gets priority at the start of each step
  - On PRIORITY_PASS: give priority to the other player
  - When both pass consecutively:
      - Stack non-empty: resolve top item, AP gets priority again
      - Stack empty: step ends
"""
import logging
from enum import Enum, auto
from typing import Optional
from server.pdu import builder
from shared.constants import ErrorCode as ec

logger = logging.getLogger(__name__)

class PriorityManager:
    def __init__(self, game_server):
        self.gs = game_server # turn manager resides here
        self.state = game_server.state # shortcut to game state

    # Give priority to player_id and broadcast PRIORITY_GRANT
    async def grant_initial_priority(self, player_id: str) -> None:
        self.state.priority_holder_id = player_id
        seq = self.state.next_seq()
        self.state.current_priority_seq = seq
        pdu = builder.priority_grant(seq, player_id)
        await self.gs.send_to(player_id, pdu)
        logger.debug("Priority granted to %s (seq=%d)", player_id, seq)

    async def grant_active_player(self) -> None:
        await self.grant_initial_priority(self.state.active_player_id)

    async def reset_pass_tracker(self) -> None:
        self.state.last_passer_id = None
        await self.grant_active_player()

    async def reissue_priority(self, player_id: str) -> None:
        pdu = builder.priority_grant(self.state.current_priority_seq, player_id)
        await self.gs.send_to(player_id, pdu)

    # Validate an incoming action PDU's seq_num
    async def validate_action(self, pdu: dict, player_id: str) -> bool:
        # Check priority holder
        if self.state.priority_holder_id != player_id:
            await self.gs.send_to(
                player_id,
                builder.error(
                    seq = self.state.next_seq(),
                    code = ec.NOT_YOUR_PRIORITY,
                    message = f"You do not hold priority. Current holder: "
                              f"{self.state.priority_holder_id}.",
                    rejected_action = pdu
                )
            )
            return False

        # Check seq_num
        incoming_seq = pdu.get("seq_num")
        expected_seq = self.state.current_priority_seq
        if incoming_seq != expected_seq:
            seq = self.state.next_seq()
            await self.gs.send_to(
                player_id,
                builder.error(
                    seq = seq,
                    code = ec.STALE_ACTION,
                    message = f"Priority token mismatch. Expected seq_num "
                              f"{expected_seq}, got {incoming_seq}.",
                    rejected_action = pdu
                )
            )
            # Re-issue the current PRIORITY_GRANT so the player can try again
            await self.reissue_priority(player_id)
            return False

        return True

    # Handle priority pass
    async def handle_pass(self, pdu: dict, player_id: str) -> None:
        # Moved validation to a separate function
        if not await self.validate_action(pdu, player_id):
            return

        last_passer = self.state.last_passer_id
        self.state.last_passer_id = player_id

        opponent_id = self.state.opponent_id(player_id)
        both_passed = (last_passer == opponent_id)

        # Check if another player previously passed without any actions in between
        if both_passed:
            self.state.last_passer_id = None # reset

            if not self.state.stack.is_empty():
                # Stack non-empty: move logic to turn manager
                await self.gs.turn_manager.resolve_top_of_stack()
            else:
                # Stack empty: advance step
                await self.gs.turn_manager.advance_step()
        else:
            # First pass in sequence: pass priority to the next player
            await self.grant_initial_priority(opponent_id)