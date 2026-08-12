"""
Called by the dispatcher for action PDU handlers: CAST_SPELL, PLAY_LAND, CONCEDE, DISCARD
"""

import logging
from shared.constants import (ErrorCode, GameOverReason, StackItemType,
                               SORCERY_SPEED_PHASES, Phase)
from server.state.player_state import Permanent
from server.pdu import builder

logger = logging.getLogger(__name__)


# Handle CAST_SPELL
async def handle_cast_spell(pdu: dict, player_id: str, game_server) -> None:    # Validate a push a spell onto stack
    state = game_server.state
    pm = game_server.priority_manager
    card_catalog = game_server.card_catalog

    if not await pm.validate_action(pdu, player_id):
        return

    card_id = pdu.get("card_id")
    targets = pdu.get("targets", [])
    payment = pdu.get("mana_payment", {})
    player = state.get_player(player_id)

    # Card must be in player's hand
    if card_id not in player.hand:
        await game_server.send_to(
            player_id,
            builder.error(
                seq = state.next_seq(),
                code = ErrorCode.ILLEGAL_ACTION,
                message = f"Card '{card_id}' is not in your hand.",
                rejected_action = pdu,
            )
        )
        return

    card = card_catalog.get(card_id)
    if card is None:
        await game_server.send_to(
            player_id,
            builder.error(
                seq = state.next_seq(),
                code = ErrorCode.ILLEGAL_ACTION,
                message = f"Unknown card ID '{card_id}'.",
                rejected_action = pdu,
            )
        )
        return

    # Sorcery & Creature speed check
    if card.is_sorcery:
        if state.phase not in SORCERY_SPEED_PHASES or player_id != state.active_player_id or not state.stack.is_empty():            
            await game_server.send_to(
                player_id,
                builder.error(
                    seq=state.next_seq(),
                    code=ErrorCode.WRONG_PHASE,
                    message="Sorceries and creatures may only be cast during your Main Phase with an empty stack.",
                    rejected_action=pdu,
                )
            )
            return

    # Mana payment check
    if not player.can_pay(card.mana_cost, card_catalog):
        await game_server.send_to(
            player_id,
            builder.error(
                seq = state.next_seq(),
                code = ErrorCode.INSUFFICIENT_MANA,
                message = f"Insufficient mana to cast '{card.name}'.",
                rejected_action = pdu,
            )
        )
        return

    # alidate targets (ILLEGAL_TARGET check)
    if targets and hasattr(game_server, "turn_manager"):
        if not game_server.turn_manager._targets_legal(targets, caster_id=player_id):
            await game_server.send_to(
                player_id,
                builder.error(
                    seq=state.next_seq(),
                    code=ErrorCode.ILLEGAL_TARGET,
                    message="One or more selected targets are illegal or no longer exist.",
                    rejected_action=pdu,
                )
            )
            return

    # Remove from hand, tap mana sources, push to stack
    player.hand.remove(card_id)
\    
    # tap the actual mana sources declared in mana_payment
    payment_sources = payment.get("sources", []) if isinstance(payment, dict) else payment
    for source_id in payment_sources:
        land_perm = next(
            (p for p in player.battlefield if p.card_id == source_id and not p.tapped),
            None
        )
        if land_perm:
            land_perm.tapped = True

    item = state.stack.push(StackItemType.SPELL, card_id, player_id, targets)

    seq = state.next_seq()
    await game_server.broadcast(builder.stack_push(seq, item))

    # Caster retains priority after casting
    await pm.grant_initial_priority(player_id)

    logger.info("Player '%s' cast '%s'.", player_id, card_id)

# Priority Pass
async def handle_priority_pass(pdu: dict, player_id: str, game_server) -> None:
    """Handles priority pass PDU and delegates to PriorityManager state machine."""
    await game_server.priority_manager.handle_pass(pdu, player_id)

# Handle PLAY_LAND
async def handle_play_land(pdu: dict, player_id: str, game_server) -> None:
    """
    Play a land. Does not use the stack. One per turn. AP only during main phase.
    """
    state = game_server.state
    pm = game_server.priority_manager
    player = state.get_player(player_id)
    card_catalog = game_server.card_catalog

    if not await pm.validate_action(pdu, player_id):
        return

    # Must be AP during main phase
    if player_id != state.active_player_id or state.phase not in SORCERY_SPEED_PHASES:
        await game_server.send_to(
            player_id,
            builder.error(
                seq = state.next_seq(),
                code = ErrorCode.WRONG_PHASE,
                message = "Lands may only be played during your main phase.",
                rejected_action = pdu,
            )
        )
        return

    if player.land_played_this_turn:
        await game_server.send_to(
            player_id,
            builder.error(
                seq = state.next_seq(),
                code = ErrorCode.ILLEGAL_ACTION,
                message = "You have already played a land this turn.",
                rejected_action = pdu,
            )
        )
        return

    card_id = pdu.get("card_id")
    if card_id not in player.hand:
        await game_server.send_to(
            player_id,
            builder.error(
                seq = state.next_seq(),
                code = ErrorCode.ILLEGAL_ACTION,
                message = f"Card '{card_id}' is not in your hand.",
                rejected_action = pdu,
            )
        )
        return

    card = card_catalog.get(card_id)
    if card is None or not card.is_land:
        await game_server.send_to(
            player_id,
            builder.error(
                seq = state.next_seq(),
                code = ErrorCode.ILLEGAL_ACTION,
                message = f"'{card_id}' is not a land.",
                rejected_action = pdu,
            )
        )
        return

    # Move land from hand to battlefield
    player.hand.remove(card_id)
    player.battlefield.append(Permanent(
        card_id = card_id,
        owner_id = player_id,
        controller_id = player_id,
        tapped = False,
        summoning_sick = False, # Lands are not creatures, making sickness irrelevant
    ))
    player.land_played_this_turn = True

    logger.info("Player '%s' played land '%s'.", player_id, card_id)

    # Broadcast updated state, AP retains priority
    for pid in state.player_ids:
        seq = state.next_seq()
        view = state.to_visible_dict(pid)
        await game_server.send_to(pid, builder.game_state_update(seq, view))

    await pm.grant_initial_priority(player_id)


# Handle CONCEDE
async def handle_concede(pdu: dict, player_id: str, game_server) -> None:
    # This results to immediate loss of player
    state = game_server.state
    winner_id = state.opponent_id(player_id)
    logger.info("Player '%s' conceded.", player_id)
    await game_server.end_game(winner_id, player_id, GameOverReason.CONCEDE)


# Handle DISCARD
async def handle_discard(pdu: dict, player_id: str, game_server) -> None:
    # Discard cards at cleanup
    state  = game_server.state
    player = state.get_player(player_id)

    card_ids = pdu.get("card_ids", [])
    for card_id in card_ids:
        if card_id not in player.hand:
            await game_server.send_to(
                player_id,
                builder.error(
                    seq = state.next_seq(),
                    code = ErrorCode.ILLEGAL_ACTION,
                    message = f"Card '{card_id}' is not in your hand.",
                    rejected_action = pdu,
                )
            )
            return
        player.hand.remove(card_id)
        player.graveyard.append(card_id)

    logger.info("Player '%s' discarded: %s", player_id, card_ids)

    # Signal the cleanup loop in turn manager that a discard was processed
    game_server.discard_event.set()


# ---------------------------------------------------------------------------
# PING
# ---------------------------------------------------------------------------
async def handle_ping(pdu: dict, player_id: str, game_server) -> None:
    # Echo a PONG back to the client with the same seq_num and timestamp
    await game_server.send_to(
        player_id,
        builder.pong(pdu.get("seq_num", 0), pdu.get("timestamp", 0))
    )