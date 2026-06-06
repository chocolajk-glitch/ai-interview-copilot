"""手动测试文档加载 + 切分。"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.loaders.markdown_loader import load_markdown_docs
from app.rag.splitters.text_splitter import split_docs

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data" / "corpus"

print("=" * 60)
print(f"=== 加载文档（{CORPUS_DIR}）===")
print("=" * 60)
docs = load_markdown_docs(CORPUS_DIR)
print(f"  加载到 {len(docs)} 个文档")
for d in docs:
    src = Path(d.metadata["source"]).name
    print(f"  - {src} ({len(d.page_content)} 字符)")

print()
print("=" * 60)
print("=== 切分文档（chunk_size=500, chunk_overlap=50）===")
print("=" * 60)
chunks = split_docs(docs, chunk_size=500, chunk_overlap=50)
print(f"  切分成 {len(chunks)} 个 chunk\n")

for i, c in enumerate(chunks[:3]):  # 只展示前 3 个 chunk
    src = Path(c.metadata["source"]).name
    print(f"--- chunk {i} (来自 {src}, {len(c.page_content)} 字符) ---")
    print(c.page_content)
    print()

print(f"✅ 切分完成: {len(docs)} 文档 → {len(chunks)} chunk")