from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityMetrics:
    total_tests: int
    failed_tests: int
    flaky_tests: int
    critical_failures: int
    duration_s: float

    @property
    def pass_rate(self) -> float:
        if self.total_tests <= 0:
            return 0.0
        return (self.total_tests - self.failed_tests) / self.total_tests

    @property
    def flakiness_rate(self) -> float:
        if self.total_tests <= 0:
            return 1.0
        return self.flaky_tests / self.total_tests


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reasons: list[str]


def evaluate_release_gate(
    metrics: QualityMetrics,
    *,
    min_pass_rate: float = 0.98,
    max_flakiness_rate: float = 0.02,
    max_duration_s: float = 600.0,
) -> GateResult:
    reasons: list[str] = []
    if metrics.pass_rate < min_pass_rate:
        reasons.append(f"pass rate {metrics.pass_rate:.2%} below {min_pass_rate:.2%}")
    if metrics.flakiness_rate > max_flakiness_rate:
        reasons.append(f"flakiness rate {metrics.flakiness_rate:.2%} above {max_flakiness_rate:.2%}")
    if metrics.critical_failures > 0:
        reasons.append(f"critical failures present: {metrics.critical_failures}")
    if metrics.duration_s > max_duration_s:
        reasons.append(f"duration {metrics.duration_s:.1f}s above {max_duration_s:.1f}s")
    return GateResult(passed=not reasons, reasons=reasons)
