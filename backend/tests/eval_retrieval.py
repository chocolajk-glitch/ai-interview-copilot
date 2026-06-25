"""检索质量评测：对比 BM25 / 向量 / RRF / Hybrid+Rerank 四种方案。

基于 data/eval/qa_dataset.json 中带 expected_source 的核心题目（25 条），
以「expected_source 是否出现在 top-k 召回结果中」计算 recall@k 与 MRR。

数据沉淀到 tests/eval_results/retrieval_metrics.json，供简历引用。
运行：poetry run python tests/eval_retrieval.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.loaders.markdown_loader import load_markdown_docs
from app.rag.retrievers.bm25_retriever import BM25Retriever
from app.rag.retrievers.vector_retriever import similarity_search
from app.rag.splitters.text_splitter import split_docs

CORPUS_DIR = "data/corpus"
EVAL_DATASET = "data/eval/qa_dataset.json"
RESULTS_DIR = Path("tests/eval_results")


def _load_eval_questions() -> list[dict]:
    raw = json.loads(Path(EVAL_DATASET).read_text(encoding="utf-8"))
    return [q for q in raw if q.get("expected_source") and q["expected_source"] != "none"]


def _source_in_doc(doc: Document, source_key: str) -> bool:
    return source_key in (doc.metadata.get("source") or "")


def _evaluate(retriever_name: str, retriever, questions: list[dict], k: int = 5) -> dict:
    """对单一 retriever 计算 recall@k / MRR。"""
    hits = 0
    reciprocal_ranks: list[float] = []
    per_query: list[dict] = []

    for q in questions:
        question = q["question"]
        target = q["expected_source"]
        results = retriever(question, top_k=k)
        rank = None
        for i, doc in enumerate(results, start=1):
            if _source_in_doc(doc, target):
                rank = i
                break
        if rank is not None:
            hits += 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)
        per_query.append({"q": question, "target": target, "rank": rank})

    n = len(questions)
    recall_at_k = round(hits / n, 4) if n else 0.0
    mrr = round(sum(reciprocal_ranks) / n, 4) if n else 0.0
    return {
        "retriever": retriever_name,
        "k": k,
        "total": n,
        "hits": hits,
        "recall_at_k": recall_at_k,
        "mrr": mrr,
        "details": per_query,
    }


def _naive_splitter(docs: list[Document], chunk_size: int = 500, chunk_overlap: int = 50) -> list[Document]:
    """对照组：朴素按字符切分（不感知标题、不保护代码块）。"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "；", " ", ""],
    )
    out: list[Document] = []
    for d in docs:
        for chunk in splitter.split_text(d.page_content):
            out.append(
                Document(
                    page_content=chunk,
                    metadata={**d.metadata, "chunk_id": "naive"},
                )
            )
    return out


def _make_bm25_only(docs: list[Document]):
    bm25 = BM25Retriever()
    bm25.index(docs)

    def _search(query: str, top_k: int = 5):
        return [doc for doc, _ in bm25.search(query, k=top_k)]
    return _search


def _make_vector_only(docs: list[Document]):
    # vector_retriever 走 Chroma：必须先 add_documents 才会被搜到
    from app.rag.retrievers.vector_retriever import get_vector_store
    vs = get_vector_store()
    try:
        existing = vs._collection.get(include=["metadatas"])
        existing_ids = {m.get("chunk_id") for m in (existing.get("metadatas") or []) if m}
    except Exception:
        existing_ids = set()
    to_add = [d for d in docs if d.metadata.get("chunk_id") not in existing_ids]
    if to_add:
        vs.add_documents(to_add)

    def _search(query: str, top_k: int = 5):
        return similarity_search(query, k=top_k)
    return _search


def _make_rrf_only(docs: list[Document]):
    """纯 RRF 融合（不重排）：用于对比 Rerank 的贡献。"""
    bm25 = BM25Retriever()
    bm25.index(docs)
    K = 60

    def _search(query: str, top_k: int = 5, bm25_k: int = 20, vec_k: int = 20):
        bm25_results = bm25.search(query, k=bm25_k)
        vector_results = similarity_search(query, k=vec_k)
        bm25_rank = {id(doc): r for r, (doc, _) in enumerate(bm25_results)}
        vector_rank = {id(doc): r for r, doc in enumerate(vector_results)}
        all_docs = {}
        for doc, _ in bm25_results:
            all_docs.setdefault(id(doc), doc)
        for doc in vector_results:
            all_docs.setdefault(id(doc), doc)
        rrf = {
            did: 1 / (K + bm25_rank.get(did, bm25_k)) + 1 / (K + vector_rank.get(did, vec_k))
            for did in all_docs
        }
        ids_sorted = sorted(rrf, key=lambda i: rrf[i], reverse=True)[:top_k]
        return [all_docs[i] for i in ids_sorted]
    return _search


def _make_hybrid_rerank(docs: list[Document]):
    from app.rag.retrievers.hybrid_retriever import HybridRetriever
    hr = HybridRetriever()
    hr.index(docs)

    def _search(query: str, top_k: int = 5):
        return hr.search(query, top_k=top_k, use_rerank=True)
    return _search


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    questions = _load_eval_questions()
    print(f"评测题目数: {len(questions)}")

    # 1) 评测自研 splitter 下的四种检索方案
    print("\n[1/2] 加载语料 + 自研 splitter 切分...")
    raw_docs = load_markdown_docs(CORPUS_DIR)
    custom_chunks = split_docs(raw_docs, chunk_size=500, chunk_overlap=50)
    print(f"  自研 splitter chunk 数: {len(custom_chunks)}")

    t0 = time.perf_counter()
    retrievers = {
        "bm25_only": _make_bm25_only(custom_chunks),
        "vector_only": _make_vector_only(custom_chunks),
        "rrf_only": _make_rrf_only(custom_chunks),
        "hybrid_rerank": _make_hybrid_rerank(custom_chunks),
    }
    print(f"  索引构建耗时: {time.perf_counter() - t0:.1f}s")

    retrieval_results: list[dict] = []
    for name, fn in retrievers.items():
        t0 = time.perf_counter()
        metrics = _evaluate(name, fn, questions, k=5)
        metrics["wall_sec"] = round(time.perf_counter() - t0, 1)
        retrieval_results.append(metrics)
        print(
            f"  [{name:<14}] recall@5={metrics['recall_at_k']:.4f}  "
            f"MRR={metrics['mrr']:.4f}  hits={metrics['hits']}/{metrics['total']}  "
            f"({metrics['wall_sec']}s)"
        )

    # 2) 评测朴素 splitter + Hybrid+Rerank（与自研对比）
    print("\n[2/2] 加载朴素 splitter 切分 + Hybrid+Rerank...")
    naive_chunks = _naive_splitter(raw_docs)
    print(f"  朴素 splitter chunk 数: {len(naive_chunks)}")
    naive_hybrid = _make_hybrid_rerank(naive_chunks)
    t0 = time.perf_counter()
    naive_metrics = _evaluate("hybrid_rerank_naive_splitter", naive_hybrid, questions, k=5)
    naive_metrics["wall_sec"] = round(time.perf_counter() - t0, 1)
    print(
        f"  [naive_splitter ] recall@5={naive_metrics['recall_at_k']:.4f}  "
        f"MRR={naive_metrics['mrr']:.4f}  hits={naive_metrics['hits']}/{naive_metrics['total']}  "
        f"({naive_metrics['wall_sec']}s)"
    )

    # 3) 汇总 + 落盘
    summary = {
        "dataset": str(EVAL_DATASET),
        "total_questions": len(questions),
        "corpus_dir": CORPUS_DIR,
        "custom_splitter_chunks": len(custom_chunks),
        "naive_splitter_chunks": len(naive_chunks),
        "retrieval_comparison": [
            {
                "retriever": m["retriever"],
                "recall_at_5": m["recall_at_k"],
                "mrr": m["mrr"],
                "hits": m["hits"],
                "total": m["total"],
                "wall_sec": m["wall_sec"],
            }
            for m in retrieval_results
        ],
        "splitter_comparison": {
            "custom_splitter": {
                "chunks": len(custom_chunks),
                "recall_at_5": next(
                    m["recall_at_k"] for m in retrieval_results if m["retriever"] == "hybrid_rerank"
                ),
                "mrr": next(
                    m["mrr"] for m in retrieval_results if m["retriever"] == "hybrid_rerank"
                ),
            },
            "naive_splitter": {
                "chunks": len(naive_chunks),
                "recall_at_5": naive_metrics["recall_at_k"],
                "mrr": naive_metrics["mrr"],
            },
        },
    }
    out = RESULTS_DIR / "retrieval_metrics.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已写入: {out}")


if __name__ == "__main__":
    main()
