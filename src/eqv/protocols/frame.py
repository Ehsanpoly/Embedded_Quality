from __future__ import annotations

from dataclasses import dataclass

from .crc16 import crc16_modbus

SOF = 0xA5


class ProtocolError(ValueError):
    """Raised when a device frame cannot be decoded deterministically."""


@dataclass(frozen=True)
class Frame:
    service: int
    payload: bytes = b""


def encode_frame(service: int, payload: bytes = b"") -> bytes:
    """Encode a small deterministic frame used by the simulator.

    Format: SOF(1) LEN(1) SERVICE(1) PAYLOAD(N) CRC16_LE(2)
    CRC covers LEN + SERVICE + PAYLOAD.
    """
    if not 0 <= service <= 0xFF:
        raise ProtocolError("service must fit in one byte")
    length = 1 + len(payload)
    if length > 255:
        raise ProtocolError("frame payload too large for one-byte length")
    body = bytes([length, service]) + payload
    crc = crc16_modbus(body).to_bytes(2, "little")
    return bytes([SOF]) + body + crc


def decode_frame(raw: bytes) -> Frame:
    if len(raw) < 5:
        raise ProtocolError(f"frame too short: {len(raw)} bytes")
    if raw[0] != SOF:
        raise ProtocolError(f"bad SOF: expected 0x{SOF:02X}, got 0x{raw[0]:02X}")
    length = raw[1]
    expected_total = 1 + 1 + length + 2
    if len(raw) != expected_total:
        raise ProtocolError(f"bad length: expected {expected_total} bytes, got {len(raw)}")
    body = raw[1 : 2 + length]
    expected_crc = int.from_bytes(raw[-2:], "little")
    actual_crc = crc16_modbus(body)
    if actual_crc != expected_crc:
        raise ProtocolError(f"bad CRC: expected 0x{expected_crc:04X}, computed 0x{actual_crc:04X}")
    return Frame(service=raw[2], payload=raw[3:-2])
