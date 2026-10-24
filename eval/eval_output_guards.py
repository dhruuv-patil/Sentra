import json
import logging
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.security.output_guards import OutputGuards

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval.output")

def run_evaluation():
    test_set_path = os.path.join(BASE_DIR, "data", "output_leak_test_set.json")
    with open(test_set_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    raw_results = []
    y_true = []
    y_pred = []

    for item in test_data:
        text = item["text"]
        is_leak = item["is_leak"]
        detected_category = OutputGuards.detect_harmful_content(text)
        pred_leak = detected_category == "System Leakage & Confidentiality"

        y_true.append(1 if is_leak else 0)
        y_pred.append(1 if pred_leak else 0)

        raw_results.append({
            "id": item["id"],
            "text": text,
            "ground_truth_leak": is_leak,
            "detected_category": detected_category,
            "predicted_leak": pred_leak,
            "correct": is_leak == pred_leak,
            "note": item.get("note", "")
        })

    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    metrics = {
        "total_samples": len(test_data),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "false_positive_rate": round(fpr, 4)
    }

    results_dir = os.path.join(BASE_DIR, "results")
    os.makedirs(results_dir, exist_ok=True)
    with open(os.path.join(results_dir, "output_guards_raw.json"), "w", encoding="utf-8") as f:
        json.dump(raw_results, f, indent=2)

    with open(os.path.join(results_dir, "output_guards_summary.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    logger.info("=" * 60)
    logger.info("OUTPUT GUARD: SYSTEM PROMPT LEAKAGE EVALUATION")
    logger.info("=" * 60)
    logger.info(f"Total Test Cases: {metrics['total_samples']}")
    logger.info(f"  Precision: {metrics['precision']:.4f}")
    logger.info(f"  Recall:    {metrics['recall']:.4f}")
    logger.info(f"  F1-Score:  {metrics['f1_score']:.4f}")
    logger.info(f"  FPR:       {metrics['false_positive_rate']:.4f}")
    logger.info(f"  Confusion: TP={tp}, FP={fp}, TN={tn}, FN={fn}")
    logger.info("=" * 60)

    return metrics

if __name__ == "__main__":
    run_evaluation()
