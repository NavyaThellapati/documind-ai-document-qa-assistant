from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", max_length=255)


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class SourceRead(BaseModel):
    id: str | None = None
    document_id: str | None = None
    document_name: str
    page_number: int | None = None
    chunk_number: int
    excerpt: str
    relevance_score: float | None = None
    highlighted_excerpt: str | None = None

    model_config = {"from_attributes": True}


class MessageRead(BaseModel):
    id: str
    question: str
    answer: str
    sources: list[SourceRead] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationRead(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    conversation_id: str | None = None
    document_ids: list[str] = Field(default_factory=list, max_length=25)


class AskResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    sources: list[SourceRead]
    confidence_score: float | None = None


class DashboardSummary(BaseModel):
    total_documents: int
    ready_documents: int
    processed_documents: int
    processing_documents: int
    failed_documents: int
    total_chats: int
    questions_asked: int
    storage_used_bytes: int
    recent_documents: list[dict[str, Any]]
    recent_conversations: list[dict[str, Any]]
    ai_usage_summary: dict[str, Any]
