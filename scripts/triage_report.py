#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    path = Path("artifacts/test_events.jsonl")
    if not path.exists():
        print("No artifacts/test_events.jsonl found. Run pytest first.")
        return 2
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    failed = [e for e in events if e["outcome"] != "passed"]
    lines = ["# Failure Triage Report", ""]
    lines.append(f"Total tests: {len(events)}")
    lines.append(f"Failures: {len(failed)}")
    lines.append("")
    if not failed:
        lines.append("No failing tests. Build is triage-clean.")
    else:
        for e in failed:
            lines.append(f"- `{e['nodeid']}` outcome={e['outcome']} markers={','.join(e.get('markers', []))}")
    Path("artifacts/triage_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("artifacts/triage_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
