# 权衡卡 04 · RAG 检索前是否做 Query 改写 / HyDE

> 场景：RAG 系统召回率低（< 70%），评估要不要在检索前加 query rewrite / HyDE 步骤。

---

## 设计 1：直接检索（不动 query）

```python
docs = vector_db.search(user_query)
answer = llm.ask(user_query, docs)
```

### 收益
- **实现极简**——5 行代码
- **latency 最低**——1× 检索耗时
- **成本最低**——1× LLM 调用
- **稳定性最高**——不依赖 LLM 生成质量

### 代价
- **短 query 召回差**——用户口语化输入（如"那个文档里说的啥"）几乎匹配不到
- **专业 query 也召回低**——多义词、同义词、缩写
- **新领域更差**——语料里没有同义改写

### 备选方案
- HyDE / Query Rewrite

### 为什么没选备选（最初）
- 系统刚上线，query 都是技术员手写，问句完整
- 加了 LLM 调用 latency 翻倍，演示时被嫌慢

---

## 设计 2：HyDE（Hypothetical Document Embeddings）

```python
# 1. LLM 先"猜"答案
hypothetical_doc = llm.invoke(f"请基于以下问题写一段可能的答案：{user_query}")
# 2. 用"假答案"去检索
docs = vector_db.search(hypothetical_doc)
# 3. LLM 答
answer = llm.ask(user_query, docs)
```

### 收益
- **召回显著提升**——短 query 效果 +20-30%
- **解决"query-doc 语义鸿沟"**——用户问的问题和文档里的表述往往不一样，HyDE 让"假答案"和"真文档"在同一向量空间
- **实现相对简单**——只需在检索前插一步

### 代价
- **latency 翻倍**——多一次 LLM 调用（500ms+）
- **成本翻倍**——每次 query 多调一次 LLM
- **依赖 LLM 质量**——LLM 生成的"假答案"如果不靠谱，反而拉低检索
- **效果抖动**——不同 query 改写质量差异大，召回方差大

### 备选方案
- 多 query 检索（Query Expansion）
- 直接检索 + 改 query 让用户自己重写

### 为什么没选备选
- HyDE 比多 query 少调 2 次 LLM（成本 2× vs 4×）
- 改 query 体验差，用户流失

---

## 设计 3：Query Expansion（多 query 检索）

```python
queries = llm.invoke(f"把以下问题改写成 3 个不同表述：{user_query}")
all_docs = []
for q in queries:
    all_docs.extend(vector_db.search(q))
all_docs = dedupe(all_docs)
answer = llm.ask(user_query, all_docs)
```

### 收益
- **召回进一步提升**——多角度搜，覆盖率高
- **不依赖单一 LLM 生成质量**——3 个 query 中至少 1-2 个靠谱

### 代价
- **latency 4×**——3 次额外 LLM 调用
- **成本 4×**——3 次额外 LLM 调用
- **去重逻辑复杂**——多路召回合并去重，工程量不小
- **top-k 分配**——3 路各取多少？合并后怎么重排？

### 备选方案
- HyDE
- 直接检索

### 为什么没选备选
- 3× LLM 调用对实时 RAG 太贵
- 实测比 HyDE 提升 < 5 个点，性价比差

---

## 选型决策树

```
query 平均 < 10 字 (口语化)     → 必加 query rewrite (HyDE)
query 平均 10-50 字 (专业)     → 看 latency 预算
query 平均 > 50 字 (搜索框)    → 直接检索
当前召回率 > 90%               → 别折腾
当前召回率 < 70%               → 必加
latency 预算 < 2s              → 别加 HyDE, 用 Expansion + cache
```

---

## 项目里的最终选择

**选 HyDE**，理由：
1. 我们的 query 80% < 20 字（用户口语化提问）
2. 召回率从 65% → 88%，**提升 23 个点**
3. 接受 2× latency（2s → 4s），因为是内部工具不是 toC
4. 不选 Expansion：4× latency 用户受不了；3 路去重重排太复杂

**埋的坑**：
- HyDE 生成质量抖动 → 监控 "query 改写置信度"，低分走 fallback 直接检索
- 冷启动 LLM 慢 → 第一次请求用更小的模型生成 hypothetical

---

## 这个权衡教会我什么

1. **没有银弹**——同样的 query 改写方案在 A 项目是神器，在 B 项目是鸡肋
2. **"够用就好"是工程真理**——召回率 90% 的时候别硬上 HyDE
3. **代价是分层级的**——latency 翻倍在内部工具可接受，在 toC 直接被骂
4. **必须有 fallback**——LLM 生成质量不稳，HyDE 不工作时直接检索兜底
