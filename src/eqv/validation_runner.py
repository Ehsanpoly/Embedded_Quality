from __future__ import annotations

import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from .artifacts import runtime_metadata, write_json
from .cloud import FakeCloudClient
from .device import DeviceError, HomeEnergyStationClient
from .quality import QualityMetrics, evaluate_release_gate
from .transports import FakeHilTransport


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    critical: bool = True
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    metadata: dict[str, Any]
    bench: dict[str, Any]
    checks: list[CheckResult]
    quality_gate: dict[str, Any]
    device_trace: list[dict[str, Any]]
    cloud_records: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata,
            "bench": self.bench,
            "checks": [asdict(check) for check in self.checks],
            "quality_gate": self.quality_gate,
            "device_trace": self.device_trace,
            "cloud_records": self.cloud_records,
        }


def _check(name: str, func: Callable[[], dict[str, Any] | None], *, critical: bool = True) -> CheckResult:
    try:
        details = func() or {}
        return CheckResult(name=name, passed=True, critical=critical, details=details)
    except Exception as exc:  # noqa: BLE001 - validation runners must preserve evidence, not hide it
        return CheckResult(
            name=name,
            passed=False,
            critical=critical,
            error=repr(exc),
            details={"traceback_tail": traceback.format_exc().splitlines()[-6:]},
        )


def run_embedded_quality_workflow(
    *,
    low_soc_for_safety_check: float = 15.0,
    output: str | Path | None = "artifacts/local_validation_report.json",
) -> ValidationReport:
    """Run a compact embedded-quality workflow without requiring physical hardware.

    The function deliberately mirrors how a real bench runner would be structured:
    create a transport, wrap it with a reusable device client, run named checks,
    collect TX/RX traces, push representative telemetry, evaluate a release gate,
    and serialize evidence for triage.
    """
    transport = FakeHilTransport()
    device = HomeEnergyStationClient(transport)
    cloud = FakeCloudClient()

    checks: list[CheckResult] = []

    checks.append(_check("device_ping", lambda: {"pong": device.ping()}))

    def measurement_check() -> dict[str, Any]:
        values = {
            name: round(device.read_measurement(name), 3)
            for name in ["pv_power_kw", "ev_power_kw", "grid_power_kw", "battery_soc_percent"]
        }
        assert values["pv_power_kw"] >= 0
        assert 0 <= values["battery_soc_percent"] <= 100
        return values

    checks.append(_check("power_measurements", measurement_check))

    checks.append(_check("ev_charge_mode", lambda: {"ack_mode": device.set_mode("EV_CHARGE")}))

    def v2h_safety_check() -> dict[str, Any]:
        transport.battery_soc_percent = low_soc_for_safety_check
        try:
            device.set_mode("V2H_BACKUP")
        except DeviceError as exc:
            return {"blocked": True, "reason": str(exc), "soc_percent": low_soc_for_safety_check}
        raise AssertionError("V2H_BACKUP was accepted below the SOC safety threshold")

    checks.append(_check("v2h_low_soc_safety_interlock", v2h_safety_check))

    def cloud_telemetry_check() -> dict[str, Any]:
        transport.battery_soc_percent = 83.0
        payload = {
            "cloud_status": device.cloud_status(),
            "ota_status": device.ota_status(),
            "pv_power_kw": round(device.read_measurement("pv_power_kw"), 2),
            "battery_soc_percent": round(device.read_measurement("battery_soc_percent"), 2),
        }
        ack = cloud.publish_telemetry("ARA-SIM-0001", payload)
        assert ack["accepted"] is True
        return {"cloud_ack": ack, "payload": payload}

    checks.append(_check("device_to_cloud_telemetry", cloud_telemetry_check))

    failed = sum(not item.passed for item in checks)
    critical = sum((not item.passed) and item.critical for item in checks)
    gate = evaluate_release_gate(
        QualityMetrics(
            total_tests=len(checks),
            failed_tests=failed,
            flaky_tests=0,
            critical_failures=critical,
            duration_s=sum(float(item.details.get("duration_s", 0.0)) for item in checks),
        ),
        min_pass_rate=1.0,
        max_flakiness_rate=0.0,
    )
    report = ValidationReport(
        metadata=runtime_metadata(),
        bench={
            "bench_type": "deterministic_simulated_hil",
            "device_id": "ARA-SIM-0001",
            "firmware_version": "sim-fw-0.1.0",
            "os_image": "sim-linux-qa",
            "transport": type(transport).__name__,
            "replaceable_by": ["SerialTransport", "CAN adapter", "Modbus adapter", "Ethernet adapter"],
        },
        checks=checks,
        quality_gate={"passed": gate.passed, "reasons": gate.reasons},
        device_trace=transport.trace,
        cloud_records=cloud.messages,
    )
    if output:
        write_json(output, report.as_dict())
    return report
