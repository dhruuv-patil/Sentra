"""
Automated unit test wrapper around the evaluation smoke test quality gate.
Guarantees that the ML injection classifier meets F1 >= 0.75 and sub-10ms latency.
"""

from eval.eval_smoke_test import run_smoke_test


def test_ml_detector_eval_quality_gate():
    """Asserts that ML prompt injection detector passes the CI quality gate on held-out test data."""
    passed = run_smoke_test(threshold=0.50)
    assert passed is True, "ML injection detector failed to meet CI performance thresholds (F1 >= 0.75)"
