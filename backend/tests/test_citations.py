"""引用溯源模块测试。"""
from langchain_core.documents import Document

from app.rag.citations import extract_citations, format_docs_with_citations, locate_in_source


def test_extract_citations():
    docs = [
        Document(
            page_content="哈希表解法",
            metadata={"source": "01_two_sum.md", "chunk_id": "abc123", "heading": "思路", "position": 10, "end": 50, "is_code": False},
        ),
        Document(
            page_content="def two_sum():",
            metadata={"source": "01_two_sum.md", "chunk_id": "def456", "heading": "代码", "position": 60, "end": 120, "is_code": True},
        ),
    ]
    citations = extract_citations(docs)
    assert len(citations) == 2
    assert citations[0]["index"] == 1
    assert citations[0]["source"] == "01_two_sum.md"
    assert citations[0]["heading"] == "思路"
    assert citations[0]["is_code"] is False
    assert citations[1]["index"] == 2
    assert citations[1]["is_code"] is True


def test_extract_citations_path_normalization():
    """测试 Windows/Unix 路径都能正确提取文件名。"""
    docs = [
        Document(page_content="x", metadata={"source": r"data\corpus\01_two_sum.md", "chunk_id": "a", "position": 0, "end": 1}),
        Document(page_content="x", metadata={"source": "data/corpus/02_reverse.md", "chunk_id": "b", "position": 0, "end": 1}),
    ]
    citations = extract_citations(docs)
    assert citations[0]["source"] == "01_two_sum.md"
    assert citations[1]["source"] == "02_reverse.md"


def test_format_docs_with_citations():
    docs = [
        Document(
            page_content="哈希表解法",
            metadata={"source": "01_two_sum.md", "chunk_id": "abc", "heading": "思路", "position": 10, "end": 50, "is_code": False},
        ),
    ]
    result = format_docs_with_citations(docs)
    assert "[1] 来源: 01_two_sum.md - 思路" in result
    assert "offset 10-50" in result
    assert "哈希表解法" in result


def test_locate_in_source():
    source = "前面一些文字哈希表解法核心内容后面一些文字"
    chunk = "哈希表解法核心内容"
    result = locate_in_source(source, chunk, context_chars=5)
    assert result["position"] >= 0
    assert result["end"] > result["position"]
    assert result["highlight"] == chunk
    assert len(result["context_before"]) <= 5
    assert len(result["context_after"]) <= 5


def test_locate_in_source_not_found():
    source = "完全无关的内容"
    chunk = "不存在的文本"
    result = locate_in_source(source, chunk)
    assert result["position"] == -1
