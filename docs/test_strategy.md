# Test strategy

This repository demonstrates an embedded-quality workflow for a cloud-connected home-energy device. It is intentionally hardware-independent so that reviewers can run it immediately, while the architecture mirrors what would later connect to real benches.

## Risk-based validation layers

1. **Protocol layer**: deterministic frame parsing, CRC verification, corrupted-frame rejection, service-status handling.
2. **Device behavior layer**: reusable Python client APIs for ping, measurements, mode changes, cloud state, and OTA state.
3. **HIL / simulator layer**: a fake target that behaves like a small embedded device and can be replaced by serial, TCP, CAN, Modbus, or vendor benches.
4. **End-to-end workflow layer**: EV charging, V2H/V2G safety blocking, device-to-cloud telemetry, and OTA status checks.
5. **Regression layer**: field logs are classified and converted into regression families.
6. **Release gate layer**: pass rate, flakiness, critical failures, and duration budgets are evaluated before release.

## What I would extend with real hardware

- Replace `FakeHilTransport` with a pyserial transport for RS-232/RS-485/USB-C UART.
- Add python-can based CAN transport and Modbus TCP/RTU adapters.
- Add a bench inventory file: device serial number, firmware version, OS image, relay/power supply channel, cloud environment, and test owner.
- Store bench artifacts: raw TX/RX traces, power-cycle logs, firmware version, cloud correlation IDs, OTA logs, and failure screenshots.
- Add nightly stress tests, soak tests, power-cycle fault injection, network-loss tests, and OTA interruption tests.
