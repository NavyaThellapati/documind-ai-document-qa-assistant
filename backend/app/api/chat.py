import asyncio
import json
import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi import Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import rate_limiter
from app.models import Conversation, Document, Message, Source, User
from app.schemas.chat import AskRequest, AskResponse, ConversationCreate, ConversationRead, ConversationSummary, ConversationUpdate, SourceRead
from app.services.llm import UNSUPPORTED_ANSWER, get_llm_service
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


def highlight_excerpt(text: str, question: str) -> str:
    highlighted = text[:500]
    terms = sorted({term for term in re.findall(r"[A-Za-z0-9]+", question) if len(term) > 3}, key=len, reverse=True)
    for term in terms[:8]:
        highlighted = re.sub(f"({re.escape(term)})", r"**\1**", highlighted, flags=re.IGNORECASE)
    return highlighted


def confidence_from_sources(sources: list[Source]) -> float | None:
    scores = [source.relevance_score for source in sources if source.relevance_score is not None]
    if not scores:
        return None
    return round(sum(scores[:3]) / min(len(scores), 3), 4)


async def answer_and_persist(payload: AskRequest, db: Session, current_user: User) -> AskResponse:
    conversation = owned_conversation(db, current_user, payload.conversation_id) if payload.conversation_id else Conversation(user_id=current_user.id, title=payload.question[:80])
    if not payload.conversation_id:
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    settings = get_settings()
    query = db.query(Document).filter(Document.user_id == current_user.id, Document.status.in_(["ready", "processed"]))
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
    if answer != UNSUPPORTED_ANSWER:
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
    db.flush()
    confidence = confidence_from_sources(source_models)
    db.commit()
    for source in source_models:
        db.refresh(source)
    return AskResponse(
        conversation_id=conversation.id,
        message_id=message.id,
        answer=answer,
        sources=[
            SourceRead(
                id=source.id,
                document_id=source.document_id,
                document_name=source.document_name,
                page_number=source.page_number,
                chunk_number=source.chunk_number,
                excerpt=source.excerpt,
                relevance_score=source.relevance_score,
                highlighted_excerpt=highlight_excerpt(source.excerpt, payload.question),
            )
            for source in source_models
        ],
        confidence_score=confidence,
    )


@router.post("/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conversation = Conversation(user_id=current_user.id, title=payload.title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Conversation, func.count(Message.id).label("message_count"))
        .outerjoin(Message)
        .filter(Conversation.user_id == current_user.id)
    )
    if search:
        query = query.filter(Conversation.title.ilike(f"%{search}%"))
    rows = (
        query
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
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
    return await answer_and_persist(payload, db, current_user)


@router.post("/ask/stream")
async def ask_question_stream(payload: AskRequest, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    settings = get_settings()
    rate_limiter.check(request, "chat", settings.chat_rate_limit_per_minute)
    result = await answer_and_persist(payload, db, current_user)

    async def stream_events():
        for token in re.findall(r"\S+\s*", result.answer):
            if await request.is_disconnected():
                return
            yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
            await asyncio.sleep(0)
        if await request.is_disconnected():
            return
        yield f"event: done\ndata: {result.model_dump_json()}\n\n"

    return StreamingResponse(stream_events(), media_type="text/event-stream")
