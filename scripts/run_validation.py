#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from eqv.validation_runner import run_embedded_quality_workflow  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic embedded validation and write JSON evidence.")
    parser.add_argument("--output", default="artifacts/local_validation_report.json")
    parser.add_argument("--low-soc", type=float, default=15.0, help="SOC used to verify V2H/V2G safety rejection.")
    args = parser.parse_args()

    report = run_embedded_quality_workflow(low_soc_for_safety_check=args.low_soc, output=args.output)
    print(json.dumps(report.quality_gate, indent=2, sort_keys=True))
    print(f"wrote {Path(args.output)}")
    return 0 if report.quality_gate["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
