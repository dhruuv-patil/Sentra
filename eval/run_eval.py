import os
import sys
import json
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from eval.data.download_datasets import main as run_download
from eval.eval_prompt_injection import run_evaluation as run_injection_eval
from eval.eval_pii import run_evaluation as run_pii_eval
from eval.eval_output_guards import run_evaluation as run_output_eval
from eval.eval_bypass import run_evaluation as run_bypass_eval
from eval.eval_latency import run_latency_benchmark

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval.master")

def generate_markdown_report(injection_res, pii_res, output_res, bypass_res, latency_res):
    md = []
    md.append("# LLM Security Gateway: Evaluation & Benchmark Report\n")
    md.append("**Status:** Automated Reproducible Evaluation Suite")
    md.append(f"**Execution Timestamp:** {latency_res['benchmark_parameters']['date']}")
    md.append(f"**Hardware Environment:** {latency_res['hardware_environment']['platform']} ({latency_res['hardware_environment']['architecture']}) | Python {latency_res['hardware_environment']['python_version']}\n")
    md.append("---\n")

    # 1. Prompt Injection Detection
    md.append("## 1. Prompt Injection Detection Benchmark\n")
    md.append("Evaluated against public benchmarks: `deepset/prompt-injections` (Hugging Face test split) and JailbreakBench (`JBB-Behaviors`).\n")
    md.append("| Dataset Split | Samples | Precision | Recall | F1 Score | False Positive Rate | Confusion Matrix (TN, FP, FN, TP) |")
    md.append("|:---|:---:|:---:|:---:|:---:|:---:|:---:|")

    d = injection_res["deepset_test_metrics"]
    cm = d["confusion_matrix"]
    md.append(f"| `deepset/prompt-injections` (test) | {d['total_samples']} | {d['precision']:.4f} | {d['recall']:.4f} | {d['f1_score']:.4f} | {d['false_positive_rate']:.4f} | TN={cm['TN']}, FP={cm['FP']}, FN={cm['FN']}, TP={cm['TP']} |")

    if injection_res.get("jailbreakbench_metrics"):
        j = injection_res["jailbreakbench_metrics"]
        jcm = j["confusion_matrix"]
        md.append(f"| JailbreakBench (`JBB-Behaviors`) | {j['total_samples']} | {j['precision']:.4f} | {j['recall']:.4f} | {j['f1_score']:.4f} | {j['false_positive_rate']:.4f} | TN={jcm['TN']}, FP={jcm['FP']}, FN={jcm['FN']}, TP={jcm['TP']} |")

    c = injection_res["combined_benchmark_metrics"]
    ccm = c["confusion_matrix"]
    md.append(f"| **Combined Benchmark** | **{c['total_samples']}** | **{c['precision']:.4f}** | **{c['recall']:.4f}** | **{c['f1_score']:.4f}** | **{c['false_positive_rate']:.4f}** | **TN={ccm['TN']}, FP={ccm['FP']}, FN={ccm['FN']}, TP={ccm['TP']}** |\n")

    # 2. PII Detection & Sanitization
    md.append("## 2. Personally Identifiable Information (PII) Masking Benchmark\n")
    md.append("Evaluated on synthetic labeled test corpus across 6 entity types, including Luhn-valid credit cards and comparison with Microsoft Presidio pattern recognizers.\n")
    md.append("| Entity Type | Gateway Precision | Gateway Recall | Gateway F1 | Presidio F1 (Comparative) |")
    md.append("|:---|:---:|:---:|:---:|:---:|")

    for ent, m in pii_res["gateway_entity_metrics"].items():
        pres_f1 = pii_res["presidio_entity_metrics"].get(ent, {}).get("f1_score", "N/A")
        pres_str = f"{pres_f1:.4f}" if isinstance(pres_f1, float) else "N/A (unsupported)"
        md.append(f"| {ent} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1_score']:.4f} | {pres_str} |")

    md.append("\n---\n")

    # 3. Output Guardrails
    md.append("## 3. Output Guardrail (System Prompt Leakage Prevention)\n")
    md.append("Evaluated on direct system prompt leakage attacks versus benign technical texts and defensive AI refusals.\n")
    md.append(f"- **Total Test Cases:** {output_res['total_samples']}")
    md.append(f"- **Precision:** {output_res['precision']:.4f}")
    md.append(f"- **Recall:** {output_res['recall']:.4f}")
    md.append(f"- **F1 Score:** {output_res['f1_score']:.4f}")
    md.append(f"- **False Positive Rate:** {output_res['false_positive_rate']:.4f} (Defensive refusals and OS instructions correctly permitted)\n")
    md.append("---\n")

    # 4. Adversarial Bypass Analysis
    md.append("## 4. Adversarial Bypass Vulnerability Analysis\n")
    md.append("Honest evaluation of static regex guard limitations across categorized evasion strategies:\n")
    md.append("| Attack Category | Total Samples | Blocked | Bypassed | Bypass Rate (%) | Vulnerability Root Cause |")
    md.append("|:---|:---:|:---:|:---:|:---:|:---|")

    for row in bypass_res["by_category"]:
        md.append(f"| {row['category']} | {row['total_attacks']} | {row['caught']} | {row['missed']} | {row['bypass_rate_pct']:.1f}% | {row['weakness_reason']} |")

    ov = bypass_res["overall"]
    md.append(f"| **OVERALL** | **{ov['total_attacks']}** | **{ov['total_caught']}** | **{ov['total_missed']}** | **{ov['overall_bypass_rate_pct']:.1f}%** | **Regex Blindness to Semantic / Encoding Variations** |\n")
    md.append("---\n")

    # 5. Latency Micro-Benchmarks
    md.append("## 5. Micro-Benchmark Latency Profile\n")
    md.append(f"Measured over 100 iterations (Deterministic Seed {latency_res['benchmark_parameters']['seed']}):\n")
    md.append("| Pipeline Stage | p50 Latency (ms) | p95 Latency (ms) | p99 Latency (ms) | Mean Latency (ms) |")
    md.append("|:---|:---:|:---:|:---:|:---:|")

    for stage_name, s in latency_res["stages"].items():
        md.append(f"| {stage_name} | {s['p50_ms']:.4f} | {s['p95_ms']:.4f} | {s['p99_ms']:.4f} | {s['mean_ms']:.4f} |")

    md.append("\n---\n")
    md.append("*Generated automatically by `make eval` / `eval/run_eval.py`.*")

    report_content = "\n".join(md)
    results_dir = os.path.join(BASE_DIR, "results")
    with open(os.path.join(results_dir, "EVALUATION_REPORT.md"), "w", encoding="utf-8") as f:
        f.write(report_content)
    logger.info(f"Consolidated evaluation report saved to {os.path.join(results_dir, 'EVALUATION_REPORT.md')}")

def main():
    logger.info("Starting Master Evaluation Harness...")
    run_download()
    
    logger.info("\n>>> [1/5] Running Prompt Injection Detection Evaluation...")
    inj_res = run_injection_eval()

    logger.info("\n>>> [2/5] Running PII Detection and Masking Evaluation...")
    pii_res = run_pii_eval()

    logger.info("\n>>> [3/5] Running Output Guardrails Evaluation...")
    out_res = run_output_eval()

    logger.info("\n>>> [4/5] Running Adversarial Bypass Analysis...")
    byp_res = run_bypass_eval()

    logger.info("\n>>> [5/5] Running Latency Micro-Benchmarks...")
    lat_res = run_latency_benchmark()

    logger.info("\nGenerating Consolidated Markdown Report...")
    generate_markdown_report(inj_res, pii_res, out_res, byp_res, lat_res)
    logger.info("Evaluation Complete! All results written to eval/results/.")

if __name__ == "__main__":
    main()
