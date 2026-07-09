from __future__ import annotations

import struct
from dataclasses import dataclass

from .protocols.frame import ProtocolError, decode_frame, encode_frame
from .transports import Service, Status, Transport


class DeviceError(RuntimeError):
    pass


@dataclass
class HomeEnergyStationClient:
    """Thin device client wrapping services under test.

    Keep this layer small and reusable: tests should validate behavior, not copy
    low-level framing logic everywhere.
    """

    transport: Transport

    measurement_names = {
        "pv_power_kw": 1,
        "ev_power_kw": 2,
        "grid_power_kw": 3,
        "battery_soc_percent": 4,
    }

    mode_codes = {
        "STANDBY": 0,
        "SELF_CONSUMPTION": 1,
        "EV_CHARGE": 2,
        "V2H_BACKUP": 3,
        "V2G_GRID_SERVICE": 4,
    }

    def _request(self, service: int, payload: bytes = b"") -> tuple[int, bytes]:
        raw = self.transport.exchange(encode_frame(service, payload))
        frame = decode_frame(raw)
        if frame.service != service:
            raise ProtocolError(f"response service mismatch: {frame.service} != {service}")
        if not frame.payload:
            raise ProtocolError("response missing status byte")
        return frame.payload[0], frame.payload[1:]

    def ping(self) -> bool:
        status, payload = self._request(Service.PING)
        return status == Status.OK and payload == b"PONG"

    def read_measurement(self, name: str) -> float:
        measurement_id = self.measurement_names[name]
        status, payload = self._request(Service.READ_MEASUREMENT, bytes([measurement_id]))
        if status != Status.OK:
            raise DeviceError(f"read_measurement({name}) failed with status 0x{status:02X}")
        return struct.unpack("<f", payload)[0]

    def set_mode(self, mode: str) -> str:
        status, payload = self._request(Service.SET_MODE, bytes([self.mode_codes[mode]]))
        if status == Status.SAFETY_BLOCKED:
            raise DeviceError(f"safety interlock rejected mode {mode}: {payload.decode(errors='replace')}")
        if status != Status.OK:
            raise DeviceError(f"set_mode({mode}) failed with status 0x{status:02X}")
        return payload.decode("ascii")

    def cloud_status(self) -> str:
        status, payload = self._request(Service.CLOUD_STATUS)
        if status != Status.OK:
            raise DeviceError(f"cloud_status failed with status 0x{status:02X}")
        return payload.decode("ascii")

    def ota_status(self) -> str:
        status, payload = self._request(Service.OTA_STATUS)
        if status != Status.OK:
            raise DeviceError(f"ota_status failed with status 0x{status:02X}")
        return payload.decode("ascii")
