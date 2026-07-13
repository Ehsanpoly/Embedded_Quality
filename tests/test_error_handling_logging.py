import pytest

from eqv.device import DeviceError
from eqv.exceptions import EqvError
from eqv.pipeline import PipelineStage, ValidationPipeline


def test_device_error_contains_structured_context(device):
    with pytest.raises(DeviceError) as exc_info:
        device.read_measurement("unknown_signal")

    error = exc_info.value.as_dict()
    assert error["type"] == "DeviceError"
    assert error["context"]["operation"] == "read_measurement"
    assert "unknown_signal" in error["message"]


def test_pipeline_preserves_exception_evidence():
    def fail():
        raise EqvError("synthetic bench failure")

    results = ValidationPipeline(run_id="unit-test").run([PipelineStage("failing_stage", fail)])

    assert results[0].passed is False
    assert results[0].error["type"] == "EqvError"
    assert "traceback_tail" in results[0].error
