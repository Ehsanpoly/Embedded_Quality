from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pytest

from eqv.artifacts import append_jsonl
from eqv.cloud import FakeCloudClient
from eqv.device import HomeEnergyStationClient
from eqv.memory_diagnostics import MemoryDiagnosticClient
from eqv.transports import FakeHilTransport


@dataclass(frozen=True)
class EnergyScenario:
    """Input profile used by a parametrized fixture.

    A single test can consume this fixture and pytest will run that test once per
    profile. In a hardware lab, these scenarios could represent different bench
    presets: sunny PV production, high EV load, low-SOC safety state, or grid
    export/import conditions.
    """

    name: str
    pv_power_kw: float
    ev_power_kw: float
    grid_power_kw: float
    battery_soc_percent: float
    expected_mode: str = "EV_CHARGE"


@dataclass(frozen=True)
class MemoryFaultCase:
    """Data object for parameterized memory/NVM fault regression examples."""

    name: str
    injected_faults: set[str] = field(default_factory=set)
    diagnostic: str = "nvm_crc"
    should_pass: bool = True
    expected_status: str = "PASS"
    expected_severity: str = "release_blocker"


@pytest.fixture(scope="session")
def validation_session_metadata() -> dict[str, str]:
    """Session-scoped metadata created once for the whole pytest run.

    This demonstrates fixture lifecycle at session scope: setup happens once
    before the first test that needs it, and the object is reused by all tests.
    """

    return {
        "suite": "embedded-quality-validation-showcase",
        "runner": "pytest",
        "fixture_scope": "session",
    }


@pytest.fixture
def artifacts_dir() -> Path:
    path = Path("artifacts")
    path.mkdir(exist_ok=True)
    return path


@pytest.fixture(autouse=True)
def record_fixture_lifecycle(request: pytest.FixtureRequest, artifacts_dir: Path) -> None:
    """Autouse fixture: records setup/teardown for every test automatically.

    Tests do not need to list this fixture in their function signature. This is
    useful for bench hygiene, because every test gets a lifecycle record even if
    the test author forgets to request it explicitly.
    """

    path = artifacts_dir / "fixture_lifecycle.jsonl"
    started_at = time.perf_counter()
    append_jsonl(
        path,
        {
            "event": "setup",
            "nodeid": request.node.nodeid,
            "fixture": "record_fixture_lifecycle",
            "scope": "function",
        },
    )
    yield
    append_jsonl(
        path,
        {
            "event": "teardown",
            "nodeid": request.node.nodeid,
            "fixture": "record_fixture_lifecycle",
            "scope": "function",
            "duration_s": round(time.perf_counter() - started_at, 6),
        },
    )


@pytest.fixture
def hil_transport() -> FakeHilTransport:
    return FakeHilTransport()


@pytest.fixture
def device(hil_transport: FakeHilTransport) -> HomeEnergyStationClient:
    return HomeEnergyStationClient(hil_transport)


@pytest.fixture
def memory_client(device: HomeEnergyStationClient) -> MemoryDiagnosticClient:
    return MemoryDiagnosticClient(device)


@pytest.fixture
def cloud() -> FakeCloudClient:
    return FakeCloudClient()


@pytest.fixture(
    params=[
        EnergyScenario(
            name="sunny_self_consumption",
            pv_power_kw=5.8,
            ev_power_kw=0.0,
            grid_power_kw=-2.2,
            battery_soc_percent=76.0,
        ),
        EnergyScenario(
            name="evening_ev_charge",
            pv_power_kw=0.4,
            ev_power_kw=7.2,
            grid_power_kw=6.9,
            battery_soc_percent=61.0,
        ),
        EnergyScenario(
            name="backup_ready_high_soc",
            pv_power_kw=1.2,
            ev_power_kw=0.0,
            grid_power_kw=0.2,
            battery_soc_percent=92.0,
        ),
    ],
    ids=lambda scenario: scenario.name,
)
def energy_scenario(request: pytest.FixtureRequest) -> EnergyScenario:
    """Parametrized fixture: one test runs once per energy profile."""

    return request.param


@pytest.fixture(
    params=[
        MemoryFaultCase(name="healthy_nvm", should_pass=True, expected_status="PASS"),
        MemoryFaultCase(
            name="crc_mismatch_release_blocker",
            injected_faults={"nvm_crc_mismatch"},
            should_pass=False,
            expected_status="FAIL",
        ),
        MemoryFaultCase(
            name="scratch_stuck_bit_release_blocker",
            injected_faults={"nvm_scratch_stuck_bit"},
            diagnostic="scratch_write_readback",
            should_pass=False,
            expected_status="FAIL",
        ),
    ],
    ids=lambda case: case.name,
)
def memory_fault_case(request: pytest.FixtureRequest) -> MemoryFaultCase:
    """Parametrized fixture for memory/NVM regression cases."""

    return request.param


@pytest.fixture
def device_factory() -> Callable[..., tuple[FakeHilTransport, HomeEnergyStationClient]]:
    """Factory fixture: create devices dynamically with per-test arguments.

    Unlike a simple fixture that always returns the same shape, this returns a
    function. Tests can call that function with custom telemetry, SOC, cloud,
    memory, or fault settings. This pattern is useful when many tests need a
    slightly different bench state without duplicating setup code.
    """

    def _factory(**transport_overrides: Any) -> tuple[FakeHilTransport, HomeEnergyStationClient]:
        faults = set(transport_overrides.pop("injected_faults", set()))
        transport = FakeHilTransport(**transport_overrides)
        transport.injected_faults.update(faults)
        return transport, HomeEnergyStationClient(transport)

    return _factory


@pytest.fixture
def memory_client_factory(
    device_factory: Callable[..., tuple[FakeHilTransport, HomeEnergyStationClient]],
) -> Callable[..., tuple[FakeHilTransport, MemoryDiagnosticClient]]:
    """Factory fixture for building memory diagnostic clients on demand."""

    def _factory(**transport_overrides: Any) -> tuple[FakeHilTransport, MemoryDiagnosticClient]:
        transport, dynamic_device = device_factory(**transport_overrides)
        return transport, MemoryDiagnosticClient(dynamic_device)

    return _factory


def pytest_sessionstart(session):
    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)
    for name in [
        "test_events.jsonl",
        "junit.xml",
        "quality_gate.json",
        "triage_report.md",
        "fixture_lifecycle.jsonl",
    ]:
        (artifacts / name).unlink(missing_ok=True)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return
    path = Path("artifacts/test_events.jsonl")
    path.parent.mkdir(exist_ok=True)
    event = {
        "nodeid": report.nodeid,
        "outcome": report.outcome,
        "duration_s": round(report.duration, 6),
        "markers": [m.name for m in item.iter_markers()],
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
