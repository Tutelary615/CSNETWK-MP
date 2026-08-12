"""
tests/test_framing.py
----------------------
Basic tests for the PDU framing layer.
Run with: python -m pytest tests/
"""

import asyncio
import struct
import json
import pytest # install
from shared.framing import read_pdu, write_pdu, MAX_PDU_SIZE


# ---------------------------------------------------------------------------
# Helpers: build a fake StreamReader with pre-loaded bytes
# ---------------------------------------------------------------------------
def make_reader(payload_dict: dict) -> asyncio.StreamReader:
    payload = json.dumps(payload_dict).encode("utf-8")
    header  = struct.pack(">I", len(payload))
    reader  = asyncio.StreamReader()
    reader.feed_data(header + payload)
    return reader


def make_reader_raw(data: bytes) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    return reader


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_round_trip_simple():
    """A PDU written then read back should be identical."""
    original = {"type": "PING", "seq_num": 1, "timestamp": 12345}
    reader = make_reader(original)
    result = await read_pdu(reader)
    assert result == original


@pytest.mark.asyncio
async def test_round_trip_via_write():
    """write_pdu → read_pdu should reproduce the dict exactly."""
    import io

    pdu_in = {"type": "PLAYER_READY", "seq_num": 1,
               "player_id": "p1", "deck_list": ["mountain_001"]}

    # Capture bytes written by write_pdu using a fake writer
    buf = bytearray()

    class FakeWriter:
        def write(self, data):
            buf.extend(data)
        async def drain(self):
            pass
        def get_extra_info(self, key):
            return None

    await write_pdu(FakeWriter(), pdu_in)

    # Feed captured bytes into a StreamReader and read back
    reader = asyncio.StreamReader()
    reader.feed_data(bytes(buf))
    pdu_out = await read_pdu(reader)

    assert pdu_out == pdu_in


@pytest.mark.asyncio
async def test_oversized_pdu_raises():
    """A PDU claiming to be larger than MAX_PDU_SIZE should raise ValueError."""
    too_big = MAX_PDU_SIZE + 1
    header  = struct.pack(">I", too_big)
    reader  = make_reader_raw(header)
    with pytest.raises(ValueError, match="too large"):
        await read_pdu(reader)


@pytest.mark.asyncio
async def test_zero_length_raises():
    """A zero-length PDU should raise ValueError."""
    header = struct.pack(">I", 0)
    reader = make_reader_raw(header)
    with pytest.raises(ValueError, match="zero"):
        await read_pdu(reader)


@pytest.mark.asyncio
async def test_partial_read_waits():
    """read_pdu should block (not crash) if only the header arrives initially."""
    payload = json.dumps({"type": "PONG", "seq_num": 2}).encode("utf-8")
    header  = struct.pack(">I", len(payload))

    reader  = asyncio.StreamReader()
    reader.feed_data(header)   # feed header only first

    async def delayed_body():
        await asyncio.sleep(0.01)
        reader.feed_data(payload)

    result, _ = await asyncio.gather(read_pdu(reader), delayed_body())
    assert result["type"] == "PONG"