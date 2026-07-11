from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import rate_limiter
from app.models import Conversation, Document, Message, Source, User
from app.schemas.chat import AskRequest, AskResponse, ConversationCreate, ConversationRead, ConversationSummary, ConversationUpdate, SourceRead
from app.services.llm import get_llm_service
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/chat", tags=["chat"])


def owned_conversation(db: Session, user: User, conversation_id: str) -> Conversation:
    conversation = (
        db.query(Conversation)
        .options(selectinload(Conversation.messages).selectinload(Message.sources))
        .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return conversation


@router.post("/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conversation = Conversation(user_id=current_user.id, title=payload.title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(Conversation, func.count(Message.id).label("message_count"))
        .outerjoin(Message)
        .filter(Conversation.user_id == current_user.id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [
        ConversationSummary(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=message_count,
        )
        for conversation, message_count in rows
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationRead)
def get_conversation(conversation_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return owned_conversation(db, current_user, conversation_id)


@router.patch("/conversations/{conversation_id}", response_model=ConversationRead)
def rename_conversation(conversation_id: str, payload: ConversationUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conversation = owned_conversation(db, current_user, conversation_id)
    conversation.title = payload.title
    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conversation = owned_conversation(db, current_user, conversation_id)
    db.delete(conversation)
    db.commit()


@router.post("/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    settings = get_settings()
    rate_limiter.check(request, "chat", settings.chat_rate_limit_per_minute)

    conversation = owned_conversation(db, current_user, payload.conversation_id) if payload.conversation_id else Conversation(user_id=current_user.id, title=payload.question[:80])
    if not payload.conversation_id:
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    query = db.query(Document).filter(Document.user_id == current_user.id, Document.status == "processed")
    if payload.document_ids:
        query = query.filter(Document.id.in_(payload.document_ids))
    documents = query.all()
    if payload.document_ids and len(documents) != len(set(payload.document_ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more documents were not found or are not processed.")
    if not documents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload and process at least one document before asking a question.")

    chunks = get_vector_store().search(current_user.id, payload.question, [doc.id for doc in documents], settings.retrieval_top_k)
    answer = await get_llm_service().answer(payload.question, chunks)
    message = Message(conversation_id=conversation.id, question=payload.question, answer=answer)
    db.add(message)
    db.flush()

    source_models: list[Source] = []
    for chunk in chunks:
        source = Source(
            message_id=message.id,
            document_id=chunk.document_id,
            document_name=chunk.document_name,
            page_number=chunk.page_number,
            chunk_number=chunk.chunk_number,
            excerpt=chunk.text[:500],
            relevance_score=chunk.relevance_score,
        )
        db.add(source)
        source_models.append(source)
    db.commit()
    db.refresh(message)
    return AskResponse(
        conversation_id=conversation.id,
        message_id=message.id,
        answer=answer,
        sources=[SourceRead.model_validate(source) for source in source_models],
    )
