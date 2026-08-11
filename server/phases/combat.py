"""
Handles combat system from BEGIN_COMBAT to END_COMBAT
"""

import logging

from shared.constants import PDU, Phase
from server.pdu import builder
from shared.constants import ErrorCode as ec

logger = logging.getLogger(__name__)


# Combat state
def _combat_data(state):
    if not hasattr(state, "combat_attackers"):
        state.combat_attackers = {}

    if not hasattr(state, "combat_blockers"):
        state.combat_blockers = {}

    if not hasattr(state, "combat_damage_orders"):
        state.combat_damage_orders = {}

    if not hasattr(state, "first_strike_done"):
        state.first_strike_done = set()


# Get all permanents
def _all_permanents(state):
    result = []

    for player in state.players.values():
        result.extend(player.battlefield)

    return result


# Find a permanent
def _find_permanent(state, permanent_id):
    for player in state.players.values():
        for permanent in player.battlefield:
            if permanent.card_id == permanent_id:
                return permanent

    return None


# Find the owner of a permanent
def _find_owner(state, permanent_id):
    for player in state.players.values():
        for permanent in player.battlefield:
            if permanent.card_id == permanent_id:
                return player

    return None


# Get the opponent
def _opponent_id(state, player_id):
    for pid in state.player_ids:
        if pid != player_id:
            return pid

    return None


# Check if a permanent is a creature
def _is_creature(permanent):
    return (
        permanent is not None
        and permanent.power is not None
        and permanent.toughness is not None
    )


# Check if a creature has a keyword
def _has_keyword(permanent, keyword):
    return keyword in getattr(permanent, "keywords", [])


# Check the sequence number
def _validate_seq(pdu, player_id, game_server):
    state = game_server.state

    expected = getattr(state, "current_priority_seq", 0)

    if expected == 0:
        expected = game_server.last_sent_seq.get(player_id)

    if pdu.get("seq_num") != expected:
        return False, expected

    return True, expected


# Send an error
async def _error(game_server, player_id, code, message, pdu):
    state = game_server.state

    await game_server.send_to(
        player_id,
        builder.error(
            seq=state.next_seq(),
            code=code,
            message=message,
            rejected_action=pdu
        )
    )


# Send the current game state
async def _broadcast_state(game_server):
    state = game_server.state

    for pid in state.player_ids:
        seq = state.next_seq()
        view = state.to_visible_dict(pid)

        await game_server.send_to(
            pid,
            builder.game_state_update(seq, view)
        )


# Change combat phase
async def _transition(game_server, new_phase):
    state = game_server.state
    old_phase = state.phase

    state.phase = new_phase

    seq = state.next_seq()

    pdu = builder.phase_transition(
        seq=seq,
        phase=new_phase,
        active_player_id=state.active_player_id
    )

    pdu["from_phase"] = old_phase
    pdu["to_phase"] = new_phase
    pdu["active_player"] = state.active_player_id
    pdu["turn"] = state.turn

    await game_server.broadcast(pdu)


# Remove creatures with lethal damage
def _remove_dead_creatures(state):
    creatures_died = []

    for player in state.players.values():
        survivors = []

        for permanent in player.battlefield:
            if not _is_creature(permanent):
                survivors.append(permanent)
                continue

            if permanent.damage >= permanent.toughness:
                player.graveyard.append(permanent.card_id)
                creatures_died.append(permanent.card_id)

                logger.info(
                    "Creature %s died for player %s.",
                    permanent.card_id,
                    player.player_id
                )
            else:
                survivors.append(permanent)

        player.battlefield = survivors

    return creatures_died


# Check if a creature has first strike
def _creature_can_first_strike(permanent):
    return (
        _has_keyword(permanent, "first_strike")
        or _has_keyword(permanent, "double_strike")
    )


# Check if a creature can deal normal combat damage
def _creature_can_normal_strike(permanent):
    if _has_keyword(permanent, "double_strike"):
        return True

    if _has_keyword(permanent, "first_strike"):
        return False

    return True


# Get blockers for each attacker
def _attacker_blockers(state):
    result = {}

    for blocker_id, attacker_id in state.combat_blockers.items():
        result.setdefault(attacker_id, []).append(blocker_id)

    return result


# Start combat
async def begin_combat(game_server):
    state = game_server.state

    _combat_data(state)

    state.combat_attackers.clear()
    state.combat_blockers.clear()
    state.combat_damage_orders.clear()
    state.first_strike_done.clear()

    await _transition(game_server, Phase.BEGIN_COMBAT)


# Handle attacker declarations
async def handle_declare_attackers(
    pdu: dict,
    player_id: str,
    game_server
) -> None:
    state = game_server.state

    _combat_data(state)

    if state.phase != Phase.DECLARE_ATTACKERS:
        await _error(
            game_server,
            player_id,
            ec.WRONG_PHASE,
            "DECLARE_ATTACKERS is only legal during DECLARE_ATTACKERS.",
            pdu
        )
        return

    if player_id != state.active_player_id:
        await _error(
            game_server,
            player_id,
            ec.NOT_YOUR_PRIORITY,
            "Only the Active Player may declare attackers.",
            pdu
        )
        return

    valid_seq, expected = _validate_seq(
        pdu,
        player_id,
        game_server
    )

    if not valid_seq:
        await _error(
            game_server,
            player_id,
            ec.STALE_ACTION,
            f"Expected seq_num {expected}, got {pdu.get('seq_num')}.",
            pdu
        )
        return

    attackers = pdu.get("attackers")

    if not isinstance(attackers, list):
        await _error(
            game_server,
            player_id,
            ec.ILLEGAL_ACTION,
            "'attackers' must be a list.",
            pdu
        )
        return

    opponent_id = _opponent_id(state, player_id)

    if opponent_id is None:
        await _error(
            game_server,
            player_id,
            ec.ILLEGAL_ACTION,
            "There is no opponent.",
            pdu
        )
        return

    declared_ids = set()

    for declaration in attackers:
        if not isinstance(declaration, dict):
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                "Each attacker declaration must be an object.",
                pdu
            )
            return

        creature_id = declaration.get("creature_id")
        target = declaration.get("target")

        if not creature_id:
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                "Attacker is missing creature_id.",
                pdu
            )
            return

        if creature_id in declared_ids:
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                f"Creature '{creature_id}' was declared more than once.",
                pdu
            )
            return

        declared_ids.add(creature_id)

        if target != opponent_id:
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_TARGET,
                f"Attacker must target opponent '{opponent_id}'.",
                pdu
            )
            return

        permanent = _find_permanent(state, creature_id)

        if permanent is None:
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                f"Creature '{creature_id}' is not on the battlefield.",
                pdu
            )
            return

        if permanent.controller_id != player_id:
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                f"Creature '{creature_id}' is not controlled by you.",
                pdu
            )
            return

        if not _is_creature(permanent):
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                f"'{creature_id}' is not a creature.",
                pdu
            )
            return

        if permanent.tapped:
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                f"Creature '{creature_id}' is tapped.",
                pdu
            )
            return

        if permanent.effective_summoning_sick:
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                f"Creature '{creature_id}' has summoning sickness.",
                pdu
            )
            return

    # Declare the attackers
    state.combat_attackers.clear()

    for declaration in attackers:
        creature_id = declaration["creature_id"]
        permanent = _find_permanent(state, creature_id)

        permanent.tapped = True

        state.combat_attackers[creature_id] = {
            "target": declaration["target"]
        }

    logger.info(
        "%s declared attackers: %s",
        player_id,
        list(state.combat_attackers.keys())
    )

    await _broadcast_state(game_server)

    # Skip combat if there are no attackers
    if not attackers:
        await _transition(game_server, Phase.END_OF_COMBAT)
        return


# Handle blocker declarations
async def handle_declare_blockers(
    pdu: dict,
    player_id: str,
    game_server
) -> None:
    state = game_server.state

    _combat_data(state)

    if state.phase != Phase.DECLARE_BLOCKERS:
        await _error(
            game_server,
            player_id,
            ec.WRONG_PHASE,
            "DECLARE_BLOCKERS is only legal during DECLARE_BLOCKERS.",
            pdu
        )
        return

    if player_id == state.active_player_id:
        await _error(
            game_server,
            player_id,
            ec.ILLEGAL_ACTION,
            "Only the Non-Active Player may declare blockers.",
            pdu
        )
        return

    valid_seq, expected = _validate_seq(
        pdu,
        player_id,
        game_server
    )

    if not valid_seq:
        await _error(
            game_server,
            player_id,
            ec.STALE_ACTION,
            f"Expected seq_num {expected}, got {pdu.get('seq_num')}.",
            pdu
        )
        return

    blockers = pdu.get("blockers")

    if not isinstance(blockers, list):
        await _error(
            game_server,
            player_id,
            ec.ILLEGAL_ACTION,
            "'blockers' must be a list.",
            pdu
        )
        return

    declared_blockers = set()
    assigned_blockers = set()

    for declaration in blockers:
        if not isinstance(declaration, dict):
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                "Each blocker declaration must be an object.",
                pdu
            )
            return

        blocker_id = declaration.get("creature_id")
        attacker_id = declaration.get("blocking_id")

        if not blocker_id or not attacker_id:
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                "Blocker declaration requires creature_id and blocking_id.",
                pdu
            )
            return

        if blocker_id in declared_blockers:
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                f"Blocker '{blocker_id}' was assigned more than once.",
                pdu
            )
            return

        declared_blockers.add(blocker_id)

        if attacker_id not in state.combat_attackers:
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                f"'{attacker_id}' is not an attacking creature.",
                pdu
            )
            return

        blocker = _find_permanent(state, blocker_id)

        if blocker is None:
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                f"Blocker '{blocker_id}' is not on the battlefield.",
                pdu
            )
            return

        if blocker.controller_id != player_id:
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                f"Creature '{blocker_id}' is not controlled by you.",
                pdu
            )
            return

        if not _is_creature(blocker):
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                f"'{blocker_id}' is not a creature.",
                pdu
            )
            return

        if blocker.tapped:
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                f"Blocker '{blocker_id}' is tapped.",
                pdu
            )
            return

        if blocker_id in assigned_blockers:
            await _error(
                game_server,
                player_id,
                ec.ILLEGAL_ACTION,
                f"Blocker '{blocker_id}' cannot block multiple attackers.",
                pdu
            )
            return

        assigned_blockers.add(blocker_id)

    # Save the blockers
    state.combat_blockers.clear()

    for declaration in blockers:
        state.combat_blockers[
            declaration["creature_id"]
        ] = declaration["blocking_id"]

    logger.info(
        "%s declared blockers: %s",
        player_id,
        state.combat_blockers
    )

    await _broadcast_state(game_server)


# Handle damage order
async def handle_assign_damage_order(
    pdu: dict,
    player_id: str,
    game_server
) -> None:
    state = game_server.state

    _combat_data(state)

    if state.phase != Phase.ASSIGN_DAMAGE_ORDER:
        await _error(
            game_server,
            player_id,
            ec.WRONG_PHASE,
            "ASSIGN_DAMAGE_ORDER is only legal during ASSIGN_DAMAGE_ORDER.",
            pdu
        )
        return

    if player_id != state.active_player_id:
        await _error(
            game_server,
            player_id,
            ec.NOT_YOUR_PRIORITY,
            "Only the Active Player may assign damage order.",
            pdu
        )
        return

    valid_seq, expected = _validate_seq(
        pdu,
        player_id,
        game_server
    )

    if not valid_seq:
        await _error(
            game_server,
            player_id,
            ec.STALE_ACTION,
            f"Expected seq_num {expected}, got {pdu.get('seq_num')}.",
            pdu
        )
        return

    attacker_id = pdu.get("attacker_id")
    blocker_order = pdu.get("blocker_order")

    if not attacker_id:
        await _error(
            game_server,
            player_id,
            ec.ILLEGAL_ACTION,
            "Missing attacker_id.",
            pdu
        )
        return

    if not isinstance(blocker_order, list):
        await _error(
            game_server,
            player_id,
            ec.ILLEGAL_ACTION,
            "'blocker_order' must be a list.",
            pdu
        )
        return

    attacker = _find_permanent(state, attacker_id)

    if attacker is None:
        await _error(
            game_server,
            player_id,
            ec.ILLEGAL_ACTION,
            f"Attacker '{attacker_id}' does not exist.",
            pdu
        )
        return

    if attacker.controller_id != player_id:
        await _error(
            game_server,
            player_id,
            ec.ILLEGAL_ACTION,
            "You do not control this attacker.",
            pdu
        )
        return

    actual_blockers = [
        blocker_id
        for blocker_id, blocked_attacker in state.combat_blockers.items()
        if blocked_attacker == attacker_id
    ]

    if len(actual_blockers) < 2:
        await _error(
            game_server,
            player_id,
            ec.ILLEGAL_ACTION,
            f"Attacker '{attacker_id}' does not have multiple blockers.",
            pdu
        )
        return

    if len(blocker_order) != len(actual_blockers):
        await _error(
            game_server,
            player_id,
            ec.ILLEGAL_ACTION,
            "blocker_order must contain every blocker exactly once.",
            pdu
        )
        return

    if set(blocker_order) != set(actual_blockers):
        await _error(
            game_server,
            player_id,
            ec.ILLEGAL_ACTION,
            "blocker_order does not match the declared blockers.",
            pdu
        )
        return

    if len(set(blocker_order)) != len(blocker_order):
        await _error(
            game_server,
            player_id,
            ec.ILLEGAL_ACTION,
            "A blocker may only appear once in blocker_order.",
            pdu
        )
        return

    state.combat_damage_orders[attacker_id] = list(blocker_order)

    logger.info(
        "%s ordered blockers for %s: %s",
        player_id,
        attacker_id,
        blocker_order
    )


# Assign attacker damage
def _assign_attacker_damage(
    state,
    attacker,
    blockers,
    damage_events
):
    remaining = max(attacker.power or 0, 0)

    for blocker in blockers:
        if remaining <= 0:
            break

        lethal_needed = max(
            blocker.toughness - blocker.damage,
            0
        )

        amount = min(remaining, lethal_needed)

        if amount > 0:
            blocker.damage += amount

            damage_events.append({
                "source": attacker.card_id,
                "target": blocker.card_id,
                "amount": amount
            })

            remaining -= amount


# Assign blocker damage
def _assign_blocker_damage(
    attacker,
    blocker,
    damage_events
):
    amount = max(blocker.power or 0, 0)

    if amount <= 0:
        return

    attacker.damage += amount

    damage_events.append({
        "source": blocker.card_id,
        "target": attacker.card_id,
        "amount": amount
    })


# Resolve combat damage
def _resolve_damage_step(state, first_strike=False):
    damage_events = []

    blockers_by_attacker = _attacker_blockers(state)

    for attacker_id, attacker_data in state.combat_attackers.items():
        attacker = _find_permanent(state, attacker_id)

        if attacker is None:
            continue

        if first_strike:
            attacker_eligible = _creature_can_first_strike(attacker)

            if attacker_eligible:
                state.first_strike_done.add(attacker_id)
        else:
            if attacker_id in state.first_strike_done:
                attacker_eligible = _has_keyword(
                    attacker,
                    "double_strike"
                )
            else:
                attacker_eligible = _creature_can_normal_strike(
                    attacker
                )

        if attacker_eligible:
            blocker_ids = blockers_by_attacker.get(
                attacker_id,
                []
            )

            if blocker_ids:
                order = state.combat_damage_orders.get(
                    attacker_id,
                    blocker_ids
                )

                blockers = []

                for blocker_id in order:
                    blocker = _find_permanent(
                        state,
                        blocker_id
                    )

                    if blocker is not None:
                        blockers.append(blocker)

                _assign_attacker_damage(
                    state,
                    attacker,
                    blockers,
                    damage_events
                )
            else:
                target_id = attacker_data["target"]
                defending_player = state.get_player(target_id)

                if defending_player is not None:
                    amount = max(attacker.power or 0, 0)

                    if amount > 0:
                        defending_player.life -= amount

                        damage_events.append({
                            "source": attacker.card_id,
                            "target": target_id,
                            "amount": amount
                        })

    # Blockers deal damage
    for blocker_id, attacker_id in state.combat_blockers.items():
        blocker = _find_permanent(state, blocker_id)
        attacker = _find_permanent(state, attacker_id)

        if blocker is None or attacker is None:
            continue

        if first_strike:
            if not _creature_can_first_strike(blocker):
                continue
        else:
            if blocker_id in state.first_strike_done:
                if not _has_keyword(blocker, "double_strike"):
                    continue
            elif not _creature_can_normal_strike(blocker):
                continue

        _assign_blocker_damage(
            attacker,
            blocker,
            damage_events
        )

        if first_strike:
            state.first_strike_done.add(blocker_id)

    return damage_events


# Resolve first strike damage
async def resolve_first_strike_damage(game_server):
    state = game_server.state

    if state.phase != Phase.FIRST_STRIKE_DAMAGE:
        return

    damage_events = _resolve_damage_step(
        state,
        first_strike=True
    )

    creatures_died = _remove_dead_creatures(state)

    life_totals = {
        pid: player.life
        for pid, player in state.players.items()
    }

    seq = state.next_seq()

    result = builder.combat_damage_result(
        seq=seq,
        damage_report=damage_events
    )

    result["damage_events"] = damage_events
    result["life_totals"] = life_totals
    result["creatures_died"] = creatures_died

    await game_server.broadcast(result)

    await _broadcast_state(game_server)

    winner = _check_life_win(state)

    if winner is not None:
        loser = _opponent_id(state, winner)

        await game_server.end_game(
            winner,
            loser,
            "LIFE_ZERO"
        )


# Resolve normal combat damage
async def resolve_combat_damage(game_server):
    state = game_server.state

    if state.phase != Phase.COMBAT_DAMAGE:
        return

    damage_events = _resolve_damage_step(
        state,
        first_strike=False
    )

    creatures_died = _remove_dead_creatures(state)

    life_totals = {
        pid: player.life
        for pid, player in state.players.items()
    }

    seq = state.next_seq()

    result = builder.combat_damage_result(
        seq=seq,
        damage_report=damage_events
    )

    result["damage_events"] = damage_events
    result["life_totals"] = life_totals
    result["creatures_died"] = creatures_died

    await game_server.broadcast(result)

    await _broadcast_state(game_server)

    winner = _check_life_win(state)

    if winner is not None:
        loser = _opponent_id(state, winner)

        await game_server.end_game(
            winner,
            loser,
            "LIFE_ZERO"
        )
        return


# Check for a player at zero life
def _check_life_win(state):
    for pid, player in state.players.items():
        if player.life <= 0:
            return _opponent_id(state, pid)

    return None


# End combat
async def end_combat(game_server):
    state = game_server.state

    _combat_data(state)

    state.combat_attackers.clear()
    state.combat_blockers.clear()
    state.combat_damage_orders.clear()
    state.first_strike_done.clear()

    await _transition(
        game_server,
        Phase.END_OF_COMBAT
    )
