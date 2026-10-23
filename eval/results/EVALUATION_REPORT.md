# LLM Security Gateway: Evaluation & Benchmark Report

**Status:** Automated Reproducible Evaluation Suite
**Execution Timestamp:** 2026-10-23 07:15:34 UTC
**Hardware Environment:** macOS-27.0-arm64-arm-64bit-Mach-O (arm64) | Python 3.14.3

---

## 1. Prompt Injection Detection Benchmark

Evaluated against public benchmarks: `deepset/prompt-injections` (Hugging Face test split) and JailbreakBench (`JBB-Behaviors`).

| Dataset Split | Samples | Precision | Recall | F1 Score | False Positive Rate | Confusion Matrix (TN, FP, FN, TP) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `deepset/prompt-injections` (test) | 116 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | TN=56, FP=0, FN=60, TP=0 |
| JailbreakBench (`JBB-Behaviors`) | 200 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | TN=100, FP=0, FN=100, TP=0 |
| **Combined Benchmark** | **316** | **0.0000** | **0.0000** | **0.0000** | **0.0000** | **TN=156, FP=0, FN=160, TP=0** |

## 2. Personally Identifiable Information (PII) Masking Benchmark

Evaluated on synthetic labeled test corpus across 6 entity types, including Luhn-valid credit cards and comparison with Microsoft Presidio pattern recognizers.

| Entity Type | Gateway Precision | Gateway Recall | Gateway F1 | Presidio F1 (Comparative) |
|:---|:---:|:---:|:---:|:---:|
| Email | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| SSN | 1.0000 | 1.0000 | 1.0000 | 0.5000 |
| Credit Card | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Phone Number | 1.0000 | 1.0000 | 1.0000 | 0.8571 |
| API Key | 1.0000 | 1.0000 | 1.0000 | N/A (unsupported) |
| JWT Token | 1.0000 | 1.0000 | 1.0000 | N/A (unsupported) |

---

## 3. Output Guardrail (System Prompt Leakage Prevention)

Evaluated on direct system prompt leakage attacks versus benign technical texts and defensive AI refusals.

- **Total Test Cases:** 10
- **Precision:** 1.0000
- **Recall:** 1.0000
- **F1 Score:** 1.0000
- **False Positive Rate:** 0.0000 (Defensive refusals and OS instructions correctly permitted)

---

## 4. Adversarial Bypass Vulnerability Analysis

Honest evaluation of static regex guard limitations across categorized evasion strategies:

| Attack Category | Total Samples | Blocked | Bypassed | Bypass Rate (%) | Vulnerability Root Cause |
|:---|:---:|:---:|:---:|:---:|:---|
| leetspeak | 3 | 0 | 3 | 100.0% | Uncaught by English-only exact regex heuristics |
| multi_turn | 1 | 0 | 1 | 100.0% | Uncaught by English-only exact regex heuristics |
| other_encodings | 3 | 0 | 3 | 100.0% | Uncaught by English-only exact regex heuristics |
| other_languages | 3 | 0 | 3 | 100.0% | Uncaught by English-only exact regex heuristics |
| paraphrase | 3 | 1 | 2 | 66.7% | Uncaught by English-only exact regex heuristics |
| roleplay_hypothetical | 1 | 0 | 1 | 100.0% | Uncaught by English-only exact regex heuristics |
| split_payloads | 2 | 1 | 1 | 50.0% | Uncaught by English-only exact regex heuristics |
| unicode_homoglyphs | 2 | 1 | 1 | 50.0% | Uncaught by English-only exact regex heuristics |
| **OVERALL** | **18** | **3** | **15** | **83.3%** | **Regex Blindness to Semantic / Encoding Variations** |

---

## 5. Micro-Benchmark Latency Profile

Measured over 100 iterations (Deterministic Seed 42):

| Pipeline Stage | p50 Latency (ms) | p95 Latency (ms) | p99 Latency (ms) | Mean Latency (ms) |
|:---|:---:|:---:|:---:|:---:|
| 1. Input Guard (Injection Scan) | 0.0655 | 0.0708 | 0.0732 | 0.0670 |
| 2. PII Masking Engine | 0.0274 | 0.0291 | 0.0322 | 0.0279 |
| 3. Adversarial Risk Scoring | 0.1019 | 0.1127 | 0.1160 | 0.1052 |
| 4. Cache Engine (Cache HIT) | 0.4433 | 0.5553 | 0.9000 | 0.4578 |
| 5. Output Guard (Leakage Scan) | 0.0275 | 0.0290 | 0.0310 | 0.0280 |
| 6. Full Gateway Request (Mock Upstream) | 3.1201 | 4.5935 | 12.5650 | 3.4953 |

---

*Generated automatically by `make eval` / `eval/run_eval.py`.*