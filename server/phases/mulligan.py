"""
Handles MULLIGAN_CHOICE PDUs
"""

import logging

from server.pdu import builder
from shared.constants import ErrorCode as ec

logger = logging.getLogger(__name__)

async def handle_mulligan_choice(pdu: dict, player_id: str, game_server) -> None:
    state = game_server.state
    player = state.get_player(player_id)

    if player is None:
        return

    expected_seq = game_server.last_sent_seq.get(player_id)
    if pdu.get("seq_num") != expected_seq:
        await game_server.send_to(
            player_id, 
            builder.error(
                seq = state.next_seq(),
                code = ec.STALE_ACTION,
                message = f"MULLIGAN_CHOICE seq_num mismatch."
                            f"Expected {expected_seq}, got {pdu.get('seq_num')}.",
                rejected_action = pdu
            )
        )
        return

    keep = pdu.get("keep", True)
    cards_to_bottom = pdu.get("cards_to_bottom", [])

    if not keep:
        # London Mulligan: draw fresh 7, will bottom N cards when keeping
        player.mulligan_count += 1
        player.hand.clear()
        # Put remaining library + previous hand back, then reshuffle
        player.library = list(player.library) # already emptied by prior draw
        player.draw_opening_hand(7)
        player.shuffle_library()

        logger.info("Player '%s' mulligans (count=%d).", player_id, player.mulligan_count)

        # Send the new hand
        seq = state.next_seq()
        view = state.to_visible_dict(player_id)
        game_server.last_sent_seq[player_id] = seq
        await game_server.send_to(player_id, builder.game_state_update(seq, view))
        return

    # keep=True: validate cards_to_bottom
    n = player.mulligan_count
    if len(cards_to_bottom) != n:
        await game_server.send_to(
            player_id,
            builder.error(
                seq = state.next_seq(),
                code = ec.ILLEGAL_ACTION,
                message = f"cards_to_bottom must contain exactly {n} card(s)."
                          f"Got {len(cards_to_bottom)}.",
                rejected_action = pdu,
            )
        )
        return

    for card_id in cards_to_bottom:
        if card_id not in player.hand:
            await game_server.send_to(
                player_id,
                builder.error(
                    seq = state.next_seq(),
                    code = ec.ILLEGAL_ACTION,
                    message = f"Card '{card_id}' is not in your hand.",
                    rejected_action = pdu,
                )
            )
            return

    # Move cards_to_bottom to the bottom of the library
    for card_id in cards_to_bottom:
        player.hand.remove(card_id)
        player.library.append(card_id)

    player.has_kept = True
    logger.info("Player '%s' keeps hand (%d cards).", player_id, len(player.hand))

    # Check if both players have kept
    if all(state.get_player(pid).has_kept for pid in state.player_ids):
        logger.info("Both players kept. Starting IN_GAME.")
        await game_server.start_in_game()