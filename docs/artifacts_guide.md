# Artifact Guide

Artifacts are the evidence left behind by validation. They make failures reproducible, reviewable, and auditable.

## Responsibilities

Artifacts answer these questions:

- What was tested?
- On which bench/device/firmware/OS image?
- Which checks passed or failed?
- What raw TX/RX trace was observed?
- What RAM/NVM diagnostic report was returned?
- What telemetry was sent to the cloud?
- Why did the quality gate pass or fail?
- What should an engineer inspect first?

## Main artifacts

| Artifact | Produced by | Responsibility |
|---|---|---|
| `local_validation_report.json` | `main.py smoke` / validation runner | Full bench-style evidence package |
| `memory_sanity.json` | `main.py memory-sanity` | RAM/NVM smoke evidence |
| `nvm_check.json` | `main.py nvm-check` | NVM CRC/schema/factory/wear evidence |
| `fast_gate.json` | `main.py fast-gate` | Fast-state cache decision |
| `endurance_plan.json` | `main.py endurance-plan` | Long-running validation plan |
| `test_events.jsonl` | pytest hook in `tests/conftest.py` | Per-test event stream |
| `junit.xml` | pytest | Standard CI test result |
| `quality_gate.json` | `scripts/run_quality_gate.py` | Automatic release decision |
| `triage_report.md` | `scripts/triage_report.py` | Human-readable failure summary |

## Creation sequence

```text
validation command or pytest run
  ↓
checks execute against simulator or hardware
  ↓
reports/traces/events are written to artifacts/
  ↓
quality gate reads those artifacts
  ↓
triage report summarizes failures
  ↓
CI uploads artifacts for inspection
```
