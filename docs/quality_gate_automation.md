# Quality Gate Automation

A quality gate is an automatic release decision based on measured evidence.

## Inputs

In this repo, the gate reads:

- `artifacts/test_events.jsonl` from the pytest hook;
- `artifacts/junit.xml` from pytest;
- `artifacts/local_validation_report.json` from the validation runner;
- memory diagnostic reports inside the validation report.

## Meters

The gate measures:

| Meter | Meaning |
|---|---|
| total tests | number of executed tests |
| failed tests | tests that did not pass |
| pass rate | `(total - failed) / total` |
| flaky tests | tests marked or historically detected as flaky |
| flakiness rate | `flaky / total` |
| critical failures | failed tests marked as release-gating |
| memory release blockers | failed RAM/NVM reports with release-blocker severity |
| duration | total test runtime |
| required artifacts | whether expected evidence files exist |

## Automation flow

```text
git push / pull request
  ↓
GitHub Actions starts
  ↓
install package and dev tools
  ↓
run smoke validation
  ↓
run pytest
  ↓
pytest hook writes test_events.jsonl
  ↓
pytest writes junit.xml
  ↓
run_quality_gate.py evaluates meters
  ↓
quality_gate.json is written
  ↓
CI passes or fails automatically
  ↓
artifacts are uploaded for review
```

## Why this is automatic

The gate is just code. If a threshold is violated, the script exits with a non-zero exit code. GitHub Actions interprets that as a failed job, so a pull request can be blocked before release.

Example release-blocking reasons:

- pass rate below threshold;
- flakiness above threshold;
- critical failures present;
- memory release blockers present;
- required artifacts missing;
- runtime exceeds budget.
