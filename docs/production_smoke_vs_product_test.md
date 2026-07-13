# Production Smoke Test vs Product Test

A production smoke test is a fast confidence check. It does not prove the entire product is perfect. It answers: is this firmware/hardware/software pipeline healthy enough for deeper testing?

## What are we testing?

Depending on the target, automated tests may test:

1. **Python validation framework**: CLI, pytest, fixtures, artifact creation, quality gate.
2. **Protocol layer**: frame encode/decode, CRC, malformed frame rejection, timeout behavior.
3. **Firmware interface**: ping, telemetry, mode command, diagnostic service responses.
4. **Firmware logic**: state transitions, safety interlocks, NVM schema, RAM diagnostic report, OTA status.
5. **Hardware interaction**: serial/CAN/Modbus/Ethernet connectivity, board boot, sensor path, relay/contactor commands, power-path behavior.
6. **Cloud-connected behavior**: telemetry publish, cloud status, reconnect, OTA state reporting.
7. **System release evidence**: pass rate, critical failures, memory blockers, artifact completeness.

## In this repo

The simulator tests framework + protocol + expected firmware behavior model. When `SerialTransport` replaces `FakeHilTransport`, the same tests begin validating real firmware and hardware communication.

## Good interview sentence

> A smoke test is not only a software connectivity test. On real hardware it verifies that the board boots, firmware exposes required services, the communication pipeline works, safety-critical state can be observed, RAM/NVM diagnostics are healthy, and enough evidence exists to decide whether deeper HIL/regression testing should continue.
