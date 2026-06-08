"""文档 ORM 模型。"""
from datetime import datetime
from enum import StrEnum

from sqlalchemy import String, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class DocStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class Document(Base):
    __tablename__ = "documents"

    doc_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default=DocStatus.PENDING)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    new_chunks: Mapped[int] = mapped_column(Integer, default=0)
    skipped_chunks: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
