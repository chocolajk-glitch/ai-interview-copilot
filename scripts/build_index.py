"""建索引脚本：加载 data/corpus/ 下所有文档，切分后写入 Chroma + BM25 索引。

用法：
    python -m scripts.build_index
"""
import sys
from pathlib import Path

# 确保可以导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.loaders import load_docs
from app.rag.splitters.text_splitter import split_docs
from app.rag.retrievers.vector_retriever import get_vector_store
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

    # 2. 切分
    logger.info("切分文档...")
    chunks = split_docs(docs, chunk_size=500, chunk_overlap=50)
    logger.info(f"切分为 {len(chunks)} 个 chunks")

    # 3. 写入 Chroma
    logger.info("写入 Chroma 向量库...")
    vs = get_vector_store()
    from langchain_core.documents import Document
    sanitized = [
        Document(page_content=c.page_content, metadata={k: v for k, v in c.metadata.items() if v is not None})
        for c in chunks
    ]
    vs.add_documents(sanitized)
    logger.info("Chroma 写入完成")

    # 4. 构建 BM25 索引
    logger.info("构建 BM25 + 混合检索索引...")
    hr = HybridRetriever()
    hr.index(chunks)
    logger.info("索引构建完成")

    # 5. 持久化 chunks
    import json
    processed_dir = backend_root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    chunks_data = [{"content": c.page_content, "metadata": c.metadata} for c in chunks]
    (processed_dir / "all_chunks.json").write_text(
        json.dumps(chunks_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"chunks 已持久化到 {processed_dir / 'all_chunks.json'}")


if __name__ == "__main__":
    main()
