from __future__ import annotations

import json
import logging
from typing import Any

from .device import HomeEnergyStationClient
from .exceptions import DeviceError, DiagnosticError, ErrorContext
from .memory_health_models import MemoryDiagnosticReport
from .transports import Service, Status, service_name

log = logging.getLogger(__name__)


class MemoryDiagnosticClient:
    """High-level Python client for firmware-exposed memory diagnostics.

    Real embedded RAM/EEPROM tests should be implemented in firmware/bootloader
    where memory access is safe and deterministic. This Python layer triggers
    those diagnostics, validates the structured result, logs the evidence, and
    turns it into release-gate inputs.
    """

    def __init__(self, device: HomeEnergyStationClient) -> None:
        self.device = device

    def _request_report(self, service: int, payload: dict[str, Any] | None = None) -> MemoryDiagnosticReport:
        raw_payload = b"" if payload is None else json.dumps(payload, sort_keys=True).encode("utf-8")
        status, response = self.device._request(service, raw_payload)  # noqa: SLF001 - deliberate showcase boundary
        name = service_name(service)
        if status != Status.OK:
            raise DeviceError(
                f"memory diagnostic service {name} failed with status 0x{status:02X}",
                context=ErrorContext(service=name, operation="memory_diagnostic", details={"response": response.decode(errors="replace")}),
            )
        try:
            data = json.loads(response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DiagnosticError(
                "memory diagnostic service returned invalid JSON",
                context=ErrorContext(service=name, operation="parse_memory_json", details={"response_hex": response.hex()}),
            ) from exc
        report = MemoryDiagnosticReport.from_payload(data)
        log.info("memory diagnostic service=%s test=%s status=%s severity=%s", name, report.test_name, report.status, report.severity)
        return report

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
            raise DeviceError(
                f"fault injection failed with status 0x{status:02X}",
                context=ErrorContext(service="FAULT_INJECTION", operation=fault_code),
            )
        log.warning("simulated fault injected: %s", fault_code)
        return payload.decode("ascii")
