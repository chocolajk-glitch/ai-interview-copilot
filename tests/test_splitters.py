from langchain_core.documents import Document

from app.rag.splitters.text_splitter import split_docs, split_markdown


def test_multilevel_heading_split():
    text = (
        "# 题目\n"
        "两数之和\n"
        "## 思路\n"
        "用哈希表\n"
        "## 代码\n"
        "```python\n"
        "def two_sum(nums, target):\n"
        "    seen = {}\n"
        "    for i, n in enumerate(nums):\n"
        "        if target - n in seen:\n"
        "            return [seen[target - n], i]\n"
        "        seen[n] = i\n"
        "```\n"
        "## 复杂度\n"
        "O(n) 时间 O(n) 空间\n"
    )
    chunks = split_markdown(text, "两数之和.md")
    headings = [c.metadata["heading"] for c in chunks]
    assert "题目" in headings
    assert "思路" in headings
    assert "代码" in headings
    assert "复杂度" in headings
    levels = [c.metadata["level"] for c in chunks]
    assert 1 in levels
    assert levels.count(2) >= 3


def test_code_block_not_sliced():
    long_code_line = "    x = 1\n" * 200
    text = (
        f"## 题目\n代码如下：\n"
        f"```python\n{long_code_line}```\n"
        f"## 结束\n完\n"
    )
    chunks = split_markdown(text, "test.md", chunk_size=200, chunk_overlap=20)
    code_chunks = [c for c in chunks if c.metadata["is_code"]]
    assert len(code_chunks) == 1
    assert code_chunks[0].page_content.count("\n") >= 200


def test_heading_injected_into_chunk():
    text = "## 思路\n用哈希表可以 O(n) 解决。\n更多解释...\n"
    chunks = split_markdown(text, "test.md")
    assert any(c.page_content.startswith("## 思路") for c in chunks)


def test_chunk_metadata_fields():
    text = (
        "## 思路\n用哈希表\n"
        "## 代码\n```python\npass\n```\n"
        "## 复杂度\nO(n)\n"
    )
    chunks = split_markdown(text, "test.md")
    assert len(chunks) >= 3
    for c in chunks:
        assert c.metadata["source"] == "test.md"
        assert isinstance(c.metadata["chunk_id"], str)
        assert len(c.metadata["chunk_id"]) == 16
        assert isinstance(c.metadata["position"], int)
        assert isinstance(c.metadata["end"], int)
        assert c.metadata["end"] > c.metadata["position"]
        assert "heading" in c.metadata
        assert "level" in c.metadata
        assert "is_code" in c.metadata


def test_split_docs_preserves_source():
    docs = [
        Document(page_content="## 思路\n哈希表", metadata={"source": "a.md"}),
        Document(page_content="## 思路\n双指针", metadata={"source": "b.md"}),
    ]
    chunks = split_docs(docs, chunk_size=500, chunk_overlap=50)
    sources = {c.metadata["source"] for c in chunks}
    assert sources == {"a.md", "b.md"}


def test_no_orphan_heading_chunks():
    """修复：不能产生只含 '## 代码实现' 这种 7 字节的伪 chunk。

    切分器命中 ``` 围栏时，应把紧邻的 heading 合并到代码 chunk 内，
    否则 code 意图检索会回退到这些无内容 chunk。
    """
    text = (
        "# 1. Two Sum\n"
        "## 题目描述\n给定数组 nums...\n"
        "## 解题思路\n哈希表。\n"
        "## 代码实现\n"
        "```python\ndef two_sum(nums, target):\n    pass\n```\n"
        "## 复杂度\nO(n)\n"
    )
    chunks = split_markdown(text, "01_two_sum.md")
    # 不应有 is_code=False 且 heading == '代码实现' 的 chunk
    orphans = [c for c in chunks
               if c.metadata.get("heading") == "代码实现"
               and not c.metadata.get("is_code")]
    assert orphans == [], (
        f"发现孤标题 chunk: {[(o.page_content, o.metadata) for o in orphans]}"
    )
    # 应当有一个 is_code=True 的代码 chunk，且其内容以 '## 代码实现' 开头
    code_chunks = [c for c in chunks if c.metadata.get("is_code")]
    assert len(code_chunks) == 1
    assert code_chunks[0].page_content.startswith("## 代码实现")
    assert "def two_sum" in code_chunks[0].page_content


def test_corpus_no_orphan_chunks_after_split():
    """实际语料（5 个 .md）切分后不应有孤标题 chunk。"""
    from pathlib import Path
    from app.rag.loaders.markdown_loader import load_markdown_docs

    backend = Path(__file__).resolve().parent.parent
    corpus_dir = str(backend / "data" / "corpus")
    docs = load_markdown_docs(corpus_dir)
    chunks = split_docs(docs, chunk_size=500, chunk_overlap=50)

    orphans = [c for c in chunks
               if c.metadata.get("heading") in ("代码实现", "代码")
               and not c.metadata.get("is_code")]
    assert orphans == [], (
        f"实际语料发现 {len(orphans)} 个孤标题 chunk，应为 0"
    )