import json
import logging
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pandas as pd

from core.security.input_guards import InputGuards

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval.injection")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

def evaluate_predictions(y_true: list[int], y_pred: list[int]):
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0.0

    return {
        "total_samples": len(y_true),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "confusion_matrix": {
            "TN": tn,
            "FP": fp,
            "FN": fn,
            "TP": tp
        }
    }

def run_evaluation():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    deepset_test_path = os.path.join(DATA_DIR, "deepset_test.parquet")
    jbb_harmful_path = os.path.join(DATA_DIR, "jbb_harmful.csv")
    jbb_benign_path = os.path.join(DATA_DIR, "jbb_benign.csv")

    raw_results = []

    # 1. Evaluate on deepset/prompt-injections test split
    if not os.path.exists(deepset_test_path):
        from eval.data.download_datasets import main as dl_main
        dl_main()

    df_deepset = pd.read_parquet(deepset_test_path)
    logger.info(f"Loaded deepset/prompt-injections test split: {len(df_deepset)} examples")

    y_true_deepset = []
    y_pred_deepset = []

    for idx, row in df_deepset.iterrows():
        text = str(row["text"])
        label = int(row["label"]) # 1 = injection, 0 = benign
        pred = 1 if InputGuards.detect_prompt_injection(text) else 0

        y_true_deepset.append(label)
        y_pred_deepset.append(pred)

        raw_results.append({
            "dataset": "deepset/prompt-injections-test",
            "index": idx,
            "text": text[:200] + ("..." if len(text) > 200 else ""),
            "ground_truth": label,
            "predicted": pred,
            "correct": label == pred
        })

    deepset_metrics = evaluate_predictions(y_true_deepset, y_pred_deepset)

    # 2. Evaluate on JailbreakBench (harmful goals vs benign goals)
    jbb_metrics = None
    if os.path.exists(jbb_harmful_path) and os.path.exists(jbb_benign_path):
        df_jbb_harm = pd.read_csv(jbb_harmful_path)
        df_jbb_benign = pd.read_csv(jbb_benign_path)

        y_true_jbb = []
        y_pred_jbb = []

        # JBB Harmful behaviors (label = 1)
        for idx, row in df_jbb_harm.iterrows():
            text = str(row["Goal"])
            pred = 1 if InputGuards.detect_prompt_injection(text) else 0
            y_true_jbb.append(1)
            y_pred_jbb.append(pred)
            raw_results.append({
                "dataset": "JailbreakBench-Harmful",
                "index": idx,
                "text": text[:200],
                "ground_truth": 1,
                "predicted": pred,
                "correct": pred == 1
            })

        # JBB Benign behaviors (label = 0)
        for idx, row in df_jbb_benign.iterrows():
            text = str(row["Goal"])
            pred = 1 if InputGuards.detect_prompt_injection(text) else 0
            y_true_jbb.append(0)
            y_pred_jbb.append(pred)
            raw_results.append({
                "dataset": "JailbreakBench-Benign",
                "index": idx,
                "text": text[:200],
                "ground_truth": 0,
                "predicted": pred,
                "correct": pred == 0
            })

        jbb_metrics = evaluate_predictions(y_true_jbb, y_pred_jbb)

    # Combined metrics
    all_true = y_true_deepset + (y_true_jbb if jbb_metrics else [])
    all_pred = y_pred_deepset + (y_pred_jbb if jbb_metrics else [])
    combined_metrics = evaluate_predictions(all_true, all_pred)

    output_payload = {
        "deepset_test_metrics": deepset_metrics,
        "jailbreakbench_metrics": jbb_metrics,
        "combined_benchmark_metrics": combined_metrics
    }

    # Save raw per-example results
    raw_path = os.path.join(RESULTS_DIR, "prompt_injection_raw.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_results, f, indent=2)

    summary_path = os.path.join(RESULTS_DIR, "prompt_injection_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    logger.info("=" * 60)
    logger.info("PROMPT INJECTION EVALUATION SUMMARY (Current Regex Guard)")
    logger.info("=" * 60)
    logger.info(f"Dataset: deepset/prompt-injections (test split, n={deepset_metrics['total_samples']})")
    logger.info(f"  Precision: {deepset_metrics['precision']:.4f}")
    logger.info(f"  Recall:    {deepset_metrics['recall']:.4f}")
    logger.info(f"  F1-Score:  {deepset_metrics['f1_score']:.4f}")
    logger.info(f"  FPR:       {deepset_metrics['false_positive_rate']:.4f}")
    logger.info(f"  Confusion: TP={deepset_metrics['tp']}, FP={deepset_metrics['fp']}, TN={deepset_metrics['tn']}, FN={deepset_metrics['fn']}")
    if jbb_metrics:
        logger.info(f"Dataset: JailbreakBench JBB-Behaviors (n={jbb_metrics['total_samples']})")
        logger.info(f"  Precision: {jbb_metrics['precision']:.4f}")
        logger.info(f"  Recall:    {jbb_metrics['recall']:.4f}")
        logger.info(f"  F1-Score:  {jbb_metrics['f1_score']:.4f}")
        logger.info(f"  FPR:       {jbb_metrics['false_positive_rate']:.4f}")
    logger.info(f"Combined Benchmark (n={combined_metrics['total_samples']})")
    logger.info(f"  Precision: {combined_metrics['precision']:.4f}")
    logger.info(f"  Recall:    {combined_metrics['recall']:.4f}")
    logger.info(f"  F1-Score:  {combined_metrics['f1_score']:.4f}")
    logger.info(f"  FPR:       {combined_metrics['false_positive_rate']:.4f}")
    logger.info("=" * 60)

    return output_payload

if __name__ == "__main__":
    run_evaluation()
