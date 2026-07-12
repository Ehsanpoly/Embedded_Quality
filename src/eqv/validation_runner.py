from __future__ import annotations

import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from .artifacts import runtime_metadata, write_json
from .cloud import FakeCloudClient
from .device import DeviceError, HomeEnergyStationClient
from .fast_state_store import FastStateStore
from .memory_diagnostics import MemoryDiagnosticClient
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
    memory_reports: list[dict[str, Any]]
    fast_state_snapshot: dict[str, Any]
    artifact_manifest: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata,
            "bench": self.bench,
            "checks": [asdict(check) for check in self.checks],
            "quality_gate": self.quality_gate,
            "device_trace": self.device_trace,
            "cloud_records": self.cloud_records,
            "memory_reports": self.memory_reports,
            "fast_state_snapshot": self.fast_state_snapshot,
            "artifact_manifest": self.artifact_manifest,
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
    memory = MemoryDiagnosticClient(device)
    cloud = FakeCloudClient()
    store = FastStateStore()
    memory_reports: list[dict[str, Any]] = []

    store.set("bench.device_id", "ARA-SIM-0001")
    store.set("bench.firmware_version", "sim-fw-0.1.0")
    store.set("bench.transport", type(transport).__name__)
    store.set("cloud.heartbeat", "CONNECTED", ttl_s=30.0)

    checks: list[CheckResult] = []

    checks.append(_check("device_ping", lambda: {"pong": device.ping()}))

    def measurement_check() -> dict[str, Any]:
        values = {
            name: round(device.read_measurement(name), 3)
            for name in ["pv_power_kw", "ev_power_kw", "grid_power_kw", "battery_soc_percent"]
        }
        assert values["pv_power_kw"] >= 0
        assert 0 <= values["battery_soc_percent"] <= 100
        for key, value in values.items():
            store.set(f"telemetry.latest.{key}", value, ttl_s=10.0)
        store.append_stream("telemetry", values)
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

    def ram_quick_check() -> dict[str, Any]:
        report = memory.run_ram_quick_check()
        memory_reports.append(report.as_dict())
        store.set("memory.ram.status", report.status)
        store.set("memory.ram.tested_bytes", report.details.get("tested_bytes"))
        assert report.passed, report.as_dict()
        return report.as_dict()

    checks.append(_check("ram_quick_check", ram_quick_check))

    def nvm_crc_check() -> dict[str, Any]:
        before = store.snapshot()
        report = memory.verify_nvm_crc()
        memory_reports.append(report.as_dict())
        crc = report.details.get("actual_crc")
        expensive_scan_needed = store.has_changed("memory.nvm.crc", crc)
        store.set("memory.nvm.crc", crc)
        store.set("memory.nvm.schema_version", report.details.get("schema_version"))
        assert report.passed, report.as_dict()
        after = store.snapshot()
        details = report.as_dict()
        details["cache_decision"] = {
            "expensive_scan_needed": expensive_scan_needed,
            "changed_keys": FastStateStore.diff(before, after),
        }
        return details

    checks.append(_check("nvm_crc_integrity", nvm_crc_check))

    def nvm_scratch_check() -> dict[str, Any]:
        report = memory.scratch_write_readback(key="bench_counter", value=1)
        memory_reports.append(report.as_dict())
        store.set("memory.nvm.scratch_last_status", report.status)
        assert report.passed, report.as_dict()
        return report.as_dict()

    checks.append(_check("nvm_scratch_write_readback", nvm_scratch_check))

    def nvm_schema_check() -> dict[str, Any]:
        report = memory.validate_nvm_schema()
        memory_reports.append(report.as_dict())
        store.set("memory.nvm.schema_status", report.status)
        assert report.passed, report.as_dict()
        return report.as_dict()

    checks.append(_check("nvm_schema_validate", nvm_schema_check))

    def factory_lock_check() -> dict[str, Any]:
        report = memory.verify_factory_region_locked()
        memory_reports.append(report.as_dict())
        store.set("memory.nvm.factory_region_locked", report.details.get("factory_region_locked"))
        assert report.passed, report.as_dict()
        return report.as_dict()

    checks.append(_check("nvm_factory_region_locked", factory_lock_check))

    def wear_level_check() -> dict[str, Any]:
        report = memory.read_wear_level_stats()
        memory_reports.append(report.as_dict())
        store.set("memory.nvm.erase_write_cycles", report.details.get("erase_write_cycles"))
        assert report.status in {"PASS", "WARN"}
        return report.as_dict()

    checks.append(_check("nvm_wear_level_stats", wear_level_check, critical=False))

    def fast_cache_sanity_check() -> dict[str, Any]:
        before = store.snapshot()
        current_crc = store.get("memory.nvm.crc")
        should_skip_full_nvm_scan = not store.has_changed("memory.nvm.crc", current_crc)
        store.set("validation.cache.full_nvm_scan_skipped", should_skip_full_nvm_scan)
        after = store.snapshot()
        return {
            "current_crc": current_crc,
            "should_skip_full_nvm_scan": should_skip_full_nvm_scan,
            "reason": "CRC unchanged in host fast-state cache",
            "diff": FastStateStore.diff(before, after),
        }

    checks.append(_check("fast_state_store_cached_nvm_crc", fast_cache_sanity_check, critical=False))

    def cloud_telemetry_check() -> dict[str, Any]:
        transport.battery_soc_percent = 83.0
        payload = {
            "cloud_status": device.cloud_status(),
            "ota_status": device.ota_status(),
            "pv_power_kw": round(device.read_measurement("pv_power_kw"), 2),
            "battery_soc_percent": round(device.read_measurement("battery_soc_percent"), 2),
            "nvm_crc": store.get("memory.nvm.crc"),
        }
        ack = cloud.publish_telemetry("ARA-SIM-0001", payload)
        assert ack["accepted"] is True
        store.append_stream("cloud_acks", ack)
        return {"cloud_ack": ack, "payload": payload}

    checks.append(_check("device_to_cloud_telemetry", cloud_telemetry_check))

    failed = sum(not item.passed for item in checks)
    critical = sum((not item.passed) and item.critical for item in checks)
    memory_release_blockers = sum(1 for report in memory_reports if report["status"] != "PASS" and report["severity"] == "release_blocker")
    gate = evaluate_release_gate(
        QualityMetrics(
            total_tests=len(checks),
            failed_tests=failed,
            flaky_tests=0,
            critical_failures=critical,
            duration_s=sum(float(item.details.get("duration_s", 0.0)) for item in checks),
            memory_release_blockers=memory_release_blockers,
            required_artifacts_present=True,
        ),
        min_pass_rate=1.0,
        max_flakiness_rate=0.0,
    )
    artifact_manifest = {
        "local_validation_report": str(output) if output else None,
        "contains": [
            "runtime_metadata",
            "bench_metadata",
            "named_check_results",
            "memory_diagnostic_reports",
            "device_tx_rx_trace",
            "cloud_records",
            "fast_state_snapshot",
            "quality_gate_decision",
        ],
    }
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
        memory_reports=memory_reports,
        fast_state_snapshot=store.snapshot(),
        artifact_manifest=artifact_manifest,
    )
    if output:
        write_json(output, report.as_dict())
    return report
