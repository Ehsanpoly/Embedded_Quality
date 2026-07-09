import pytest

from eqv.protocols import ProtocolError, crc16_modbus, decode_frame, encode_frame


def test_crc16_modbus_known_vector():
    assert crc16_modbus(b"123456789") == 0x4B37


def test_frame_round_trip():
    raw = encode_frame(0x10, b"\x01\x02")
    frame = decode_frame(raw)
    assert frame.service == 0x10
    assert frame.payload == b"\x01\x02"


def test_frame_rejects_corrupted_crc():
    raw = bytearray(encode_frame(0x10, b"\x01"))
    raw[-1] ^= 0xFF
    with pytest.raises(ProtocolError, match="bad CRC"):
        decode_frame(bytes(raw))
