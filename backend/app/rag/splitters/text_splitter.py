import hashlib
import re

from langchain_core.documents import Document


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_FENCE_RE = re.compile(r"^```")


def _hash(source: str, position: int, content: str) -> str:
    raw = f"{position}::{content[:64]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _build_chunk(
    text: str,
    position: int,
    source: str,
    heading: str | None,
    level: int,
    is_code: bool,
) -> Document | None:
    text = text.rstrip()
    if not text:
        return None
    return Document(
        page_content=text,
        metadata={
            "source": source,
            "chunk_id": _hash(source, position, text),
            "position": position,
            "end": position + len(text),
            "heading": heading,
            "level": level,
            "is_code": is_code,
        },
    )


def _tail(buffer: str, overlap: int) -> str:
    if overlap <= 0 or len(buffer) <= overlap:
        return ""
    return buffer[-overlap:]


def split_markdown(
    text: str,
    source: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[Document]:
    lines = text.splitlines(keepends=True)
    chunks: list[Document] = []
    buffer = ""
    buffer_start = 0
    cursor = 0
    heading: str | None = None
    level = 0
    in_code = False
    code_buffer = ""
    code_start = 0
    code_heading: str | None = None
    code_level = 0

    def flush_buffer() -> None:
        nonlocal buffer, buffer_start
        if not buffer.strip():
            buffer = ""
            return
        c = _build_chunk(buffer, buffer_start, source, heading, level, is_code=False)
        if c:
            chunks.append(c)
        tail = _tail(buffer, chunk_overlap)
        buffer_start = buffer_start + len(buffer) - len(tail)
        buffer = tail

    def _split_code_buffer(buffer: str) -> list[str]:
        """把超长代码块按行二次切分，每段尽量贴近 chunk_size，段间保留 overlap。

        设计动机：单 ```...``` 围栏内可能上千行（如完整算法实现），不能整块喂给
        embedding（BGE 512 token 上限）。按行切能保留代码可读性。

        围栏处理：扫描 buffer 找到第一个/最后一个 fence 行作为开闭围栏，
        对中间 body 按行切，每段前后补回 fence。code_buffer 可能含进入 fence
        前的标题/空白（由 splitter 在 fence 入口处拼接），所以 fence 不一定在
        第一行。
        """
        if len(buffer) <= chunk_size:
            return [buffer]
        lines = buffer.splitlines(keepends=True)
        if not lines:
            return [buffer]
        # 找开闭 fence:第一个 ``` 行 = 开,最后一个 ``` 行 = 闭
        open_idx = None
        close_idx = None
        for i, line in enumerate(lines):
            if _FENCE_RE.match(line):
                if open_idx is None:
                    open_idx = i
                close_idx = i
        if open_idx is None:
            return [buffer]
        if close_idx is None or close_idx <= open_idx:
            return [buffer]
        open_fence = lines[open_idx]
        close_fence = lines[close_idx]
        # prefix = 开 fence 之前的文本(标题/空白),append 到首段
        prefix = "".join(lines[:open_idx])
        body_lines = lines[open_idx + 1:close_idx]
        if not body_lines:
            return [buffer]

        def _wrap(seg: str) -> str:
            if seg.startswith(open_fence):
                # 第一段保留 prefix
                return prefix + seg
            return open_fence + seg + close_fence

        segments: list[str] = []
        seg = ""
        for line in body_lines:
            # 预估加入这一行后是否超限（再留 ~10% buffer 避免边界处切到关键字中间）
            if seg and len(seg) + len(line) > chunk_size * 1.1:
                segments.append(_wrap(seg))
                # overlap: 保留上一段尾部几行作为下一段开头
                seg = _tail(seg, chunk_overlap) + line
            else:
                seg += line
        if seg:
            segments.append(_wrap(seg))
        return segments

    def flush_code() -> None:
        nonlocal code_buffer
        # 同一 fence 内的所有切出段共享 code_block_id，便于 split_parent_child
        # 后续把它们归到同一 parent（保持"代码块作为原子单位"的语义）
        code_block_id = _hash(source, code_start, code_heading or "code")
        for seg in _split_code_buffer(code_buffer):
            c = _build_chunk(seg, code_start, source, code_heading, code_level, is_code=True)
            if c:
                c.metadata["code_block_id"] = code_block_id
                chunks.append(c)
        code_buffer = ""

    for line in lines:
        if in_code:
            code_buffer += line
            cursor += len(line)
            if _FENCE_RE.match(line):
                flush_code()
                in_code = False
                buffer_start = cursor
            continue
        m = _HEADING_RE.match(line.rstrip("\n"))
        if m:
            flush_buffer()
            heading = m.group(2).strip()
            level = len(m.group(1))
            buffer = line
            buffer_start = cursor
        elif _FENCE_RE.match(line):
            if buffer.strip():
                code_buffer = buffer + line
                code_start = buffer_start
            else:
                code_buffer = line
                code_start = cursor
            in_code = True
            code_heading = heading
            code_level = level
            buffer = ""
            buffer_start = 0
        else:
            buffer += line
            if len(buffer) >= chunk_size:
                flush_buffer()
        cursor += len(line)

    if in_code:
        flush_code()
    flush_buffer()
    return [c for c in chunks if c is not None]


def split_docs(
    docs: list[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[Document]:
    out: list[Document] = []
    for d in docs:
        source = d.metadata.get("source", "unknown")
        out.extend(split_markdown(d.page_content, source, chunk_size, chunk_overlap))
    return out


def _parent_id(source: str, position: int, heading: str) -> str:
    raw = f"{source}::{position}::{heading}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def split_parent_child(
    docs: list[Document],
    child_size: int = 500,
    child_overlap: int = 50,
    parent_level: int = 2,
) -> tuple[list[Document], list[Document]]:
    """Parent-Child 切分：parent 按 parent_level 级标题切，child 复用 split_markdown。

    Returns:
        (parents, children)
        - parents: 较大的上下文块（用于喂 LLM），metadata 包含 doc_kind="parent"
        - children: 用于向量/BM25 检索的小块（用于精召），metadata 包含
          doc_kind="child" 和 parent_id，content 中保留 heading 前缀以辅助匹配

    关键约束：被 _split_code_buffer 切出的多段代码 child 共享同一 parent_id，
    保证"代码块"作为原子单位在 parent 展开后能拼回完整。
    """
    parents: list[Document] = []
    children: list[Document] = []

    for d in docs:
        source = d.metadata.get("source", "unknown")
        # 先按现有逻辑拿到所有 child，保留 heading 上下文
        child_chunks = split_markdown(d.page_content, source, child_size, child_overlap)

        # 第一遍：按 H_parent_level 边界给 child 分配候选 parent_id
        # 同时记录每个 parent 内的 (heading, level, child_ids, position, end)
        current_parent_heading: str | None = None
        current_parent_level = 0
        current_parent_position = 0
        current_parent_end = 0
        current_parent_id: str | None = None
        current_child_ids: list[str] = []
        current_parent_text: list[str] = []

        section_records: list[dict] = []  # 每段 parent 区间

        def flush_parent() -> None:
            nonlocal current_parent_heading, current_parent_level
            nonlocal current_parent_text, current_parent_position, current_parent_end
            nonlocal current_parent_id, current_child_ids
            if current_parent_id is None:
                return
            section_records.append({
                "id": current_parent_id,
                "heading": current_parent_heading,
                "level": current_parent_level,
                "position": current_parent_position,
                "end": current_parent_end,
                "child_ids": list(current_child_ids),
                "text_parts": list(current_parent_text),
            })
            current_parent_heading = None
            current_parent_level = 0
            current_parent_text = []
            current_parent_id = None
            current_child_ids = []
            current_parent_position = 0
            current_parent_end = 0

        for child in child_chunks:
            level = child.metadata.get("level", 0) or 0
            heading = child.metadata.get("heading")
            child.metadata["doc_kind"] = "child"

            if level <= parent_level and heading:
                flush_parent()
                current_parent_heading = heading
                current_parent_level = level
                current_parent_position = child.metadata.get("position", 0)
                current_parent_id = _parent_id(
                    source, current_parent_position, heading or ""
                )
                child.metadata["parent_id"] = current_parent_id
                current_child_ids = [child.metadata["chunk_id"]]
                current_parent_text = [child.page_content]
                current_parent_end = child.metadata.get("end", 0)
            else:
                if current_parent_id is None:
                    current_parent_heading = heading or source
                    current_parent_level = level or 1
                    current_parent_position = child.metadata.get("position", 0)
                    current_parent_id = _parent_id(
                        source, current_parent_position, current_parent_heading
                    )
                child.metadata["parent_id"] = current_parent_id
                current_child_ids.append(child.metadata["chunk_id"])
                current_parent_text.append(child.page_content)
                current_parent_end = child.metadata.get("end", current_parent_end)

        flush_parent()

        # 第二遍：同一 code_block_id 的 child 强制共享 parent_id（用首个 child 的）
        # 这样 parent 展开后能把整段代码拼回去
        code_block_to_parent: dict[str, str] = {}
        for child in child_chunks:
            cbid = child.metadata.get("code_block_id")
            if not cbid:
                continue
            if cbid not in code_block_to_parent:
                code_block_to_parent[cbid] = child.metadata["parent_id"]
            else:
                # 强制绑回首个 child 的 parent_id
                child.metadata["parent_id"] = code_block_to_parent[cbid]

        # 第三遍：按最终 parent_id 聚合建 parent Document
        # 同一 parent_id 可能有多个 section_records（代码块跨越 H2 时），需合并
        parent_agg: dict[str, dict] = {}
        for sec in section_records:
            pid = sec["id"]
            # 该 section 内 child_ids 中,凡被强制改写 parent_id 的，归到目标 section
            for cid in sec["child_ids"]:
                # 找到对应 child
                ch = next((c for c in child_chunks if c.metadata.get("chunk_id") == cid), None)
                if ch and ch.metadata.get("parent_id") != pid:
                    # 已被改写到别的 parent:不计入本 section 的 child_ids
                    sec["child_ids"] = [c for c in sec["child_ids"] if c != cid]
                    sec["text_parts"] = [
                        c.page_content for c in child_chunks
                        if c.metadata.get("chunk_id") in sec["child_ids"]
                    ]
            agg = parent_agg.setdefault(pid, {
                "heading": sec["heading"],
                "level": sec["level"],
                "position": sec["position"],
                "end": sec["end"],
                "child_ids": set(),
                "text_parts": [],
            })
            agg["child_ids"].update(sec["child_ids"])
            agg["text_parts"].extend(sec["text_parts"])
            agg["position"] = min(agg["position"], sec["position"])
            agg["end"] = max(agg["end"], sec["end"])

        for pid, agg in parent_agg.items():
            text = "".join(agg["text_parts"]).rstrip()
            if not text:
                continue
            parents.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": source,
                        "chunk_id": pid,
                        "position": agg["position"],
                        "end": agg["end"],
                        "heading": agg["heading"],
                        "level": agg["level"],
                        "is_code": False,
                        "doc_kind": "parent",
                        "child_ids": sorted(agg["child_ids"]),
                    },
                )
            )

        children.extend(child_chunks)

    return parents, children