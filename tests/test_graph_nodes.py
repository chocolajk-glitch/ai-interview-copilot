"""测试 graph.nodes 的 retriever / reranker 行为（Fix B + C）。"""
from unittest.mock import patch

import pytest
from langchain_core.documents import Document

from app.graph import nodes
from app.graph.nodes import retriever, reranker_node


def _doc(content: str, source: str, heading: str, is_code: bool = False) -> Document:
    return Document(
        page_content=content,
        metadata={
            "source": source,
            "chunk_id": f"id-{heading}",
            "position": 0,
            "end": len(content),
            "heading": heading,
            "level": 2,
            "is_code": is_code,
        },
    )


class _FakeHybridRetriever:
    """模拟 HybridRetriever，固定返回预置的文档列表。"""

    def __init__(self, docs):
        self._docs = docs

    def search(self, query, top_k=5, **kwargs):
        # 按输入顺序返回，模拟 rerank 后的相关度
        return self._docs[:top_k]


@pytest.fixture
def fake_retriever_with_corpus():
    """构造一个模拟语料：4 个文件各有一个 is_code=True 的代码 chunk 和
    一个 is_code=False 的文本 chunk。"""
    docs = [
        _doc("```python\ndef two_sum(...):\n```", "01_two_sum.md", "代码实现", is_code=True),
        _doc("哈希表遍历一次", "01_two_sum.md", "解题思路"),
        _doc("```python\ndef reverse_list(...):\n```", "02_reverse_linked_list.md", "代码实现", is_code=True),
        _doc("prev / curr 指针", "02_reverse_linked_list.md", "解题思路"),
        _doc("```python\ndef is_valid(s):\n```", "03_valid_parentheses.md", "代码实现", is_code=True),
        _doc("栈压左括号", "03_valid_parentheses.md", "解题思路"),
        _doc("```python\ndef search(nums, target):\n```", "04_binary_search.md", "代码实现", is_code=True),
        _doc("闭区间二分", "04_binary_search.md", "解题思路"),
        _doc("```python\nclass ListNode:\n  def merge_two_lists(l1, l2):\n```",
             "05_merge_two_sorted_lists.md", "代码实现", is_code=True),
        _doc("双指针 + 哨兵", "05_merge_two_sorted_lists.md", "解题思路"),
    ]
    return _FakeHybridRetriever(docs)


def test_retriever_code_intent_prefers_code_chunks(fake_retriever_with_corpus):
    """Fix B: code 意图时，retriever 应优先返回 is_code=True 的 chunk。

    行为：候选池 → 取所有 is_code=True → 给 Reranker 至少 k 个。
    """
    with patch.object(nodes, "_get_hybrid_retriever",
                      return_value=fake_retriever_with_corpus):
        state = {
            "question": "详细讲解一下代码",
            "rewritten_query": "合并K个升序链表 代码实现 详细讲解",
            "intent": "code",
            "k": 3,
        }
        out = retriever(state)
    docs = out["docs"]
    # 候选数 ≤ k*2（给 Reranker 的预算）
    assert len(docs) <= 6
    # 至少 k=3 个是代码 chunk
    n_code = sum(1 for d in docs if d.metadata.get("is_code"))
    assert n_code >= 3, f"code 意图应至少返回 3 个代码 chunk，实际 {n_code}"


def test_retriever_code_intent_fills_with_non_code_when_insufficient():
    """Fix B 兜底：code chunk 不足 k 个时，用相关非代码 chunk 补足。"""
    docs = [
        _doc("```python\ndef foo(): pass\n```", "a.md", "代码实现", is_code=True),
        _doc("思路1", "a.md", "思路"),
        _doc("思路2", "b.md", "思路"),
        _doc("思路3", "c.md", "思路"),
    ]
    fake = _FakeHybridRetriever(docs)
    with patch.object(nodes, "_get_hybrid_retriever", return_value=fake):
        state = {
            "question": "q",
            "rewritten_query": "q",
            "intent": "code",
            "k": 3,
        }
        out = retriever(state)
    final = out["docs"]
    # 候选池就 4 个，全都返回
    assert len(final) == 4
    # 包含那唯一的一个 code chunk
    assert any(d.metadata.get("is_code") for d in final)
    # code chunk 排在最前（因为 code_docs 在前拼接）
    assert final[0].metadata.get("is_code") is True


def test_retriever_code_intent_passes_at_least_k_to_reranker(fake_retriever_with_corpus):
    """修复后的 retriever 至少要传 k 个候选给 Reranker。"""
    with patch.object(nodes, "_get_hybrid_retriever",
                      return_value=fake_retriever_with_corpus):
        state = {
            "question": "q",
            "rewritten_query": "q",
            "intent": "code",
            "k": 3,
        }
        out = retriever(state)
    assert len(out["docs"]) >= 3, "应至少传 3 个候选给 Reranker"


def test_retriever_factual_intent_no_code_filter():
    """非 code 意图：不过滤 is_code。"""
    docs = [
        _doc("思路文本", "a.md", "思路"),
        _doc("```python\nx = 1\n```", "a.md", "代码实现", is_code=True),
        _doc("复杂度", "a.md", "复杂度"),
    ]
    fake = _FakeHybridRetriever(docs)
    with patch.object(nodes, "_get_hybrid_retriever", return_value=fake):
        state = {
            "question": "原理",
            "rewritten_query": "原理",
            "intent": "factual",
            "k": 3,
        }
        out = retriever(state)
    final = out["docs"]
    # 应按 hybrid 检索顺序保留 top-3，不做 is_code 过滤
    assert len(final) == 3


def test_reranker_uses_rewritten_query():
    """Fix C: reranker 必须用 rewritten_query（追问/指代没有 topic 信号）。"""
    captured = {}

    def fake_rerank(query, documents, top_k=None):
        captured["query"] = query
        return list(documents)

    docs = [
        _doc("思路1", "a.md", "思路"),
        _doc("```python\n```", "a.md", "代码实现", is_code=True),
    ]
    with patch.object(nodes, "rerank", side_effect=fake_rerank):
        state = {
            "question": "详细讲解一下代码",        # 短追问，没 topic
            "rewritten_query": "合并K个升序链表 代码实现 详细讲解",
            "docs": docs,
            "k": 3,
        }
        reranker_node(state)
    assert captured["query"] == "合并K个升序链表 代码实现 详细讲解"
    # 当 rewritten_query 为空时，应回退到 question
    with patch.object(nodes, "rerank", side_effect=fake_rerank):
        state2 = {
            "question": "两数之和",
            "rewritten_query": "",
            "docs": docs,
            "k": 3,
        }
        reranker_node(state2)
    assert captured["query"] == "两数之和"
