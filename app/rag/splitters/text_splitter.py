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

    def flush_code() -> None:
        nonlocal code_buffer
        c = _build_chunk(code_buffer, code_start, source, code_heading, code_level, is_code=True)
        if c:
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