from __future__ import annotations

import logging
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

from .exceptions import EqvError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    critical: bool = True
    duration_s: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None


@dataclass(frozen=True)
class PipelineStage:
    """A named validation action with severity.

    This file is the connective tissue between repo sections: device client,
    memory diagnostics, cloud test double, fast state store, artifacts, and the
    release gate are executed through the same standard stage interface.
    """

    name: str
    action: Callable[[], dict[str, Any] | None]
    critical: bool = True


class ValidationPipeline:
    def __init__(self, *, run_id: str) -> None:
        self.run_id = run_id
        self.results: list[CheckResult] = []

    def run(self, stages: list[PipelineStage]) -> list[CheckResult]:
        for stage in stages:
            self.results.append(self._run_stage(stage))
        return self.results

    def _run_stage(self, stage: PipelineStage) -> CheckResult:
        log.info("run_id=%s stage=%s status=START critical=%s", self.run_id, stage.name, stage.critical)
        start = time.perf_counter()
        try:
            details = stage.action() or {}
            duration = time.perf_counter() - start
            details = {**details, "duration_s": round(duration, 6)}
            log.info("run_id=%s stage=%s status=PASS duration_s=%.4f", self.run_id, stage.name, duration)
            return CheckResult(stage.name, True, stage.critical, round(duration, 6), details)
        except Exception as exc:  # noqa: BLE001 - runner must preserve evidence instead of crashing early
            duration = time.perf_counter() - start
            if isinstance(exc, EqvError):
                error = exc.as_dict()
            else:
                error = {"type": type(exc).__name__, "message": str(exc), "context": {}}
            error["traceback_tail"] = traceback.format_exc().splitlines()[-8:]
            log.exception("run_id=%s stage=%s status=FAIL duration_s=%.4f", self.run_id, stage.name, duration)
            return CheckResult(stage.name, False, stage.critical, round(duration, 6), {}, error)
