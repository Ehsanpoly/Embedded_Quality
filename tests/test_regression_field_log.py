from pathlib import Path

import pytest

from eqv.telemetry import classify_event, load_field_events, regression_ids


@pytest.mark.regression
def test_field_logs_are_mapped_to_regression_families():
    events = load_field_events(Path("sample_data/field_logs.jsonl"))
    classifications = {event.case_id: classify_event(event) for event in events}
    assert classifications["FLD-001"] == "device_to_cloud_regression"
    assert classifications["FLD-002"] == "power_path_safety_regression"
    assert classifications["FLD-003"] == "ota_update_regression"
    assert "REG-CLOUD-HEARTBEAT" in regression_ids(events)
