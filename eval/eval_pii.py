import os
import sys
import json
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.security.input_guards import InputGuards

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval.pii")

# Try importing Presidio recognizers for comparative evaluation
PRESIDIO_AVAILABLE = False
try:
    from presidio_analyzer.predefined_recognizers import (
        EmailRecognizer,
        PhoneRecognizer,
        CreditCardRecognizer,
        UsSsnRecognizer
    )
    presidio_email = EmailRecognizer()
    presidio_phone = PhoneRecognizer()
    presidio_cc = CreditCardRecognizer()
    presidio_ssn = UsSsnRecognizer()
    PRESIDIO_AVAILABLE = True
except Exception as e:
    logger.warning(f"Presidio recognizers not available for comparison: {e}")

def run_presidio_detection(text: str) -> list[str]:
    """Runs Presidio predefined pattern recognizers on input text."""
    if not PRESIDIO_AVAILABLE:
        return []
    detected = []
    try:
        if presidio_email.analyze(text, entities=["EMAIL_ADDRESS"]):
            detected.append("Email")
        if presidio_phone.analyze(text, entities=["PHONE_NUMBER"]):
            detected.append("Phone Number")
        if presidio_cc.analyze(text, entities=["CREDIT_CARD"]):
            detected.append("Credit Card")
        if presidio_ssn.analyze(text, entities=["US_SSN"]):
            detected.append("SSN")
    except Exception:
        pass
    return detected

def calculate_entity_metrics(y_true_list: list[list[str]], y_pred_list: list[list[str]], entity: str):
    tp = sum(1 for yt, yp in zip(y_true_list, y_pred_list) if entity in yt and entity in yp)
    fp = sum(1 for yt, yp in zip(y_true_list, y_pred_list) if entity not in yt and entity in yp)
    fn = sum(1 for yt, yp in zip(y_true_list, y_pred_list) if entity in yt and entity not in yp)
    tn = sum(1 for yt, yp in zip(y_true_list, y_pred_list) if entity not in yt and entity not in yp)

    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4)
    }

def run_evaluation():
    test_set_path = os.path.join(BASE_DIR, "data", "pii_test_set.json")
    with open(test_set_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    all_entities = ["Email", "SSN", "Credit Card", "Phone Number", "API Key", "JWT Token"]
    
    ground_truth = []
    gateway_preds = []
    presidio_preds = []
    raw_results = []

    for item in test_data:
        text = item["text"]
        expected = item["expected_entities"]
        
        # 1. Gateway PII evaluation
        sanitized_text, detected_gateway = InputGuards.mask_pii(text)
        
        # 2. Presidio evaluation
        detected_presidio = run_presidio_detection(text)

        ground_truth.append(expected)
        gateway_preds.append(detected_gateway)
        presidio_preds.append(detected_presidio)

        raw_results.append({
            "id": item["id"],
            "text": text,
            "expected": expected,
            "gateway_detected": detected_gateway,
            "gateway_sanitized": sanitized_text,
            "presidio_detected": detected_presidio,
            "contains_pii": item["contains_pii"],
            "gateway_correct": set(expected) == set(detected_gateway)
        })

    # Per-entity metrics for Gateway
    gateway_entity_metrics = {}
    for ent in all_entities:
        gateway_entity_metrics[ent] = calculate_entity_metrics(ground_truth, gateway_preds, ent)

    # Per-entity metrics for Presidio (for entities it supports)
    presidio_entity_metrics = {}
    for ent in ["Email", "Phone Number", "Credit Card", "SSN"]:
        presidio_entity_metrics[ent] = calculate_entity_metrics(ground_truth, presidio_preds, ent)

    # Overall binary PII detection (contains PII vs benign)
    y_true_binary = [1 if len(e) > 0 else 0 for e in ground_truth]
    y_pred_binary_gw = [1 if len(e) > 0 else 0 for e in gateway_preds]
    y_pred_binary_pres = [1 if len(e) > 0 else 0 for e in presidio_preds]

    def binary_stats(y_t, y_p):
        tp = sum(1 for yt, yp in zip(y_t, y_p) if yt == 1 and yp == 1)
        fp = sum(1 for yt, yp in zip(y_t, y_p) if yt == 0 and yp == 1)
        fn = sum(1 for yt, yp in zip(y_t, y_p) if yt == 1 and yp == 0)
        tn = sum(1 for yt, yp in zip(y_t, y_p) if yt == 0 and yp == 0)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4)}

    output_payload = {
        "presidio_available": PRESIDIO_AVAILABLE,
        "total_test_samples": len(test_data),
        "gateway_entity_metrics": gateway_entity_metrics,
        "presidio_entity_metrics": presidio_entity_metrics,
        "overall_gateway_binary": binary_stats(y_true_binary, y_pred_binary_gw),
        "overall_presidio_binary": binary_stats(y_true_binary, y_pred_binary_pres) if PRESIDIO_AVAILABLE else None
    }

    results_dir = os.path.join(BASE_DIR, "results")
    os.makedirs(results_dir, exist_ok=True)
    with open(os.path.join(results_dir, "pii_eval_raw.json"), "w", encoding="utf-8") as f:
        json.dump(raw_results, f, indent=2)

    with open(os.path.join(results_dir, "pii_summary.json"), "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    logger.info("=" * 60)
    logger.info("PII DETECTION & MASKING EVALUATION")
    logger.info("=" * 60)
    logger.info(f"{'Entity Type':<16} | {'Gateway Prec':<12} | {'Gateway Rec':<12} | {'Gateway F1':<10} | {'Presidio F1':<10}")
    logger.info("-" * 68)
    for ent in all_entities:
        gw = gateway_entity_metrics[ent]
        pres_f1 = presidio_entity_metrics.get(ent, {}).get("f1_score", "N/A")
        pres_str = f"{pres_f1:.4f}" if isinstance(pres_f1, float) else "N/A (unsupported)"
        logger.info(f"{ent:<16} | {gw['precision']:<12.4f} | {gw['recall']:<12.4f} | {gw['f1_score']:<10.4f} | {pres_str:<10}")
    logger.info("=" * 60)

    return output_payload

if __name__ == "__main__":
    run_evaluation()
