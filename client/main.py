"""
Entry point for client: connects to server, starts client
"""

import asyncio
import logging
import sys
import json
import argparse

from pathlib import Path
from client.display import (render_lobby, render_game, render_game_over,
                            render_error, render_stack_push, render_stack_resolve,
                            render_phase_transition)
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
    def __init__(self, player_id: str, deck_slot: int, host: str, port: int, verbose: bool = False):
        self.player_id = player_id
        self.player_ready_seq = 0
        self.deck = self._load_fixed_deck(deck_slot)
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.handler = InputHandler(self)
        self.handler.my_id = player_id
        self.verbose = verbose

    def _load_fixed_deck(self, slot: int) -> list:
        deck_path = Path(__file__).parent.parent / "data" / f"deck_{slot}.json"
        with open(deck_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def connect(self) -> None:
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        print(f"Connected to {self.host}:{self.port} as '{self.player_id}'")

    async def send(self, pdu: dict) -> None:
        await write_pdu(self.writer, pdu)

    async def run(self) -> None:
        await self.connect()
        self.player_ready_seq += 1

        # Send PLAYER_READY PDU after connecting
        await self.send({
            "type": PDU.PLAYER_READY,
            "seq_num": self.player_ready_seq,
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
            state = pdu.get("game_state", {})
            phase = state.get("phase", "")

            # Update player hand and opponent id
            my_hand = state.get("hand", {}).get(self.player_id, [])
            self.handler.update_hand(my_hand)
            self.handler.update_state_seq(pdu.get("seq_num", 0))

            for pid in state.get("life_totals", {}):
                if pid != self.player_id:
                    self.handler.opponent_id = pid

            if phase == "LOBBY":
                render_lobby(state, self.player_id)
            else:
                render_game(state, self.player_id)

        elif pdu_type == PDU.PHASE_TRANSITION:
            render_phase_transition(pdu)

        elif pdu_type == PDU.PRIORITY_GRANT:
            seq = pdu.get("seq_num")
            self.handler.update_seq(seq)
            holder = pdu.get("player_id")
            if holder == self.player_id:
                print(f"\n[PRIORITY GRANTED - seq {seq}] Your move:")
                print(" > ", end="", flush=True)
            else:
                print(f"\nWaiting for {holder}...")

        elif pdu_type == PDU.STACK_PUSH:
            render_stack_push(pdu)

        elif pdu_type == PDU.STACK_RESOLVE:
            render_stack_resolve(pdu)

        elif pdu_type == PDU.TRIGGER_ORDER:
            pass

        elif pdu_type == PDU.TRIGGER_CHOICE:
            pass

        elif pdu_type == PDU.COMBAT_DAMAGE_RESULT:
            print(f"\n[COMBAT DAMAGE] ")
            for ev in pdu.get("damage_events", []):
                print(f"{ev['source']} -> {ev['target']}: {ev['amount']} damage")
            for pid, life in pdu.get("life_totals", {}).items():
                print(f"Life: {pid} = {life}")
            died = pdu.get("creatures_died", [])
            if died:
                print(f"Died: {died}")

        elif pdu_type == PDU.GAME_OVER:
            render_game_over(pdu, self.player_id)

            # Send a fresh PLAYER_READY to re-queue
            await self.send({
                "type": PDU.PLAYER_READY,
                "seq_num": 1, # TODO: change this
                "player_id": self.player_id,
                "deck_list": self.deck
            })

        elif pdu_type == PDU.ERROR:
            render_error(pdu)
            print(" > ", end="", flush = True)

        elif pdu_type == PDU.PONG:
            logger.debug("PONG received (ts = %s)", pdu.get("timestamp"))

        else:
            print(f"Unhandled PDU type: {pdu_type}")

def main():
    parser = argparse.ArgumentParser(description="MTGNP Client")
    parser.add_argument("player_id", help="must be a non-empty string")
    parser.add_argument("deck_slot", help="1 or 2")
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

    client = MTGNPClient(args.player_id, args.deck_slot, "127.0.0.1", 
                         DEFAULT_PORT, verbose=args.verbose)

    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\nGoodbye!")

if __name__ == "__main__":
    main()