from __future__ import annotations

import json
from typing import Any

from .device import DeviceError, HomeEnergyStationClient
from .memory_health_models import MemoryDiagnosticReport
from .transports import Service, Status


class MemoryDiagnosticClient:
    """High-level Python client for firmware-exposed memory diagnostics.

    Real embedded RAM/EEPROM tests should be implemented in firmware/bootloader
    where memory access is safe and deterministic. This Python layer triggers
    those diagnostics, validates the structured result, and turns it into release
    evidence and quality-gate inputs.
    """

    def __init__(self, device: HomeEnergyStationClient) -> None:
        self.device = device

    def _request_report(self, service: int, payload: dict[str, Any] | None = None) -> MemoryDiagnosticReport:
        raw_payload = b"" if payload is None else json.dumps(payload, sort_keys=True).encode("utf-8")
        status, response = self.device._request(service, raw_payload)  # noqa: SLF001 - deliberate showcase boundary
        if status != Status.OK:
            raise DeviceError(f"memory diagnostic service 0x{service:02X} failed with status 0x{status:02X}")
        data = json.loads(response.decode("utf-8"))
        return MemoryDiagnosticReport.from_payload(data)

    def run_ram_quick_check(self) -> MemoryDiagnosticReport:
        return self._request_report(Service.RAM_QUICK_CHECK)

    def verify_nvm_crc(self) -> MemoryDiagnosticReport:
        return self._request_report(Service.NVM_CRC_CHECK)

    def scratch_write_readback(self, *, key: str, value: int | str | float | bool) -> MemoryDiagnosticReport:
        return self._request_report(Service.NVM_SCRATCH_WRITE_READBACK, {"key": key, "value": value})

    def validate_nvm_schema(self) -> MemoryDiagnosticReport:
        return self._request_report(Service.NVM_SCHEMA_VALIDATE)

    def verify_factory_region_locked(self) -> MemoryDiagnosticReport:
        return self._request_report(Service.NVM_FACTORY_REGION_LOCKED)

    def read_wear_level_stats(self) -> MemoryDiagnosticReport:
        return self._request_report(Service.NVM_WEAR_LEVEL_STATS)

    def inject_fault(self, fault_code: str) -> str:
        status, payload = self.device._request(Service.FAULT_INJECTION, fault_code.encode("ascii"))  # noqa: SLF001
        if status != Status.OK:
            raise DeviceError(f"fault injection failed with status 0x{status:02X}")
        return payload.decode("ascii")
