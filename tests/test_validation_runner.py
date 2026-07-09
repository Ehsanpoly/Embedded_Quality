from pathlib import Path

from eqv.validation_runner import run_embedded_quality_workflow


def test_validation_runner_generates_release_evidence(tmp_path):
    output = tmp_path / "validation_report.json"
    report = run_embedded_quality_workflow(output=output)
    assert output.exists()
    assert report.quality_gate["passed"] is True
    assert {check.name for check in report.checks} >= {
        "device_ping",
        "power_measurements",
        "v2h_low_soc_safety_interlock",
        "device_to_cloud_telemetry",
    }
    assert len(report.device_trace) >= 5


def test_validation_runner_keeps_v2h_safety_as_critical_check(tmp_path):
    output = Path(tmp_path) / "validation_report.json"
    report = run_embedded_quality_workflow(low_soc_for_safety_check=10.0, output=output)
    safety = next(check for check in report.checks if check.name == "v2h_low_soc_safety_interlock")
    assert safety.passed is True
    assert safety.critical is True
    assert safety.details["blocked"] is True
