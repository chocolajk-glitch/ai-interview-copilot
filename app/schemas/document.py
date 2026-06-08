
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.document import DocStatus


class DocumentUploadRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255, description="文件名")
    content_b64: str = Field(..., min_length=1, description="base64 编码的文件内容")


class DocumentUploadResponse(BaseModel):
    status: DocStatus
    doc_id: str
    message: str = ""


class DocumentStatusResponse(BaseModel):
    doc_id: str
    status: DocStatus
    filename: str
    chunk_count: int = 0
    new_chunks: int = 0
    skipped_chunks: int = 0
    error: str | None = None
    created_at: datetime


class DocumentListResponse(BaseModel):
    total: int
    documents: list[DocumentStatusResponse]
