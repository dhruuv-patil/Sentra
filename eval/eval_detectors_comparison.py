import os
import sys
import json
import time
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.security.detectors import RegexDetector, MLDetector, EnsembleDetector

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval.detectors")

def benchmark_latency(detector, sample_texts: list[str], iterations: int = 100) -> dict:
    """Measures micro-benchmark latencies (p50, p95, p99, mean) for a detector."""
    timings_ms = []
    # Warmup
    for text in sample_texts[:5]:
        detector.predict(text)

    for text in sample_texts:
        for _ in range(iterations):
            t0 = time.perf_counter()
            detector.predict(text)
            timings_ms.append((time.perf_counter() - t0) * 1000)

    arr = np.array(timings_ms)
    return {
        "p50_ms": round(float(np.percentile(arr, 50)), 4),
        "p95_ms": round(float(np.percentile(arr, 95)), 4),
        "p99_ms": round(float(np.percentile(arr, 99)), 4),
        "mean_ms": round(float(np.mean(arr)), 4)
    }

def evaluate_detector(detector, X_test: list[str], y_test: list[int]):
    """Evaluates detector predictions on test set."""
    y_pred = []
    y_scores = []

    for text in X_test:
        res = detector.predict(text)
        y_pred.append(1 if res.is_injection else 0)
        y_scores.append(res.score)

    tp = sum(1 for yt, yp in zip(y_test, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_test, y_pred) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(y_test, y_pred) if yt == 1 and yp == 0)
    tn = sum(1 for yt, yp in zip(y_test, y_pred) if yt == 0 and yp == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    acc = (tp + tn) / len(y_test) if len(y_test) > 0 else 0.0

    return {
        "accuracy": round(acc, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "confusion_matrix": {"TN": tn, "FP": fp, "FN": fn, "TP": tp},
        "scores": y_scores
    }

def run_comparison():
    test_path = os.path.join(BASE_DIR, "data", "deepset_test.parquet")
    if not os.path.exists(test_path):
        from eval.data.download_datasets import main as dl_main
        dl_main()

    # Train model if missing
    model_path = os.path.join(ROOT_DIR, "models", "injection_classifier.joblib")
    if not os.path.exists(model_path):
        from eval.train_ml_detector import train_and_evaluate
        train_and_evaluate()

    df_test = pd.read_parquet(test_path)
    X_test = df_test["text"].astype(str).tolist()
    y_test = df_test["label"].astype(int).tolist()

    regex_det = RegexDetector()
    ml_det = MLDetector(threshold=0.5)
    ensemble_det = EnsembleDetector(threshold=0.5)

    # 1. Performance metrics
    regex_metrics = evaluate_detector(regex_det, X_test, y_test)
    ml_metrics = evaluate_detector(ml_det, X_test, y_test)
    ensemble_metrics = evaluate_detector(ensemble_det, X_test, y_test)

    # 2. Latency metrics (benchmark across sample texts)
    sample_bench_texts = X_test[:10]
    regex_lat = benchmark_latency(regex_det, sample_bench_texts, iterations=50)
    ml_lat = benchmark_latency(ml_det, sample_bench_texts, iterations=50)
    ensemble_lat = benchmark_latency(ensemble_det, sample_bench_texts, iterations=50)

    # 3. Precision-Recall Curve across thresholds for ML & Ensemble
    thresholds = [round(t, 2) for t in np.linspace(0.05, 0.95, 19)]
    pr_curve_data = []

    precisions_ml = []
    recalls_ml = []

    for t in thresholds:
        ml_temp = MLDetector(threshold=t)
        m = evaluate_detector(ml_temp, X_test, y_test)
        precisions_ml.append(m["precision"])
        recalls_ml.append(m["recall"])
        pr_curve_data.append({
            "threshold": t,
            "precision": m["precision"],
            "recall": m["recall"],
            "f1": m["f1_score"]
        })

    # Generate Precision-Recall Curve Plot
    docs_dir = os.path.join(ROOT_DIR, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    plot_path = os.path.join(docs_dir, "precision_recall_curve.png")

    plt.figure(figsize=(8, 6), dpi=150)
    plt.plot(recalls_ml, precisions_ml, marker='o', color='#2563eb', linewidth=2, label="ML (TF-IDF + Logistic Regression)")
    plt.scatter([regex_metrics["recall"]], [regex_metrics["precision"]], color='#dc2626', s=120, zorder=5, label="Regex Guard (Heuristic baseline)")
    plt.scatter([ensemble_metrics["recall"]], [ensemble_metrics["precision"]], color='#16a34a', s=120, zorder=5, marker='^', label="Ensemble Guard (Regex + ML)")
    
    plt.title("Precision-Recall Curve: Prompt Injection Defense", fontsize=14, fontweight='bold', pad=12)
    plt.xlabel("Recall (Detection Rate)", fontsize=12)
    plt.ylabel("Precision (Accuracy of Flagged Injections)", fontsize=12)
    plt.xlim([-0.05, 1.05])
    plt.ylim([-0.05, 1.05])
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(loc="lower left", fontsize=10)
    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close()
    logger.info(f"Precision-Recall curve plot saved to {plot_path}")

    # Results Comparison Table
    comparison_table = [
        {
            "detector": "Regex Guard",
            "type": "Deterministic Heuristic",
            "accuracy": regex_metrics["accuracy"],
            "precision": regex_metrics["precision"],
            "recall": regex_metrics["recall"],
            "f1_score": regex_metrics["f1_score"],
            "fpr": regex_metrics["false_positive_rate"],
            "latency_p50_ms": regex_lat["p50_ms"],
            "latency_p95_ms": regex_lat["p95_ms"],
            "confusion_matrix": regex_metrics["confusion_matrix"]
        },
        {
            "detector": "ML Detector (TF-IDF + LogReg)",
            "type": "Statistical Classifier",
            "accuracy": ml_metrics["accuracy"],
            "precision": ml_metrics["precision"],
            "recall": ml_metrics["recall"],
            "f1_score": ml_metrics["f1_score"],
            "fpr": ml_metrics["false_positive_rate"],
            "latency_p50_ms": ml_lat["p50_ms"],
            "latency_p95_ms": ml_lat["p95_ms"],
            "confusion_matrix": ml_metrics["confusion_matrix"]
        },
        {
            "detector": "Ensemble (Regex + ML)",
            "type": "Hybrid Cascade",
            "accuracy": ensemble_metrics["accuracy"],
            "precision": ensemble_metrics["precision"],
            "recall": ensemble_metrics["recall"],
            "f1_score": ensemble_metrics["f1_score"],
            "fpr": ensemble_metrics["false_positive_rate"],
            "latency_p50_ms": ensemble_lat["p50_ms"],
            "latency_p95_ms": ensemble_lat["p95_ms"],
            "confusion_matrix": ensemble_metrics["confusion_matrix"]
        }
    ]

    results_dir = os.path.join(BASE_DIR, "results")
    os.makedirs(results_dir, exist_ok=True)
    with open(os.path.join(results_dir, "detector_comparison.json"), "w", encoding="utf-8") as f:
        json.dump({
            "test_split_samples": len(y_test),
            "comparison": comparison_table,
            "pr_curve_data": pr_curve_data
        }, f, indent=2)

    logger.info("=" * 85)
    logger.info("DETECTOR COMPARISON BENCHMARK (Held-Out Test Set: deepset/prompt-injections, n=116)")
    logger.info("=" * 85)
    logger.info(f"{'Detector':<26} | {'Precision':<9} | {'Recall':<9} | {'F1':<9} | {'FPR':<9} | {'p50 (ms)':<9} | {'p95 (ms)':<9}")
    logger.info("-" * 85)
    for row in comparison_table:
        logger.info(f"{row['detector']:<26} | {row['precision']:<9.4f} | {row['recall']:<9.4f} | {row['f1_score']:<9.4f} | {row['fpr']:<9.4f} | {row['latency_p50_ms']:<9.4f} | {row['latency_p95_ms']:<9.4f}")
    logger.info("=" * 85)

    return comparison_table

if __name__ == "__main__":
    run_comparison()
