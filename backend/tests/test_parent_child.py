"""Parent-Child 切分与展开的单测。"""
from langchain_core.documents import Document

from app.rag.retrievers.vector_retriever import (
    expand_to_parents,
    reset_parent_store,
)
from app.rag.splitters.text_splitter import (
    split_docs,
    split_markdown,
    split_parent_child,
)


SAMPLE = (
    "# Leetcode 题解\n"
    "## 1. 两数之和\n"
    "### 题目描述\n给定一个整数数组 nums 和目标值 target，"
    "返回两个下标使对应数字之和等于 target。\n"
    "### 解题思路\n用哈希表一次遍历：边走边把已经看到的数字记下来，"
    "查询 target - 当前数字是否在表里。命中即返回下标对。\n"
    "### 代码实现\n"
    "```python\n"
    "def two_sum(nums, target):\n"
    "    seen = {}\n"
    "    for i, n in enumerate(nums):\n"
    "        if target - n in seen:\n"
    "            return [seen[target - n], i]\n"
    "        seen[n] = i\n"
    "```\n"
    "### 复杂度\n时间 O(n) 空间 O(n)。\n"
    "## 2. 反转链表\n"
    "### 题目描述\n给定单链表头节点，反转后返回新头。\n"
    "### 解题思路\n迭代翻转：保存 prev/curr/next 三指针，逐节点反转 next 指针。\n"
)


def test_split_parent_child_returns_both_lists():
    parents, children = split_parent_child(
        [Document(page_content=SAMPLE, metadata={"source": "lc.md"})]
    )
    # parent_level=2: H1 标题 + 2 个 H2 章节 = 3 个 parent
    # （H3 题目/思路/代码/复杂度 都并入所属 H2 的 parent）
    assert len(parents) == 3
    # child 至少要细于 parent（同一 parent 内被切分）
    assert len(children) >= len(parents)


def test_children_carry_parent_id():
    parents, children = split_parent_child(
        [Document(page_content=SAMPLE, metadata={"source": "lc.md"})]
    )
    # 至少一个 child 必须有 parent_id
    children_with_pid = [c for c in children if c.metadata.get("parent_id")]
    assert len(children_with_pid) == len(children)
    # 所有 parent_id 都能在 parents 里找到
    parent_ids = {p.metadata["chunk_id"] for p in parents}
    for c in children:
        assert c.metadata["parent_id"] in parent_ids


def test_parent_groups_h2_sections():
    parents, _ = split_parent_child(
        [Document(page_content=SAMPLE, metadata={"source": "lc.md"})]
    )
    # H1 标题 + 2 个 H2 章节（题目/思路/代码/复杂度都归到 '1. 两数之和' 下）
    headings = [p.metadata["heading"] for p in parents]
    assert "Leetcode 题解" in headings
    assert "1. 两数之和" in headings
    assert "2. 反转链表" in headings


def test_parent_doc_kind_and_metadata():
    parents, _ = split_parent_child(
        [Document(page_content=SAMPLE, metadata={"source": "lc.md"})]
    )
    for p in parents:
        assert p.metadata["doc_kind"] == "parent"
        assert p.metadata["source"] == "lc.md"
        assert isinstance(p.metadata.get("child_ids"), list)
        assert len(p.metadata["child_ids"]) >= 1
        # 边界 = level<=2 (H1 触发, H2 触发);这里也允许 == 1
        assert p.metadata["level"] <= 2


def test_child_doc_kind_marker():
    _, children = split_parent_child(
        [Document(page_content=SAMPLE, metadata={"source": "lc.md"})]
    )
    for c in children:
        assert c.metadata["doc_kind"] == "child"


def test_no_h2_fallback_to_single_parent():
    """文档没有 H2 时（如只有 H1），应兜底为单个 parent。"""
    text = (
        "# 总纲\n"
        "### 子节 A\n内容 A\n"
        "### 子节 B\n内容 B\n"
    )
    parents, children = split_parent_child(
        [Document(page_content=text, metadata={"source": "no_h2.md"})]
    )
    # H1 触发边界,得到 1 个 parent(总纲),但其内部没有 H2/H1 边界,
    # 所以子节 A/B 仍被合并到 H1 之下. 总 parent 数 = 1 (总纲)
    # H3(子节 A/B) 不会触发新边界,直接并入总纲
    assert len(parents) == 1
    assert len(children) >= 2
    # 全部 child 关联到同一个 parent
    pids = {c.metadata["parent_id"] for c in children}
    assert len(pids) == 1


def test_expand_to_parents_dedupes():
    parents, children = split_parent_child(
        [Document(page_content=SAMPLE, metadata={"source": "lc.md"})]
    )
    reset_parent_store(parents)
    # 挑 child 最多的那个 parent（保证 ≥2 child 用于测去重）
    pid_to_children: dict[str, list[Document]] = {}
    for c in children:
        pid_to_children.setdefault(c.metadata["parent_id"], []).append(c)
    target_pid, target_children = max(pid_to_children.items(), key=lambda kv: len(kv[1]))
    assert len(target_children) >= 2, "测试前提：需要至少 1 个 parent 含 2+ child"
    expanded = expand_to_parents(target_children)
    assert len(expanded) == 1
    assert expanded[0].metadata["doc_kind"] == "parent"
    assert expanded[0].metadata["chunk_id"] == target_pid


def test_expand_to_parents_returns_child_when_no_pid():
    reset_parent_store([])
    child = Document(
        page_content="orphan",
        metadata={"doc_kind": "child", "source": "x.md", "chunk_id": "c1"},
    )
    out = expand_to_parents([child])
    assert out == [child]


def test_expand_to_parents_truncates_oversized_parent():
    """parent 过长时展开应截断并标记 truncated。"""
    big = "x" * 10_000
    parent = Document(
        page_content=big,
        metadata={
            "doc_kind": "parent",
            "source": "big.md",
            "chunk_id": "p_big",
            "child_ids": [],
        },
    )
    reset_parent_store([parent])
    child = Document(
        page_content="hint",
        metadata={
            "doc_kind": "child",
            "source": "big.md",
            "chunk_id": "c_hint",
            "parent_id": "p_big",
        },
    )
    out = expand_to_parents([child], parent_max_chars=200)
    assert len(out) == 1
    assert len(out[0].page_content) < len(big)
    assert out[0].metadata.get("truncated") is True
    assert "已截断" in out[0].page_content


def test_split_parent_child_preserves_existing_split_markdown():
    """回归：旧 API split_docs / split_markdown 行为不变。"""
    text = "## 思路\n哈希表\n## 代码\n```python\npass\n```\n"
    old_chunks = split_docs(
        [Document(page_content=text, metadata={"source": "old.md"})],
        chunk_size=500,
        chunk_overlap=50,
    )
    direct = split_markdown(text, "old.md", chunk_size=500, chunk_overlap=50)
    assert [c.page_content for c in old_chunks] == [c.page_content for c in direct]
