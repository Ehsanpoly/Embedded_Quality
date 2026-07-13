from __future__ import annotations

import json
from pathlib import Path

import pytest

from eqv.device import DeviceError


@pytest.mark.hil
def test_parametrized_energy_scenarios_run_same_test_against_multiple_profiles(device_factory, energy_scenario):
    """The same validation logic is executed once per EnergyScenario parameter."""

    _, device = device_factory(
        pv_power_kw=energy_scenario.pv_power_kw,
        ev_power_kw=energy_scenario.ev_power_kw,
        grid_power_kw=energy_scenario.grid_power_kw,
        battery_soc_percent=energy_scenario.battery_soc_percent,
    )

    assert device.ping() is True
    assert round(device.read_measurement("pv_power_kw"), 2) == round(energy_scenario.pv_power_kw, 2)
    assert round(device.read_measurement("battery_soc_percent"), 2) == round(
        energy_scenario.battery_soc_percent, 2
    )
    assert device.set_mode(energy_scenario.expected_mode) == energy_scenario.expected_mode


@pytest.mark.memory
@pytest.mark.release_gate
def test_parametrized_memory_fault_cases_are_release_gate_ready(memory_client_factory, memory_fault_case):
    """One test covers healthy and faulty NVM cases through a parametrized fixture."""

    _, memory = memory_client_factory(injected_faults=memory_fault_case.injected_faults)

    if memory_fault_case.diagnostic == "nvm_crc":
        report = memory.verify_nvm_crc()
    elif memory_fault_case.diagnostic == "scratch_write_readback":
        report = memory.scratch_write_readback(key="fx", value=42)
    else:  # defensive check keeps future fixture data honest
        raise AssertionError(f"unknown diagnostic {memory_fault_case.diagnostic}")

    assert report.passed is memory_fault_case.should_pass
    assert report.status == memory_fault_case.expected_status
    assert report.severity == memory_fault_case.expected_severity


@pytest.mark.hil
def test_factory_fixture_creates_dynamic_low_soc_safety_bench(device_factory):
    """Factory fixtures let a test construct the exact bench state it needs."""

    transport, device = device_factory(battery_soc_percent=12.5, pv_power_kw=0.1, ev_power_kw=0.0)

    assert round(device.read_measurement("battery_soc_percent"), 1) == 12.5
    with pytest.raises(DeviceError, match="safety interlock"):
        device.set_mode("V2H_BACKUP")
    assert transport.trace[-1]["service_name"] == "SET_MODE"


@pytest.mark.memory
def test_factory_fixture_creates_dynamic_schema_mismatch(memory_client_factory):
    """Dynamic arguments can model firmware/NVM migration risks."""

    _, memory = memory_client_factory(nvm_schema_version=2, expected_nvm_schema_version=3)

    report = memory.validate_nvm_schema()

    assert report.passed is False
    assert report.details["migration_required"] is True
    assert report.details["actual_schema_version"] == 2


def test_autouse_fixture_records_lifecycle_without_being_requested(request):
    """The lifecycle fixture runs automatically even though this test does not request it by name."""

    path = Path("artifacts/fixture_lifecycle.jsonl")
    assert path.exists()
    setup_events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert any(
        event["event"] == "setup" and event["nodeid"] == request.node.nodeid
        for event in setup_events
    )


def test_session_fixture_metadata_is_reused(validation_session_metadata):
    """Session-scoped fixtures provide run-level data without rebuilding it per test."""

    assert validation_session_metadata["suite"] == "embedded-quality-validation-showcase"
    assert validation_session_metadata["fixture_scope"] == "session"
