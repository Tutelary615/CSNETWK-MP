"""
Entry point for client: connects to server, starts client
"""

import asyncio
import logging
import sys
import json
import argparse

from pathlib import Path
from client.display import render_lobby, render_game
from client.input_handler import InputHandler
from shared.constants import DEFAULT_PORT, PDU
from shared.framing import read_pdu, write_pdu, set_verbose

logging.basicConfig(
    level = logging.WARNING, # debugging for PDUs
    format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream = sys.stderr
)

logger = logging.getLogger(__name__)

class MTGNPClient:
    def __init__(self, player_id: str, player_name: str, host: str, port: int, verbose: bool = False):
        self.player_id = player_id
        self.deck = self._load_fixed_deck(player_id)
        self.player_name = player_name
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.handler = InputHandler(self)
        self.handler.player_name = player_name
        self.handler.my_id = player_id
        self.verbose = verbose

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
                render_lobby(state, self.player_id, self.player_name)
            else:
                render_game(state, self.player_id, self.player_name)

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
    parser = argparse.ArgumentParser(description="MTGNP Client")
    parser.add_argument("player_id", help="(e.g. player_1, player_2)")
    parser.add_argument(
        "-v", "--verbose",
        action = "store_true",
        help = "Print all PDUs sent and received to stdout"
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level = level,
        format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream = sys.stderr
    )
    
    if args.verbose:
        set_verbose(True)
        logger.info("Verbose mode ON. All PDUs will be printed.\n")

    player_name = input("Enter your player name: ").strip()
    client = MTGNPClient(args.player_id, player_name, "127.0.0.1", DEFAULT_PORT, verbose=args.verbose)

    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\nGoodbye!")

if __name__ == "__main__":
    main()