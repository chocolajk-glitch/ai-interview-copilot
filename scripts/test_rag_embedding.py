"""手动测试 embedding + Chroma 持久化 + 检索。"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.rag.loaders.markdown_loader import load_markdown_docs
from app.rag.splitters.text_splitter import split_docs
from app.rag.retrievers.vector_retriever import (
    add_documents,
    get_vector_store,
    similarity_search,
)

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data" / "corpus"

print("=" * 60)
print("=== Step 1: 加载 + 切分文档 ===")
print("=" * 60)
docs = load_markdown_docs(CORPUS_DIR)
chunks = split_docs(docs, chunk_size=500, chunk_overlap=50)
print(f"  5 文档 → {len(chunks)} chunk\n")

print("=" * 60)
print(f"=== Step 2: Embedding + 存入 Chroma ===")
print(f"    模型: {settings.EMBEDDING_MODEL}（{settings.EMBEDDING_DEVICE}）")
print("=" * 60)
vs = get_vector_store()
existing = vs.get()
print(f"  Chroma collection 已有文档数: {len(existing['ids'])}")
if len(existing["ids"]) == 0:
    print("  首次运行，开始 embedding（首次会下载模型 1-3 分钟）...")
    ids = add_documents(chunks)
    print(f"  ✅ 存储了 {len(ids)} 个 chunk")
else:
    print(f"  跳过（已有数据）\n")

print()
print("=" * 60)
print("=== Step 3: 相似度检索测试 ===")
print("=" * 60)

test_queries = [
    "两数之和怎么解",
    "反转链表",
    "二分查找",
]

for q in test_queries:
    print(f"\n查询: {q}")
    results = similarity_search(q, k=3)
    for i, doc in enumerate(results):
        src = Path(doc.metadata["source"]).name
        preview = doc.page_content[:80].replace("\n", " ")
        print(f"  [{i+1}] {src}: {preview}...")

print(f"\n✅ 检索测试完成（top-3）")