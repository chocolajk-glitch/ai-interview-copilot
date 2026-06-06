"""测试向量检索（集成测试，需要 Day 4 已存 Chroma 数据）。"""
from app.rag.retrievers.vector_retriever import similarity_search


def test_similarity_search_two_sum_top1():
    """搜'两数之和'，top-1 应是 01_two_sum.md。"""
    results = similarity_search("两数之和怎么解", k=3)
    assert len(results) >= 1
    assert "01_two_sum" in results[0].metadata["source"]


def test_similarity_search_reverse_list_top1():
    """搜'反转链表'，top-1 应是 02_reverse_linked_list.md。"""
    results = similarity_search("反转链表", k=3)
    assert "02_reverse_linked_list" in results[0].metadata["source"]