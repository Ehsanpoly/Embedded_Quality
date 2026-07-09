from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class FieldEvent:
    case_id: str
    severity: str
    subsystem: str
    code: str
    message: str
    expected_regression: str


def load_field_events(path: str | Path) -> list[FieldEvent]:
    events: list[FieldEvent] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            events.append(FieldEvent(**item))
    return events


def classify_event(event: FieldEvent) -> str:
    code = event.code.lower()
    if "cloud" in code or event.subsystem == "cloud":
        return "device_to_cloud_regression"
    if "ota" in code or event.subsystem == "ota":
        return "ota_update_regression"
    if "dc_link" in code or "power" in event.subsystem:
        return "power_path_safety_regression"
    if event.subsystem in {"protocol", "comms", "serial"}:
        return "protocol_regression"
    return "general_regression"


def regression_ids(events: Iterable[FieldEvent]) -> set[str]:
    return {e.expected_regression for e in events}
