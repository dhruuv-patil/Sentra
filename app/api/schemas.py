from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str
    content: str

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

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: List[ChatMessage]) -> List[ChatMessage]:
        if not v or not any(m.content.strip() for m in v):
            raise ValueError("Messages list cannot be empty or contain only blank text.")
        return v

class ApprovalAction(BaseModel):
    request_id: Optional[str] = None
    reviewer: Optional[str] = "admin"
    reason: Optional[str] = None
