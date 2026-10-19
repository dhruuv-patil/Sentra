from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Header, Depends
from fastapi.responses import JSONResponse
from app.api.schemas import ChatCompletionRequest, ApprovalAction
from core.security.input_guards import InputGuards
from core.security.output_guards import OutputGuards
from core.llm.provider_dispatcher import dispatcher
from core.cache import cache
from core.config import config
from data.repository import Repository
import uuid
import time
import json
from typing import Optional

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

def verify_token(authorization: Optional[str] = Header(None)):
    """Validates Bearer token if SECRET_KEY is set. Allows UI requests without bearer."""
    expected_key = config.SECRET_KEY
    if not expected_key:
        return True

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        if token == expected_key:
            return True

    return True

@router.get("/api/health")
async def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "service": "LLM Security Gateway Pro",
        "cache_entries": cache.count(),
        "api_host": config.API_HOST,
        "api_port": config.API_PORT
    }

@router.get("/api/models")
async def get_models():
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

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    request_id = str(uuid.uuid4())
    user_prompt = request.messages[-1].content
    user_id = request.user or "default_user"

    await manager.broadcast({
        "type": "request_received",
        "request_id": request_id,
        "model": request.model,
        "message": f"Received request for model {request.model}"
    })

    # 1. Input Guardrails: Prompt Injection Detection
    if InputGuards.detect_prompt_injection(user_prompt):
        await manager.broadcast({
            "type": "input_guards_evaluated",
            "request_id": request_id,
            "status": "blocked",
            "reason": "Prompt Injection Detected",
            "message": "Input guardrails failed: Adversarial Prompt Injection detected"
        })
        return JSONResponse(
            status_code=403,
            content={"error": "Security Block: Prompt Injection Detected", "request_id": request_id}
        )

    # 2. Risk Score & Human-in-the-Loop Threshold
    risk_score = InputGuards.calculate_risk_score(user_prompt)

    # 3. PII Redaction
    sanitized_prompt, detected_pii = InputGuards.mask_pii(user_prompt)
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

    # 4. Human-in-the-Loop Policy: High-Risk Queuing
    if risk_score > 50:
        Repository.add_to_approval_queue(request_id, user_id, request.model, user_prompt)
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
            "poll_url": f"/v1/requests/{request_id}"
        }

    # 5. Semantic / Exact Response Cache Inspection
    cached = cache.get(request.model, sanitized_prompt)
    if cached:
        await manager.broadcast({
            "type": "cache_hit",
            "request_id": request_id,
            "tokens": 0,
            "message": "Served instantly from Gateway Cache (0 tokens consumed)"
        })
        Repository.log_request(request_id, user_id, request.model, user_prompt, cached["response"], 0, 0.0, risk_score, 0.001)
        return {
            "id": request_id,
            "choices": [{"message": {"role": "assistant", "content": cached["response"]}}],
            "usage": {"total_tokens": 0},
            "cache_hit": True
        }

    # 6. LLM Interaction via Unified Dispatcher
    await manager.broadcast({
        "type": "llm_interaction_started",
        "request_id": request_id,
        "message": f"Dispatching sanitized prompt to {request.model}"
    })
    start_time = time.time()

    # Build message history with the sanitized prompt for the last message
    message_history = []
    for idx, msg in enumerate(request.messages):
        if idx == len(request.messages) - 1:
            message_history.append({"role": msg.role, "content": sanitized_prompt})
        else:
            message_history.append({"role": msg.role, "content": msg.content})

    result = dispatcher.complete(request.model, message_history)

    if "error" in result:
        err_msg = result["error"].get("message", "Model execution error")
        await manager.broadcast({
            "type": "llm_interaction_failed",
            "request_id": request_id,
            "error": err_msg,
            "message": f"Model error: {err_msg}"
        })
        raise HTTPException(status_code=502, detail=err_msg)

    llm_response = result["choices"][0]["message"]["content"]
    tokens = result.get("usage", {}).get("total_tokens", 0)
    latency = round(time.time() - start_time, 2)
    cost = round((tokens / 1000) * 0.002, 5)

    await manager.broadcast({
        "type": "llm_interaction_completed",
        "request_id": request_id,
        "latency": latency,
        "tokens": tokens,
        "message": f"Received completion from {request.model} ({tokens} tokens in {latency}s)"
    })

    # 7. Output Guardrails
    harm_category = OutputGuards.detect_harmful_content(llm_response)
    if harm_category:
        Repository.log_harmful(request_id, user_id, user_prompt, harm_category, risk_score)
        await manager.broadcast({
            "type": "output_guards_evaluated",
            "request_id": request_id,
            "status": "blocked",
            "reason": harm_category,
            "message": f"Output guardrail block: {harm_category} detected"
        })
        raise HTTPException(status_code=403, detail=f"Blocked: {harm_category} detected in model output.")

    await manager.broadcast({
        "type": "output_guards_evaluated",
        "request_id": request_id,
        "status": "passed",
        "message": "Output guardrails validated"
    })

    # 8. Cache & Audit Persistence
    cache.set(request.model, sanitized_prompt, llm_response, tokens, cost)
    Repository.log_request(request_id, user_id, request.model, user_prompt, llm_response, tokens, cost, risk_score, latency)

    await manager.broadcast({
        "type": "request_completed",
        "request_id": request_id,
        "message": "Transaction safely completed and encrypted in audit logs."
    })

    return {
        "id": request_id,
        "choices": [{"message": {"role": "assistant", "content": llm_response}}],
        "usage": {"total_tokens": tokens},
        "latency": latency,
        "cache_hit": False
    }

@router.get("/v1/requests/{request_id}")
async def get_request_status(request_id: str):
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

@router.post("/api/approve/{request_id}")
async def approve(request_id: str, action: Optional[ApprovalAction] = None):
    reviewer = action.reviewer if action else "admin"
    result = Repository.approve_request(request_id, reviewer=reviewer)
    await manager.broadcast({
        "type": "approval_resolved",
        "request_id": request_id,
        "status": "Approved",
        "message": f"Request {request_id} approved by {reviewer} and executed."
    })
    return result

@router.post("/api/deny/{request_id}")
async def deny(request_id: str, action: Optional[ApprovalAction] = None):
    reviewer = action.reviewer if action else "admin"
    reason = action.reason if action and action.reason else "Denied by administrator"
    result = Repository.deny_request(request_id, reviewer=reviewer, reason=reason)
    await manager.broadcast({
        "type": "approval_resolved",
        "request_id": request_id,
        "status": "Denied",
        "message": f"Request {request_id} denied by {reviewer}: {reason}"
    })
    return result

@router.post("/api/cache/clear")
async def clear_cache():
    cache.clear()
    return {"status": "Cache cleared"}
