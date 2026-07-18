from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, computed_field


class DocumentRead(BaseModel):
    id: str
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    status: str
    error_message: str | None
    chunk_count: int
    page_count: int | None = None
    embedding_status: str
    processed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def file_type(self) -> str:
        return Path(self.original_filename).suffix.lower().lstrip(".") or self.content_type

    @computed_field
    @property
    def processing_progress(self) -> int:
        progress_by_status = {
            "uploaded": 10,
            "queued": 25,
            "processing": 60,
            "ready": 100,
            "processed": 100,
            "failed": 100,
        }
        return progress_by_status.get(self.status, 0)


class DocumentList(BaseModel):
    documents: list[DocumentRead] = Field(default_factory=list)


class DocumentUploadResponse(BaseModel):
    document: DocumentRead
    duplicate: bool = False
    message: str


class DocumentSearchResult(BaseModel):
    page_number: int | None = None
    excerpt: str
    highlighted_excerpt: str | None = None


class DocumentSearchResponse(BaseModel):
    query: str
    results: list[DocumentSearchResult] = Field(default_factory=list)


class DocumentPreviewSection(BaseModel):
    page_number: int | None = None
    text: str


class DocumentPreviewChunk(BaseModel):
    page_number: int | None = None
    chunk_number: int
    text: str


class DocumentPreviewResponse(BaseModel):
    document: DocumentRead
    sections: list[DocumentPreviewSection] = Field(default_factory=list)
    chunks: list[DocumentPreviewChunk] = Field(default_factory=list)


class DocumentInsightSource(BaseModel):
    page_number: int | None = None
    chunk_number: int
    excerpt: str


class DocumentInsightSection(BaseModel):
    title: str
    description: str


class DocumentInsightEntity(BaseModel):
    name: str
    type: str


class DocumentInsightResponse(BaseModel):
    id: str
    document_id: str
    summary_length: str
    document_type: str
    status: str
    overview: str
    summary: str
    key_points: list[str] = Field(default_factory=list)
    main_sections: list[DocumentInsightSection] = Field(default_factory=list)
    key_entities: list[DocumentInsightEntity] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    sources: list[DocumentInsightSource] = Field(default_factory=list)
    notice: str | None = None
    llm_configured: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
