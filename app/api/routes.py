from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from app.api.schemas import ChatCompletionRequest
from core.security.input_guards import InputGuards
from core.security.output_guards import OutputGuards
from core.llm.groq_client import GroqClient
from data.repository import Repository
import uuid
import time
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass

manager = ConnectionManager()

router = APIRouter()
groq_client = GroqClient()

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    request_id = str(uuid.uuid4())
    user_prompt = request.messages[-1].content
    user_id = request.user
    
    await manager.broadcast({
        "type": "request_received",
        "request_id": request_id,
        "model": request.model,
        "message": f"Received request for model {request.model}"
    })
    
    # 1. Input Guardrails
    is_injection = InputGuards.detect_prompt_injection(user_prompt)
    if is_injection:
        await manager.broadcast({
            "type": "input_guards_evaluated",
            "request_id": request_id,
            "status": "blocked",
            "reason": "Prompt Injection Detected",
            "message": "Input guardrails failed: Prompt Injection"
        })
        return {"error": "Security Block: Prompt Injection Detected", "request_id": request_id}, 403
        
    risk_score = InputGuards.calculate_risk_score(user_prompt)
    await manager.broadcast({
        "type": "input_guards_evaluated",
        "request_id": request_id,
        "status": "passed",
        "risk_score": risk_score,
        "message": f"Input guardrails passed with risk score: {risk_score}"
    })
    
    # 2. Policy: Human-in-the-loop for high risk
    if risk_score > 50:
        Repository.add_to_approval_queue(request_id, user_id, request.model, user_prompt)
        await manager.broadcast({
            "type": "human_in_the_loop",
            "request_id": request_id,
            "status": "queued",
            "message": "High risk detected. Queued for admin approval."
        })
        return {"status": "Pending Approval", "request_id": request_id, "message": "High-risk request queued for admin review."}

    # 3. LLM Interaction
    try:
        provider, model_name = request.model.split("/", 1) if "/" in request.model else ("groq", request.model)
    except Exception:
        provider, model_name = "groq", request.model

    await manager.broadcast({
        "type": "llm_interaction_started",
        "request_id": request_id,
        "message": f"Forwarding request to {model_name} via {provider}"
    })
    start_time = time.time()
    
    # Convert Pydantic message objects to a list of dicts for the payload
    message_history = [{"role": msg.role, "content": msg.content} for msg in request.messages]
    
    try:
        response_data = groq_client.complete(model_name, message_history)
        if 'error' in response_data:
            raise Exception(response_data['error'].get('message', 'Unknown Groq API Error'))
        llm_response = response_data['choices'][0]['message']['content']
        tokens = response_data.get('usage', {}).get('total_tokens', 0)
    except Exception as e:
        await manager.broadcast({
            "type": "llm_interaction_failed",
            "request_id": request_id,
            "error": str(e),
            "message": f"LLM interaction failed: {str(e)}"
        })
        raise HTTPException(status_code=500, detail=str(e))
    
    latency = round(time.time() - start_time, 2)
    cost = (tokens / 1000) * 0.002 # Semi-static cost estimation
    
    latency = round(time.time() - start_time, 2)
    cost = (tokens / 1000) * 0.002 # Semi-static cost estimation
    
    await manager.broadcast({
        "type": "llm_interaction_completed",
        "request_id": request_id,
        "latency": latency,
        "tokens": tokens,
        "message": f"Received response from {request.model} in {latency}s"
    })
    
    # 4. Output Guardrails
    harm_category = OutputGuards.detect_harmful_content(llm_response)
    if harm_category:
        Repository.log_harmful(request_id, user_id, user_prompt, harm_category, risk_score)
        await manager.broadcast({
            "type": "output_guards_evaluated",
            "request_id": request_id,
            "status": "blocked",
            "reason": harm_category,
            "message": f"Output guardrails failed: {harm_category} detected"
        })
        raise HTTPException(status_code=403, detail=f"Blocked: {harm_category} detected in output.")

    await manager.broadcast({
        "type": "output_guards_evaluated",
        "request_id": request_id,
        "status": "passed",
        "message": "Output guardrails passed"
    })

    # 5. Success Logging
    Repository.log_request(request_id, user_id, request.model, user_prompt, llm_response, tokens, cost, risk_score, latency)
    
    await manager.broadcast({
        "type": "request_completed",
        "request_id": request_id,
        "message": "Request completed successfully and logged."
    })
    
    return {
        "id": request_id,
        "choices": [{"message": {"role": "assistant", "content": llm_response}}],
        "usage": {"total_tokens": tokens}
    }

@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect messages from client, just keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.post("/api/approve/{request_id}")
async def approve(request_id: str):
    Repository.approve_request(request_id)
    return {"status": "approved"}

@router.post("/api/deny/{request_id}")
async def deny(request_id: str):
    Repository.deny_request(request_id)
    return {"status": "denied"}
