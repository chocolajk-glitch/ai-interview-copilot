"""引用溯源模块：chunk 级别引用 + 原文位置定位 + 高亮标记。"""
from langchain_core.documents import Document


def extract_citations(docs: list[Document]) -> list[dict]:
    """从检索到的文档列表中提取引用信息。

    Args:
        docs: 检索返回的 Document 列表

    Returns:
        引用列表，每项包含 index / chunk_id / source / heading / position / end / is_code
    """
    citations = []
    for i, d in enumerate(docs, start=1):
        md = d.metadata
        citations.append({
            "index": i,
            "chunk_id": md.get("chunk_id"),
            "source": md.get("source", "").split("\\")[-1].split("/")[-1],
            "heading": md.get("heading"),
            "position": md.get("position"),
            "end": md.get("end"),
            "is_code": md.get("is_code", False),
        })
    return citations


def format_docs_with_citations(docs: list[Document]) -> str:
    """格式化文档内容，附带引用标签。

    Args:
        docs: 检索返回的 Document 列表

    Returns:
        格式化后的文本，每段前带 [n] 来源标签
    """
    parts = []
    for i, d in enumerate(docs, start=1):
        md = d.metadata
        source = md.get("source", "").split("\\")[-1].split("/")[-1]
        heading = md.get("heading")
        position = md.get("position", "?")
        end = md.get("end", "?")
        prefix = f"[{i}] 来源: {source}"
        if heading:
            prefix += f" - {heading}"
        prefix += f" (offset {position}-{end})"
        parts.append(f"{prefix}\n{d.page_content}")
    return "\n\n---\n\n".join(parts)


def locate_in_source(source_text: str, chunk_content: str, context_chars: int = 100) -> dict:
    """在原文中定位 chunk 的精确位置，返回高亮上下文。

    Args:
        source_text: 原文完整文本
        chunk_content: chunk 内容
        context_chars: 上下文字符数

    Returns:
        {"position": int, "end": int, "highlight": str, "context_before": str, "context_after": str}
    """
    pos = source_text.find(chunk_content[:64])  # 用前 64 字符定位
    if pos == -1:
        return {"position": -1, "end": -1, "highlight": "", "context_before": "", "context_after": ""}

    end = pos + len(chunk_content)
    ctx_before = source_text[max(0, pos - context_chars):pos]
    ctx_after = source_text[end:end + context_chars]

    return {
        "position": pos,
        "end": end,
        "highlight": chunk_content,
        "context_before": ctx_before,
        "context_after": ctx_after,
    }
