"""
Handles PDU message framing
"""

import asyncio
import json
import struct

_verbose = False

MAX_PDU_SIZE = 65535
HEADER_SIZE = 4

def set_verbose(enabled: bool) -> None:
    global _verbose
    _verbose = enabled

def _print_pdu(direction: str, pdu: dict) -> None:
    label = ">>>" if direction == "Sent" else "<<<"
    print(f"\n{label} [{direction}] {pdu.get('type', '?')}"
          f"(seq={pdu.get('seq_num', '?')})")
    print(json.dumps(pdu, indent=4))
    print()

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

    pdu = json.loads(payload.decode("utf-8"))
    if _verbose:
        _print_pdu("Received", pdu)

    return pdu

# Serialize PDU as JSON to the stream
async def write_pdu(writer: asyncio.StreamWriter, pdu: dict) -> None:
    payload = json.dumps(pdu, separators=(",", ":")).encode("utf-8")
    if _verbose:
        _print_pdu("Sent", pdu)
        
    if len(payload) > MAX_PDU_SIZE:
        raise ValueError(f"PDU too large to send.")

    header = struct.pack(">I", len(payload))
    writer.write(header + payload)
    await writer.drain()

