import json
from pathlib import Path

import pytest

from eqv.cloud import FakeCloudClient
from eqv.device import HomeEnergyStationClient
from eqv.transports import FakeHilTransport


@pytest.fixture
def artifacts_dir() -> Path:
    path = Path("artifacts")
    path.mkdir(exist_ok=True)
    return path


@pytest.fixture
def hil_transport() -> FakeHilTransport:
    return FakeHilTransport()


@pytest.fixture
def device(hil_transport: FakeHilTransport) -> HomeEnergyStationClient:
    return HomeEnergyStationClient(hil_transport)


@pytest.fixture
def cloud() -> FakeCloudClient:
    return FakeCloudClient()


def pytest_sessionstart(session):
    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)
    for name in ["test_events.jsonl", "junit.xml", "quality_gate.json", "triage_report.md"]:
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
