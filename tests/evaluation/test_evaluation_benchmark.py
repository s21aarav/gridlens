"""Evaluation test asserting that GridLens achieves target metrics across the golden dataset."""
import pytest
from services.evaluation.evaluator import SystemEvaluator


@pytest.mark.asyncio
async def test_golden_dataset_benchmark_run():
    report = await SystemEvaluator.evaluate_full_gridlens()
    metrics = report.metrics

    print(f"\n============================================================")
    print(f"EVALUATION BENCHMARK RESULTS ({report.system_name}):")
    print(f"Total Test Cases: {metrics.total_test_cases}")
    print(f"Overall Accuracy: {metrics.accuracy_percent}%")
    print(f"Diagnosis Accuracy: {metrics.diagnosis_accuracy_percent}%")
    print(f"Tool Selection Accuracy: {metrics.tool_selection_accuracy_percent}%")
    print(f"Contradiction Detection: {metrics.contradiction_detection_percent}%")
    print(f"Abstention Accuracy: {metrics.abstention_accuracy_percent}%")
    print(f"Unsupported Claim Rate: {metrics.unsupported_claim_rate_percent}%")
    print(f"Avg Latency: {metrics.avg_latency_ms} ms")
    print(f"============================================================\n")

    assert metrics.diagnosis_accuracy_percent >= 90.0
    assert metrics.tool_selection_accuracy_percent >= 90.0
    assert metrics.abstention_accuracy_percent == 100.0
    assert metrics.contradiction_detection_percent == 100.0
    assert metrics.unsupported_claim_rate_percent == 0.0
