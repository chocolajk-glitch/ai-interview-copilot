# 权衡卡 01 · FlagEmbedding CLS pooling vs sentence-transformers Mean pooling

> 场景：同一个 BGE 模型（bge-small-zh-v1.5），用两个不同库加载，算出的向量不一样——因为默认 pooling 不同。
> 现象：项目里早期用 FlagEmbedding 算的向量库里存的 query 跟 sentence-transformers 算的 query 算相似度时，召回率异常低。

---

## 设计 1：FlagEmbedding 默认 CLS pooling

```python
def pooling(self, last_hidden_state, attention_mask=None):
    if self.pooling_method == 'cls':
        return last_hidden_state[:, 0]   # 只取 [CLS] 那一行
```

### 收益
- **实现极简**：一个 `[:, 0]` 切片，零额外计算
- **跟 BERT 预训练目标一致**：NSP 任务就是用 [CLS] 预测"两句是否相邻"，BGE v1.5 训练时大概率也围绕 [CLS] 优化
- **推理快**：少一个 mean 计算，batch 大时有微小性能优势

### 代价
- **信息利用率低**：只用 1 个 token 的向量，剩下 511 个全扔了
- **对短文本特别敏感**：[CLS] 预训练时见过的是长上下文，遇到超短 query（如 1-2 个词）时[CLS] 向量可能没充分激活
- **跟主流 sentence-transformers 不兼容**：跨库算的向量算相似度会失效

### 备选方案
- sentence-transformers 默认的 mean pooling
- 自己实现 weighted mean（用 attention 倒数第二层权重加权）

### 为什么没选备选
- FlagEmbedding 是 BGE **官方**维护的库，作者认为 CLS 已经够用
- 工程上"跟官方一致"减少意外风险

---

## 设计 2：sentence-transformers 默认 Mean pooling

```python
s = (h * mask.unsqueeze(-1).float()).sum(dim=1)
d = mask.sum(dim=1, keepdim=True).float()
return s / d
```

### 收益
- **全员投票**：用上所有 token，信号更稳
- **短文本友好**：3 个 token 也能算 mean，不会因 [CLS] 单点失效
- **学术界背书**：SBERT/Reimers 2019 论文证明 mean 普遍优于 CLS

### 代价
- **实现稍复杂**：要处理 mask（pad 位置不计入分母）
- **跟 BGE 官方不一致**：BGE 训练时未必针对 mean 优化，向量分布可能跟官方 demo 算的有偏差
- **pad 噪声风险**：mask 实现错一位，整个 batch 算出的向量会污染

### 备选方案
- FlagEmbedding 的 CLS pooling
- [CLS] + dense + tanh（BERT 原始 pooler，BGE 推理时**不**用这个）

### 为什么没选备选
- mean 是 sentence-transformers 库的硬编码默认，改了等于偏离 ST 生态
- 改 CLS 会跟 BGE 官方 README 算出的向量不一致，文档/demo 全失效

---

## 我的项目应该选哪个？

**结论**：跟项目的"现状"绑定，不要混用。

| 场景 | 推荐 |
|---|---|
| 库只用 FlagEmbedding | 跟官方：CLS |
| 库只用 sentence-transformers | 跟生态：Mean |
| 混合 / 历史数据有 FlagEmbedding 算的 | **统一到 Mean**（ST 路线），重算历史 embedding，否则新旧向量算相似度会失效 |
| 微调 BGE 自己做训练 | 看训练时用哪个 pooling（`--sentence_pooling_method`），推理时必须一致 |

---

## 这个权衡教会我什么

1. **同一模型不同封装 = 行为可能不同**，不能假设"加载 BGE = 同一个向量"
2. **默认值是设计选择，不是真理**——FlagEmbedding 和 ST 各自有理由，但**不互通**
3. **工程上的"约定"比"理论最优"重要**——项目里一旦选定，混用代价远大于选错代价
