# Architecture

The showcase uses a layered design so test logic does not depend on the transport.

```text
Tests / CLI / CI
  ↓
Validation runner
  ↓
Device client + MemoryDiagnosticClient
  ↓
Transport interface
  ↓
FakeHilTransport or SerialTransport
```

## Replaceable transport boundary

`FakeHilTransport` simulates device behavior and runs in CI. `SerialTransport` is the real-hardware extension point. A future CAN, Modbus, Ethernet, or USB adapter can implement the same `exchange()` method.

## Device client

`HomeEnergyStationClient` hides frame encoding/decoding from tests. Tests call readable operations such as `ping`, `read_measurement`, `set_mode`, `cloud_status`, and `ota_status`.

## Memory diagnostic client

`MemoryDiagnosticClient` triggers firmware-exposed RAM/NVM services and returns structured reports. This keeps destructive or hardware-specific memory access inside firmware while Python collects evidence and gates releases.

## Fast state store

`FastStateStore` is a Redis-inspired host-side cache. It tracks values like firmware version, NVM CRC, cloud heartbeat, latest telemetry, and dirty keys. This allows the framework to skip slow checks when state is unchanged and run deeper validation when risk increases.

## Release evidence

The validation runner creates a structured report containing metadata, bench info, named check results, memory reports, TX/RX trace, cloud records, fast-state snapshot, and quality-gate result.
