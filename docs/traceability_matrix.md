# Traceability matrix

| Requirement | Risk | Test(s) | Release impact |
|---|---|---|---|
| REQ-PROT-001 | Corrupted frames accepted as valid | `test_frame_rejects_corrupted_crc` | Blocks release |
| REQ-HIL-001 | Device telemetry not observable | `test_device_ping_and_measurements_are_observable` | Blocks release |
| REQ-SAFE-001 | Unsafe bidirectional energy mode under low SOC | `test_v2h_mode_is_blocked_when_soc_is_too_low` | Blocks release |
| REQ-CLOUD-001 | Device-to-cloud state loss | `test_device_to_cloud_telemetry_round_trip` | Blocks release |
| REQ-REG-001 | Field failures not converted into coverage | `test_field_logs_are_mapped_to_regression_families` | Expands regression suite |
