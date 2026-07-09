#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from eqv.quality import QualityMetrics, evaluate_release_gate  # noqa: E402


def main() -> int:
    events_path = Path("artifacts/test_events.jsonl")
    if not events_path.exists():
        print("No test_events.jsonl found. Run pytest first.")
        return 2

    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    total = len(events)
    failed = sum(1 for e in events if e["outcome"] != "passed")
    # Demo heuristic: in a real CI system this would come from rerun history.
    flaky = sum(1 for e in events if "flaky" in e.get("markers", []))
    critical = sum(1 for e in events if e["outcome"] != "passed" and "release_gate" in e.get("markers", []))
    duration = sum(float(e.get("duration_s", 0.0)) for e in events)

    result = evaluate_release_gate(QualityMetrics(total, failed, flaky, critical, duration))
    report = {"passed": result.passed, "reasons": result.reasons, "total_tests": total, "failed_tests": failed}
    Path("artifacts/quality_gate.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
