# Embedded Quality Validation Showcase

Python validation framework showcase for **cloud-connected embedded home-energy devices**: EV charging, PV/BESS telemetry, bidirectional-energy safety interlocks, protocol framing, device-to-cloud behavior, OTA status, regression from field logs, CI artifacts, and release quality gates.

This is a portfolio project. It uses a deterministic simulator and contains no proprietary code.

## Why this repo exists

The target role requires Python-based embedded validation, reusable test libraries, HIL/integration/regression testing, CI/CD quality gates, field-log-driven coverage, diagnosability, and reliable release evidence. This repo demonstrates those skills in a compact, runnable form.

## What makes this a stronger showcase

| Showcase element | Why it matters for an Embedded Quality Developer |
|---|---|
| `main.py` and `eqv` CLI | Interview-friendly entry point; one command can run a complete validation workflow. |
| `Makefile` | Linux/macOS developer workflow: install, smoke, test, validate, coverage, clean, CI. |
| `run_validation.bat` | Windows one-click workflow for teams using Windows benches and USB/serial tools. |
| `scripts/run_validation.py` | Bench-style runner that produces JSON evidence without requiring pytest. |
| `scripts/check_repo_health.py` | Fast structural/import gate before expensive validation. |
| `.github/workflows/ci.yml` | Multi-version CI, lint gate, smoke runner, pytest, coverage, release gate, artifact upload. |
| `SerialTransport` boundary | Shows where USB-C UART / RS-232 / RS-485 real hardware plugs in without changing tests. |
| `validation_runner.py` | Demonstrates release-evidence thinking: named checks, bench metadata, traces, cloud records, and gate result. |

## Architecture

```text
main.py / eqv CLI
  │
  ├── smoke / validate / bench-info commands
  │
  ▼
eqv.validation_runner.run_embedded_quality_workflow
  │
  ├── eqv.device.HomeEnergyStationClient     readable behavior API
  ├── eqv.transports.Transport               replaceable hardware boundary
  │      ├── FakeHilTransport                deterministic HIL simulator
  │      └── SerialTransport                 optional real USB/serial adapter
  ├── eqv.cloud.FakeCloudClient              device-to-cloud test double
  ├── eqv.protocols.frame                    SOF/LEN/SERVICE/PAYLOAD/CRC validation
  └── eqv.quality.evaluate_release_gate      pass/fail release evidence
```

## Repository map

```text
src/eqv/
  protocols/                  frame codec and CRC validation
  transports.py               fake HIL transport + optional SerialTransport boundary
  device.py                   reusable device client for tests and runners
  cloud.py                    mock cloud endpoint
  telemetry.py                field-log parsing and regression mapping
  quality.py                  release gate metrics
  validation_runner.py        bench-style validation workflow
  cli.py                      command-line interface
scripts/
  run_validation.py           local/bench validation runner
  run_quality_gate.py         converts pytest events into release gate evidence
  triage_report.py            markdown triage artifact
  check_repo_health.py        fast import/structure gate
tests/                        protocol, HIL, cloud, regression, quality-gate tests
docs/                         strategy, runbook, traceability, interview walkthrough
.github/workflows/ci.yml      CI quality gate and artifact upload
main.py                       repository-level entry point
Makefile                      Linux/macOS automation
run_validation.bat            Windows one-click automation
```

## Quick start

### Cross-platform Python commands

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
python main.py smoke
python main.py validate --with-pytest --clean
```

### Linux/macOS Makefile workflow

```bash
make install-dev
make validate
make coverage
```

### Windows workflow

Double-click or run:

```bat
run_validation.bat
```

## Expected artifacts

```text
artifacts/local_validation_report.json  # bench-style named checks + metadata + device traces
artifacts/smoke_report.json             # fast local demo report
artifacts/junit.xml                     # pytest result artifact
artifacts/test_events.jsonl             # per-test event stream
artifacts/quality_gate.json             # release-gate result
artifacts/triage_report.md              # failure triage summary
```

## Services covered

| Service area | What is demonstrated |
|---|---|
| Protocol validation | frame encode/decode, CRC16, corrupted-frame rejection |
| HIL/simulator validation | device ping, power telemetry, mode changes |
| Safety behavior | V2H/V2G blocked when SOC is below threshold |
| Device-to-cloud | JSON-serializable telemetry and cloud status workflow |
| OTA/update validation | OTA state endpoint included in workflow |
| Field-log regression | field events mapped to permanent regression families |
| CI quality gates | pass rate, flakiness, critical failures, duration budget |
| Artifact collection | JUnit XML, test events, quality gate JSON, triage report |

## What to show in an interview

1. `main.py` — one-command demo entry point.
2. `src/eqv/validation_runner.py` — named checks, bench metadata, device trace, cloud records, release gate.
3. `src/eqv/transports.py` — transport boundary, deterministic simulator, real serial extension point.
4. `src/eqv/device.py` — reusable test client hiding byte-level details from test cases.
5. `tests/test_device_workflows.py` — HIL-style workflows for measurements, EV mode, V2H safety, and cloud telemetry.
6. `.github/workflows/ci.yml` — CI validation, quality gate, coverage, and artifact upload.
7. `docs/traceability_matrix.md` — release evidence and requirement-to-test traceability.

A strong 30-second explanation:

> I prepared this portfolio repo to show how I think about embedded validation architecture. It has a replaceable transport layer, deterministic protocol validation, a simulated HIL target, pytest fixtures, a CLI runner, Windows and Makefile automation, device-to-cloud telemetry checks, field-log-driven regression mapping, CI quality gates, and artifact generation. The point is not the simulator itself; the point is the structure: readable tests, reusable libraries, reproducible failures, and release evidence.

## How this would connect to real hardware

- Use `SerialTransport` with the `serial` extra: `python -m pip install -e ".[dev,serial]"`.
- Add CAN support using `python-can` and Modbus RTU/TCP using a Modbus client library.
- Add bench controls for relay/power cycling and network-loss injection.
- Store every run with firmware version, OS image, device serial, raw TX/RX traces, cloud correlation IDs, and failure triage notes.
- Split tests into smoke, PR gate, nightly regression, long soak, OTA interruption, and release-candidate suites.

## Interview positioning

The important message is not that the simulator is complex. The message is that the validation architecture is scalable: tests are readable, transports are replaceable, failures produce artifacts, field issues become regressions, and release gates are explicit.
