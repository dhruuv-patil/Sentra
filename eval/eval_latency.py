import json
import logging
import os
import platform
import random
import sys
import time
from unittest.mock import patch

import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi.testclient import TestClient

from app.server import app
from core.cache import cache
from core.config import config
from core.security.input_guards import InputGuards
from core.security.output_guards import OutputGuards

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval.latency")

def get_system_hardware_info() -> dict:
    """Collects deterministic hardware and runtime execution environment details."""
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version.split()[0],
        "python_compiler": platform.python_compiler()
    }

def calculate_percentiles(durations_ms: list[float]) -> dict:
    durations = np.array(durations_ms)
    return {
        "samples": len(durations),
        "mean_ms": round(float(np.mean(durations)), 4),
        "p50_ms": round(float(np.percentile(durations, 50)), 4),
        "p95_ms": round(float(np.percentile(durations, 95)), 4),
        "p99_ms": round(float(np.percentile(durations, 99)), 4),
        "min_ms": round(float(np.min(durations)), 4),
        "max_ms": round(float(np.max(durations)), 4)
    }

def run_latency_benchmark(iterations: int = 100, seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)

    hw_info = get_system_hardware_info()
    logger.info("=" * 65)
    logger.info("GATEWAY LATENCY BENCHMARK (Deterministic Seed 42)")
    logger.info(f"Hardware: {hw_info['os']} ({hw_info['architecture']}) | Python {hw_info['python_version']}")
    logger.info("=" * 65)

    sample_prompt = (
        "Hello security team, please verify my credentials and send confirmation to "
        "test.engineer@company.org or reach me at (415) 555-0199. SSN: 111-22-3333. "
        "Also confirm how our distributed architecture handles zero-trust authorization."
    )
    sample_response = (
        "Your security credentials have been processed. The distributed gateway validates "
        "tokens across each microservice using constant-time verification."
    )

    stage_timings = {
        "1. Input Guard (Injection Scan)": [],
        "2. PII Masking Engine": [],
        "3. Adversarial Risk Scoring": [],
        "4. Cache Engine (Cache HIT)": [],
        "5. Output Guard (Leakage Scan)": [],
        "6. Full Gateway Request (Mock Upstream)": []
    }

    # Setup cache entry for stage 4
    cache.clear()
    model_name = "groq/llama-3.3-70b-versatile"
    tenant_id = "latency_test_tenant"
    sanitized_text, _ = InputGuards.mask_pii(sample_prompt)
    cache.set(model_name, sanitized_text, sample_response, tokens=45, cost=0.0009, tenant_id=tenant_id)

    # 1. Input Guard: Injection Detection
    for _ in range(iterations):
        t0 = time.perf_counter()
        InputGuards.detect_prompt_injection(sample_prompt)
        stage_timings["1. Input Guard (Injection Scan)"].append((time.perf_counter() - t0) * 1000)

    # 2. PII Masking Engine
    for _ in range(iterations):
        t0 = time.perf_counter()
        InputGuards.mask_pii(sample_prompt)
        stage_timings["2. PII Masking Engine"].append((time.perf_counter() - t0) * 1000)

    # 3. Adversarial Risk Scoring
    for _ in range(iterations):
        t0 = time.perf_counter()
        InputGuards.calculate_risk_score(sample_prompt)
        stage_timings["3. Adversarial Risk Scoring"].append((time.perf_counter() - t0) * 1000)

    # 4. Cache Engine (Cache Hit)
    for _ in range(iterations):
        t0 = time.perf_counter()
        cache.get(model_name, sanitized_text, tenant_id=tenant_id)
        stage_timings["4. Cache Engine (Cache HIT)"].append((time.perf_counter() - t0) * 1000)

    # 5. Output Guard: Leakage Detection
    for _ in range(iterations):
        t0 = time.perf_counter()
        OutputGuards.detect_harmful_content(sample_response)
        stage_timings["5. Output Guard (Leakage Scan)"].append((time.perf_counter() - t0) * 1000)

    # 6. Full Request Roundtrip via FastAPI TestClient (Mock Upstream)
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {config.SECRET_KEY}"
    request_payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Explain microservices security in 2 sentences."}]
    }

    mock_completion = {
        "mode": "mock",
        "choices": [{"message": {"role": "assistant", "content": "Microservices security requires zero-trust verification."}}],
        "usage": {"total_tokens": 20}
    }

    with patch("core.llm.provider_dispatcher.dispatcher.complete", return_value=mock_completion):
        for _ in range(iterations):
            cache.clear() # Force full pipeline execution on each run
            from app.api.routes import rate_limiter
            rate_limiter.reset() # Reset sliding window for deterministic latency test
            t0 = time.perf_counter()
            resp = client.post("/v1/chat/completions", json=request_payload)
            dur_ms = (time.perf_counter() - t0) * 1000
            assert resp.status_code == 200
            stage_timings["6. Full Gateway Request (Mock Upstream)"].append(dur_ms)

    benchmark_results = {}
    logger.info(f"{'Pipeline Stage':<42} | {'p50 (ms)':<9} | {'p95 (ms)':<9} | {'p99 (ms)':<9} | {'Mean (ms)':<9}")
    logger.info("-" * 88)

    for stage_name, durations in stage_timings.items():
        stats = calculate_percentiles(durations)
        benchmark_results[stage_name] = stats
        logger.info(f"{stage_name:<42} | {stats['p50_ms']:<9.4f} | {stats['p95_ms']:<9.4f} | {stats['p99_ms']:<9.4f} | {stats['mean_ms']:<9.4f}")

    logger.info("=" * 88)

    output_payload = {
        "hardware_environment": hw_info,
        "benchmark_parameters": {
            "iterations": iterations,
            "seed": seed,
            "date": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        },
        "stages": benchmark_results
    }

    results_dir = os.path.join(BASE_DIR, "results")
    os.makedirs(results_dir, exist_ok=True)
    with open(os.path.join(results_dir, "latency_benchmark.json"), "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    return output_payload

if __name__ == "__main__":
    run_latency_benchmark()
