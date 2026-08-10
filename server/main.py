"""
Entry point for server: start asyncio server on port 4444
"""

import asyncio # to install
import logging
import sys
import argparse
from functools import partial
from shared.constants import DEFAULT_PORT
from shared.framing import set_verbose
from server.game_server import GameServer
from server.connection import handle_client

logging.basicConfig(
    level = logging.INFO,
    format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream = sys.stdout
)

logger = logging.getLogger(__name__)

async def main():
    # For verbose function
    parser = argparse.ArgumentParser(description="MTGNP Game Server")
    parser.add_argument(
        "-v", "--verbose",
        action = "store_true",
        help = "Print all PDUs sent and received to stdout"
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level = level,
        format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream = sys.stdout
    )

    if args.verbose:
        set_verbose(True)
        logger.info("Verbose mode ON. All PDUs will be printed.")
        
    # Start game server
    game_server = GameServer()

    # Bind client to game server instance
    client_handler = partial(handle_client, game_server=game_server)
    server = await asyncio.start_server(
        client_handler,
        host = "0.0.0.0",
        port = DEFAULT_PORT
    )

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    logger.info("MTGNP server listening on %s", addrs)
    logger.info("Waiting for 2 players to connect...")


    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shut down.")