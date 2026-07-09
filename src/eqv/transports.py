from __future__ import annotations

import logging
import struct
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .protocols.frame import Frame, decode_frame, encode_frame

log = logging.getLogger(__name__)


class Service:
    PING = 0x01
    READ_MEASUREMENT = 0x10
    SET_MODE = 0x20
    CLOUD_STATUS = 0x30
    OTA_STATUS = 0x40
    FAULT_INJECTION = 0xF0


class Status:
    OK = 0x00
    BAD_REQUEST = 0x01
    SAFETY_BLOCKED = 0x02
    UNKNOWN_SERVICE = 0xFE


class Transport(ABC):
    @abstractmethod
    def exchange(self, request: bytes, timeout_s: float = 1.0) -> bytes:
        """Send one request and return one response."""


@dataclass
class FakeHilTransport(Transport):
    """Deterministic HIL simulator used when physical hardware is unavailable.

    The simulator deliberately behaves like a small embedded target: requests are
    framed, status bytes are returned, telemetry is mutable, and injected faults
    can be used to reproduce field failures.
    """

    pv_power_kw: float = 4.2
    ev_power_kw: float = 7.4
    grid_power_kw: float = -1.1
    battery_soc_percent: float = 83.0
    cloud_connected: bool = True
    ota_state: str = "IDLE"
    active_mode: str = "SELF_CONSUMPTION"
    injected_faults: set[str] = field(default_factory=set)
    trace: list[dict[str, Any]] = field(default_factory=list)

    measurement_ids = {
        1: "pv_power_kw",
        2: "ev_power_kw",
        3: "grid_power_kw",
        4: "battery_soc_percent",
    }

    mode_codes = {
        0: "STANDBY",
        1: "SELF_CONSUMPTION",
        2: "EV_CHARGE",
        3: "V2H_BACKUP",
        4: "V2G_GRID_SERVICE",
    }

    def exchange(self, request: bytes, timeout_s: float = 1.0) -> bytes:
        start = time.perf_counter()
        req = decode_frame(request)
        status, payload = self._handle(req)
        response = encode_frame(req.service, bytes([status]) + payload)
        self.trace.append(
            {
                "service": req.service,
                "request_payload_hex": req.payload.hex(),
                "status": status,
                "response_payload_hex": payload.hex(),
                "duration_ms": round((time.perf_counter() - start) * 1000, 3),
            }
        )
        log.debug("simulated exchange service=0x%02X status=0x%02X", req.service, status)
        return response

    def _handle(self, req: Frame) -> tuple[int, bytes]:
        if req.service == Service.PING:
            return Status.OK, b"PONG"

        if req.service == Service.READ_MEASUREMENT:
            if len(req.payload) != 1:
                return Status.BAD_REQUEST, b""
            name = self.measurement_ids.get(req.payload[0])
            if not name:
                return Status.BAD_REQUEST, b""
            value = getattr(self, name)
            return Status.OK, struct.pack("<f", float(value))

        if req.service == Service.SET_MODE:
            if len(req.payload) != 1:
                return Status.BAD_REQUEST, b""
            mode = self.mode_codes.get(req.payload[0])
            if not mode:
                return Status.BAD_REQUEST, b""
            if mode.startswith("V2") and self.battery_soc_percent < 20:
                return Status.SAFETY_BLOCKED, b"soc_below_threshold"
            self.active_mode = mode
            return Status.OK, mode.encode("ascii")

        if req.service == Service.CLOUD_STATUS:
            text = b"CONNECTED" if self.cloud_connected else b"DISCONNECTED"
            return Status.OK, text

        if req.service == Service.OTA_STATUS:
            return Status.OK, self.ota_state.encode("ascii")

        if req.service == Service.FAULT_INJECTION:
            fault = req.payload.decode("ascii", errors="replace")
            self.injected_faults.add(fault)
            return Status.OK, fault.encode("ascii")

        return Status.UNKNOWN_SERVICE, b""


@dataclass
class SerialTransport(Transport):
    """Real-hardware adapter placeholder for USB-C UART / RS-232 / RS-485 benches.

    The class is intentionally optional: the showcase runs without pyserial, while
    the boundary shows exactly where a production bench would plug in physical
    hardware. Tests can keep using HomeEnergyStationClient unchanged.
    """

    port: str
    baudrate: int = 115200
    write_timeout_s: float = 1.0

    def exchange(self, request: bytes, timeout_s: float = 1.0) -> bytes:
        try:
            import serial  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:  # pragma: no cover - pyserial is optional in the showcase
            raise RuntimeError("SerialTransport requires pyserial: python -m pip install pyserial") from exc

        with serial.Serial(
            self.port,
            self.baudrate,
            timeout=timeout_s,
            write_timeout=self.write_timeout_s,
        ) as ser:
            ser.write(request)
            ser.flush()
            header = ser.read(2)
            if len(header) != 2:
                raise TimeoutError(f"serial timeout waiting for frame header on {self.port}")
            length = header[1]
            rest = ser.read(length + 2)
            if len(rest) != length + 2:
                raise TimeoutError(f"serial timeout waiting for {length + 2} frame bytes on {self.port}")
            return header + rest
