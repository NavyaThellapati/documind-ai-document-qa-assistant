from pathlib import Path
import re

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.config import get_settings
from app.models import Document, User
from app.schemas.documents import DocumentInsightResponse, DocumentList, DocumentPreviewChunk, DocumentPreviewResponse, DocumentPreviewSection, DocumentRead, DocumentSearchResponse, DocumentSearchResult, DocumentUploadResponse
from app.services.documents import delete_document as delete_document_service
from app.services.documents import process_document, process_document_by_id, save_upload
from app.services.document_intelligence import get_or_create_document_insight
from app.services.text_processing import extract_text_sections, search_sections, split_sections
from app.utils.files import ensure_within_directory

router = APIRouter(prefix="/documents", tags=["documents"])


def highlight_terms(text: str, query: str) -> str:
    highlighted = text
    terms = sorted({term for term in re.findall(r"[A-Za-z0-9]+", query) if len(term) > 2}, key=len, reverse=True)
    for term in terms[:8]:
        highlighted = re.sub(f"({re.escape(term)})", r"**\1**", highlighted, flags=re.IGNORECASE)
    return highlighted


def get_owned_document(db: Session, user: User, document_id: str) -> Document:
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == user.id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return document


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document, duplicate = await save_upload(db, current_user, file)
    if not duplicate and document.status != "processing":
        background_tasks.add_task(process_document_by_id, document.id)
        document.status = "queued"
        document.embedding_status = "queued"
        db.commit()
        db.refresh(document)
    message = "Document already exists and was not processed again." if duplicate else "Document uploaded and queued for processing."
    return DocumentUploadResponse(document=document, duplicate=duplicate, message=message)


@router.get("", response_model=DocumentList)
def list_documents(
    search: str | None = None,
    status_filter: str | None = None,
    sort_by: str = Query(default="created_at", pattern="^(created_at|updated_at|original_filename|file_size|status)$"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Document).filter(Document.user_id == current_user.id)
    if search:
        query = query.filter(Document.original_filename.ilike(f"%{search}%"))
    if status_filter:
        if status_filter == "processed":
            status_filter = "ready"
        query = query.filter(Document.status == status_filter)
    sort_column = getattr(Document, sort_by)
    if sort_dir == "desc":
        sort_column = sort_column.desc()
    return DocumentList(documents=query.order_by(sort_column).offset(offset).limit(limit).all())


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_owned_document(db, current_user, document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document = get_owned_document(db, current_user, document_id)
    delete_document_service(db, current_user, document)


@router.post("/{document_id}/reprocess", response_model=DocumentRead)
def reprocess_document(document_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document = get_owned_document(db, current_user, document_id)
    return process_document(db, document)


@router.post("/{document_id}/reprocess/background", response_model=DocumentRead)
def reprocess_document_background(document_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document = get_owned_document(db, current_user, document_id)
    if document.status == "processing":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document is already processing.")
    document.status = "queued"
    document.embedding_status = "queued"
    document.error_message = None
    db.commit()
    db.refresh(document)
    background_tasks.add_task(process_document_by_id, document.id)
    return document


@router.get("/{document_id}/download")
def download_document(document_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document = get_owned_document(db, current_user, document_id)
    path = ensure_within_directory(Path(get_settings().upload_dir) / current_user.id, Path(document.file_path))
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file was not found.")
    return FileResponse(path, filename=document.original_filename, media_type=document.content_type)


@router.get("/{document_id}/search", response_model=DocumentSearchResponse)
def search_document(document_id: str, query: str = Query(min_length=2, max_length=200), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document = get_owned_document(db, current_user, document_id)
    sections = extract_text_sections(Path(document.file_path), Path(document.original_filename).suffix.lower())
    results = [
        DocumentSearchResult(page_number=page, excerpt=excerpt, highlighted_excerpt=highlight_terms(excerpt, query))
        for page, excerpt in search_sections(sections, query)
    ]
    return DocumentSearchResponse(query=query, results=results)


@router.get("/{document_id}/preview", response_model=DocumentPreviewResponse)
def preview_document(document_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document = get_owned_document(db, current_user, document_id)
    sections = extract_text_sections(Path(document.file_path), Path(document.original_filename).suffix.lower())
    settings = get_settings()
    chunks = split_sections(sections, settings.chunk_size, settings.chunk_overlap)
    return DocumentPreviewResponse(
        document=document,
        sections=[DocumentPreviewSection(page_number=section.page_number, text=section.text) for section in sections],
        chunks=[DocumentPreviewChunk(page_number=chunk.page_number, chunk_number=chunk.chunk_number, text=chunk.text) for chunk in chunks],
    )


@router.get("/{document_id}/insight", response_model=DocumentInsightResponse)
def get_document_insight(
    document_id: str,
    summary_length: str = Query(default="standard", pattern="^(brief|standard|detailed)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_owned_document(db, current_user, document_id)
    try:
        return get_or_create_document_insight(db, document, summary_length=summary_length)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{document_id}/explain", response_model=DocumentInsightResponse)
def explain_document(
    document_id: str,
    summary_length: str = Query(default="standard", pattern="^(brief|standard|detailed)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_owned_document(db, current_user, document_id)
    try:
        return get_or_create_document_insight(db, document, force=True, summary_length=summary_length)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
