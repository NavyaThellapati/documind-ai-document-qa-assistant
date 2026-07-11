from datetime import datetime
from pydantic import BaseModel, Field


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


class DocumentList(BaseModel):
    documents: list[DocumentRead] = Field(default_factory=list)


class DocumentUploadResponse(BaseModel):
    document: DocumentRead
    duplicate: bool = False
    message: str


class DocumentSearchResult(BaseModel):
    page_number: int | None = None
    excerpt: str


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
