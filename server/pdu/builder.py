"""
Constructs outgoing PDU for the server
"""

from shared.constants import PDU, Phase

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

def lobby_state(players_ready : int, waiting_for : list[int]) -> dict:
    return {
        'phase': Phase.LOBBY,
        'players_ready' : players_ready,
        'waiting_for': waiting_for
    }

# PHASE TRANSITION PDU (S->C)
def phase_transition(seq: int, phase: str, active_player_id: str) -> dict:
    return {
        "type": PDU.PHASE_TRANSITION,
        "seq_num": seq,
        "phase": phase,
        "active_player_id": active_player_id,
    }


# PRIORITY GRANT PDU (S->C)
def priority_grant(seq: int, player_id: str) -> dict:
    return {
        "type": PDU.PRIORITY_GRANT,
        "seq_num": seq,
        "player_id": player_id,
    }

# STACK PUSH PDU (S->C)
def stack_push(seq: int, item_id: str, card_data: dict, controller_id: str) -> dict:
    return {
        "type": PDU.STACK_PUSH,
        "seq_num": seq,
        "item_id": item_id,
        "card_data": card_data,
        "controller_id": controller_id
    }

# STACK RESOLVE PDU (S->C)
def stack_resolve(seq: int, item_id: str, result_data: dict = None) -> dict:
    pdu = {
        "type": PDU.STACK_RESOLVE,
        "seq_num": seq,
        "item_id": item_id,
    }
    if result_data is not None:
        pdu["result_data"] = result_data
    return pdu

# TRIGGER ORDER PDU (S->C)
def trigger_order(seq: int, triggers: list) -> dict:
    return {
        "type": PDU.TRIGGER_ORDER,
        "seq_num": seq,
        "triggers": triggers
    }

# TRIGGER CHOICE PDU (S->C)
def trigger_choice(seq: int, trigger_id: str, choices: list) -> dict:
    return {
        "type": PDU.TRIGGER_CHOICE,
        "seq_num": seq,
        "trigger_id": trigger_id,
        "choices": choices,
    }


# COMBAT DAMAGE RESULT PDU (S->C)
def combat_damage_result(seq: int, damage_report: list) -> dict:
    return {
        "type": PDU.COMBAT_DAMAGE_RESULT,
        "seq_num": seq,
        "damage_report": damage_report,
    }


# GAME OVER PDU (S->C)
def game_over(seq: int, winner_id: str, reason: str) -> dict:
    return {
        "type": PDU.GAME_OVER,
        "seq_num": seq,
        "winner_id": winner_id,
        "reason": reason,
    }


# PONG PDU (S->C)
def pong(seq: int, timestamp: int) -> dict:
    return {
        "type": PDU.PONG,
        "seq_num": seq,
        "timestamp": timestamp,
    }
