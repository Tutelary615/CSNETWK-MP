"""
Constructs outgoing PDU for the server
"""

from shared.constants import PDU

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

# TODO: Create other PDUs here