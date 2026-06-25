# 权衡卡 03 · Chroma vs Milvus 向量库选型

> 场景：项目要做 RAG 知识库，向量库选 Chroma 还是 Milvus？

---

## 设计 1：Chroma（轻量级）

```python
import chromadb
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("docs")
collection.add(documents=["..."], embeddings=[...], ids=["..."])
results = collection.query(query_embeddings=[...], n_results=5)
```

### 收益
- **零运维** — `pip install` 就跑，不用起 server
- **单机嵌入式** — 适合原型 / 中小规模（< 千万级）
- **DuckDB + HNSW 性能不差** — 单机场景下查询快
- **API 极简** — 5 行代码跑通 add + query

### 代价
- **单机上限** — 千万级数据开始吃力，**亿级扛不住**
- **没有分布式** — 没法水平扩展
- **没有副本/高可用** — 单点故障
- **没有生产级监控** — prometheus/告警都得自己接

### 备选方案
- Milvus（分布式生产级）

### 为什么没选备选
- 项目当前数据量 < 50 万条，Chroma 完全够用
- 团队 3 人，没运维人力起 Milvus 集群
- 6 个月内不预期扩到亿级

---

## 设计 2：Milvus（分布式生产级）

```python
from pymilvus import MilvusClient
client = MilvusClient(uri="http://localhost:19530")
client.create_collection("docs", dimension=768)
client.insert("docs", [...])
client.search("docs", [...], limit=5)
```

### 收益
- **亿级 / 十亿级** — 生产环境验证过
- **分布式** — 多副本、sharding、负载均衡
- **多种索引** — HNSW / IVF / IVF_PQ / DiskANN 按需选
- **生产级特性** — RBAC、监控、备份、慢查询日志

### 代价
- **运维重** — 要起 etcd + MinIO + Milvus 多个容器
- **学习曲线** — schema 设计、索引参数、partition 策略
- **资源占用** — 至少 3 台机器起步
- **过度设计** — 项目早期用 Milvus 是杀鸡用牛刀

### 备选方案
- Chroma（轻量级）

### 为什么没选备选
- 当前规模 Chroma 够用
- 团队人手不够运维分布式

---

## 选型决策树

```
数据量 < 100 万 + 单机 + 快速原型 → Chroma
数据量 100 万-1 亿 + 单机能扛 → Chroma / Qdrant
数据量 > 1 亿 + 分布式 + 高可用 → Milvus / Weaviate
需要最强生态 + 云原生 → Qdrant
```

---

## 这个权衡教会我什么

1. **"够用就好"是工程第一原则** — 数据量没到 1 亿选 Milvus 是过度设计
2. **运维成本是被低估的代价** — Milvus 的"3 容器"在生产环境出问题时是真正的痛
3. **可迁移性是后路** — Chroma → Milvus 切换成本主要是**数据迁移 + 索引重建**，API 差异小。选 Chroma 不代表"上贼船"
4. **数据量是动态的** — 决策要按"未来 6-12 个月"的规模选，不是当前规模
