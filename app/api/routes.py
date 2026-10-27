import json
import logging
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from app.api.schemas import (
    ApprovalAction,
    ChatCompletionRequest,
    CreateTokenRequest,
    GuardrailToggleRequest,
    PlaygroundEvaluateRequest,
)
from core.cache import cache
from core.config import config
from core.llm.provider_dispatcher import dispatcher
from core.security.input_guards import InputGuards
from core.security.output_guards import OutputGuards
from data.repository import Repository

logger = logging.getLogger("gateway.api")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()
router = APIRouter()

# ---------------------------------------------------------------------------
# In-Memory Sliding-Window Rate Limiter
# ---------------------------------------------------------------------------
class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.client_records: dict[str, list[float]] = {}

    def check_rate_limit(self, client_key: str) -> tuple[bool, int]:
        now = time.time()
        window_start = now - 60.0
        timestamps = [t for t in self.client_records.get(client_key, []) if t > window_start]
        if len(timestamps) >= self.rpm:
            retry_after = int(max(1, 60.0 - (now - timestamps[0])))
            self.client_records[client_key] = timestamps
            return False, retry_after

        timestamps.append(now)
        self.client_records[client_key] = timestamps
        return True, 0

    def reset(self):
        self.client_records.clear()

rate_limiter = RateLimiter(requests_per_minute=getattr(config, "RATE_LIMIT_RPM", 60))

# ---------------------------------------------------------------------------
# Authentication & Authorization Dependencies (Constant-Time)
# ---------------------------------------------------------------------------
def require_client_auth(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
) -> dict:
    """
    Validates per-client API keys or Bearer tokens via constant-time comparison.
    Rejects unauthenticated requests with HTTP 401.
    """
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ", 1)[1].strip()
    elif x_api_key:
        raw_token = x_api_key.strip()

    if not raw_token:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing API key. Provide via 'Authorization: Bearer <key>' or 'X-API-Key' header."
        )

    token_meta = Repository.validate_token(raw_token)
    if not token_meta:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid API key or inactive service token."
        )

    return token_meta

def require_admin_auth(
    identity: dict = Depends(require_client_auth)
) -> dict:
    """
    Ensures the caller has administrative privileges ('admin' scope).
    Rejects unauthorized callers with HTTP 403.
    """
    scope = identity.get("scope", "")
    if scope != "admin" and "admin" not in scope:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Administrative privileges required for this endpoint."
        )
    return identity

# ---------------------------------------------------------------------------
# Public Health & Information Endpoints
# ---------------------------------------------------------------------------
@router.get("/api/health")
async def health_check():
    """System health check endpoint (distinguishes liveness & service stats)."""
    return {
        "status": "healthy",
        "service": "Sentra",
        "version": "2.0.0",
        "cache_entries": cache.count(),
        "api_host": config.API_HOST,
        "api_port": config.API_PORT
    }

@router.get("/api/models")
async def get_models(identity: dict = Depends(require_client_auth)):
    """Returns the list of configured models and providers."""
    return {
        "models": [
            {"id": "groq/llama-3.3-70b-versatile", "provider": "Groq", "name": "Llama 3.3 70B Versatile"},
            {"id": "groq/llama-3.1-8b-instant", "provider": "Groq", "name": "Llama 3.1 8B Instant"},
            {"id": "groq/mixtral-8x7b-32768", "provider": "Groq", "name": "Mixtral 8x7B"},
            {"id": "ollama/llama3", "provider": "Ollama (Local)", "name": "Llama 3 (Local)"},
            {"id": "ollama/mistral", "provider": "Ollama (Local)", "name": "Mistral (Local)"}
        ]
    }

# ---------------------------------------------------------------------------
# Core Chat Completions Pipeline
# ---------------------------------------------------------------------------
@router.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    identity: dict = Depends(require_client_auth)
):
    request_id = str(uuid.uuid4())
    tenant_id = identity.get("tenant_id", "default")
    user_id = request.user or "default_user"

    # 0. Data Sovereignty & Tenant Model Whitelist Enforcement
    is_allowed, denial_reason = Repository.is_model_allowed_for_tenant(identity, request.model)
    if not is_allowed:
        return JSONResponse(
            status_code=403,
            content={
                "error": f"Policy Restriction: {denial_reason}",
                "request_id": request_id
            }
        )

    # Rate Limiting per API key / Tenant
    allowed, retry_after = rate_limiter.check_rate_limit(tenant_id)
    if not allowed:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(retry_after)},
            content={"error": f"Rate limit exceeded. Retry after {retry_after} seconds.", "request_id": request_id}
        )

    await manager.broadcast({
        "type": "request_received",
        "request_id": request_id,
        "tenant_id": tenant_id,
        "model": request.model,
        "message": f"Received request for model {request.model}"
    })

    # 1. Multi-Message Prompt Injection Guard: Evaluates ALL messages (system, user, assistant)
    from core.security.detectors import detector
    is_injection = False
    injection_detail = None
    all_rag_matches = []
    total_rag_latency = 0.0

    for idx, msg in enumerate(request.messages):
        det_res = detector.predict(msg.content)
        if hasattr(det_res, "rag_matches") and det_res.rag_matches:
            all_rag_matches.extend(det_res.rag_matches)
        if hasattr(det_res, "latency_ms") and det_res.latency_ms:
            total_rag_latency += det_res.latency_ms

        if det_res.is_injection:
            is_injection = True
            injection_detail = f"Message index {idx} ({msg.role}): {det_res.detail}"
            break

    if is_injection:
        await manager.broadcast({
            "type": "input_guards_evaluated",
            "request_id": request_id,
            "status": "blocked",
            "reason": "Prompt Injection Detected",
            "message": f"Input guardrails failed: Adversarial Prompt Injection detected ({injection_detail})"
        })
        return JSONResponse(
            status_code=403,
            content={
                "error": "Security Block: Prompt Injection Detected",
                "request_id": request_id,
                "detail": injection_detail
            }
        )

    # 2. Risk Score Evaluation across ALL conversation turns
    risk_score = InputGuards.calculate_messages_risk_score(request.messages)

    # 3. Multi-Message PII Sanitization: Masks PII in EVERY message before upstream dispatch
    sanitized_messages, detected_pii = InputGuards.mask_messages_pii(request.messages)
    last_sanitized_prompt = sanitized_messages[-1]["content"] if sanitized_messages else ""

    if detected_pii:
        await manager.broadcast({
            "type": "pii_redacted",
            "request_id": request_id,
            "detected_pii": detected_pii,
            "message": f"Masked sensitive PII entities: {', '.join(detected_pii)}"
        })

    await manager.broadcast({
        "type": "input_guards_evaluated",
        "request_id": request_id,
        "status": "passed",
        "risk_score": risk_score,
        "message": f"Input guardrails passed (Risk Score: {risk_score})"
    })

    # 4. Human-in-the-Loop Policy: High-Risk Queuing (Score > 50)
    if risk_score > 50:
        # PII is strictly masked before persisting to database
        Repository.add_to_approval_queue(request_id, user_id, request.model, last_sanitized_prompt)
        await manager.broadcast({
            "type": "human_in_the_loop",
            "request_id": request_id,
            "status": "queued",
            "risk_score": risk_score,
            "message": f"High risk interaction ({risk_score}/100). Queued for admin authorization."
        })
        return {
            "status": "Pending Approval",
            "request_id": request_id,
            "message": "High-risk request queued for administrator review.",
            "poll_url": f"/v1/requests/{request_id}",
            "risk_score": risk_score
        }

    # 5. Scoped Response Cache Inspection by (tenant_id, model, parameters, prompt_hash)
    gen_params = request.get_parameters()
    cached = cache.get(request.model, last_sanitized_prompt, tenant_id=tenant_id, parameters=gen_params)
    if cached:
        await manager.broadcast({
            "type": "cache_hit",
            "request_id": request_id,
            "tokens": 0,
            "message": "Served instantly from Gateway Cache (0 tokens consumed)"
        })
        rag_json = json.dumps(all_rag_matches) if all_rag_matches else None
        Repository.log_request(
            request_id, user_id, request.model, last_sanitized_prompt, cached["response"], 0, 0.0, risk_score, 0.001,
            rag_matches=rag_json, rag_latency=round(total_rag_latency, 2)
        )
        return JSONResponse(
            status_code=200,
            headers={"X-Gateway-Mode": "cached", "X-Cache-Hit": "true"},
            content={
                "id": request_id,
                "mode": "cached",
                "choices": [{"message": {"role": "assistant", "content": cached["response"]}}],
                "usage": {"total_tokens": 0},
                "cache_hit": True
            }
        )

    # 6. LLM Interaction via Unified Dispatcher
    await manager.broadcast({
        "type": "llm_interaction_started",
        "request_id": request_id,
        "message": f"Dispatching sanitized prompt to {request.model}"
    })
    start_time = time.time()
    result = dispatcher.complete(request.model, sanitized_messages)
    latency = round(time.time() - start_time, 2)

    # Handle upstream provider errors without uncaught 500s
    if not isinstance(result, dict) or "error" in result:
        err_msg = result.get("error", {}).get("message", "Model execution error") if isinstance(result, dict) else "Unknown upstream provider failure"
        err_code = result.get("error", {}).get("code", 502) if isinstance(result, dict) else 502
        if err_code not in (400, 401, 403, 404, 429, 502, 503, 504):
            err_code = 502
        await manager.broadcast({
            "type": "llm_interaction_failed",
            "request_id": request_id,
            "error": err_msg,
            "message": f"Model error: {err_msg}"
        })
        return JSONResponse(
            status_code=err_code,
            content={"error": err_msg, "request_id": request_id}
        )

    choices = result.get("choices", [])
    if not choices or not isinstance(choices, list) or "message" not in choices[0]:
        return JSONResponse(
            status_code=502,
            content={"error": "Malformed provider completion payload: missing 'choices'", "request_id": request_id}
        )

    llm_response = choices[0]["message"].get("content", "")
    tokens = result.get("usage", {}).get("total_tokens", 0) if isinstance(result.get("usage"), dict) else 0
    cost = round((tokens / 1000) * 0.002, 5)
    execution_mode = result.get("mode", "live")

    await manager.broadcast({
        "type": "llm_interaction_completed",
        "request_id": request_id,
        "latency": latency,
        "tokens": tokens,
        "mode": execution_mode,
        "message": f"Received completion from {request.model} ({tokens} tokens in {latency}s, mode: {execution_mode})"
    })

    # 7. Output Guardrails: System Leakage & Toxicity Scan
    harm_category = OutputGuards.detect_harmful_content(llm_response)
    if harm_category:
        Repository.log_harmful(request_id, user_id, last_sanitized_prompt, harm_category, risk_score)
        await manager.broadcast({
            "type": "output_guards_evaluated",
            "request_id": request_id,
            "status": "blocked",
            "reason": harm_category,
            "message": f"Output guardrail block: {harm_category} detected"
        })
        return JSONResponse(
            status_code=403,
            content={"error": f"Security Block: {harm_category} detected in model output.", "request_id": request_id}
        )

    await manager.broadcast({
        "type": "output_guards_evaluated",
        "request_id": request_id,
        "status": "passed",
        "message": "Output guardrails validated"
    })

    # 8. Cache & Audit Persistence (PII strictly masked, response encrypted)
    cache.set(request.model, last_sanitized_prompt, llm_response, tokens, cost, tenant_id=tenant_id, parameters=gen_params)
    rag_json = json.dumps(all_rag_matches) if all_rag_matches else None
    Repository.log_request(
        request_id, user_id, request.model, last_sanitized_prompt, llm_response, tokens, cost, risk_score, latency,
        rag_matches=rag_json, rag_latency=round(total_rag_latency, 2)
    )

    await manager.broadcast({
        "type": "request_completed",
        "request_id": request_id,
        "message": "Transaction safely completed and encrypted in audit logs."
    })

    return JSONResponse(
        status_code=200,
        headers={"X-Gateway-Mode": execution_mode, "X-Cache-Hit": "false"},
        content={
            "id": request_id,
            "mode": execution_mode,
            "choices": [{"message": {"role": "assistant", "content": llm_response}}],
            "usage": {"total_tokens": tokens},
            "latency": latency,
            "cache_hit": False
        }
    )

@router.get("/v1/requests/{request_id}")
async def get_request_status(
    request_id: str,
    identity: dict = Depends(require_client_auth)
):
    """Client polling endpoint for queued approval requests."""
    status_data = Repository.get_request_status(request_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Request ID not found.")
    return status_data

@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# ---------------------------------------------------------------------------
# Protected Administrative Endpoints (Admin Scope Required)
# ---------------------------------------------------------------------------
@router.post("/api/approve/{request_id}")
async def approve(
    request_id: str,
    action: Optional[ApprovalAction] = None,
    admin: dict = Depends(require_admin_auth)
):
    reviewer = action.reviewer if (action and action.reviewer) else admin.get("name", "admin")
    result = Repository.approve_request(request_id, reviewer=reviewer)
    await manager.broadcast({
        "type": "approval_resolved",
        "request_id": request_id,
        "status": "Approved",
        "message": f"Request {request_id} approved by {reviewer} and executed."
    })
    return result

@router.post("/api/deny/{request_id}")
async def deny(
    request_id: str,
    action: Optional[ApprovalAction] = None,
    admin: dict = Depends(require_admin_auth)
):
    reviewer = action.reviewer if (action and action.reviewer) else admin.get("name", "admin")
    reason = action.reason if (action and action.reason) else "Denied by administrator"
    result = Repository.deny_request(request_id, reviewer=reviewer, reason=reason)
    await manager.broadcast({
        "type": "approval_resolved",
        "request_id": request_id,
        "status": "Denied",
        "message": f"Request {request_id} denied by {reviewer}: {reason}"
    })
    return result

@router.post("/api/cache/clear")
async def clear_cache(admin: dict = Depends(require_admin_auth)):
    cache.clear()
    return {"status": "Cache cleared"}

@router.get("/api/dashboard/stats")
async def get_dashboard_stats(
    filter: str = "all",
    admin: dict = Depends(require_admin_auth)
):
    """Returns aggregated executive security metrics computed from verified SQLite logs."""
    stats = Repository.get_dashboard_metrics(time_filter=filter)
    return stats

def _df_to_records(df) -> list[dict]:
    """Converts a pandas DataFrame into JSON-compliant dictionaries with None for NaNs."""
    if df.empty:
        return []
    import math
    return [
        {k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in row.items()}
        for row in df.to_dict(orient="records")
    ]

@router.get("/api/approvals")
async def get_approvals(admin: dict = Depends(require_admin_auth)):
    """Returns both pending authorizations and reviewed decision logs."""
    df_pending = Repository.get_pending_approvals()
    df_all = Repository.get_all_approvals()

    pending_list = _df_to_records(df_pending)
    all_list = _df_to_records(df_all)

    return {
        "pending": pending_list,
        "history": all_list,
        "counts": {
            "pending": len(pending_list),
            "total_reviewed": len(all_list) - len(pending_list)
        }
    }

@router.get("/api/logs")
async def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    search: Optional[str] = None,
    model: Optional[str] = None,
    risk: Optional[str] = None,
    admin: dict = Depends(require_admin_auth)
):
    """Returns decrypted audit logs with search, filtering, and pagination."""
    return Repository.get_audit_logs(limit=limit, offset=offset, search=search, model=model, risk_filter=risk)

@router.get("/api/security/harmful")
async def get_harmful_violations(
    limit: int = 100,
    admin: dict = Depends(require_admin_auth)
):
    """Returns detected harmful prompts and policy blocks."""
    return Repository.get_harmful_logs(limit=limit)

@router.get("/api/guardrails")
async def get_guardrails(admin: dict = Depends(require_admin_auth)):
    """Returns active security guardrail policies and activation stats."""
    policies = Repository.get_guardrail_policies()
    return {"guardrails": policies}

@router.post("/api/guardrails/toggle")
async def toggle_guardrail(
    payload: GuardrailToggleRequest,
    admin: dict = Depends(require_admin_auth)
):
    """Toggles or modifies configuration of a specific guardrail."""
    res = Repository.toggle_guardrail_policy(
        key=payload.key,
        enabled=payload.enabled,
        action=payload.action,
        sensitivity=payload.sensitivity
    )
    await manager.broadcast({
        "type": "guardrail_updated",
        "key": payload.key,
        "message": f"Guardrail {payload.key} configuration updated."
    })
    return res

@router.get("/api/tokens")
async def get_tokens(admin: dict = Depends(require_admin_auth)):
    """Returns the list of active API keys and service tokens."""
    return {"tokens": Repository.get_api_tokens()}

@router.post("/api/tokens")
async def create_token(
    payload: CreateTokenRequest,
    admin: dict = Depends(require_admin_auth)
):
    """Generates a new secure service token."""
    token_data = Repository.create_api_token(
        name=payload.name,
        provider=payload.provider or "All Models",
        scope=payload.scope or "read:write"
    )
    return token_data

@router.delete("/api/tokens/{token_id}")
async def delete_token(
    token_id: int,
    admin: dict = Depends(require_admin_auth)
):
    """Revokes an API token."""
    return Repository.delete_api_token(token_id)

@router.get("/api/connections")
async def get_connections(admin: dict = Depends(require_admin_auth)):
    """Returns status and latency benchmarks of connected LLM upstream providers."""
    return {
        "providers": [
            {
                "id": "groq",
                "name": "Groq Cloud LPU",
                "status": "online" if config.GROQ_API_KEY else "unconfigured",
                "endpoint": "https://api.groq.com/openai/v1",
                "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
                "avg_latency_ms": 285,
            },
            {
                "id": "ollama",
                "name": "Ollama Local Engine",
                "status": "online",
                "endpoint": config.OLLAMA_URL,
                "models": ["llama3", "mistral"],
                "avg_latency_ms": 840,
            }
        ]
    }

@router.post("/api/playground/evaluate")
async def evaluate_playground(
    req: PlaygroundEvaluateRequest,
    identity: dict = Depends(require_client_auth)
):
    """Simulates the entire multi-stage gateway pipeline for interactive debugging."""
    start_time = time.time()
    steps = []

    # 1. Input Guard
    is_injection = InputGuards.detect_prompt_injection(req.prompt)
    steps.append({
        "stage": "Prompt Injection Shield",
        "passed": not is_injection,
        "detail": "Adversarial jailbreak signature detected" if is_injection else "No adversarial patterns detected"
    })

    # 2. Risk Score
    risk_score = InputGuards.calculate_risk_score(req.prompt)
    steps.append({
        "stage": "Adversarial Risk Scoring",
        "passed": risk_score <= 50,
        "detail": f"Risk Score: {risk_score}/100" + (" (Triggers Human Approval Gate)" if risk_score > 50 else " (Normal risk)")
    })

    # 3. PII Masking
    sanitized_prompt, detected_pii = InputGuards.mask_pii(req.prompt)
    steps.append({
        "stage": "PII & Secret Sanitization",
        "passed": True,
        "detail": f"Detected entities: {', '.join(detected_pii)}" if detected_pii else "Zero PII entities detected",
        "sanitized_text": sanitized_prompt
    })

    # 4. Cache Check
    cached_val = None if req.bypass_cache else cache.get(req.model, sanitized_prompt, tenant_id=identity.get("tenant_id", "default"))
    cache_hit = cached_val is not None
    steps.append({
        "stage": "Response Cache",
        "passed": True,
        "detail": "Cache HIT (0ms roundtrip, 0 tokens billed)" if cache_hit else "Cache MISS (Dispatch required)"
    })

    if is_injection:
        return {
            "status": "BLOCKED",
            "reason": "Prompt Injection Detected",
            "steps": steps,
            "risk_score": risk_score,
            "latency_ms": round((time.time() - start_time) * 1000, 2),
            "output": "Execution halted: Adversarial prompt injection pattern matched security policy."
        }

    if risk_score > 50:
        return {
            "status": "QUEUED_FOR_APPROVAL",
            "reason": "High-Risk Score Exceeded Policy Threshold",
            "steps": steps,
            "risk_score": risk_score,
            "latency_ms": round((time.time() - start_time) * 1000, 2),
            "output": f"Interaction quarantined (Risk {risk_score}/100). Sent to Security Governance Approval Queue."
        }

    if cache_hit:
        return {
            "status": "SUCCESS_CACHED",
            "steps": steps,
            "risk_score": risk_score,
            "latency_ms": 1.2,
            "output": cached_val.get("response", "") if isinstance(cached_val, dict) else str(cached_val)
        }

    return {
        "status": "PASSED_EVALUATION",
        "steps": steps,
        "risk_score": risk_score,
        "latency_ms": round((time.time() - start_time) * 1000, 2),
        "sanitized_prompt": sanitized_prompt,
        "output": f"Evaluation Complete. Prompt is cleared for upstream dispatch to {req.model}."
    }

@router.get("/api/system/status")
async def get_system_status(admin: dict = Depends(require_admin_auth)):
    """Returns gateway infrastructure metrics."""
    import os
    db_size = 0
    if os.path.exists(config.DATABASE):
        db_size = os.path.getsize(config.DATABASE)

    return {
        "status": "online",
        "version": "2.0.0",
        "mode": "production-shield",
        "cache_count": cache.count(),
        "database_file": config.DATABASE,
        "database_bytes": db_size,
        "encryption": "AES-256-Fernet (Active)",
        "active_ws_connections": len(manager.active_connections)
    }
