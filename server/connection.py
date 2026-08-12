"""
Handles the client-server connection
"""

import asyncio
import logging
from shared.framing import read_pdu
from shared.constants import ErrorCode as ec, Phase, GameOverReason, READ_TIMEOUT_SECONDS
from server.pdu import builder

logger = logging.getLogger(__name__)

_connection_counter = 0 # temporary ID

async def handle_client(reader: asyncio.StreamReader,
                        writer: asyncio.StreamWriter,
                        game_server) -> None:
    
    global _connection_counter
    _connection_counter += 1
    provisional_id = f"__conn_{_connection_counter}__"

    addr = writer.get_extra_info("peername")
    logger.info("New connection from %s assigned provisional id '%s'.", addr, provisional_id)

    game_server.register_connection(provisional_id, writer)

    timed_out = False

    try:
        while True:
            try:
                pdu = await asyncio.wait_for(read_pdu(reader), timeout=READ_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                logger.warning("Player '%s' timed out (no PDU in %ds).",
                                provisional_id, READ_TIMEOUT_SECONDS)
                timed_out = True
                break
            
            logger.debug("Received [%s]: %s", provisional_id, pdu)

            if pdu.get("type") == "PLAYER_READY":
                chosen_id = pdu.get("player_id", provisional_id)
                if chosen_id != provisional_id:
                    if chosen_id in game_server.state.player_ids and chosen_id not in (provisional_id,):
                        await game_server.send_to(provisional_id, builder.error(
                            seq=game_server.state.next_seq(),
                            code=ec.DUPLICATE_ID,
                            message=f"Player ID '{chosen_id}' is already taken.",
                            rejected_action=pdu
                            ))
                        continue
                    game_server.remove_connection(provisional_id, purge_state=True)
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
            pass 
        if game_server.state.phase not in (Phase.LOBBY, Phase.GAME_OVER):
            winner_id = game_server.state.opponent_id(provisional_id)
            if winner_id:
                await game_server.end_game(winner_id, provisional_id, GameOverReason.DISCONNECT)