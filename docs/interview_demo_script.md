# Five-minute interview demo script

1. **Purpose**: “This is a small validation framework for a simulated cloud-connected home-energy station. It shows how I structure Python validation so it can move from simulator to HIL to CI.”
2. **Architecture**: “The tests do not talk directly to bytes. They call a reusable device client. The client uses a transport interface. Today the transport is a deterministic simulator; tomorrow it can be pyserial, CAN, Modbus, or Ethernet.”
3. **Protocol discipline**: “The frame layer validates SOF, length, service, and CRC. A corrupted frame fails deterministically, which is critical for reproducibility.”
4. **System behavior**: “The tests cover telemetry, EV charging mode, V2H safety interlock, cloud telemetry, and OTA status.”
5. **Regression from field data**: “Field events are classified into regression families so real failures become permanent coverage.”
6. **Release gate**: “CI produces JUnit, a JSON quality gate, and a triage report. A critical release-gate failure blocks the build.”
7. **Close**: “My goal is to help firmware, OS, cloud, and systems engineers detect defects earlier and make failures diagnosable instead of intermittent.”
