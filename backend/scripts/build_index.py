"""建索引脚本：加载 data/corpus/ 下所有文档，切分后写入 Chroma + BM25 索引。

用法：
    python -m scripts.build_index
"""
import os
import sys
from pathlib import Path

# 必须先于任何 app.* import,避免 langchain_community / sentence_transformers
# 在 config.py 设 HF_HUB_OFFLINE 之前就 HEAD huggingface.co
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# 确保可以导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.loaders import load_docs
from app.rag.splitters.text_splitter import split_parent_child
from app.rag.retrievers.vector_retriever import (
    get_vector_store,
    reset_parent_store,
)
from app.rag.retrievers.hybrid_retriever import HybridRetriever
from app.core.logging import setup_logging, logger


def main():
    setup_logging()
    backend_root = Path(__file__).resolve().parent.parent
    corpus_dir = backend_root / "data" / "corpus"

    if not corpus_dir.exists():
        logger.error(f"语料目录不存在: {corpus_dir}")
        sys.exit(1)

    # 1. 加载文档
    logger.info(f"从 {corpus_dir} 加载文档...")
    docs = load_docs(corpus_dir)
    logger.info(f"加载了 {len(docs)} 个文档")

    if not docs:
        logger.warning("没有找到文档，退出")
        return

    # 2. Parent-Child 切分
    logger.info("Parent-Child 切分文档...")
    parents, children = split_parent_child(docs, child_size=500, child_overlap=50)
    logger.info(f"切分为 {len(parents)} 个 parent / {len(children)} 个 child")

    # 3. 写入 Chroma（仅 child 进入向量库）
    logger.info("写入 Chroma 向量库（child）...")
    # 不走 get_vector_store 的 lazy auto-build 路径,直接 new 一个新的 Chroma
    # 实例,避免与 build_index 自己的 add 重复写 2 遍。
    from langchain_community.vectorstores import Chroma
    from app.core.config import settings
    from app.rag.embeddings.bge import get_embeddings
    from app.rag.retrievers.vector_retriever import COLLECTION_NAME

    persist_dir = Path(settings.CHROMA_PERSIST_DIR).resolve()
    vs = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(persist_dir),
    )
    # 同步覆盖 retriever 模块内的单例,让后续 search() 用新 store
    import app.rag.retrievers.vector_retriever as vr_module
    vr_module._vector_store = vs

    from langchain_core.documents import Document
    sanitized = [
        Document(page_content=c.page_content, metadata={k: v for k, v in c.metadata.items() if v is not None})
        for c in children
    ]
    vs.add_documents(sanitized)
    logger.info(f"Chroma 写入完成,共 {vs._collection.count()} 个 child")

    # 4. 构建 BM25 索引（仅 child；parent 用于上下文展开）
    logger.info("构建 BM25 + 混合检索索引...")
    hr = HybridRetriever()
    hr.index(children)
    logger.info("索引构建完成")

    # 5. 持久化 chunks + parents
    import json
    processed_dir = backend_root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    chunks_data = [{"content": c.page_content, "metadata": c.metadata} for c in children]
    (processed_dir / "all_chunks.json").write_text(
        json.dumps(chunks_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    parents_data = [{"content": p.page_content, "metadata": p.metadata} for p in parents]
    (processed_dir / "parents.json").write_text(
        json.dumps(parents_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(
        f"chunks 已持久化到 {processed_dir / 'all_chunks.json'}；"
        f"parents 已持久化到 {processed_dir / 'parents.json'}"
    )

    # 6. 同步到内存中的 parent 映射（避免冷启动后第一次 expand 走磁盘）
    reset_parent_store(parents)


if __name__ == "__main__":
    main()
