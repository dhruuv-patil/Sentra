#!/usr/bin/env python3
"""
Fast Evaluation Smoke Test for CI / CD Pipelines.
Loads the held-out test split (eval/data/deepset_test.parquet), evaluates the
trained ML prompt-injection detector, and asserts that detection F1 score meets or
exceeds the required quality gate (F1 >= 0.75) with sub-10ms p50 latency.

Returns exit code 0 on success, exit code 1 if metrics drop below threshold.
"""

import os
import sys
import time

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.security.detectors import MLDetector

MIN_F1_THRESHOLD = 0.75
MIN_PRECISION_THRESHOLD = 0.80
MAX_P50_LATENCY_MS = 10.0


def run_smoke_test(test_path: str = None, threshold: float = 0.50) -> bool:
    if test_path is None:
        test_path = os.path.join(BASE_DIR, "data", "deepset_test.parquet")

    if not os.path.exists(test_path):
        print(f"❌ Test dataset not found at: {test_path}")
        print("Run `python3 eval/data/download_datasets.py` first.")
        return False

    df = pd.read_parquet(test_path)
    X = df["text"].tolist()
    y_true = df["label"].tolist()

    detector = MLDetector(threshold=threshold)
    if not detector.is_available():
        print("❌ ML Detector weights not found. Run `python3 eval/train_ml_detector.py`.")
        return False

    # Inference loop with micro-timings
    latencies = []
    y_pred = []
    for text in X:
        t0 = time.perf_counter()
        res = detector.predict(text)
        latencies.append((time.perf_counter() - t0) * 1000)
        y_pred.append(1 if res.is_injection else 0)

    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    p50_latency = float(np.percentile(latencies, 50))

    print("=" * 60)
    print("🛡️  EVALUATION SMOKE TEST: ML INJECTION DETECTOR QUALITY GATE")
    print("=" * 60)
    print(f"Dataset:            {os.path.basename(test_path)} (n={len(X)})")
    print(f"Decision Threshold: {threshold:.2f}")
    print(f"Precision:          {precision:.4f} (Required: >= {MIN_PRECISION_THRESHOLD})")
    print(f"Recall:             {recall:.4f}")
    print(f"F1 Score:           {f1:.4f} (Required: >= {MIN_F1_THRESHOLD})")
    print(f"False Positive Rate:{fpr:.4f}")
    print(f"p50 Latency:        {p50_latency:.3f} ms (Required: < {MAX_P50_LATENCY_MS} ms)")
    print(f"Confusion Matrix:   TP={tp}, FP={fp}, FN={fn}, TN={tn}")
    print("=" * 60)

    passed = True
    if f1 < MIN_F1_THRESHOLD:
        print(f"❌ FAIL: F1 score {f1:.4f} dropped below threshold {MIN_F1_THRESHOLD}!")
        passed = False
    if precision < MIN_PRECISION_THRESHOLD:
        print(f"❌ FAIL: Precision {precision:.4f} dropped below threshold {MIN_PRECISION_THRESHOLD}!")
        passed = False
    if p50_latency > MAX_P50_LATENCY_MS:
        print(f"❌ FAIL: p50 latency {p50_latency:.3f}ms exceeded limit {MAX_P50_LATENCY_MS}ms!")
        passed = False

    if passed:
        print("✅ QUALITY GATE PASSED: Detector satisfies production performance invariants.")
    return passed


if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)
