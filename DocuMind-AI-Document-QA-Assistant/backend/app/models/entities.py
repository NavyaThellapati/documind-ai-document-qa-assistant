from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def uuid_str() -> str:
    return str(uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    documents: Mapped[list["Document"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("user_id", "content_hash", name="uq_documents_user_hash"),
        Index("ix_documents_user_status", "user_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="uploaded", index=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    owner: Mapped[User] = relationship(back_populates="documents")


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="New conversation", nullable=False)

    owner: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    sources: Mapped[list["Source"]] = relationship(back_populates="message", cascade="all, delete-orphan")
    feedback: Mapped["Feedback | None"] = relationship(back_populates="message", cascade="all, delete-orphan")


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True, nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    chunk_number: Mapped[int] = mapped_column(Integer, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    relevance_score: Mapped[float | None] = mapped_column()

    message: Mapped[Message] = relationship(back_populates="sources")


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedback"
    __table_args__ = (UniqueConstraint("message_id", name="uq_feedback_message"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    helpful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)

    message: Mapped[Message] = relationship(back_populates="feedback")
