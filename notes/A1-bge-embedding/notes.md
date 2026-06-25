# A1 · BGE Embedding 原理 学习笔记

> 目标：能不看笔记答出 4 题 → 通过
> 资料：
> 1. BGE 官方文档 https://bge-model.com/bge/bge_v1_v1.5.html
> 2. HuggingFace `BAAI/bge-small-zh-v1.5` 的 `config.json`（已读）
> 3. FlagEmbedding `BaseEmbedder.pooling` 源码（已读）
> 4. 推理时数据流的真实代码路径

---

## 一、关键事实（来自 config.json，对的）

| 字段 | bge-small-zh-v1.5 | bge-base-zh-v1.5 | bge-large-zh-v1.5 |
|---|---|---|---|
| 参数量 | 24M | 102M | 326M |
| hidden_size | **512** | **768** | 1024 |
| num_hidden_layers | 4 | 12 | 24 |
| num_attention_heads | 8 | 12 | 16 |
| intermediate_size | 2048 | 3072 | 4096 |
| vocab_size | 21128 | 21128 | 21128 |
| max_position_embeddings | 512 | 512 | 512 |
| architectures | BertModel | BertModel | BertModel |

> **注**：文档第一版我写成 768 维和 6 层，已修正。网上部分博客（zilliz 那篇写 small=384）也错，config.json 才是 ground truth。

---

## 二、数据流图（基于真实源码）

```
输入: sentences = ["今天天气真好", "明天要下雨"]
     │
     ▼
[Tokenizer]  (BertTokenizer, vocab=21128, WordPiece)
     │
     ▼  add [CLS]...[SEP]
input_ids: (B, L)  attention_mask: (B, L)  token_type_ids: (B, L) 全 0
     │
     ▼
[BertModel]  (transformers 加载, 4 层 for small)
   Embedding:
     token_embed     : (B, L, 512)
     position_embed  : (B, L, 512)   max=512, absolute
     token_type_embed: (B, L, 512)   2 种
     sum + LayerNorm + Dropout(0.1)
   Encoder × 4:
     MultiHeadSelfAttn(8 heads, 双向, no causal mask)
       + Add&LayerNorm
     FFN(512 → 2048 → 512, GELU)
       + Add&LayerNorm
     │
     ▼
last_hidden_state  shape = (B, L, 512)   # 每个 token 都有 512 维向量
     │
     ▼
[Pooling: BaseEmbedder.pooling]  (FlagEmbedding 默认)
   if method == 'cls':
       return last_hidden_state[:, 0]                # 取 [CLS]
   elif method == 'mean':
       s = (h * mask.unsqueeze(-1)).sum(dim=1)
       d = mask.sum(dim=1, keepdim=True)
       return s / d                                  # mask 后的均值
     │
     ▼
embeddings  shape = (B, 512)
     │
     ▼
[L2 Normalize]  (normalize_embeddings=True 时)
   F.normalize(embeddings, p=2, dim=-1)              # 模长 = 1
     │
     ▼
最终 sentence embedding, shape = (B, 512), 单位向量
```

**关键源码（已读到）**:
```python
# FlagEmbedding/inference/embedder/encoder_only/base.py
def pooling(self, last_hidden_state, attention_mask=None):
    if self.pooling_method == 'cls':
        return last_hidden_state[:, 0]
    elif self.pooling_method == 'mean':
        s = torch.sum(last_hidden_state * attention_mask.unsqueeze(-1).float(), dim=1)
        d = attention_mask.sum(dim=1, keepdim=True).float()
        return s / d
    else:
        raise NotImplementedError(...)

# 在 encode() 主循环里:
last_hidden_state = self.model(**inputs, return_dict=True).last_hidden_state
embeddings = self.pooling(last_hidden_state, inputs_batch['attention_mask'])
if self.normalize_embeddings:
    embeddings = torch.nn.functional.normalize(embeddings, dim=-1)
```

**两个易错点**（面试可能问）：
1. **没有 dense 投影层**。hidden_size 就是输出 embedding 维度。文档里默认的"BertPooler"（含 dense+tanh）**没有在 BGE 推理中使用**，因为 FlagEmbedding 直接取 last_hidden_state 跳过 pooler。BertModel 的 pooler 是 BERT 预训练 NSP 任务用的，BGE v1.5 推理时不用。
2. **不同封装默认 pooling 不一样**：FlagEmbedding 默认 `cls`，sentence-transformers 默认 `mean`。两个库加载同一个 `bge-small-zh-v1.5` 算出的向量**会不一样**（如果用 ST 包装 ST 内部明确写了 `mean`）。

---

## 三、4 题自问自答

### Q1: BGE 用的是 BERT 类的双向 Transformer 还是 GPT 类的单向？为什么检索场景要双向？

**答**:
- **双向** (BERT 类，encoder-only)。`config.json` 里 `architectures: ["BertModel"]`，self-attention **没有 causal mask**，每个 token 能 attend 到序列中所有其他 token。
- 检索场景要双向的原因：
  - 检索是"语义匹配"，不是"生成"。给定 query 和 doc，需要从两端各自编码向量再做相似度比较。
  - **否定语义依赖双向**："我**不**喜欢" → "不喜欢"必须能在同一句里互相看见，单向注意力看不到前面。
  - **[CLS] 位置的语义需要看完整句子**：BGE 用 CLS pooling（第 0 个位置），它要"代表全句"，必须能 attend 到所有 token。
  - 单向 (GPT 类) 适合生成下一个 token，不适合"整句浓缩成一个向量"。

**追问可能：单向也能做检索吗？**
- 能，但通常用作 decoder-only LLM 拿 embedding（如 `text-embedding-3-small` 用了类似 trick）。BGE 选 BERT 路线是更直接的工程选择：预训练目标（NSP+MLM）和检索目标（语义匹配）天然匹配。

### Q2: pooling 阶段为什么 [CLS] 和 mean pool 都能用？两者效果差多少？

**答**:
- **为什么能用**：
  - **CLS**：BERT 预训练时 NSP/MLM 任务把 [CLS] 当作"整句浓缩位"训练过，理论上它已经能代表全句。
  - **Mean**：BERT 每一层输出每个 token 的 hidden state 都已经是**上下文感知**的（双向 attention 让每个 token 看到全句），所以对这些 token 取平均等价于"全员投票"。
- **效果差多少**：
  - 经验结论：**mean pooling 普遍略优于 CLS pooling**（1-3 个点），尤其在 sentence-level semantic similarity 任务上。
  - 来源：sentence-transformers/Reimers 论文、GTE/E5 等公开对比。
  - **BGE 官方两个封装的默认 pooling 还不一样**：FlagEmbedding 默认 `cls`，sentence-transformers 包装默认 `mean`。这本身就是个"工程上没有银弹"的证据——差得不大，所以没统一。
- **一句话记忆**：mean pool 是工程实践的默认选择（ST 路线），CLS 是 BERT 预训练任务的副产物（FlagEmbedding 路线）。

**追问可能：还有哪些 pooling 方式？**
- `last_token`：取最后一个非 padding token（decoder-only LLM 常用，比如 Qwen3-Embedding）
- `weightedmean`：用 attention mask 倒数第二层权重加权平均
- `[CLS] + dense + tanh`：BERT 原始 pooler，BGE 推理不用

### Q3: 为什么最后要做 L2 归一化？（提示：归一化后内积 = 余弦相似度）

**答**:
- 余弦相似度公式: `cos(a, b) = <a, b> / (||a|| · ||b||)`
- 如果 `||a|| = ||b|| = 1`，那么 `cos(a, b) = <a, b>`
- **工程意义**：
  1. **检索时只需算内积** → 走矩阵乘 (`emb @ emb.T`) + FAISS/GPU 向量库，吞吐远高于算余弦
  2. **统一相似度尺度**：向量模长不再干扰排序，纯粹看方向。**否则长文档模长大，会被错误地判为更相似**
  3. **训练/推理一致**：InfoNCE 损失里 normalize 后的内积直接当 logits
- **不归一化的代价**：必须算 `||a||` 和 `||b||`，相似度结果受模长干扰，FAISS 只能用欧氏距离索引（慢）。
- **BGE v1.5 的改进点**（README 重点强调）：v1.5 改了相似度分布，让 `[不归一化也能用点积]` 时分数更合理。但**官方推荐仍然是 L2 归一化后用内积**。

**追问可能：内积和点积是同一个东西吗？**
- 数学上一样。但在 embedding 场景我们强调的是"cos similarity 通过归一化降维到 inner product"。

### Q4: 微调时 BGE 用的是什么损失？（提示：对比学习 InfoNCE）

**答**:
- **InfoNCE** (Information Noise-Contrastive Estimation)，形式:
  ```
  L = -log( exp(sim(q, p+) / τ) / Σ_i exp(sim(q, pi) / τ) )
  ```
  - `q`: query embedding
  - `p+`: positive (相关 doc)
  - `pi`: negatives (不相关 doc, 通常 batch 内其他样本 + 难负样本)
  - `τ`: 温度系数，BGE 微调典型 0.01~0.05
- **直观理解**:
  - 把 (q, p+) 的相似度往大了拉
  - 把 (q, 其他所有) 的相似度往小了推
  - 分子只有 1 个正样本，分母 1 个正 + N 个负，**结构类似多分类交叉熵**
- **BGE 微调的关键增强 — 难负样本挖掘 (Hard Negative Mining)**：
  - 简单负样本：batch 内随机其他 doc。**太容易**，模型学不到东西。
  - 难负样本：用 BM25/第一版 BGE 检索出"看起来相关、其实不相关"的样本。**让模型必须真正理解语义**才能把它们推开。
  - BGE 训练 pipeline：`BM25 粗排 → top-K 召回 → 人工/规则挑难负 → InfoNCE`
- **同 batch 共享负样本的优化**：`--negatives_cross_device` 把多卡 batch 合并算 logits，**有效负样本数 = world_size × batch_size**。

**追问可能：InfoNCE 和 triplet loss 的区别？**
- Triplet: `L = max(0, d(a, p) - d(a, n) + margin)`，只关心 1 个负样本
- InfoNCE: 1 个正 + N 个负，**softmax 形式**让所有负样本都参与梯度，训练更稳定
- InfoNCE 在 batch 大时等价于一个大分类问题，效果通常更好

---

## 四、面试可能追问 & 我的回答清单

| 追问 | 关键词 | 一句话回答 |
|---|---|---|
| BERT 和 RoBERTa 在 BGE 里有什么区别？ | 后归一化 | BGE base 在 BERT 基础上做了 L2 归一化后训练（scaled cosine similarity） |
| BGE 怎么处理长文本（>512 token）？ | 截断 / 分段 | 推理时直接截断到 512，训练时用 overlap 分段（实际工程中也会切 chunk） |
| v1 和 v1.5 的区别？ | 相似度分布 | v1.5 优化了相似度分数分布，让 cosine 分数更集中在合理区间 |
| BGE 和 text-embedding-3-small (OpenAI) 区别？ | 训练数据 + 架构 | OpenAI 用 decoder-only + 对比学习，BGE 用 encoder BERT + InfoNCE；中文 BGE 显著强于通用模型 |
| 怎么选 small / base / large？ | 速度 vs 精度 | small 24M 适合端侧/低延迟，base 平衡，large 在 MTEB 上明显领先但慢 3-5x |

---

## 五、通过自评（学完后勾）

- [ ] 不看笔记能答 Q1 双向 vs 单向
- [ ] 不看笔记能答 Q2 pooling 差异 + 真实源码
- [ ] 不看笔记能答 Q3 L2 归一化的工程意义
- [ ] 不看笔记能答 Q4 InfoNCE 形式和温度系数
- [ ] 能手画数据流图 (token → embedding → encoder → pool → norm)
- [ ] 能说出 small/base/large 的 hidden_size 数字
- [ ] 能说出"没有 dense 投影"和"两个封装默认 pooling 不一致"两个易错点
