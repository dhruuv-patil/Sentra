import json
import logging
import os
import sys
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.security.input_guards import InputGuards

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval.bypass")

def run_evaluation():
    test_set_path = os.path.join(BASE_DIR, "data", "adversarial_bypass_set.json")
    with open(test_set_path, "r", encoding="utf-8") as f:
        adversarial_data = json.load(f)

    category_stats = defaultdict(lambda: {"total": 0, "caught": 0, "missed": 0, "missed_examples": []})
    raw_results = []

    for item in adversarial_data:
        cat = item["category"]
        category_stats[cat]["total"] += 1

        # Check whether prompt or multi-turn messages
        if "messages" in item:
            is_detected, detail = InputGuards.detect_messages_injection(item["messages"])
            input_repr = " -> ".join(f"[{m['role']}]: {m['content']}" for m in item["messages"])
        else:
            is_detected = InputGuards.detect_prompt_injection(item["prompt"])
            detail = "Direct prompt regex match" if is_detected else "No pattern matched"
            input_repr = item["prompt"]

        if is_detected:
            category_stats[cat]["caught"] += 1
        else:
            category_stats[cat]["missed"] += 1
            category_stats[cat]["missed_examples"].append({
                "id": item["id"],
                "input": input_repr,
                "description": item.get("description", "")
            })

        raw_results.append({
            "id": item["id"],
            "category": cat,
            "input": input_repr,
            "is_detected": is_detected,
            "detail": detail,
            "description": item.get("description", "")
        })

    summary_table = []
    total_attacks = len(adversarial_data)
    total_caught = sum(stats["caught"] for stats in category_stats.values())
    total_missed = sum(stats["missed"] for stats in category_stats.values())

    for cat, stats in sorted(category_stats.items()):
        caught = stats["caught"]
        total = stats["total"]
        bypass_rate = round((stats["missed"] / total) * 100, 1)
        summary_table.append({
            "category": cat,
            "total_attacks": total,
            "caught": caught,
            "missed": stats["missed"],
            "bypass_rate_pct": bypass_rate,
            "weakness_reason": (
                "Uncaught by English-only exact regex heuristics" if stats["missed"] > 0 else "Fully mitigated"
            ),
            "sample_missed": stats["missed_examples"][0]["input"] if stats["missed_examples"] else None
        })

    results_dir = os.path.join(BASE_DIR, "results")
    os.makedirs(results_dir, exist_ok=True)

    with open(os.path.join(results_dir, "bypass_analysis_raw.json"), "w", encoding="utf-8") as f:
        json.dump(raw_results, f, indent=2)

    output_payload = {
        "overall": {
            "total_attacks": total_attacks,
            "total_caught": total_caught,
            "total_missed": total_missed,
            "overall_bypass_rate_pct": round((total_missed / max(total_attacks, 1)) * 100, 1),
            "overall_defense_rate_pct": round((total_caught / max(total_attacks, 1)) * 100, 1)
        },
        "by_category": summary_table
    }

    with open(os.path.join(results_dir, "bypass_summary.json"), "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    logger.info("=" * 70)
    logger.info("ADVERSARIAL BYPASS ANALYSIS (Static Regex Guard Weaknesses)")
    logger.info("=" * 70)
    logger.info(f"{'Attack Category':<22} | {'Total':<6} | {'Caught':<7} | {'Missed':<7} | {'Bypass Rate':<12}")
    logger.info("-" * 70)
    for row in summary_table:
        logger.info(f"{row['category']:<22} | {row['total_attacks']:<6} | {row['caught']:<7} | {row['missed']:<7} | {row['bypass_rate_pct']:.1f}%")
    logger.info("-" * 70)
    logger.info(f"OVERALL: {total_caught}/{total_attacks} blocked ({output_payload['overall']['overall_defense_rate_pct']}%), {total_missed}/{total_attacks} bypassed ({output_payload['overall']['overall_bypass_rate_pct']}%)")
    logger.info("=" * 70)

    return output_payload

if __name__ == "__main__":
    run_evaluation()
