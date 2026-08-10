"""
Reads player input and converts commands to PDU dicts
"""
import asyncio
import sys

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
  hand                          Re-display your hand
  help                          Show this message
"""

class InputHandler:
    def __init__(self, client):
        self.client = client
        self.current_seq = 0 # updated by client when it receives PRIORITY_GRANT
        self.player_name = ""
        self.my_id = ""
        self.opponent_id = ""
        self.last_hand = []

    def update_seq(self, seq: int) -> None:
        self.current_seq = seq

    def update_hand(self, hand: list) -> None:
        self.last_hand = hand

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
        if cmd == "help":
            print(HELP_TEXT)
            return None

        if cmd == "pass":
            pass

        if cmd == "cast":
            pass

        if cmd == "land":
            pass

        if cmd == "attack":
            pass

        if cmd == "block":
            pass

        if cmd == "concede":
            pass

        elif cmd == "hand":
            pass

        else:
            print("Unknown command. Type 'help' for command list.")
            return None

        
            