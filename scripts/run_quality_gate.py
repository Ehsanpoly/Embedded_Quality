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


REQUIRED_ARTIFACTS = [
    Path("artifacts/test_events.jsonl"),
    Path("artifacts/junit.xml"),
]


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    events_path = Path("artifacts/test_events.jsonl")
    if not events_path.exists():
        print("No test_events.jsonl found. Run pytest first.")
        return 2

    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    total = len(events)
    failed = sum(1 for e in events if e["outcome"] != "passed")
    # Demo heuristic: in a real CI system this would come from rerun history or a flaky-test database.
    flaky = sum(1 for e in events if "flaky" in e.get("markers", []))
    critical = sum(1 for e in events if e["outcome"] != "passed" and "release_gate" in e.get("markers", []))
    duration = sum(float(e.get("duration_s", 0.0)) for e in events)

    validation_report = _load_json(Path("artifacts/local_validation_report.json"))
    memory_release_blockers = sum(
        1
        for report in validation_report.get("memory_reports", [])
        if report.get("status") != "PASS" and report.get("severity") == "release_blocker"
    )
    required_artifacts_present = all(path.exists() and path.stat().st_size > 0 for path in REQUIRED_ARTIFACTS)

    result = evaluate_release_gate(
        QualityMetrics(
            total_tests=total,
            failed_tests=failed,
            flaky_tests=flaky,
            critical_failures=critical,
            duration_s=duration,
            memory_release_blockers=memory_release_blockers,
            required_artifacts_present=required_artifacts_present,
        )
    )
    report = {
        "passed": result.passed,
        "reasons": result.reasons,
        "meters": {
            "total_tests": total,
            "failed_tests": failed,
            "pass_rate": 0.0 if total == 0 else round((total - failed) / total, 4),
            "flaky_tests": flaky,
            "flakiness_rate": 1.0 if total == 0 else round(flaky / total, 4),
            "critical_failures": critical,
            "memory_release_blockers": memory_release_blockers,
            "duration_s": round(duration, 3),
            "required_artifacts_present": required_artifacts_present,
        },
        "required_artifacts": [str(path) for path in REQUIRED_ARTIFACTS],
    }
    Path("artifacts/quality_gate.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
