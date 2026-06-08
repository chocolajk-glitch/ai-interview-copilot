import base64
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.models.document import DocStatus


SAMPLE_MD_1 = """# 两数之和

给定一个整数数组 nums 和目标值 target。

## 思路

用哈希表记录已遍历数字到下标的映射。

## 代码

```python
def two_sum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        if target - n in seen:
            return [seen[target - n], i]
        seen[n] = i
```

## 复杂度

O(n) 时间，O(n) 空间。
"""

SAMPLE_MD_2 = """# 反转链表

给你单链表头节点 head，反转链表。

## 思路

双指针：prev 初始 None，curr 初始 head。

## 代码

```python
def reverse_list(head):
    prev, curr = None, head
    while curr:
        nxt = curr.next
        curr.next = prev
        prev = curr
        curr = nxt
    return prev
```

## 复杂度

O(n) 时间，O(1) 空间。
"""


def _b64(content: str) -> str:
    return base64.b64encode(content.encode("utf-8")).decode("ascii")


@pytest.fixture(autouse=True)
def _clean():
    """每个测试前后清理 Chroma 和数据库中的测试数据。"""
    import asyncio
    from app.rag.retrievers.vector_retriever import get_vector_store
    from app.models import async_session, Document as DocumentModel

    # 清理 Chroma
    vs = get_vector_store()
    try:
        vs.delete(where={"source": "test1.md"})
        vs.delete(where={"source": "test2.md"})
    except Exception:
        pass

    # 清理数据库
    async def _clean_db():
        async with async_session() as session:
            await session.execute(delete(DocumentModel))
            await session.commit()

    asyncio.run(_clean_db())

    yield

    # 测试后也清理
    try:
        vs.delete(where={"source": "test1.md"})
        vs.delete(where={"source": "test2.md"})
    except Exception:
        pass

    asyncio.run(_clean_db())


def test_doc_status_enum_values():
    assert DocStatus.PENDING.value == "pending"
    assert DocStatus.PROCESSING.value == "processing"
    assert DocStatus.READY.value == "ready"
    assert DocStatus.FAILED.value == "failed"
    assert DocStatus.DUPLICATE.value == "duplicate"


def test_upload_endpoint_returns_pending(client: TestClient):
    r = client.post(
        "/api/document/upload",
        json={"filename": "test1.md", "content_b64": _b64(SAMPLE_MD_1)},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("pending", "ready", "indexing")
    assert "doc_id" in data


def test_upload_duplicate_detected(client: TestClient):
    r1 = client.post(
        "/api/document/upload",
        json={"filename": "test1.md", "content_b64": _b64(SAMPLE_MD_1)},
    )
    doc_id_1 = r1.json()["doc_id"]
    time.sleep(0.5)
    r2 = client.post(
        "/api/document/upload",
        json={"filename": "test1.md", "content_b64": _b64(SAMPLE_MD_1)},
    )
    assert r2.json()["status"] == "duplicate"
    assert r2.json()["doc_id"] == doc_id_1


def test_status_endpoint_404(client: TestClient):
    r = client.get("/api/document/nonexistent/status")
    assert r.status_code == 404


def test_status_endpoint_returns_record(client: TestClient):
    r = client.post(
        "/api/document/upload",
        json={"filename": "test1.md", "content_b64": _b64(SAMPLE_MD_1)},
    )
    doc_id = r.json()["doc_id"]
    time.sleep(1.0)
    s = client.get(f"/api/document/{doc_id}/status")
    assert s.status_code == 200
    data = s.json()
    assert data["status"] in ("ready", "indexing", "pending")
    assert data["chunk_count"] > 0


def test_document_model_db_round_trip():
    """测试 Document ORM 模型可以正确写入和读取数据库。"""
    import asyncio
    from app.models import async_session, Document as DocumentModel

    async def _test():
        async with async_session() as session:
            doc = DocumentModel(
                doc_id="test-db-001",
                sha256="abc123",
                filename="test.md",
                status=DocStatus.READY,
                chunk_count=5,
                new_chunks=3,
                skipped_chunks=2,
            )
            session.add(doc)
            await session.commit()

            from sqlalchemy import select
            result = await session.execute(
                select(DocumentModel).where(DocumentModel.doc_id == "test-db-001")
            )
            fetched = result.scalar_one()
            assert fetched.filename == "test.md"
            assert fetched.status == DocStatus.READY
            assert fetched.chunk_count == 5
            assert fetched.new_chunks == 3
            assert fetched.skipped_chunks == 2

            # 清理
            await session.delete(fetched)
            await session.commit()

    asyncio.run(_test())
