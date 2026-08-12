"""
Handles phase transitions, draw step logic, stack resolution, and cleanup
"""

import logging
from server.pdu import builder
from shared.constants import (Phase, PHASE_ORDER, NO_PRIORITY_PHASES,
                              GameOverReason, MAX_HAND_SIZE)

logger = logging.getLogger(__name__)

class TurnManager:
    def __init__(self, game_server):
        self.gs = game_server
        self.state = game_server.state
        self.pm = None

    # Called at the start of each turn
    async def begin_turn(self) -> None:
        self.state.turn += 1
        ap = self.state.active_player_id
        logger.info("Turn %d - Active Player %s", self.state.turn, ap)
        await self._enter_phase(Phase.UNTAP)

    # Advance to next step
    async def advance_step(self) -> None:
        current = self.state.phase
        try:
            idx = PHASE_ORDER.index(current)
        except ValueError:
            logger.error("Current phase '%s' not in PHASE_ORDER", current)

        if idx + 1 >= len(PHASE_ORDER):
            await self._end_of_turn()
            return

        next_phase = PHASE_ORDER[idx + 1]
        await self._enter_phase(next_phase)

    # Enter a specific phase
    async def _enter_phase(self, phase: str) -> None:
        prev_phase = self.state.phase
        self.state.phase = phase

        # Broadcast PHASE_TRANSITION
        seq = self.state.next_seq()
        pt_pdu = builder.phase_transition(
            seq = seq,
            from_phase = prev_phase,
            to_phase = phase,
            active_player = self.state.active_player_id,
            turn = self.state.turn,
        )
        await self.gs.broadcast(pt_pdu)

        # Phase-specific entry logic
        if phase == Phase.UNTAP:
            await self._do_untap()
        elif phase == Phase.DRAW:
            await self._do_draw()
        elif phase == Phase.CLEANUP:
            await self._do_cleanup()
        elif phase in (Phase.DECLARE_ATTACKERS, Phase.DECLARE_BLOCKERS,
                       Phase.ASSIGN_DAMAGE_ORDER, Phase.COMBAT_DAMAGE,
                       Phase.FIRST_STRIKE_DAMAGE):
            await self.gs.combat_manager.transition(phase)
        elif phase not in NO_PRIORITY_PHASES:
            # All other phases with a priority window
            await self._broadcast_state_to_all()
            await self.pm.reset_pass_tracker()

    # UNTAP step
    async def _do_untap(self) -> None:
        ap = self.state.get_player(self.state.active_player_id)
        ap.untap_all()
        ap.land_played_this_turn = False

        await self._broadcast_state_to_all()
        # No priority, advance immediately to UPKEEP
        await self._enter_phase(Phase.UPKEEP)

    # DRAW step
    async def _do_draw(self) -> None:
        ap = self.state.get_player(self.state.active_player_id)

        # First player does not draw on turn 1
        if self.state.turn > 1 or self.state.active_player_id != self.state.player_ids[0]:
            drawn = ap.draw()
            if drawn is None:
                # Drawing from empty library = lose
                loser = self.state.active_player_id
                winner = self.state.opponent_id(loser)
                await self.gs.end_game(winner, loser, GameOverReason.DECK_EMPTY)
                return

        await self._broadcast_state_to_all()
        await self.pm.reset_pass_tracker()

    # CLEANUP step
    async def _do_cleanup(self) -> None:
        ap_id = self.state.active_player_id
        ap = self.state.get_player(ap_id)

        # Hand size check: loop until < = 7 cards
        while len(ap.hand) > MAX_HAND_SIZE:
            # Send current state to the AP so they know what to discard
            seq = self.state.next_seq()
            view = self.state.to_visible_dict(ap_id)
            await self.gs.send_to(ap_id, builder.game_state_update(seq, view))

            # DISCARD PDU (handled by action handler)
            self.gs.discard_event.clear()
            await self.gs.discard_event.wait()

        # Clear damage from all creatures and end-of-turn effects
        for player in self.state.players.values():
            for perm in player.battlefield:
                perm.damage = 0

        # TODO: clear "until end of turn" effects when those are implemented

        await self._broadcast_state_to_all()
        await self._end_of_turn()

    async def _end_of_turn(self) -> None:
        # Switch to next player
        self.state.switch_active_player()
        await self.begin_turn()

    # Stack resolution
    async def resolve_top_of_stack(self) -> None:
        item = self.state.stack.pop()
        if item is None:
            return

        # Check target legality
        state_changes = []
        result = "RESOLVED"

        if item.targets and not self._targets_legal(item.targets):
            result = "FIZZLE"
        else:
            state_changes = await self.gs.rules_engine.apply_effect(item)

        seq = self.state.next_seq()
        await self.gs.broadcast(
            builder.stack_resolve(seq, item.stack_item_id, result, state_changes)
        )

        # Check SBAs after resolution
        losses = self.state.check_sbas()
        if losses:
            loser_id, reason = losses[0]
            winner_id = self.state.opponent_id(loser_id)
            await self.gs.end_game(winner_id, loser_id, reason)
            return

        await self._broadcast_state_to_all()
        # AP retakes priority after resolution
        await self.pm.grant_active_player()

    def _targets_legal(self, target_ids: list[str]) -> bool:
        # Check that all listed targets still exist on the battlefield or are valid players.
        # TODO: extend with protection, hexproof, etc. as cards are added.
    
        for tid in target_ids:
            if tid in self.state.player_ids:
                continue
            # Check if it's a permanent on any battlefield
            found = False
            for player in self.state.players.values():
                if any(p.card_id == tid for p in player.battlefield):
                    found = True
                    break
            if not found:
                return False
        return True

    # Utility function
    async def _broadcast_state_to_all(self) -> None:
        for pid in self.state.player_ids:
            seq  = self.state.next_seq()
            view = self.state.to_visible_dict(pid)
            await self.gs.send_to(pid, builder.game_state_update(seq, view))