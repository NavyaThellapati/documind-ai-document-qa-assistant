from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models import Conversation, Document, Message, User
from app.schemas.chat import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    settings = get_settings()
    documents = db.query(Document).filter(Document.user_id == current_user.id)
    conversations = db.query(Conversation).filter(Conversation.user_id == current_user.id)
    question_count = (
        db.query(func.count(Message.id))
        .join(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .scalar()
        or 0
    )
    recent_documents = [
        {
            "id": doc.id,
            "name": doc.original_filename,
            "status": doc.status,
            "embedding_status": doc.embedding_status,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in documents.order_by(Document.created_at.desc()).limit(5).all()
    ]
    recent_conversations = [
        {
            "id": convo.id,
            "title": convo.title,
            "updated_at": convo.updated_at.isoformat() if convo.updated_at else None,
        }
        for convo in conversations.order_by(Conversation.updated_at.desc()).limit(5).all()
    ]
    ready_count = documents.filter(Document.status.in_(["ready", "processed"])).count()
    in_progress_count = documents.filter(Document.status.in_(["queued", "uploaded", "processing"])).count()
    return DashboardSummary(
        total_documents=documents.count(),
        ready_documents=ready_count,
        processed_documents=ready_count,
        processing_documents=in_progress_count,
        failed_documents=documents.filter(Document.status == "failed").count(),
        total_chats=conversations.count(),
        questions_asked=question_count,
        storage_used_bytes=documents.with_entities(func.coalesce(func.sum(Document.file_size), 0)).scalar() or 0,
        recent_documents=recent_documents,
        recent_conversations=recent_conversations,
        ai_usage_summary={"questions_asked": question_count, "retrieval_top_k": settings.retrieval_top_k, "llm_provider": settings.llm_provider},
    )
