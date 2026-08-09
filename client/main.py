"""
Entry point for client: connects to server, starts client
"""

import asyncio
import logging
import sys
import json

from pathlib import Path
from client.display import render_lobby, render_game
from client.input_handler import InputHandler
from shared.constants import DEFAULT_PORT, PDU
from shared.framing import read_pdu, write_pdu

logging.basicConfig(
    level = logging.WARNING, # debugging for PDUs
    format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream = sys.stderr
)

logger = logging.getLogger(__name__)

class MTGNPClient:
    def __init__(self, slot: str, player_id: str, host: str, port: int):
        self.player_id = player_id
        self.deck = self._load_fixed_deck(slot)
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.handler = InputHandler(self)
        self.handler.my_id = player_id

    def _load_fixed_deck(self, player_id: str) -> list[str]:
        decks_path = Path(__file__).parent.parent / "data" / "player-decks.json"
        
        with open(decks_path, "r", encoding="utf-8") as f:
            decks = json.load(f)
        
        if player_id not in decks:
            print(f"No fixed deck found for player_id '{player_id}'.")
            print(f"Available player IDs: {list(decks.keys())}")
            sys.exit(1)
        
        return decks[player_id]

    async def connect(self) -> None:
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        print(f"Connected to {self.host}:{self.port} as '{self.player_id}'")

    async def send(self, pdu: dict) -> None:
        logger.debug("Sending PDU: %s", pdu)
        await write_pdu(self.writer, pdu)

    async def run(self) -> None:
        await self.connect()

        # Send PLAYER_READY PDU after connecting
        await self.send({
            "type": PDU.PLAYER_READY,
            "seq_num": 1,
            "player_id": self.player_id,
            "deck_list": self.deck
        })

        await asyncio.gather(
            self._receive_loop(), # continuously receive incoming PDUs
            self.handler.read_loop()  # handle input from user
        )

    async def _receive_loop(self) -> None:
        try:
            while True:
                pdu = await read_pdu(self.reader)
                logger.debug("Receiving PDU: %s", pdu)
                await self._handle_pdu(pdu)
        except ConnectionResetError:
            print("\nDisconnected from server.")
        except Exception as e:
            logger.exception("Receive loop error: %s", e)

    async def _handle_pdu(self, pdu: dict) -> None:
        pdu_type = pdu.get("type")

        # Handle PDUs received from server here
        if pdu_type == PDU.GAME_STATE_UPDATE:
            state = pdu.get("state", {})
            phase = state.get("phase", "")

            for pid in state.get("life_totals", {}):
                if pid != self.player_id:
                    pass

            if phase == "LOBBY":
                render_lobby(state, self.player_id)
            else:
                render_game(state, self.player_id)

        elif pdu_type == PDU.PHASE_TRANSITION:
            pass

        elif pdu_type == PDU.PRIORITY_GRANT:
            pass

        elif pdu_type == PDU.STACK_PUSH:
            pass

        elif pdu_type == PDU.STACK_RESOLVE:
            pass

        elif pdu_type == PDU.TRIGGER_ORDER:
            pass

        elif pdu_type == PDU.TRIGGER_CHOICE:
            pass

        elif pdu_type == PDU.COMBAT_DAMAGE_RESULT:
            pass

        elif pdu_type == PDU.GAME_OVER:
            pass

        elif pdu_type == PDU.ERROR:
            pass

        elif pdu_type == PDU.PONG:
            pass

        else:
            print(f"Unhandled PDU type: {pdu_type}")

def main():
    args = sys.argv[1:]
    if len(args) < 1:
        print("Usage: python -m client.main <slot>")
        sys.exit(1)

    slot = args[0]
    if slot not in ("player_1", "player_2"):
        print("Slot must either be 'player_1' or 'player_2'.")
        sys.exit(1)

    player_id = input("Enter your player name: ").strip()
    host = "127.0.0.1"
    client = MTGNPClient(slot, player_id, host, DEFAULT_PORT)

    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\nGoodbye!")

if __name__ == "__main__":
    main()