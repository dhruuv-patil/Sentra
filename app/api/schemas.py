from pydantic import BaseModel
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    user: Optional[str] = "default_user"

class ApprovalAction(BaseModel):
    request_id: str
