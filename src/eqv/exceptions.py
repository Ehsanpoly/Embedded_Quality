from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ErrorContext:
    """Structured context attached to validation errors.

    The goal is interview-relevant: when a bench test fails, the error should
    carry enough evidence to reproduce it, not only a Python stack trace.
    """

    service: str | None = None
    operation: str | None = None
    target: str | None = None
    run_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "operation": self.operation,
            "target": self.target,
            "run_id": self.run_id,
            "details": self.details,
        }


class EqvError(RuntimeError):
    """Base exception for the validation framework."""

    def __init__(self, message: str, *, context: ErrorContext | None = None) -> None:
        super().__init__(message)
        self.context = context or ErrorContext()

    def as_dict(self) -> dict[str, Any]:
        return {"type": type(self).__name__, "message": str(self), "context": self.context.as_dict()}


class TransportError(EqvError):
    """Transport layer failed: timeout, serial error, malformed frame, or bench connection issue."""


class DeviceError(EqvError):
    """Device service returned a non-OK status or violated expected behavior."""


class DiagnosticError(EqvError):
    """Diagnostic service returned malformed or incomplete evidence."""


class ArtifactError(EqvError):
    """Artifact creation or persistence failed."""


class PipelineError(EqvError):
    """Validation pipeline orchestration failed."""
