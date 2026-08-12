"""
Reads player input and converts commands to PDU dicts
"""
import asyncio
import sys

from shared.constants import PDU

HELP_TEXT = """
Commands:
  pass                          Pass priority
  cast <card_id> [target_id]    Cast a spell (target defaults to opponent)
  land <card_id>                Play a land
  attack <creature_id>          Declare attacker (against opponent)
  attack none                   Declare no attackers
  block <creature_id> <atk_id>  Declare a blocker
  block none                    Declare no blockers
  concede                       Concede the game
  mulligan                      Take a mulligan
  keep                          Keep your opening hand
  hand                          Re-display your hand
  help                          Show this message
"""

class InputHandler:
    def __init__(self, client):
        self.client = client
        self.current_seq = 0 # updated by client when it receives PRIORITY_GRANT
        self.last_state_seq = 0
        self.my_id = ""
        self.opponent_id = ""
        self.last_hand = []

    def update_seq(self, seq: int) -> None:
        self.current_seq = seq

    def update_hand(self, hand: list) -> None:
        self.last_hand = hand

    def update_state_seq(self, seq: int) -> None:
        self.last_state_seq = seq

    # Continuously read lines from stdin and convert to PDU to be sent
    async def read_loop(self) -> None:
        loop = asyncio.get_event_loop()
        while True:
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
            except EOFError:
                break

            if not line:
                break

            line = line.strip()
            if not line:
                continue

            pdu = self._parse_command(line)
            if pdu is not None:
                await self.client.send(pdu)

    # Parse user input to PDU
    def _parse_command(self, line: str):
        parts = line.split()
        if not parts:
            return None

        cmd = parts[0].lower()

        # HELP command
        if cmd == "help":
            print(HELP_TEXT)
            return None

        # PASS command
        if cmd == "pass":
            return {
                "type": PDU.PRIORITY_PASS,
                "seq_num": self.current_seq
            }

        # CAST command
        if cmd == "cast":
            if len(parts) < 2:
                print(" Usage: cast <card_id> [target_id]")
                return None
            card_id = parts[1]
            targets = [parts[2]] if len(parts) >= 3 else []
            return {
                "type": PDU.CAST_SPELL,
                "seq_num": self.current_seq,
                "card_id": card_id,
                "targets": targets,
                "mana_payment": {} # TODO: prompt for mana payment
            }

        # LAND command
        if cmd == "land":
            if len(parts) < 2:
                print("Usage: land <card_id>")
                return None
            return {
                "type": PDU.PLAY_LAND,
                "seq_num": self.current_seq,
                "card_id": parts[1]
            }

        # ATTACK command
        if cmd == "attack":
            if len(parts) < 2:
                print("Usage: attack <creature_id OR attack none")
                return None
            
            if parts[1].lower() == "none":
                return {
                    "type": PDU.DECLARE_ATTACKERS,
                    "seq_num": self.current_seq,
                    "attackers": []
                }
            
            return {
                "type": PDU.DECLARE_ATTACKERS,
                "seq_num": self.current_seq,
                "attackers": [{"creature_id": parts[1], "target": self.opponent_id}]
            }

        # BLOCK command
        if cmd == "block":
            if len(parts) < 2:
                print("Usage: block <creature_id> <attacker_id>  OR  block none")
                return None
            
            if parts[1].lower() == "none":
                return {
                    "type": PDU.DECLARE_BLOCKERS,
                    "seq_num": self.current_seq,
                    "blockers": []
                }
            
            if len(parts) < 3:
                print("Usage: block <creature_id> <attacker_id>")
                return None
            
            return {
                "type": PDU.DECLARE_BLOCKERS,
                "seq_num": self.current_seq,
                "blockers": [{"creature_id": parts[1], "blocking_id": parts[2]}],
            }

        # CONCEDE command
        if cmd == "concede":
            return {
                "type": PDU.CONCEDE,
                "seq_num": self.current_seq,
                "player_id": self.my_id,
            }

        # MULLIGAN command
        if cmd == "mulligan":
            return {
                "type": PDU.MULLIGAN_CHOICE,
                "seq_num": self.last_state_seq,
                "keep": False,
                "cards_to_bottom": []
            }

        # KEEP command
        if cmd == "keep":
            bottoms = parts[1:] # optional
            return {
                "type": PDU.MULLIGAN_CHOICE,
                "seq_num": self.last_state_seq,
                "keep": True,
                "cards_to_bottom": bottoms
            }

        # HAND command
        if cmd == "hand":
            print("Your hand:", self.last_hand)
            return None

        else:
            print("Unknown command. Type 'help' for command list.")
            return None

        
            