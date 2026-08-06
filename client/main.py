"""
Entry point for client: connects to server, starts client
"""

import asyncio
import logging
import sys

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

    # TODO: Call this function in run()
    async def _receive_loop(self) -> None:
        try:
            while True:
                pdu = await read_pdu(self.reader)
                logger.debug("Receiving PDU: %s", pdu)
                # handle pdu
        except ConnectionResetError:
            print("\nDisconnected from server.")
        except Exception as e:
            logger.exception("Receive loop error: %s", e)

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