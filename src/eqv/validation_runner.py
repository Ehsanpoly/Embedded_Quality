from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .artifacts import ArtifactManager, runtime_metadata
from .cloud import FakeCloudClient
from .context import ValidationContext
from .device import HomeEnergyStationClient
from .exceptions import DeviceError
from .fast_state_store import FastStateStore
from .memory_diagnostics import MemoryDiagnosticClient
from .pipeline import CheckResult, PipelineStage, ValidationPipeline
from .quality import QualityMetrics, evaluate_release_gate
from .transports import FakeHilTransport

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidationReport:
    metadata: dict[str, Any]
    context: dict[str, Any]
    bench: dict[str, Any]
    checks: list[CheckResult]
    quality_gate: dict[str, Any]
    device_trace: list[dict[str, Any]]
    cloud_records: list[dict[str, Any]]
    memory_reports: list[dict[str, Any]]
    fast_state_snapshot: dict[str, Any]
    artifact_manifest: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata,
            "context": self.context,
            "bench": self.bench,
            "checks": [asdict(check) for check in self.checks],
            "quality_gate": self.quality_gate,
            "device_trace": self.device_trace,
            "cloud_records": self.cloud_records,
            "memory_reports": self.memory_reports,
            "fast_state_snapshot": self.fast_state_snapshot,
            "artifact_manifest": self.artifact_manifest,
        }


def run_embedded_quality_workflow(
    *,
    low_soc_for_safety_check: float = 15.0,
    output: str | Path | None = "artifacts/local_validation_report.json",
    context: ValidationContext | None = None,
) -> ValidationReport:
    """Run a compact embedded-quality workflow without requiring physical hardware.

    This mirrors how a real bench runner is structured: create a run context,
    configure transport/client layers, execute a standard pipeline of named
    checks, collect TX/RX traces and diagnostic evidence, evaluate a release
    quality gate, then write artifacts for triage.
    """

    ctx = context or ValidationContext()
    ctx.artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifacts = ArtifactManager(ctx.artifacts_dir, run_id=ctx.run_id)
    transport = FakeHilTransport()
    device = HomeEnergyStationClient(transport)
    memory = MemoryDiagnosticClient(device)
    cloud = FakeCloudClient()
    store = FastStateStore()
    memory_reports: list[dict[str, Any]] = []

    log.info("run_id=%s embedded validation workflow started target=%s", ctx.run_id, ctx.target)

    store.set("bench.device_id", ctx.device_id)
    store.set("bench.firmware_version", ctx.firmware_version)
    store.set("bench.transport", type(transport).__name__)
    store.set("cloud.heartbeat", "CONNECTED", ttl_s=30.0)

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

    def v2h_safety_check() -> dict[str, Any]:
        transport.battery_soc_percent = low_soc_for_safety_check
        try:
            device.set_mode("V2H_BACKUP")
        except DeviceError as exc:
            return {"blocked": True, "reason": str(exc), "soc_percent": low_soc_for_safety_check}
        raise AssertionError("V2H_BACKUP was accepted below the SOC safety threshold")

    def ram_quick_check() -> dict[str, Any]:
        report = memory.run_ram_quick_check()
        memory_reports.append(report.as_dict())
        store.set("memory.ram.status", report.status)
        store.set("memory.ram.tested_bytes", report.details.get("tested_bytes"))
        assert report.passed, report.as_dict()
        return report.as_dict()

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

    def nvm_scratch_check() -> dict[str, Any]:
        report = memory.scratch_write_readback(key="bench_counter", value=1)
        memory_reports.append(report.as_dict())
        store.set("memory.nvm.scratch_last_status", report.status)
        assert report.passed, report.as_dict()
        return report.as_dict()

    def nvm_schema_check() -> dict[str, Any]:
        report = memory.validate_nvm_schema()
        memory_reports.append(report.as_dict())
        store.set("memory.nvm.schema_status", report.status)
        assert report.passed, report.as_dict()
        return report.as_dict()

    def factory_lock_check() -> dict[str, Any]:
        report = memory.verify_factory_region_locked()
        memory_reports.append(report.as_dict())
        store.set("memory.nvm.factory_region_locked", report.details.get("factory_region_locked"))
        assert report.passed, report.as_dict()
        return report.as_dict()

    def wear_level_check() -> dict[str, Any]:
        report = memory.read_wear_level_stats()
        memory_reports.append(report.as_dict())
        store.set("memory.nvm.erase_write_cycles", report.details.get("erase_write_cycles"))
        assert report.status in {"PASS", "WARN"}
        return report.as_dict()

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

    def cloud_telemetry_check() -> dict[str, Any]:
        transport.battery_soc_percent = 83.0
        payload = {
            "cloud_status": device.cloud_status(),
            "ota_status": device.ota_status(),
            "pv_power_kw": round(device.read_measurement("pv_power_kw"), 2),
            "battery_soc_percent": round(device.read_measurement("battery_soc_percent"), 2),
            "nvm_crc": store.get("memory.nvm.crc"),
        }
        ack = cloud.publish_telemetry(ctx.device_id, payload)
        assert ack["accepted"] is True
        store.append_stream("cloud_acks", ack)
        return {"cloud_ack": ack, "payload": payload}

    stages = [
        PipelineStage("device_ping", lambda: {"pong": device.ping()}),
        PipelineStage("power_measurements", measurement_check),
        PipelineStage("ev_charge_mode", lambda: {"ack_mode": device.set_mode("EV_CHARGE")}),
        PipelineStage("v2h_low_soc_safety_interlock", v2h_safety_check),
        PipelineStage("ram_quick_check", ram_quick_check),
        PipelineStage("nvm_crc_integrity", nvm_crc_check),
        PipelineStage("nvm_scratch_write_readback", nvm_scratch_check),
        PipelineStage("nvm_schema_validate", nvm_schema_check),
        PipelineStage("nvm_factory_region_locked", factory_lock_check),
        PipelineStage("nvm_wear_level_stats", wear_level_check, critical=False),
        PipelineStage("fast_state_store_cached_nvm_crc", fast_cache_sanity_check, critical=False),
        PipelineStage("device_to_cloud_telemetry", cloud_telemetry_check),
    ]

    checks = ValidationPipeline(run_id=ctx.run_id).run(stages)
    failed = sum(not item.passed for item in checks)
    critical = sum((not item.passed) and item.critical for item in checks)
    memory_release_blockers = sum(
        1 for report in memory_reports if report["status"] != "PASS" and report["severity"] == "release_blocker"
    )
    gate = evaluate_release_gate(
        QualityMetrics(
            total_tests=len(checks),
            failed_tests=failed,
            flaky_tests=0,
            critical_failures=critical,
            duration_s=sum(item.duration_s for item in checks),
            memory_release_blockers=memory_release_blockers,
            required_artifacts_present=True,
        ),
        min_pass_rate=1.0,
        max_flakiness_rate=0.0,
    )

    bench = {
        "bench_type": ctx.bench_type,
        "device_id": ctx.device_id,
        "firmware_version": ctx.firmware_version,
        "os_image": ctx.os_image,
        "transport": type(transport).__name__,
        "replaceable_by": ["SerialTransport", "CAN adapter", "Modbus adapter", "Ethernet adapter"],
    }
    report = ValidationReport(
        metadata=runtime_metadata(),
        context=ctx.as_dict(),
        bench=bench,
        checks=checks,
        quality_gate={"passed": gate.passed, "reasons": gate.reasons},
        device_trace=transport.trace,
        cloud_records=cloud.messages,
        memory_reports=memory_reports,
        fast_state_snapshot=store.snapshot(),
    )

    if output:
        output_path = Path(output)
        from .artifacts import write_json

        write_json(output_path, report.as_dict())
        artifacts.register(output_path, purpose="main validation report with checks, trace, memory, cloud and gate evidence")
    artifacts.register(ctx.path("validation.log"), purpose="structured console/file log for this validation run")
    manifest_path = artifacts.write_manifest()
    report = ValidationReport(
        metadata=report.metadata,
        context=report.context,
        bench=report.bench,
        checks=report.checks,
        quality_gate=report.quality_gate,
        device_trace=report.device_trace,
        cloud_records=report.cloud_records,
        memory_reports=report.memory_reports,
        fast_state_snapshot=report.fast_state_snapshot,
        artifact_manifest={"path": str(manifest_path), "artifacts": artifacts.manifest},
    )
    if output:
        from .artifacts import write_json

        write_json(output, report.as_dict())
    log.info("run_id=%s embedded validation workflow completed gate_passed=%s", ctx.run_id, gate.passed)
    return report
