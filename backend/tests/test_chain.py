from langchain_core.documents import Document

from app.rag.chain import _extract_citations, _format_docs, ask


def _make_doc(content: str, source: str = "test.md", **md_extra) -> Document:
    md = {"source": source, "chunk_id": "abc123", "position": 0, "end": 100, "is_code": False}
    md.update(md_extra)
    return Document(page_content=content, metadata=md)


def test_extract_citations_returns_chunk_level_structure():
    docs = [
        _make_doc("思路1", source="a.md", chunk_id="c1", heading="思路", position=10, end=50),
        _make_doc("代码1", source="a.md", chunk_id="c2", heading="代码", position=60, end=200, is_code=True),
        _make_doc("思路2", source="b.md", chunk_id="c3", heading="思路", position=0, end=80),
    ]
    citations = _extract_citations(docs)
    assert len(citations) == 3
    assert [c["index"] for c in citations] == [1, 2, 3]
    assert citations[0]["chunk_id"] == "c1"
    assert citations[0]["source"] == "a.md"
    assert citations[0]["heading"] == "思路"
    assert citations[0]["position"] == 10
    assert citations[0]["end"] == 50
    assert citations[0]["is_code"] is False
    assert citations[1]["is_code"] is True


def test_format_docs_adds_indexed_prefix():
    docs = [
        _make_doc("哈希表内容", heading="思路", position=120, end=580),
        _make_doc("code", heading="代码", position=600, end=900, is_code=True),
    ]
    formatted = _format_docs(docs)
    assert "[1] 来源: test.md - 思路 (offset 120-580)" in formatted
    assert "[2] 来源: test.md - 代码 (offset 600-900)" in formatted
    assert "---" in formatted


def test_ask_returns_citations_not_sources():
    result = ask("两数之和怎么解", provider="qwen", k=2)
    assert "citations" in result
    assert "sources" not in result
    assert isinstance(result["citations"], list)
    for c in result["citations"]:
        assert "index" in c
        assert "chunk_id" in c
        assert "source" in c
        assert "position" in c
        assert "end" in c
        assert "heading" in c
        assert "is_code" in c


def test_ask_chat_intent_skips_rag():
    """修复 D3：chain.py ask 应该走意图分类，chat 意图时跳过 RAG。

    修复前：所有问题都走 RAG，retriever 总会返回 top-k 个 doc，
    LLM 看到无关 doc + RAG prompt → 输出"无相关信息"。
    修复后：chat 意图（闲聊/数学/生活）直接用历史回答，citations=[]。
    """
    from app.rag import chain as chain_module
    # monkey-patch _classify_intent 让它强制返回 chat
    orig = chain_module._classify_intent
    chain_module._classify_intent = lambda q, h, p: "chat"
    try:
        result = ask("六个苹果怎么分给3个人", provider="qwen", k=3)
    finally:
        chain_module._classify_intent = orig
    assert "无相关信息" not in result["answer"], (
        f"chat 意图应跳过 RAG，但答成了：{result['answer']!r}"
    )
    assert "苹果" in result["answer"] or "分" in result["answer"], (
        f"应直接回答苹果问题，实际：{result['answer'][:200]!r}"
    )
    assert result["citations"] == [], (
        f"chat 意图不应有 citations，实际：{result['citations']}"
    )


def test_ask_no_docs_falls_back_to_chat():
    """修复 D3：chain.py ask 在 RAG 路径下没召回 doc 时也应 fallback 到 chat + history。"""
    from app.rag import chain as chain_module
    from langchain_core.documents import Document

    def _empty_search(query, top_k=None, **kwargs):
        return []  # 模拟 RAG 召回为空

    orig = chain_module._classify_intent
    chain_module._classify_intent = lambda q, h, p: "factual"   # 强制 factual
    orig_get = chain_module._get_hybrid_retriever
    chain_module._get_hybrid_retriever = lambda: type("F", (), {"search": staticmethod(_empty_search)})()
    try:
        result = ask("某个factual问题", provider="qwen", k=3)
    finally:
        chain_module._classify_intent = orig
        chain_module._get_hybrid_retriever = orig_get
    assert "无相关信息" not in result["answer"], (
        f"RAG 没 doc 时应 fallback chat，实际：{result['answer']!r}"
    )
    assert result["citations"] == []