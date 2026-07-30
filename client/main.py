# Entry point: connects to server, starts client

import asyncio
import logging
import sys
from shared.constants import DEFAULT_PORT

logging.basicConfig(
    level = logging.WARNING, # debugging for PDUs
    format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream = sys.stderr
)

logger = logging.getLogger(__name__)

class MTGNPClient:
    def __init__(self, player_id: str, deck: list[str], host: str, port: int):
        self.player_id = player_id
        self.deck = deck
        self.host = host
        self.port = port


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print("Client connected!")
        sys.exit(1)

    player_id = args[0]
    deck = args[1].split(",")
    host = args[2] if len(args) > 2 else "127.0.0.1"
    port = int(args[3]) if len(args) > 3 else DEFAULT_PORT

    client = MTGNPClient(player_id, deck, host, port)
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\n Goodbye!")

if __name__ == "__main__":
    main()