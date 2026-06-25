# AI 面试助手 (RAG Interview Copilot)

> 基于 LangGraph Agentic RAG 的垂直领域问答系统，支持文档上传、带引用溯源答案、自适应反思重检索。

[![Python](https://img.shields.io/badge/Python-3.13-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)]()
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)]()
[![License](https://img.shields.io/badge/license-MIT-lightgrey)]()

---

## ✨ 核心特性

| 模块 | 设计 |
|---|---|
| **混合检索** | BM25 稀疏 + 向量稠密 + RRF 融合 + BGE-Rerank 精排 |
| **Parent-Child 索引** | parent 按 H2 切保留上下文、child 按段落切用于精准召回 |
| **意图分流** | factual / code / chat 三类，code 意图下扩候选池并优先召回代码块 |
| **多模型工厂** | DeepSeek / Qwen / MiniMax 一键切换 + 自动降级 |
| **自适应反思** | Reflection 节点结构化 JSON 评估 + 4 档重试策略（expand_k → rewrite_query → hyde → fallback） |
| **引用溯源** | [1][2][3] 标注来源 chunk + 文档级 SHA-256 去重 |
| **流式输出** | SSE 协议 + Redis TTL 缓存避免重复 Embedding |

---

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Vue 3 + Vite)                 │
└─────────────────────────────────────────────────────────────┘
                              │ SSE / HTTP
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend                                 │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            LangGraph Agentic RAG Workflow             │   │
│  │                                                        │   │
│  │  START → query_analyzer ─┬→ query_rewriter →          │   │
│  │            │              │  retriever → reranker →    │   │
│  │            │              │  generator → reflection ───┤   │
│  │            └→ [chat 路径] → generator ────────────────┤   │
│  │                                          │             │   │
│  │                                          │ [verdict]   │   │
│  │                          ┌───────────────┴──────┐      │   │
│  │                  [pass]   │  [fail]               │      │   │
│  │                          ▼                       ▼      │   │
│  │                         END  ←── fallback   retry→retriever/rewriter │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Parent-Child Indexing (text_splitter)         │   │
│  │                                                        │   │
│  │  markdown 文件                                          │   │
│  │     ↓ split_markdown (单遍扫描 + 状态机)                │   │
│  │  child chunks (500 字符, is_code, heading)             │   │
│  │     ↓ split_parent_child (三遍算法)                     │   │
│  │  ┌─────────────────────┐    ┌─────────────────────┐   │   │
│  │  │ parents (按 H2 切)   │    │ children (检索用)   │   │   │
│  │  │ → parents.json       │    │ → Chroma + BM25    │   │   │
│  │  └─────────────────────┘    └─────────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │     Multi-Model Factory (llm/factory.py)              │   │
│  │  FallbackChatModel: invoke/ainvoke/stream/astream     │   │
│  │  DeepSeek → Qwen → MiniMax (按性能+成本降级)            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
            Chroma         Redis         SQLite
        (vector index)  (history+TTL)  (docs+meta)
```

---

## 📂 项目结构

```
ai-interview-copilot/
├── backend/
│   ├── app/
│   │   ├── api/                  # FastAPI 路由
│   │   │   ├── chat.py           # /api/chat/ask + /stream + /agent
│   │   │   ├── document.py       # /api/document/upload + /list
│   │   │   └── eval.py           # /api/eval/ragas
│   │   ├── graph/                # LangGraph 状态图
│   │   │   ├── workflow.py       # 6 节点 + 2 条件边
│   │   │   ├── nodes.py          # analyzer/rewriter/retriever/reranker/generator/reflection
│   │   │   └── state.py          # GraphState TypedDict
│   │   ├── llm/
│   │   │   └── factory.py        # FallbackChatModel 多模型降级
│   │   ├── rag/
│   │   │   ├── splitters/        # split_markdown + split_parent_child
│   │   │   ├── retrievers/       # BM25 + 向量 + HybridRetriever
│   │   │   ├── rerankers/        # BGE rerank
│   │   │   ├── embeddings/       # BGE 模型
│   │   │   ├── citations/        # 引用溯源
│   │   │   └── cache/            # Redis embedding 缓存
│   │   ├── eval/                 # RAGAS 评估
│   │   ├── memory/               # Redis + 内存两种历史后端
│   │   ├── models/               # SQLAlchemy ORM
│   │   └── core/                 # config + logging
│   ├── data/
│   │   ├── corpus/               # 语料 md 文件
│   │   ├── processed/            # parents.json + chunks.json
│   │   ├── chroma/               # 向量索引持久化
│   │   ├── logs/                 # reflection.jsonl 结构化日志
│   │   └── uploads/              # 用户上传文件
│   ├── tests/                    # pytest 测试
│   │   ├── test_parent_child.py
│   │   ├── test_parent_child_hybrid.py
│   │   └── ...
│   └── pyproject.toml
├── frontend/                     # Vue 3 + Vite + Element Plus
├── docs/                         # 架构图 + 笔记
├── notes/                        # 学习卡（tradeoff-cards / motivation-cards）
├── first-interview.md            # 第一次面试复盘
└── README.md
```

---

## 🚀 快速开始

### 1. 安装依赖
```bash
cd backend
poetry install   # 或 pip install -r requirements.txt
cp .env.example .env  # 填入 LLM API Key
```

### 2. 构建索引（首次）
```bash
poetry run python scripts/build_index.py
```

### 3. 启动后端
```bash
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. 启动前端
```bash
cd frontend
npm install
npm run dev
```

打开 `http://127.0.0.1:5173` 即可使用。

---

## 🧪 运行测试

```bash
cd backend
poetry run pytest                                    # 全部测试
poetry run pytest tests/test_parent_child.py -v      # Parent-Child 专项
poetry run pytest tests/test_parent_child_hybrid.py -v
```

**测试覆盖（13+ 场景）**：
- ✅ Parent-Child 三遍算法（按 H2 聚合、child 关联、代码块共享）
- ✅ expand_to_parents（去重、截断、缺失降级）
- ✅ Hybrid 集成（默认展开 / 关闭展开 / 同 parent 去重）

---

## 🎯 设计动机（面试应答要点）

### 为什么用 Parent-Child？
**单层切分**的问题：chunk 太小喂 LLM 时上下文断裂（"反转链表"问题讲了一半就丢）；**只切大块**的问题：检索粒度粗，召回噪声多。
**Parent-Child 解法**：检索用 child（小、精准），喂 LLM 用 parent（大、完整）。

### 为什么不用 LangChain 内置 `ParentDocumentRetriever`？
| 我的实现 | LangChain 默认 |
|---|---|
| parent 单独存 JSON（不 embedding） | parent 存 docstore，child 存向量库 |
| 显式三遍算法处理代码块跨 H2 边界 | 单遍分配，边界 case 容易丢 |
| 缺失 parent 优雅降级 | 严格依赖映射 |

### 为什么做 Reflection 重试而不是只调 top_k？
**单纯调 k 收益小**——召回到的还是同一批文档。**4 档策略梯子**（expand_k → rewrite_query → hyde → fallback）让反思失败时逐步升级：先扩大召回、再换 query 角度、再用假设性答案、最后兜底。

### 为什么 three-tier 混合检索？
- **BM25** 补向量在专有名词/缩写上的召回弱（`def twoSum` / `HTTP 500`）
- **向量** 补 BM25 在语义相近但字面不同的召回弱
- **Rerank** 用 cross-encoder 做精细排序，比双塔向量准一个量级

---

## 📊 评估体系

RAGAS 4 指标：
- **Faithfulness**：答案拆 claim → 逐条对照上下文 → 比例
- **Answer Relevance**：答案反生成问题 → 与原 query 余弦相似度
- **Context Precision**：相关 doc 排在前列的比例
- **Context Recall**：ground-truth 信息在 context 中的覆盖率

---

## 📝 License

MIT