"""Chatbot and AI Context Schemas."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    title: str
    source_name: str
    source_type: str  # verified_crop_profile, traditional_rag_knowledge, live_sensor_history, weather_forecast, market_price
    content_excerpt: str
    relevance_score: Optional[float] = None
    url: Optional[str] = None


class ChatMessageCreate(BaseModel):
    message: str = Field(min_length=1)
    batch_id: Optional[str] = None
    language: str = "en"


class ChatMessageOut(BaseModel):
    message_id: str
    conversation_id: str
    role: str  # user, assistant, system
    content: str
    sources: list[SourceReference] = Field(default_factory=list)
    suggested_followups: list[str] = Field(default_factory=list)
    batch_context_used: Optional[dict[str, Any]] = None
    pending_action: Optional[dict[str, Any]] = None
    action_executed: Optional[dict[str, Any]] = None
    timestamp: str


class ConversationCreate(BaseModel):
    title: Optional[str] = "Storage Advisory Chat"
    batch_id: Optional[str] = None
    language: str = "en"


class ConversationOut(BaseModel):
    conversation_id: str
    user_id: str
    batch_id: Optional[str] = None
    title: str
    language: str
    created_at: str
    updated_at: str
    message_count: int = 0
