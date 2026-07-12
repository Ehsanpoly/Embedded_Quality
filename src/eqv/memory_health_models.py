from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MemoryDiagnosticReport:
    """Structured report returned by firmware memory diagnostic services.

    In real hardware this payload would be produced by the firmware or bootloader
    diagnostic service. The Python validation framework treats it as release
    evidence: a failed NVM CRC or protected-region check should block a release,
    while an informational wear counter can be tracked as a trend.
    """

    test_name: str
    status: str
    severity: str
    duration_ms: float
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status.upper() == "PASS"

    @property
    def is_release_blocker(self) -> bool:
        return (not self.passed) and self.severity == "release_blocker"

    def as_dict(self) -> dict[str, Any]:
        return {
            "test_name": self.test_name,
            "status": self.status,
            "severity": self.severity,
            "duration_ms": self.duration_ms,
            "details": self.details,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "MemoryDiagnosticReport":
        return cls(
            test_name=str(payload["test_name"]),
            status=str(payload["status"]),
            severity=str(payload.get("severity", "info")),
            duration_ms=float(payload.get("duration_ms", 0.0)),
            details=dict(payload.get("details", {})),
        )
