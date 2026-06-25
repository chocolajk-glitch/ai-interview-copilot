import base64
import hashlib
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from langchain_core.documents import Document
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document as DocumentModel, DocStatus, get_db
from app.rag.loaders import load_single_file
from app.rag.retrievers.vector_retriever import get_vector_store
from app.rag.splitters.text_splitter import split_docs

_UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "uploads"
_PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"
from app.schemas.document import (
    DocumentListResponse,
    DocumentStatusResponse,
    DocumentUploadRequest,
    DocumentUploadResponse,
)

router = APIRouter(prefix="/api/document", tags=["document"])


async def _index_document(doc_id: str, file_bytes: bytes, filename: str) -> None:
    """后台任务：切分文档并写入向量库 + BM25 索引。"""
    from app.models import async_session

    async with async_session() as session:
        result = await session.execute(
            select(DocumentModel).where(DocumentModel.doc_id == doc_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            return
        record.status = DocStatus.PROCESSING
        await session.commit()

        try:
            # 根据文件后缀选择加载器
            ext = Path(filename).suffix.lower()
            if ext in (".pdf", ".html", ".htm"):
                # PDF/HTML 需要写临时文件再加载
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False, encoding=None) as tmp:
                    tmp.write(file_bytes)
                    tmp_path = tmp.name
                docs = load_single_file(tmp_path, filename)
                Path(tmp_path).unlink(missing_ok=True)
            else:
                # Markdown / 纯文本直接解码
                docs = [Document(page_content=file_bytes.decode("utf-8"), metadata={"source": filename})]

            new_chunks = split_docs(docs, chunk_size=500, chunk_overlap=50)

            # 持久化 chunks 到 data/processed/
            import json
            _PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
            processed_path = _PROCESSED_DIR / f"{doc_id}_chunks.json"
            chunks_data = [
                {"content": c.page_content, "metadata": c.metadata}
                for c in new_chunks
            ]
            processed_path.write_text(json.dumps(chunks_data, ensure_ascii=False, indent=2), encoding="utf-8")

            vs = get_vector_store()
            all_data = vs._collection.get(include=["metadatas", "documents"])
            metadatas = all_data.get("metadatas") or []
            documents = all_data.get("documents") or []

            existing_ids: set[str] = set()
            existing_chunks: list[Document] = []
            for i, m in enumerate(metadatas):
                if m and m.get("chunk_id"):
                    existing_ids.add(m["chunk_id"])
                    if i < len(documents):
                        existing_chunks.append(Document(
                            page_content=documents[i],
                            metadata=m,
                        ))

            to_add = [c for c in new_chunks if c.metadata.get("chunk_id") not in existing_ids]
            skipped = len(new_chunks) - len(to_add)

            if to_add:
                sanitized = []
                for c in to_add:
                    clean_meta = {k: v for k, v in c.metadata.items() if v is not None}
                    sanitized.append(Document(page_content=c.page_content, metadata=clean_meta))
                vs.add_documents(sanitized)

            from app.graph.nodes import _get_hybrid_retriever
            hr = _get_hybrid_retriever()
            all_chunks = existing_chunks + to_add
            hr._bm25.index(all_chunks)

            record.chunk_count = len(new_chunks)
            record.new_chunks = len(to_add)
            record.skipped_chunks = skipped
            record.status = DocStatus.READY
            await session.commit()
        except Exception as e:
            record.status = DocStatus.FAILED
            record.error = str(e)[:200]
            await session.commit()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    req: DocumentUploadRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    file_bytes = base64.b64decode(req.content_b64)
    doc_sha = hashlib.sha256(file_bytes).hexdigest()

    # 检查是否已存在（按 sha256）
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.sha256 == doc_sha)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return DocumentUploadResponse(
            status=DocStatus.DUPLICATE,
            doc_id=existing.doc_id,
            message="文档已存在",
        )

    doc_id = uuid.uuid4().hex[:16]

    # 保存文件到 data/uploads/
    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    upload_path = _UPLOADS_DIR / f"{doc_id}_{req.filename}"
    upload_path.write_bytes(file_bytes)

    record = DocumentModel(
        doc_id=doc_id,
        sha256=doc_sha,
        filename=req.filename,
        status=DocStatus.PENDING,
    )
    db.add(record)
    await db.commit()

    background_tasks.add_task(_index_document, doc_id, file_bytes, req.filename)

    return DocumentUploadResponse(
        status=DocStatus.PENDING,
        doc_id=doc_id,
        message="已加入后台索引队列",
    )


@router.get("/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentStatusResponse:
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.doc_id == doc_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentStatusResponse(
        doc_id=record.doc_id,
        status=record.status,
        filename=record.filename,
        chunk_count=record.chunk_count,
        new_chunks=record.new_chunks,
        skipped_chunks=record.skipped_chunks,
        error=record.error,
        created_at=record.created_at,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """获取所有已上传文档列表。"""
    result = await db.execute(
        select(DocumentModel).order_by(DocumentModel.created_at.desc())
    )
    records = result.scalars().all()
    docs = [
        DocumentStatusResponse(
            doc_id=r.doc_id,
            status=r.status,
            filename=r.filename,
            chunk_count=r.chunk_count,
            new_chunks=r.new_chunks,
            skipped_chunks=r.skipped_chunks,
            error=r.error,
            created_at=r.created_at,
        )
        for r in records
    ]
    return DocumentListResponse(total=len(docs), documents=docs)


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """删除文档及其向量索引。"""
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.doc_id == doc_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")

    # 从 Chroma 中删除该文档的所有 chunks
    vs = get_vector_store()
    try:
        vs.delete(where={"source": record.filename})
    except Exception:
        pass

    # 从数据库删除
    await db.delete(record)
    await db.commit()
    return {"message": "文档已删除", "doc_id": doc_id}
