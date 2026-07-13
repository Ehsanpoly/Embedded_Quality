# Error Handling, Logging, and Pipeline Design

The goal of this repo is to show production-style embedded validation behavior. A mature validation framework should not fail with only a Python stack trace. It should say what service failed, which operation was running, what target was used, and what artifact should be inspected.

## Structured errors

`src/eqv/exceptions.py` defines typed errors:

- `TransportError`: timeout, serial failure, malformed frame, bench connection failure.
- `DeviceError`: non-OK device status, invalid mode, invalid measurement, safety rejection.
- `DiagnosticError`: malformed RAM/NVM diagnostic evidence.
- `ArtifactError`: artifact write/append failure.
- `PipelineError`: orchestration failure.

Each error can carry `ErrorContext`:

```text
service, operation, target, run_id, details
```

## Logging

`src/eqv/logging_config.py` writes UTC logs to console and `artifacts/validation.log`. Logs include run ID, stage name, pass/fail status, and duration.

## Pipeline connection

The pipeline connects repo components in this order:

```text
main.py / eqv CLI
  → ValidationContext
  → configure_logging
  → ValidationPipeline
  → PipelineStage actions
  → HomeEnergyStationClient / MemoryDiagnosticClient / FakeCloudClient / FastStateStore
  → QualityGate
  → ArtifactManager
```

## Why this matters in an embedded-quality interview

Embedded failures are expensive to reproduce. The framework should keep evidence: run ID, firmware version, bench target, TX/RX traces, memory reports, cloud payloads, stage timing, structured errors, and log files. This is the difference between a script and a validation infrastructure.
