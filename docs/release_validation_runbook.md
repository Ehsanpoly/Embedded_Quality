# Release Validation Runbook

## Purpose

This runbook explains how the showcase would be used as a release-confidence workflow for a cloud-connected embedded energy product.

## Local smoke validation

```bash
python main.py smoke --output artifacts/smoke_report.json
```

Use this before a pull request or before connecting a physical bench. It verifies protocol framing, measurement reads, EV mode acknowledgement, V2H low-SOC safety rejection, cloud telemetry serialization, and release-gate calculation.

## Full local validation

```bash
python main.py validate --with-pytest --clean
```

This runs the bench-style workflow, pytest validation suite, release quality gate, and triage report.

## CI release gate

The CI job runs:

1. repository health check
2. ruff lint gate
3. smoke validation runner
4. pytest suite with coverage
5. release quality gate
6. triage artifact upload

## Evidence expected for a real device

For a physical HIL bench, each run should persist:

- device serial number
- firmware version
- OS image version
- test bench ID
- transport type and port/interface
- raw TX/RX trace
- device logs
- cloud correlation IDs
- JUnit report
- triage summary
- quality gate status

## Failure triage philosophy

A failure report should allow a firmware, OS, cloud, or systems engineer to reproduce the issue without guessing. A useful report includes exact command sequence, timestamps, observed state, expected state, actual state, reproduction rate, and logs/traces.
