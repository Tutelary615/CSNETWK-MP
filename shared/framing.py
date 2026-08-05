"""
Handles PDU message framing
"""

import asyncio
import json
import struct

MAX_PDU_SIZE = 65535
HEADER_SIZE = 4

# Deserialize PDU from the stream
async def read_pdu(reader: asyncio.StreamReader) -> dict:
    try:
        header = await reader.readexactly(HEADER_SIZE)
    except asyncio.IncompleteReadError:
        raise ConnectionResetError("Connection closed while reading PDU header.")

    length = struct.unpack(">I", header)[0]

    if length == 0:
        raise ValueError("Received PDU with zero-byte payload.")
    if length > MAX_PDU_SIZE:
        raise ValueError(f"PDU too large: {length} bytes (max {MAX_PDU_SIZE})")

    try:
        payload = await reader.readexactly(length)
    except asyncio.IncompleteReadError:
        raise ConnectionResetError("Connection closed while reading PDU payload.")

    return json.loads(payload.decode("utf-8"))

# Serialize PDU as JSON to the stream
async def write_pdu(writer: asyncio.StreamWriter, pdu: dict) -> None:
    payload = json.dumps(pdu, separators=(",", ":")).encode("utf-8")

    if len(payload) > MAX_PDU_SIZE:
        raise ValueError(f"PDU too large to send.")

    header = struct.pack(">I", len(payload))
    writer.write(header + payload)
    await writer.drain()

