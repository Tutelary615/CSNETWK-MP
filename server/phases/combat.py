"""
Handles combat system from BEGIN_COMBAT to END_COMBAT
"""

import logging

from shared.constants import PDU, Phase
from server.pdu import builder
from shared.constants import ErrorCode as ec

logger = logging.getLogger(__name__)

class CombatManager:
    def __init__(self, game_server):
        self.gs = game_server
        self.state = game_server.state

        self.attackers: list[dict] = []
        self.blockers: list[dict] = []
        self.damage_orders: dict = {}

        self.awaiting_attackers = False
        self.awaiting_blockers = False
        self.awaiting_damage_order = False

    # Change combat phase
    async def transition(self, phase: str):
        if phase == Phase.BEGIN_COMBAT:
            await self._do_begin_combat()
        elif phase == Phase.DECLARE_ATTACKERS:
            await self._do_declare_attackers_step()
        elif phase == Phase.DECLARE_BLOCKERS:
            await self._do_declare_blockers_step()
        elif phase == Phase.ASSIGN_DAMAGE_ORDER:
            await self._do_assign_damage_order_step()
        elif phase == Phase.COMBAT_DAMAGE:
            await self._do_combat_damage()
        elif phase == Phase.END_OF_COMBAT:
            await self._do_end_combat()

    # Start combat
    async def _do_begin_combat(self) -> None:
        self.attackers = []
        self.blockers = []
        self.damage_orders = {}

        await self._broadcast_state()
        await self.gs.priority_manager.reset_pass_tracker()

    # Handle attacker declarations
    async def _do_declare_attackers_step(self) -> None:
        self.awaiting_attackers = True

    async def handle_declare_attackers(self, pdu: dict, player_id: str) -> None:
        # TODO: Validate summoning sickness, tap check, etc.
        if player_id != self.state.active_player_id:
            await self.gs.send_to(
                player_id,
                builder.error(
                    seq     = self.state.next_seq(),
                    code    = ec.ILLEGAL_ACTION,
                    message = "Only the active player may declare attackers.",
                    rejected_action = pdu
                )
            )
            return

        # Validate seq_num
        if not await self.gs.priority_manager.validate_action(pdu, player_id):
            return

        attackers = pdu.get("attackers")
        self.attackers = attackers
        self.awaiting_attackers = False

        # Tap attacking creatures
        ap = self.state.get_player(player_id)
        for atk in attackers:
            perm = ap.get_permanent(atk["creature_id"])
            if perm:
                perm.tapped = True
        logger.info("Player '%s' declared %d attacker(s).", player_id, len(attackers))

        # If no attackers, end combat
        if not attackers:
            await self.gs.turn_manager._enter_phase(Phase.END_OF_COMBAT)
            return

        await self._broadcast_state()
        await self.gs.priority_manager.reset_pass_tracker()

    # Handle blocker declarations
    async def _do_declare_blockers_step(self) -> None:
        self.awaiting_blockers = True

    async def handle_declare_blockers(self, pdu: dict, player_id: str) -> None:
        nap_id = self.state.non_active_player_id()
        if player_id != nap_id:
            await self.gs.send_to(
                player_id,
                builder.error(
                    seq = self.state.next_seq(),
                    code = ec.ILLEGAL_ACTION,
                    message = "Only the non-active player may declare blockers.",
                    rejected_action = pdu,
                )
            )
            return

        if not await self.gs.priority_manager.validate_action(pdu, player_id):
            return
        self.blockers = pdu.get("blockers", [])
        self.awaiting_blockers = False

        logger.info("%s declared blockers: %s", player_id, self.blockers)

        await self._broadcast_state()
        await self.gs.priority_manager.reset_pass_tracker()

    async def _do_assign_damage_order_step(self) -> None:
        # TODO: identify multiply-blocked attackers and request ordering
        self.awaiting_damage_order = True

    # Handle damage order
    async def handle_assign_damage_order(self, pdu: dict, player_id: str) -> None:
        # TODO: record damage ordering
        attacker_id = pdu.get("attacker_id")
        blocker_order = pdu.get("blocker_order", [])

        self.damage_orders[attacker_id] = list(blocker_order)

        # TODO: Check if all orderings have been received
        logger.info(
            "%s ordered blockers for %s: %s",
            player_id,
            attacker_id,
            blocker_order
        )
        await self.gs.priority_manager.reset_pass_tracker()


    # Resolve normal combat damage
    async def _do_combat_damage(self) -> None:
        damage_events = []
        creatures_died = []

        ap_id = self.state.active_player_id
        nap_id = self.state.non_active_player_id()
        ap = self.state.get_player(ap_id)
        nap = self.state.get_player(nap_id)

        # Create list of blocking creature_ids
        blocker_map: dict[str, list] = {a["creature_id"]: [] for a in self.attackers}
        for blk in self.blockers:
            if blk["blocking_id"] in blocker_map:
                blocker_map[blk["blocking_id"]].append(blk["creature_id"])

        for atk_info in self.attackers:
            atk_id = atk_info["creature_id"]
            atk_perm = ap.get_permanent(atk_id)
            if atk_perm is None:
                continue

            blocking = blocker_map.get(atk_id, [])

            if not blocking:
                # Deal damage to defending player
                nap.life -= atk_perm.power
                damage_events.append({
                    "source": atk_id,
                    "target": nap_id,
                    "amount": atk_perm.power,
                })
            else:
                # Deal damage to first blocker in order
                # TODO: implement full damage assignment order (trample, etc.)
                blk_id = blocking[0]
                blk_perm = nap.get_permanent(blk_id)
                if blk_perm:
                    blk_perm.damage += atk_perm.power
                    atk_perm.damage += blk_perm.power
                    damage_events.append({
                        "source": atk_id,
                        "target": blk_id,
                        "amount": atk_perm.power,
                    })
                    damage_events.append({
                        "source": blk_id,
                        "target": atk_id,
                        "amount": blk_perm.power,
                    })

        # Check SBAs: remove creatures with lethal damage
        losses = self.state.check_sbas()

        # Collect died creatures
        creatures_died = None # TODO: collect died creatures
        seq = self.state.next_seq()
        life_totals = {pid: player.life for pid, player in self.state.players.items()}

        await self.gs.broadcast(
            builder.combat_damage_result(
                seq=seq,
                damage_events=damage_events, 
                life_totals=life_totals, 
                creatures_died=creatures_died
            )
        )

        if losses:
            loser_id, reason = losses[0]
            winner_id = self.state.opponent_id(loser_id)
            await self.gs.end_game(winner_id, loser_id, reason)
            return

        await self._broadcast_state()
        await self.gs.turn_manager._enter_phase(Phase.END_OF_COMBAT)


    # End combat
    async def _do_end_combat(self) -> None:
        self.attackers.clear()
        self.blockers.clear()
        self.damage_orders.clear()

        await self._broadcast_state()
        await self.gs.priority_manager.reset_pass_tracker()

    async def _broadcast_state(self) -> None:
        for pid in self.state.player_ids:
            seq  = self.state.next_seq()
            view = self.state.to_visible_dict(pid)
            await self.gs.send_to(pid, builder.game_state_update(seq, view))