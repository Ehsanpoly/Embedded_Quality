# Memory Validation Strategy

## Principle

RAM and EEPROM/NVM validation should be split between firmware and the Python validation framework.

- Firmware/bootloader owns direct memory access because it knows safe regions, boot phase, RTOS state, stack/heap layout, and flash/EEPROM endurance limits.
- Python owns orchestration, evidence collection, release gating, regression creation, and fast/slow test selection.

## RAM validation

### Runtime-safe checks

The showcase models a `ram_quick_check` over a reserved diagnostic RAM region. This is safe for a running device because it does not overwrite stack, heap, DMA buffers, communication buffers, or RTOS memory.

Typical runtime-safe checks:

- reserved-region walking 1 / walking 0;
- canary verification;
- stack watermark;
- heap high-water mark;
- reset-reason and watchdog history;
- critical buffer guard bands.

### Bootloader/startup checks

Full RAM March tests are usually destructive and should run before the application uses RAM.

Typical boot/startup checks:

- March C / March X;
- checkerboard pattern;
- data bus test;
- address bus test;
- ECC/parity status where available.

## EEPROM / NVM validation

The showcase models:

- configuration CRC verification;
- reserved scratch-page write/readback;
- schema-version validation;
- factory-region lock verification;
- wear-level statistics.

Important production rule: never run aggressive write-cycling on every PR. EEPROM/flash endurance is finite. Use a reserved scratch page and bounded write counts for smoke tests; move endurance tests to nightly or weekly benches.

## Fast-vs-deep strategy

| Tier | Typical trigger | Memory scope |
|---|---|---|
| L0 simulator sanity | every commit | simulated RAM/NVM logic |
| L1 hardware smoke | PR label / bench check | RAM quick check, NVM CRC, scratch readback |
| L2 HIL regression | nightly / release candidate | recovery, OTA migration, power-loss-safe NVM transactions |
| L3 endurance | overnight / weekly | wear, repeated power cycle, long telemetry, thermal/load stress |

## Release-blocking examples

A release should be blocked when:

- RAM diagnostic reports an address/data mismatch;
- NVM CRC mismatch is detected;
- factory identity/calibration region is writable;
- NVM schema version is incompatible after OTA;
- scratch write/readback fails;
- required memory artifacts are missing.
