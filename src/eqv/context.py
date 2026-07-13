from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .artifacts import utc_now_iso


@dataclass
class ValidationContext:
    """Run-level context passed through CLI, pipeline, checks, and artifacts."""

    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    target: str = "sim"
    artifacts_dir: Path = Path("artifacts")
    device_id: str = "ARA-SIM-0001"
    firmware_version: str = "sim-fw-0.1.0"
    os_image: str = "sim-linux-qa"
    bench_type: str = "deterministic_simulated_hil"
    started_at_utc: str = field(default_factory=utc_now_iso)

    def path(self, filename: str) -> Path:
        return self.artifacts_dir / filename

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "target": self.target,
            "artifacts_dir": str(self.artifacts_dir),
            "device_id": self.device_id,
            "firmware_version": self.firmware_version,
            "os_image": self.os_image,
            "bench_type": self.bench_type,
            "started_at_utc": self.started_at_utc,
        }
