from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Document, User
from app.schemas.documents import DocumentList, DocumentRead, DocumentUploadResponse
from app.services.documents import delete_document as delete_document_service
from app.services.documents import process_document, save_and_process_upload

router = APIRouter(prefix="/documents", tags=["documents"])


def get_owned_document(db: Session, user: User, document_id: str) -> Document:
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == user.id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return document


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document, duplicate = await save_and_process_upload(db, current_user, file)
    message = "Document already exists and was not processed again." if duplicate else "Document uploaded and processed."
    return DocumentUploadResponse(document=document, duplicate=duplicate, message=message)


@router.get("", response_model=DocumentList)
def list_documents(
    search: str | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Document).filter(Document.user_id == current_user.id)
    if search:
        query = query.filter(Document.original_filename.ilike(f"%{search}%"))
    if status_filter:
        query = query.filter(Document.status == status_filter)
    return DocumentList(documents=query.order_by(Document.created_at.desc()).all())


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
