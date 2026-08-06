"""
Reads player input and converts commands to PDU dicts
"""

class InputHandler:
    def __init__(self, client):
        self.client = client
        self.my_id = ""
        self.opponent_id = ""