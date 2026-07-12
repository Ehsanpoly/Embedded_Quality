# Embedded Quality Validation Showcase

Python validation framework showcase for **cloud-connected embedded home-energy devices**: EV charging, PV/BESS telemetry, bidirectional-energy safety interlocks, protocol framing, RAM/NVM diagnostics, device-to-cloud behavior, OTA status, regression from field logs, CI artifacts, and automatic release quality gates.

This is a portfolio project. It uses a deterministic simulator and contains no proprietary code.

## Why this repo exists

An Embedded Quality Developer does more than write isolated pytest files. The role is about building validation infrastructure that makes embedded releases safer, faster, more reproducible, and easier to diagnose. This repo demonstrates that mindset with:

- reusable Python validation clients and fixtures;
- a replaceable transport boundary for simulator, USB-C serial, RS-232/RS-485, CAN, Modbus, or Ethernet;
- deterministic simulated HIL behavior for CI;
- RAM and EEPROM/NVM diagnostic workflows;
- Redis-inspired host-side fast state caching to avoid unnecessary slow tests;
- safety-interlock validation for bidirectional-energy workflows;
- device-to-cloud telemetry validation;
- field-log-to-regression mapping;
- quality gates and release artifacts.

## Interview message

> I designed this showcase as a compact embedded validation framework. The simulator can run in CI, while the same device client and tests can later run against USB/serial hardware. The framework collects traces, memory diagnostic reports, cloud records, quality-gate results, and triage artifacts. The important point is scalable validation: fast sanity checks for every commit, deeper HIL regression for release candidates, and long endurance tests for memory, OTA, and cloud reliability.

## Architecture

```text
main.py / eqv CLI
  │
  ├── smoke / validate / memory-sanity / nvm-check / fast-gate / endurance-plan
  │
  ▼
eqv.validation_runner.run_embedded_quality_workflow
  │
  ├── eqv.device.HomeEnergyStationClient       readable behavior API
  ├── eqv.memory_diagnostics                   RAM/NVM diagnostic service client
  ├── eqv.fast_state_store                     Redis-inspired host-side state cache
  ├── eqv.transports.Transport                 replaceable hardware boundary
  │      ├── FakeHilTransport                  deterministic HIL simulator
  │      └── SerialTransport                   optional real USB/serial adapter
  ├── eqv.cloud.FakeCloudClient                device-to-cloud test double
  ├── eqv.protocols.frame                      SOF/LEN/SERVICE/PAYLOAD/CRC validation
  ├── eqv.telemetry                            field-log regression mapping
  └── eqv.quality.evaluate_release_gate        automatic pass/fail release decision
```

## Repository map

```text
src/eqv/
  protocols/                    frame codec and CRC validation
  transports.py                 fake HIL transport + optional SerialTransport boundary
  device.py                     reusable device client for tests and runners
  memory_diagnostics.py         firmware RAM/NVM diagnostic client
  memory_health_models.py       structured memory diagnostic reports
  fast_state_store.py           Redis-inspired host validation cache
  cloud.py                      mock cloud endpoint
  telemetry.py                  field-log parsing and regression mapping
  quality.py                    release gate metrics and decision logic
  validation_runner.py          bench-style validation workflow
  cli.py                        command-line interface
scripts/
  run_validation.py             local/bench validation runner
  run_quality_gate.py           converts pytest events + artifacts into release gate evidence
  triage_report.py              markdown triage artifact
  check_repo_health.py          fast import/structure gate
tests/                          protocol, HIL, memory, cloud, regression, quality-gate tests
docs/                           strategy, runbook, memory validation, quality gate, artifacts
.github/workflows/ci.yml        CI quality gate and artifact upload
main.py                         repository-level entry point
Makefile                        Linux/macOS automation
run_validation.bat              Windows one-click automation
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

### New memory and fast-gate commands

```bash
python main.py memory-sanity --target sim
python main.py nvm-check --target sim
python main.py fast-gate
python main.py endurance-plan
```

For a real serial target:

```bash
python -m pip install -e ".[dev,serial]"
python main.py memory-sanity --target serial --port COM4 --baudrate 115200
# Linux example:
python main.py memory-sanity --target serial --port /dev/ttyUSB0 --baudrate 115200
```

### Linux/macOS Makefile workflow

```bash
make install-dev
make validate
make memory-sanity
make nvm-check
make fast-gate
make coverage
```

### Windows workflow

Double-click or run:

```bat
run_validation.bat
```

## Services covered

| Service area | What is demonstrated |
|---|---|
| Protocol validation | frame encode/decode, CRC16, corrupted-frame rejection |
| Deterministic HIL simulation | device ping, measurements, mode changes, telemetry, injected faults |
| RAM diagnostics | quick reserved-region RAM check with structured firmware-style report |
| EEPROM/NVM diagnostics | CRC, scratch write/readback, schema version, factory-region lock, wear stats |
| Fast testing strategy | host-side fast state store for CRC caching, TTL heartbeat, dirty keys, snapshots |
| Safety behavior | V2H/V2G blocked when SOC is below threshold |
| Device-to-cloud | telemetry payload, cloud ack, OTA state, cloud connectivity |
| Field-log regression | field events mapped to permanent regression families |
| CI quality gates | pass rate, flakiness, critical failures, memory blockers, duration, artifacts |
| Artifact collection | JUnit XML, test events, validation report, memory reports, triage report |

## RAM and EEPROM/NVM testing strategy

Python should not blindly overwrite embedded memory. A professional product exposes a **firmware diagnostic service**. Python triggers it, reads the structured result, and gates the release.

RAM examples in this showcase:

- `ram_quick_check` over a reserved diagnostic RAM region;
- release-blocking status when a RAM fault is reported;
- report fields such as tested bytes, algorithm, address, expected value, actual value.

NVM/EEPROM examples:

- configuration CRC verification;
- reserved scratch-page write/readback;
- schema-version compatibility check;
- factory identity/calibration region lock check;
- wear-level statistics.

The real-world split should be:

```text
L0 simulator sanity       every commit, seconds
L1 hardware smoke         bench/PR label, 30-90 seconds
L2 HIL regression         nightly/release candidate, minutes
L3 endurance/soak         overnight/weekly/release branch, hours
```

## Redis-inspired fast validation idea

The repo includes `FastStateStore`, a host-side in-memory cache. It is inspired by Redis concepts: fast key-value state, streams, TTL, snapshots, diffs, and dirty keys. The goal is to avoid repeating slow hardware operations when nothing relevant changed.

Example decisions:

```text
NVM CRC unchanged             → skip expensive full NVM scan in PR smoke
Firmware version changed      → run migration and compatibility tests
Cloud heartbeat TTL expired   → run reconnect/recovery test
Memory fault in field logs    → promote to regression test
SOC/grid state changed        → run safety-interlock transition checks
```

## Expected artifacts

```text
artifacts/local_validation_report.json  # named checks + metadata + memory reports + device traces
artifacts/memory_sanity.json            # RAM/NVM smoke result
artifacts/nvm_check.json                # NVM CRC/schema/factory/wear evidence
artifacts/fast_gate.json                # fast-state cache decision artifact
artifacts/endurance_plan.json           # suggested long-running test plan
artifacts/junit.xml                     # pytest result artifact
artifacts/test_events.jsonl             # per-test event stream from pytest hook
artifacts/quality_gate.json             # automatic release-gate result
artifacts/triage_report.md              # failure triage summary
```

Artifacts are produced after validation commands, pytest runs, and quality-gate scripts. They are the evidence package used for debugging, release decisions, and audit-style traceability.

## What to show in an interview

1. `main.py` — one-command demo entry point.
2. `src/eqv/validation_runner.py` — named checks, bench metadata, memory diagnostics, traces, cloud records, release gate.
3. `src/eqv/transports.py` — transport boundary, deterministic simulator, real serial extension point.
4. `src/eqv/memory_diagnostics.py` — Python client for firmware RAM/NVM diagnostic services.
5. `src/eqv/fast_state_store.py` — Redis-inspired cache for fast sanity validation.
6. `tests/test_memory_diagnostics.py` — RAM/NVM release-blocking examples.
7. `.github/workflows/ci.yml` — CI validation, quality gate, coverage, and artifact upload.

## How this would connect to real hardware

- Replace `FakeHilTransport` with `SerialTransport`, CAN, Modbus, or Ethernet adapter.
- Keep `HomeEnergyStationClient`, `MemoryDiagnosticClient`, pytest tests, and quality gates unchanged.
- Add bench controls for relay/power cycling, network-loss injection, charger/EV simulator, PV/BESS emulator, and OTA package server.
- Store every run with firmware version, OS image, device serial, raw TX/RX traces, cloud correlation IDs, memory reports, and failure triage notes.

## Professional positioning

The important message is not that the simulator is complex. The message is that the validation architecture is scalable: tests are readable, transports are replaceable, failures produce artifacts, field issues become regressions, memory diagnostics are release-gated, and quality decisions are automatic.
