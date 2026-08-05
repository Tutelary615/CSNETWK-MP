"""
Handles the client-server connection
"""

import asyncio
import logging
from shared.framing import read_pdu

logger = logging.getLogger(__name__)

_connection_counter = 0 # temporary ID

async def handle_client(reader: asyncio.StreamReader,
                        writer: asyncio.StreamWriter,
                        game_server) -> None:
    
    global _connection_counter
    _connection_counter += 1
    provisional_id = f"player_{_connection_counter}"

    addr = writer.get_extra_info("peername")
    logger.info("New connection from %s assigned provisional id '%s'.", addr, provisional_id)

    game_server.register_connection(provisional_id, writer)

    try:
        while True:
            pdu = await read_pdu(reader)
            logger.debug("Received [%s]: %s", provisional_id, pdu)

            if pdu.get("type") == "PLAYER_READY":
                chosen_id = pdu.get("player_id", provisional_id)
                if chosen_id != provisional_id:
                    game_server.remove_connection(provisional_id)
                    provisional_id = chosen_id
                    game_server.register_connection(provisional_id, writer)

            await game_server.handle_pdu(pdu, provisional_id)

    except ConnectionResetError:
        logger.warning("Player %s disconnected.", provisional_id)
    except Exception as e:
        logger.exception("Error on connection for '%s': %s", provisional_id, e)
    finally:
        game_server.remove_connection(provisional_id)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass # TODO: handle DISCONNECT win condition here (Section 6.6)