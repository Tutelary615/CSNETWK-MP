"""
Constructs outgoing PDU for the server
"""

from shared.constants import PDU, Phase, DEFAULT_TIME_LIMIT

# ERROR PDU (S->C)
def error(seq: int, code: str, message: str, rejected_action: dict = None) -> dict:
    pdu = {
        "type": PDU.ERROR,
        "seq_num": seq,
        "code": code,
        "message": message,
    }

    if rejected_action is not None:
        pdu["rejected_action"] = rejected_action

    return pdu

# GAME STATE UPDATE PDU (S->C)
def game_state_update(seq: int, game_state : dict) -> dict:
    return {
        "type": PDU.GAME_STATE_UPDATE,
        "seq_num": seq,
        "game_state": game_state,
    }

# LOBBY GAME STATE UPDATE (S->C)
def lobby_state(seq: int, players_ready : int, waiting_for : list[int]) -> dict:
    return {
        "type": PDU.GAME_STATE_UPDATE,
        "seq_num": seq,
        "state": {
            "phase": "LOBBY",
            "players_ready": players_ready,
            "waiting_for": waiting_for
        }
    }

# PHASE TRANSITION PDU (S->C)
def phase_transition(seq: int, from_phase: str, to_phase: str, 
                     active_player: str, turn: int) -> dict:
    return {
        "type": PDU.PHASE_TRANSITION,
        "seq_num": seq,
        "from_phase": from_phase,
        "to_phase": to_phase,
        "active_player": active_player,
        "turn": turn
    }


# PRIORITY GRANT PDU (S->C)
def priority_grant(seq: int, player_id: str, 
                   time_limit_ms: int = DEFAULT_TIME_LIMIT) -> dict:
    return {
        "type": PDU.PRIORITY_GRANT,
        "seq_num": seq,
        "player_id": player_id,
        "time_limit_ms": time_limit_ms
    }

# STACK PUSH PDU (S->C)
def stack_push(seq: int, item) -> dict:
    # item is a StackItem instance
    return {
        "type": PDU.STACK_PUSH,
        "seq_num": seq,
        "stack_item_id": item.stack_item_id,
        "item_type": item.item_type,
        "source": item.source_id,
        "targets": item.targets,
        "controller": item.controller_id
    }

# STACK RESOLVE PDU (S->C)
def stack_resolve(seq: int, stack_item_id: str, result: str, 
                  state_changes: list) -> dict:
    return {
        "type": PDU.STACK_RESOLVE,
        "seq_num": seq,
        "stack_item_id": stack_item_id,
        "result": result,
        "state_changes": state_changes
    }

# TRIGGER ORDER PDU (S->C)
def trigger_order(seq: int, player_id: str, trigger_ids: list) -> dict:
    return {
        "type": PDU.TRIGGER_ORDER,
        "seq_num": seq,
        "player_id": player_id,
        "trigger_ids": trigger_ids
    }

# TRIGGER CHOICE PDU (S->C)
def trigger_choice(seq: int, trigger_id: str, source_id: str,
                   effect_summary: str, requires_target: bool,
                   legal_targets: list) -> dict:
    return {
        "type": PDU.TRIGGER_CHOICE,
        "seq_num": seq,
        "trigger_id": trigger_id,
        "source_id": source_id,
        "effect_summary": effect_summary,
        "requires_target": requires_target,
        "legal_targets": legal_targets,
    }


# COMBAT DAMAGE RESULT PDU (S->C)
def combat_damage_result(seq: int, damage_events: list,
                         life_totals: dict, creatures_died: list) -> dict:
    return {
        "type": PDU.COMBAT_DAMAGE_RESULT,
        "seq_num": seq,
        "damage_events": damage_events,
        "life_totals": life_totals,
        "creatures_died": creatures_died
    }


# GAME OVER PDU (S->C)
def game_over(seq: int, winner_id: str, loser_id: str, reason: str) -> dict:
    return {
        "type": PDU.GAME_OVER,
        "seq_num": seq,
        "winner_id": winner_id,
        "loser_id": loser_id,
        "reason": reason
    }


# PONG PDU (S->C)
def pong(seq: int, timestamp: int) -> dict:
    return {
        "type": PDU.PONG,
        "seq_num": seq,
        "timestamp": timestamp,
    }
