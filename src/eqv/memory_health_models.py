from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .exceptions import DiagnosticError, ErrorContext


@dataclass(frozen=True)
class MemoryDiagnosticReport:
    """Structured report returned by firmware memory diagnostic services.

    In real hardware this payload would be produced by firmware or bootloader.
    The Python validation framework treats it as release evidence: a failed NVM
    CRC or protected-region check should block a release, while wear counters can
    be tracked as a trend.
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
        required = ["test_name", "status"]
        missing = [key for key in required if key not in payload]
        if missing:
            raise DiagnosticError(
                "memory diagnostic report missing required fields",
                context=ErrorContext(operation="parse_memory_report", details={"missing": missing, "payload": payload}),
            )
        status = str(payload["status"]).upper()
        if status not in {"PASS", "FAIL", "WARN"}:
            raise DiagnosticError(
                "memory diagnostic report returned unknown status",
                context=ErrorContext(operation="parse_memory_report", details={"status": status}),
            )
        return cls(
            test_name=str(payload["test_name"]),
            status=status,
            severity=str(payload.get("severity", "info")),
            duration_ms=float(payload.get("duration_ms", 0.0)),
            details=dict(payload.get("details", {})),
        )
