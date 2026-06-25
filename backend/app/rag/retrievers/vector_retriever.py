
"""向量检索器：基于 Chroma 的相似度检索（lazy auto-build + 单例缓存）。"""
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from app.core.config import settings
from app.rag.embeddings.bge import get_embeddings

COLLECTION_NAME = "ai_interview_corpus"


def _corpus_dir() -> str:
    return str(Path(settings.CHROMA_PERSIST_DIR).resolve().parent / "corpus")


_vector_store: Chroma | None = None
_parent_store: dict[str, Document] | None = None


def _load_parent_store() -> dict[str, Document]:
    """从 data/processed/parents.json 加载 parent 索引（用于 child→parent 展开）。"""
    global _parent_store
    if _parent_store is not None:
        return _parent_store
    import json
    parents_path = (
        Path(settings.CHROMA_PERSIST_DIR).resolve().parent
        / "processed"
        / "parents.json"
    )
    _parent_store = {}
    if parents_path.exists():
        for item in json.loads(parents_path.read_text(encoding="utf-8")):
            meta = dict(item.get("metadata", {}))
            chunk_id = meta.get("chunk_id")
            if not chunk_id:
                continue
            _parent_store[chunk_id] = Document(
                page_content=item["content"], metadata=meta
            )
    return _parent_store


def reset_parent_store(parents: list[Document] | None = None) -> None:
    """设置 / 重置内存中的 parent 映射。parents=None 时清空。

    build_index / 测试场景使用：让向量检索器在不依赖 JSON 文件的情况下
    也能完成 child→parent 展开。
    """
    global _parent_store
    if parents is None:
        _parent_store = {}
        return
    _parent_store = {p.metadata["chunk_id"]: p for p in parents}


def get_vector_store() -> Chroma:
    global _vector_store
    if _vector_store is None:
        persist_dir = Path(settings.CHROMA_PERSIST_DIR).resolve()
        _vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=get_embeddings(),
            persist_directory=str(persist_dir),
        )
        if _vector_store._collection.count() == 0:
            from app.rag.loaders.markdown_loader import load_markdown_docs
            from app.rag.splitters.text_splitter import (
                split_docs,
                split_parent_child,
            )
            docs = load_markdown_docs(_corpus_dir())
            try:
                parents, children = split_parent_child(docs)
            except Exception:
                # fallback：旧版 splitter 失败时退回到扁平切分
                children = split_docs(docs, chunk_size=500, chunk_overlap=50)
                parents = []
            _vector_store.add_documents(children)
            if parents:
                reset_parent_store(parents)
    return _vector_store


def add_documents(chunks: list[Document]) -> list[str]:
    vs = get_vector_store()
    return vs.add_documents(chunks)


def similarity_search(query: str, k: int | None = None) -> list[Document]:
    vs = get_vector_store()
    k = k or settings.TOP_K
    return vs.similarity_search(query, k=k)


def expand_to_parents(
    docs: list[Document],
    parent_max_chars: int = 4000,
) -> list[Document]:
    """把 child chunk 列表展开为对应的 parent，去重后截断过长 parent。

    如果某 child 没有 parent_id 或 parent 不在 store 里，原样保留 child。
    """
    parents = _load_parent_store()
    seen: set[str] = set()
    out: list[Document] = []
    for d in docs:
        pid = d.metadata.get("parent_id")
        parent = parents.get(pid) if pid else None
        if parent is None:
            out.append(d)
            continue
        if parent.metadata["chunk_id"] in seen:
            continue
        seen.add(parent.metadata["chunk_id"])
        page = parent.page_content
        meta = dict(parent.metadata)
        if len(page) > parent_max_chars:
            page = page[:parent_max_chars] + "\n…(已截断)"
            meta["truncated"] = True
        out.append(Document(page_content=page, metadata=meta))
    return out
