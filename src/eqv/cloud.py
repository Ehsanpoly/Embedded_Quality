from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeCloudClient:
    """Cloud-edge test double for validating device-to-cloud workflows."""

    messages: list[dict[str, Any]] = field(default_factory=list)

    def publish_telemetry(self, device_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        envelope = {
            "device_id": device_id,
            "timestamp_s": int(time.time()),
            "payload": payload,
        }
        # Round trip through JSON to catch non-serializable data early.
        self.messages.append(json.loads(json.dumps(envelope)))
        return {"accepted": True, "message_index": len(self.messages) - 1}

    def last_payload(self) -> dict[str, Any]:
        if not self.messages:
            raise RuntimeError("no cloud messages published")
        return self.messages[-1]["payload"]
