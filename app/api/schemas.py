from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any

class ChatMessage(BaseModel):
    role: str
    content: str = Field(..., max_length=65536)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid_roles = {"user", "assistant", "system"}
        if v.lower() not in valid_roles:
            return "user"
        return v.lower()

class ChatCompletionRequest(BaseModel):
    model: str = "groq/llama-3.3-70b-versatile"
    messages: List[ChatMessage] = Field(..., min_length=1)
    user: Optional[str] = "default_user"
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0, le=32768)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    stream: Optional[bool] = False

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: List[ChatMessage]) -> List[ChatMessage]:
        if not v or not any(m.content.strip() for m in v):
            raise ValueError("Messages list cannot be empty or contain only blank text.")
        total_len = sum(len(m.content) for m in v)
        if total_len > 131072: # 128 KB
            raise ValueError(f"Total message payload exceeds maximum limit of 131,072 characters (got {total_len}).")
        return v

    def get_parameters(self) -> Dict[str, Any]:
        params = {}
        if self.temperature is not None:
            params["temperature"] = self.temperature
        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens
        if self.top_p is not None:
            params["top_p"] = self.top_p
        return params

class ApprovalAction(BaseModel):
    request_id: Optional[str] = None
    reviewer: Optional[str] = "admin"
    reason: Optional[str] = None

class CreateTokenRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider: Optional[str] = "All Models"
    scope: Optional[str] = "read:write"

class GuardrailToggleRequest(BaseModel):
    key: str
    enabled: Optional[bool] = None
    action: Optional[str] = None
    sensitivity: Optional[float] = Field(default=None, ge=0.0, le=1.0)

class PlaygroundEvaluateRequest(BaseModel):
    model: str = "groq/llama-3.3-70b-versatile"
    prompt: str = Field(..., max_length=65536)
    bypass_cache: bool = False
