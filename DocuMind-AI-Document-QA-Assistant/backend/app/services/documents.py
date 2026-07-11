from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Document, User
from app.services.text_processing import extract_text_sections, split_sections
from app.services.vector_store import get_vector_store
from app.utils.files import sanitize_filename, sha256_bytes, validate_extension


async def save_and_process_upload(db: Session, user: User, file: UploadFile) -> tuple[Document, bool]:
    settings = get_settings()
    try:
        suffix = validate_extension(file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"File exceeds {settings.max_upload_size_mb} MB limit.")
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    content_hash = sha256_bytes(data)
    existing = db.query(Document).filter(Document.user_id == user.id, Document.content_hash == content_hash).first()
    if existing:
        return existing, True

    upload_root = Path(settings.upload_dir) / user.id
    upload_root.mkdir(parents=True, exist_ok=True)
    stored_name = sanitize_filename(file.filename or "document")
    stored_path = upload_root / stored_name
    stored_path.write_bytes(data)

    document = Document(
        user_id=user.id,
        filename=stored_name,
        original_filename=file.filename or stored_name,
        content_type=file.content_type or "application/octet-stream",
        file_path=str(stored_path),
        file_size=len(data),
        content_hash=content_hash,
        status="processing",
    )
    db.add(document)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(Document).filter(Document.user_id == user.id, Document.content_hash == content_hash).first()
        if existing:
            return existing, True
        raise
    db.refresh(document)
    process_document(db, document)
    return document, False


def process_document(db: Session, document: Document) -> Document:
    settings = get_settings()
    document.status = "processing"
    document.error_message = None
    db.commit()
    try:
        sections = extract_text_sections(Path(document.file_path), Path(document.original_filename).suffix.lower())
        chunks = split_sections(sections, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise ValueError("No readable text was found in this document.")
        vector_store = get_vector_store()
        vector_store.delete_document(document.user_id, document.id)
        vector_store.upsert_document_chunks(document.user_id, document.id, document.original_filename, chunks)
        document.status = "processed"
        document.chunk_count = len(chunks)
        document.error_message = None
    except Exception as exc:
        document.status = "failed"
        document.error_message = str(exc)
        document.chunk_count = 0
    db.commit()
    db.refresh(document)
    return document


def delete_document(db: Session, user: User, document: Document) -> None:
    get_vector_store().delete_document(user.id, document.id)
    try:
        Path(document.file_path).unlink(missing_ok=True)
    finally:
        db.delete(document)
        db.commit()
