from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from .artifacts import write_json
from .validation_runner import run_embedded_quality_workflow


def _run(cmd: list[str]) -> int:
    print("$ " + " ".join(cmd))
    return subprocess.call(cmd)


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


def triage(args: argparse.Namespace) -> int:
    return _run([sys.executable, "scripts/triage_report.py"])


def bench_info(args: argparse.Namespace) -> int:
    report = run_embedded_quality_workflow(output=None)
    payload = {"bench": report.bench, "metadata": report.metadata}
    write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


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
