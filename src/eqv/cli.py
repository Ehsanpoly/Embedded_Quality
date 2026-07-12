from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from .artifacts import write_json
from .device import HomeEnergyStationClient
from .fast_state_store import FastStateStore
from .memory_diagnostics import MemoryDiagnosticClient
from .transports import FakeHilTransport, SerialTransport, Transport
from .validation_runner import run_embedded_quality_workflow


def _run(cmd: list[str]) -> int:
    print("$ " + " ".join(cmd))
    return subprocess.call(cmd)


def _transport_from_args(args: argparse.Namespace) -> Transport:
    if getattr(args, "target", "sim") == "serial":
        if not args.port:
            raise SystemExit("--port is required when --target serial")
        return SerialTransport(port=args.port, baudrate=args.baudrate)
    return FakeHilTransport()


def smoke(args: argparse.Namespace) -> int:
    report = run_embedded_quality_workflow(output=args.output)
    print(json.dumps(report.quality_gate, indent=2, sort_keys=True))
    return 0 if report.quality_gate["passed"] else 2


def validate(args: argparse.Namespace) -> int:
    if args.clean:
        artifacts = Path("artifacts")
        artifacts.mkdir(exist_ok=True)
        for pattern in ["*.json", "*.jsonl", "*.xml", "*.md"]:
            for path in artifacts.glob(pattern):
                path.unlink(missing_ok=True)

    smoke_code = smoke(argparse.Namespace(output=args.output))
    if smoke_code != 0:
        return smoke_code

    if args.with_pytest:
        test_code = _run([sys.executable, "-m", "pytest"])
        if test_code != 0:
            return test_code
        gate_code = _run([sys.executable, "scripts/run_quality_gate.py"])
        triage_code = _run([sys.executable, "scripts/triage_report.py"])
        if gate_code != 0:
            return gate_code
        return triage_code
    return 0


def memory_sanity(args: argparse.Namespace) -> int:
    transport = _transport_from_args(args)
    device = HomeEnergyStationClient(transport)
    memory = MemoryDiagnosticClient(device)
    reports = [
        memory.run_ram_quick_check(),
        memory.verify_nvm_crc(),
        memory.scratch_write_readback(key="bench_counter", value=1),
        memory.verify_factory_region_locked(),
    ]
    payload = {
        "target": args.target,
        "port": getattr(args, "port", None),
        "reports": [report.as_dict() for report in reports],
        "passed": all(report.passed for report in reports),
    }
    write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 2


def nvm_check(args: argparse.Namespace) -> int:
    transport = _transport_from_args(args)
    device = HomeEnergyStationClient(transport)
    memory = MemoryDiagnosticClient(device)
    reports = [
        memory.verify_nvm_crc(),
        memory.validate_nvm_schema(),
        memory.verify_factory_region_locked(),
        memory.read_wear_level_stats(),
    ]
    payload = {
        "target": args.target,
        "reports": [report.as_dict() for report in reports],
        "release_blockers": [report.as_dict() for report in reports if report.is_release_blocker],
    }
    write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not payload["release_blockers"] else 2


def fast_gate(args: argparse.Namespace) -> int:
    store = FastStateStore()
    store.set("device.firmware_version", "sim-fw-0.1.0")
    store.set("memory.nvm.crc", "0x91AF")
    store.set("cloud.heartbeat", "CONNECTED", ttl_s=30.0)
    before = store.snapshot()
    current_crc = "0x91AF"
    should_skip_full_nvm_scan = not store.has_changed("memory.nvm.crc", current_crc)
    store.set("validation.full_nvm_scan_skipped", should_skip_full_nvm_scan)
    payload = {
        "decision": "PASS" if should_skip_full_nvm_scan else "RUN_DEEP_NVM_SCAN",
        "reason": "NVM CRC unchanged in fast host state cache",
        "before": before,
        "after": store.snapshot(),
        "dirty_keys": store.dirty_keys(),
    }
    write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def endurance_plan(args: argparse.Namespace) -> int:
    payload = {
        "purpose": "Long-running tests that should not block every PR but should inform release readiness.",
        "tiers": [
            {"level": "L0", "name": "simulator sanity", "duration": "5-15 seconds", "trigger": "every commit"},
            {"level": "L1", "name": "hardware smoke", "duration": "30-90 seconds", "trigger": "bench check / PR label"},
            {"level": "L2", "name": "HIL regression", "duration": "5-20 minutes", "trigger": "nightly or release candidate"},
            {"level": "L3", "name": "endurance", "duration": "hours", "trigger": "overnight / weekly / release branch"},
        ],
        "memory_endurance_examples": [
            "bounded EEPROM scratch-page write/readback cycling",
            "power-cycle recovery while NVM transaction is active",
            "OTA migration against old NVM schema snapshots",
            "RAM canary and stack-watermark monitoring under long workload",
        ],
    }
    write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def triage(args: argparse.Namespace) -> int:
    return _run([sys.executable, "scripts/triage_report.py"])


def bench_info(args: argparse.Namespace) -> int:
    report = run_embedded_quality_workflow(output=None)
    payload = {"bench": report.bench, "metadata": report.metadata}
    write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _add_target_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target", choices=["sim", "serial"], default="sim")
    parser.add_argument("--port", default=None, help="Serial port, for example COM4 or /dev/ttyUSB0.")
    parser.add_argument("--baudrate", type=int, default=115200)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eqv",
        description="Embedded quality validation showcase runner.",
    )
    sub = parser.add_subparsers(dest="command", required=False)

    p_smoke = sub.add_parser("smoke", help="Run a hardware-free embedded validation smoke workflow.")
    p_smoke.add_argument("--output", default="artifacts/local_validation_report.json")
    p_smoke.set_defaults(func=smoke)

    p_validate = sub.add_parser("validate", help="Run local validation workflow, optionally followed by pytest/gates.")
    p_validate.add_argument("--output", default="artifacts/local_validation_report.json")
    p_validate.add_argument("--with-pytest", action="store_true", help="Run pytest, release quality gate, and triage report.")
    p_validate.add_argument("--clean", action="store_true", help="Remove previous local artifacts before running.")
    p_validate.set_defaults(func=validate)

    p_memory = sub.add_parser("memory-sanity", help="Run RAM/NVM sanity checks against simulator or serial target.")
    _add_target_args(p_memory)
    p_memory.add_argument("--output", default="artifacts/memory_sanity.json")
    p_memory.set_defaults(func=memory_sanity)

    p_nvm = sub.add_parser("nvm-check", help="Run NVM CRC/schema/factory-region checks.")
    _add_target_args(p_nvm)
    p_nvm.add_argument("--output", default="artifacts/nvm_check.json")
    p_nvm.set_defaults(func=nvm_check)

    p_fast_gate = sub.add_parser("fast-gate", help="Demo a Redis-inspired host fast-state validation decision.")
    p_fast_gate.add_argument("--output", default="artifacts/fast_gate.json")
    p_fast_gate.set_defaults(func=fast_gate)

    p_endurance = sub.add_parser("endurance-plan", help="Generate a long-running embedded endurance test plan artifact.")
    p_endurance.add_argument("--output", default="artifacts/endurance_plan.json")
    p_endurance.set_defaults(func=endurance_plan)

    p_triage = sub.add_parser("triage", help="Generate a markdown triage report from pytest events.")
    p_triage.set_defaults(func=triage)

    p_bench = sub.add_parser("bench-info", help="Write simulated bench metadata for demo/release evidence.")
    p_bench.add_argument("--output", default="artifacts/bench_info.json")
    p_bench.set_defaults(func=bench_info)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        args = parser.parse_args(["validate", "--with-pytest", "--clean"])
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
