# Architecture Notes

## Design principle

Tests should express product behavior, not byte-level implementation details. The byte-level logic lives in protocol and transport layers; the tests call a reusable device client.

## Layers

```text
pytest / CLI runner
  -> HomeEnergyStationClient
    -> Transport interface
      -> FakeHilTransport or SerialTransport
        -> protocol frame codec
```

## Why this matters

The same test can run against a simulator, a serial USB-C bench, a CAN adapter, a Modbus endpoint, or a network-connected device when the fixture selects a different transport. This is the key to scaling validation while keeping tests maintainable.

## Release evidence

The runner produces structured JSON with named checks, bench metadata, TX/RX trace, cloud records, and gate status. This mirrors real release validation where pass/fail alone is not enough; teams need diagnosable artifacts.
