"""
Entry point for client: connects to server, starts client
"""

import asyncio
import logging
import sys

from input_handler import render_lobby, render_game
from shared.constants import DEFAULT_PORT, PDU
from shared.framing import read_pdu, write_pdu

logging.basicConfig(
    level = logging.WARNING, # debugging for PDUs
    format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream = sys.stderr
)

logger = logging.getLogger(__name__)

class MTGNPClient:
    def __init__(self, player_id: str, host: str, port: int):
        self.player_id = player_id
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    async def connect(self) -> None:
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        print(f"Connected to {self.host}:{self.port} as '{self.player_id}'")

    async def send(self, pdu: dict) -> None:
        logger.debug("Sending PDU: %s", pdu)
        await write_pdu(self.writer, pdu)

    async def run(self) -> None:
        await self.connect()

        # Send PLAYER_READY after connecting
        await self.send({
            "type": PDU.PLAYER_READY,
            "seq_num": 1,
            "player_id": self.player_id,
            #"deck_list": self.deck
        })

        await asyncio.gather(
            self._receive_loop(), # continuously receive incoming PDUs
            # TODO: Handle input from player
        )

    # TODO: Call this function in run()
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
    player_id = input("Enter your player name: ").strip()
    host = "127.0.0.1"
    client = MTGNPClient(player_id, host, DEFAULT_PORT)

    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\n Goodbye!")

if __name__ == "__main__":
    main()