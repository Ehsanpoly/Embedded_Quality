# Traceability Matrix

| Requirement / Risk | Automated evidence |
|---|---|
| Device is reachable | `device_ping` check, `tests/test_device_workflows.py` |
| Protocol frames are valid | `tests/test_protocol_frame.py`, CRC rejection tests |
| Power telemetry is sane | `power_measurements`, telemetry stream artifact |
| EV charging mode can be commanded | `ev_charge_mode` check |
| V2H/V2G unsafe transition is blocked | `v2h_low_soc_safety_interlock`, release-gate critical check |
| RAM quick diagnostic is healthy | `ram_quick_check`, `tests/test_memory_diagnostics.py` |
| NVM/EEPROM configuration is valid | `nvm_crc_integrity`, `nvm_schema_validate` |
| NVM scratch page can write/readback | `nvm_scratch_write_readback` |
| Factory identity/calibration region is protected | `nvm_factory_region_locked` |
| NVM endurance is observable | `nvm_wear_level_stats` |
| Slow scans can be skipped when state is unchanged | `fast_state_store_cached_nvm_crc`, `fast_gate.json` |
| Cloud telemetry is accepted | `device_to_cloud_telemetry`, cloud records in validation report |
| Field failures become regressions | `sample_data/field_logs.jsonl`, `tests/test_regression_field_log.py` |
| CI can block unsafe releases | `scripts/run_quality_gate.py`, `artifacts/quality_gate.json` |
| Failures are diagnosable | `device_trace`, `junit.xml`, `test_events.jsonl`, `triage_report.md` |
