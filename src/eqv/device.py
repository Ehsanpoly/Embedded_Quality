from __future__ import annotations

import logging
import struct
from dataclasses import dataclass

from .exceptions import DeviceError, ErrorContext, TransportError
from .protocols.frame import ProtocolError, decode_frame, encode_frame
from .transports import Service, Status, Transport, service_name

log = logging.getLogger(__name__)


@dataclass
class HomeEnergyStationClient:
    """Reusable device client wrapping services under test.

    Tests should call this readable behavior API instead of duplicating low-level
    framing logic. Replacing FakeHilTransport with SerialTransport keeps this
    client and the tests stable.
    """

    transport: Transport
    default_timeout_s: float = 1.0

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

    def _request(self, service: int, payload: bytes = b"", *, timeout_s: float | None = None) -> tuple[int, bytes]:
        timeout = self.default_timeout_s if timeout_s is None else timeout_s
        name = service_name(service)
        log.debug("device request service=%s payload_len=%d", name, len(payload))
        try:
            raw = self.transport.exchange(encode_frame(service, payload), timeout_s=timeout)
            frame = decode_frame(raw)
        except TransportError:
            raise
        except ProtocolError as exc:
            raise TransportError(
                "device response could not be decoded",
                context=ErrorContext(service=name, operation="decode_response", details={"payload_len": len(payload)}),
            ) from exc
        if frame.service != service:
            raise TransportError(
                "response service mismatch",
                context=ErrorContext(
                    service=name,
                    operation="request_response_match",
                    details={"expected_service": service, "actual_service": frame.service},
                ),
            )
        if not frame.payload:
            raise TransportError(
                "response missing status byte",
                context=ErrorContext(service=name, operation="status_decode"),
            )
        status = frame.payload[0]
        response_payload = frame.payload[1:]
        log.debug("device response service=%s status=0x%02X payload_len=%d", name, status, len(response_payload))
        return status, response_payload

    def ping(self) -> bool:
        status, payload = self._request(Service.PING)
        if status != Status.OK:
            raise DeviceError("ping returned non-OK status", context=ErrorContext(service="PING", operation="ping"))
        return payload == b"PONG"

    def read_measurement(self, name: str) -> float:
        if name not in self.measurement_names:
            raise DeviceError(
                f"unknown measurement {name}",
                context=ErrorContext(operation="read_measurement", details={"valid": sorted(self.measurement_names)}),
            )
        measurement_id = self.measurement_names[name]
        status, payload = self._request(Service.READ_MEASUREMENT, bytes([measurement_id]))
        if status != Status.OK:
            raise DeviceError(
                f"read_measurement({name}) failed with status 0x{status:02X}",
                context=ErrorContext(service="READ_MEASUREMENT", operation=name, details={"payload": payload.decode(errors="replace")}),
            )
        if len(payload) != 4:
            raise DeviceError(
                "measurement payload has invalid length",
                context=ErrorContext(service="READ_MEASUREMENT", operation=name, details={"payload_hex": payload.hex()}),
            )
        return struct.unpack("<f", payload)[0]

    def set_mode(self, mode: str) -> str:
        if mode not in self.mode_codes:
            raise DeviceError(
                f"unknown mode {mode}",
                context=ErrorContext(operation="set_mode", details={"valid": sorted(self.mode_codes)}),
            )
        status, payload = self._request(Service.SET_MODE, bytes([self.mode_codes[mode]]))
        reason = payload.decode(errors="replace")
        if status == Status.SAFETY_BLOCKED:
            raise DeviceError(
                f"safety interlock rejected mode {mode}: {reason}",
                context=ErrorContext(service="SET_MODE", operation=mode, details={"reason": reason}),
            )
        if status != Status.OK:
            raise DeviceError(
                f"set_mode({mode}) failed with status 0x{status:02X}",
                context=ErrorContext(service="SET_MODE", operation=mode, details={"reason": reason}),
            )
        return payload.decode("ascii")

    def cloud_status(self) -> str:
        status, payload = self._request(Service.CLOUD_STATUS)
        if status != Status.OK:
            raise DeviceError(
                f"cloud_status failed with status 0x{status:02X}",
                context=ErrorContext(service="CLOUD_STATUS", operation="read"),
            )
        return payload.decode("ascii")

    def ota_status(self) -> str:
        status, payload = self._request(Service.OTA_STATUS)
        if status != Status.OK:
            raise DeviceError(
                f"ota_status failed with status 0x{status:02X}",
                context=ErrorContext(service="OTA_STATUS", operation="read"),
            )
        return payload.decode("ascii")
