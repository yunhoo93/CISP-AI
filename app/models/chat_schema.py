# app/models/chat_schema.py

from pydantic import BaseModel, Field
from typing import List, Optional


class ChatRequest(BaseModel):
    role: str = Field(..., description="user|assistant|system")
    message: str


class UsedContext(BaseModel):
    analysis_ids: List[str] = Field(default_factory=list)
    type: Optional[str] = None


class ChatResponse(BaseModel):
    message: str
    used_context: UsedContext