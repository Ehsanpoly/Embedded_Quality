from eqv.quality import QualityMetrics, evaluate_release_gate


def test_release_gate_passes_for_stable_build():
    metrics = QualityMetrics(
        total_tests=250,
        failed_tests=0,
        flaky_tests=1,
        critical_failures=0,
        duration_s=420.0,
    )
    result = evaluate_release_gate(metrics)
    assert result.passed is True
    assert result.reasons == []


def test_release_gate_blocks_flaky_or_critical_build():
    metrics = QualityMetrics(
        total_tests=250,
        failed_tests=2,
        flaky_tests=12,
        critical_failures=1,
        duration_s=420.0,
    )
    result = evaluate_release_gate(metrics)
    assert result.passed is False
    assert any("flakiness" in reason for reason in result.reasons)
    assert any("critical failures" in reason for reason in result.reasons)


def test_release_gate_blocks_memory_release_blockers():
    metrics = QualityMetrics(
        total_tests=20,
        failed_tests=0,
        flaky_tests=0,
        critical_failures=0,
        duration_s=30.0,
        memory_release_blockers=1,
    )
    result = evaluate_release_gate(metrics)
    assert result.passed is False
    assert any("memory release blockers" in reason for reason in result.reasons)
