# A3 · Chroma 索引结构 学习笔记

> 目标：能不看笔记答出 4 题 → 通过
> 资料：Chroma 官方文档 Architecture 章节 + chromadb/utils/embedding_functions.py

---

## 一、向量检索为什么需要索引

| 规模 | 推荐 | 原因 |
|---|---|---|
| < 10 万 | FLAT 或 HNSW | 数据小 |
| 10 万 - 1000 万 | **HNSW** | O(log N) 优势明显 |
| 1000 万 - 1 亿 | IVF_PQ 或 HNSW + 量化 | 内存扛不住 |
| > 1 亿 | IVF_PQ + 分片 / 分布式 | 必须分布式 |

**10 万条用 FLAT 也能扛为啥还要建索引**：
1. **常数项 + 内存** — 每次查询要 load 全量向量进 cache
2. **不可扩展** — 10 万→1000 万，FLAT 直接挂
3. **O(N) → O(log N)** — 不是"快一点"，是数量级差距

---

## 二、HNSW 是什么

**全称**：Hierarchical Navigable Small World（分层可导航小世界图）

**类比**：跳表（Skip List）的图版本
- 底层：完整近邻图（每节点连最近 M 个邻居）
- 上层：稀疏快速通道
- 搜索：从顶层贪心 → 降层 → 底层 kNN

**搜索过程**：
```
1. 从顶层入口节点出发
2. 贪心走到离 query 最近的节点
3. 下降一层
4. 重复 2-3
5. 到底层时已经非常接近 query
6. 底层做精确 kNN
```

**为什么能 work**：近邻图的边连接的在向量空间里也近，贪心走不会偏

**复杂度**：O(log N)

---

## 三、HNSW 关键参数

| 参数 | 控制 | 调大代价 | 调小代价 |
|---|---|---|---|
| **M** | 每节点邻居数 | 精度高、内存多 | 略低精度、省内存 |
| **ef_construction** | 构建时候选数 | 召回高、构建慢、内存多 | 构建快、召回略低 |
| **ef_search** | 查询时候选数 | 召回高、查询慢 | 查询快、召回略低 |

> **M 决定图的密度，ef_construction 决定构建多认真，ef_search 决定查询多认真**

---

## 四、Chroma 三件套

| 存储 | 存什么 | 为什么 |
|---|---|---|
| **SQLite** | collection 元信息（名字/schema/dimension） | 关系型、CRUD 友好 |
| **DuckDB** | embedding + HNSW 图 | 列存、向量扫描快 |
| **Parquet** | 原文 + metadata | 列存、压缩、不可变文件 |

**类比**：
- SQLite = 档案室总账本
- DuckDB = 档案室索引柜
- Parquet = 压缩饼干罐头

**记忆口诀**：**元信息进 SQLite，向量进 DuckDB，原文进 Parquet**

---

## 五、4 题自问自答

### Q1: Chroma 默认底层是 HNSW 吗？全称？复杂度？
- ✅ 是 HNSW
- ✅ Hierarchical Navigable Small World
- ✅ O(log N)

### Q2: 10 万条内 FLAT 也能扛，为何要建索引？
1. 内存/常数项（每次查询 load 全量向量）
2. 数据增长时 FLAT 不可扩展
3. 质的区别：O(N) vs O(log N)

### Q3: M 和 ef_construction 控制什么？调大代价？
- M = 每节点邻居数
- ef_construction = 构建时候选宽度
- 调大：精度高、内存多、构建慢

### Q4: Chroma 持久化底层用什么？
- SQLite（元信息）+ DuckDB（向量+HNSW）+ Parquet（原文+metadata）

---

## 六、面试可能追问 & 我的回答

| 追问 | 一句话 |
|---|---|
| FLAT 什么时候用？ | 数据小、要 100% 召回、偶尔查 |
| IVF 是什么？ | KMeans 聚类，搜最近几个簇 |
| PQ 是什么？ | 向量分段量化，内存压缩 32 倍 |
| HNSW 内存怎么算？ | O(N·M·4字节)  — 千万条 × M=32 ≈ 1.2GB |
| 为啥不用 Milvus？ | Milvus 分布式能力强，但运维重；Chroma 适合单机/小规模 |
| HNSW 索引能动态加新向量吗？ | 能，但要重建图（百万级重建几小时），生产环境要分批 |

---

## 七、通过自评

- [x] 不看笔记能答 Q1
- [x] 不看笔记能答 Q2（3 个原因）
- [x] 不看笔记能答 Q3
- [x] 不看笔记能答 Q4
- [x] 能手画 HNSW 分层结构
- [x] 能说出三件套名字和职责
