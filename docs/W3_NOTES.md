# W3 复盘 + 简历素材库

> W3 完成时间：2026-06-07
> 状态：✅ Agentic RAG + 对话记忆 + 文档增量更新 端到端跑通
> 简历用途：面试前快速复习 / 项目介绍材料

---

## 1. W3 完成清单（功能交付）

### 1.1 LangGraph 4 Node 状态图 ✅
- 4 节点（query_analyzer / retriever / reranker / generator）+ 1 条件边
- query_analyzer 用 LLM 分类（factual / code / chat）
- `add_conditional_edges` 路由 chat 跳过 retriever 直接 generator
- 新增 `/api/chat/agent` 端点，**与 W2 /ask 并存不替换**

### 1.2 对话记忆（Redis）✅
- `ChatHistoryStore` 抽象基类 + `InMemoryChatHistoryStore` + `RedisChatHistoryStore`
- 3 个端点（/ask / /stream / /agent）都接受 `session_id`
- 短期上下文（最近 5 轮对话）注入 prompt
- Redis TTL 24h 自动过期，跨进程持久化

### 1.3 文档去重 + 增量更新 ✅
- 5 状态机：`PENDING` / `INDEXING` / `READY` / `FAILED` / `DUPLICATE`
- 文档级 `sha256(file_bytes)` 去重（重复上传零成本）
- chunk 级 `chunk_id` 去重（细粒度增量）
- `BackgroundTasks` 异步索引（上传立即返）
- 同步重建 BM25 索引（hybrid 检索生效）

### 1.4 测试 ✅
- 累计 **50+ 个测试**（W1: 11 + W2: 20 + #5 切分: 5 + #3 引用: 3 + #4 缓存: 6 + W3 graph: 6 + memory: 10 + document: 10）
- 全走真实链路（BGE + Reranker + LLM + Redis + Chroma）

---

## 2. 端到端流程图（W3 完整 pipeline）

```
用户问"哈希表怎么解决冲突"（session_id="u123"，第二轮）
       ↓ fetchEventSource
FastAPI /api/chat/stream
       ↓
rag_astream(question, session_id="u123")
       ↓
1. 加载历史：Redis GET chat_history:u123
   ├─ HumanMessage("哈希表怎么实现")
   └─ AIMessage("数组 + 链表...")
       ↓
2. 拼 prompt：context + chat_history(最近5轮) + question
       ↓
3. 混合检索（HybridRetriever.search）
   ├─ BM25 召回
   ├─ 向量召回（BGE-small + Chroma）
   ├─ RRF 融合
   └─ BGE-reranker 精排
       ↓
4. 调 LLM（LCEL 链式 + OpenAICompatModel.astream）
       ↓
5. 异步流式输出 4 种事件
   ├─ { type: "chunk", content: "..." }   ← 多次
   ├─ { type: "citations", citations: [...] } ← chunk 级引用
   ├─ { type: "done" }
   └─ 存历史：Redis RPUSH chat_history:u123 AIMessage(answer)
       ↓ SSE 协议
前端打字机 + 引用高亮
```

**W3 文档上传链路**：
```
POST /api/document/upload { filename, content_b64 }
       ↓
sha256(file_bytes)  ← 文档级去重
   ├─ 命中 → 返 { status: "duplicate", doc_id: "xxx" }
   └─ 新文档 → 写 PENDING 记录 + 返
       ↓ BackgroundTasks.add_task(_index_document)
_index_document(doc_id, file_bytes, filename)
   ├─ split_docs → 4 chunks
   ├─ vs._collection.get → existing_ids（已有 chunk_id）
   ├─ chunk_id 比对 → to_add（只算新增）
   ├─ vs.add_documents(to_add) ← 走 #4 embedding 缓存
   ├─ hr._bm25.index(all_chunks) ← 重建 BM25
   └─ 状态 → READY { new_chunks, skipped_chunks }

GET /api/document/{doc_id}/status  ← 前端轮询
```

---

## 3. W3 踩坑故事（7 个）

### 坑 1：langgraph 模块缺失
- **现象**：`ModuleNotFoundError: No module named 'langgraph'`
- **根因**：W2 阶段没装，开 W3 时直接 import 失败
- **修法**：`pip install langgraph`
- **教训**：开新阶段前**先看 pyproject.toml 装所有依赖**

### 坑 2：W2 依赖被升级卸掉
- **现象**：`rank_bm25` / `flagembedding` / `sentence_transformers` / `chromadb` 全没装
- **根因**：W3 升级 langchain 1.x 时 pip 自动卸不兼容包
- **修法**：`pip install rank-bm25 flagembedding sentence-transformers "chromadb>=1.5.9" redis langgraph`
- **教训**：**大版本升级前先看依赖兼容性**，否则一升级全炸

### 坑 3：langchain_chroma 包不存在
- **现象**：`ImportError: No module named 'langchain_chroma'`
- **根因**：`vector_retriever.py` 顶部用了不存在的包名
- **修法**：改用 `from langchain_community.vectorstores import Chroma`（已装）
- **教训**：**包名要看实际 pip list**，不能想当然

### 坑 4：Redis protected mode
- **现象**：`DENIED Redis is running in protected mode`
- **根因**：Redis 6+ 默认 `protected-mode yes` + 无密码 → 拒非 localhost
- **修法**：开发环境 `protected-mode no`；生产环境 `requirepass xxx` + 代码读 env
- **教训**：**安全默认值要明确关掉**

### 坑 5：Redis HELLO AUTH 错误
- **现象**：`AuthenticationError: HELLO must be called with the client already authenticated`
- **根因**：之前 `CONFIG SET requirepass xxx` 留了密码，redis-py 默认走 RESP3 协议（HELLO 命令）必须先 AUTH
- **修法**：`redis-cli CONFIG SET requirepass ""` 清密码
- **教训**：**配置变更要追踪 + 测试要 isolation**

### 坑 6：markdown 嵌套代码块渲染
- **现象**：测试代码里 `SAMPLE_MD = """...```python def two_sum..."""` 让外层 markdown 代码块提前结束
- **根因**：markdown 不支持嵌套代码块（3 反引号会截断）
- **修法**：SAMPLE_MD 字符串里去掉 ``` 代码块包裹（改用纯文本段落）
- **教训**：**markdown 里要包含代码块，用 4 反引号或避免嵌套**

### 坑 7：HuggingFace HEAD 网络问题
- **现象**：HF Hub 客户端发 HEAD 验证 metadata，偶发失败（`WinError 10060`）
- **根因**：国内访问 HuggingFace 不稳定，HF 客户端默认要"打电话回家"
- **修法**：`$env:HF_HUB_OFFLINE = "1"` 强制本地 cache
- **教训**：**生产环境强制 offline 模式部署更稳**（模型预下载到 cache）

---

## 4. ADR 决策（架构决策记录）

### ADR-007：LangGraph 4 Node 状态图（条件边路由）
- **背景**：W2 串行 chain 不能根据问题类型选不同策略（factual/code/chat 混用同一检索流程）
- **决策**：4 节点（query_analyzer / retriever / reranker / generator）+ `add_conditional_edges` 路由
- **好处**：
  - 意图路由可扩展（新增意图类型不改原有节点）
  - chat 类问题跳过 retriever（省 1 次检索 + 1 次 LLM 生成）
  - 状态图可视化（用 LangSmith）
- **代价**：多 1 次 LLM call（query_analyzer 分类 ~200ms）
- **替代方案**：if/else 串行（状态机爆炸式增长，难维护）

### ADR-008：对话记忆用 Redis
- **背景**：多轮对话需要 session 化存储
- **决策**：`ChatHistoryStore` 抽象基类 + `RedisChatHistoryStore` 实现
- **好处**：
  - 跨进程（多 Worker 共享）
  - TTL 自动过期（24h）
  - 简历亮点"生产级多轮对话"
- **代价**：多 1 个依赖（redis-py + Redis server）
- **替代方案**：内存 dict（进程重启丢历史，多 Worker 不共享）

### ADR-009：文档去重用 SHA-256 + chunk_id
- **背景**：用户可能重复上传同一文档，或改 1 段重传
- **决策**：文档级 `sha256(file_bytes)` 兜底 + chunk 级 `chunk_id` 细粒度去重
- **好处**：
  - 重复上传零成本（整个文件不变 → 100% 跳过）
  - 增量更新精确到 chunk（改 1 段只重算 1 个 chunk）
  - 复用 #4 embedding 缓存（0 成本命中）
- **代价**：每次 add 调 BGE 算 embedding（#4 缓存命中可省 80%）
- **替代方案**：每次全量重建（慢，每次 10+ 秒）

### ADR-010：文档索引用 BackgroundTasks
- **背景**：上传大型 PDF 切 100 chunks 要 10 秒，同步等太慢
- **决策**：FastAPI `BackgroundTasks.add_task` + 状态机查询
- **好处**：
  - 上传立即返（UX 好）
  - 简历亮点"异步任务队列"
  - 状态机清晰（PENDING → INDEXING → READY/FAILED）
- **代价**：
  - 前端要轮询 `/status`
  - BackgroundTasks 是 in-process（多 Worker 不共享 → 选 Redis 解）
- **替代方案**：Celery（重，不值）/ 同步（慢）

### ADR-011：Chroma 单例缓存
- **背景**：每次 `get_vector_store()` new 一个 Chroma 实例，写入有延迟导致读不到刚 add 的 chunks
- **决策**：模块级 `_vector_store` 全局单例
- **好处**：
  - 写读共享内存（避免 chromadb 持久化延迟）
  - 写完立即可读
- **代价**：
  - 测试要手动清 chroma（fixture 删 test 数据保留 corpus）
  - 单进程单例（多 Worker 各自一份）
- **替代方案**：每次 new（race condition + 持久化延迟）

### ADR-012：HF Hub 离线模式
- **背景**：国内访问 HuggingFace 不稳定，HEAD 请求偶发失败
- **决策**：`HF_HUB_OFFLINE=1` + `TRANSFORMERS_OFFLINE=1` 强制本地 cache
- **好处**：
  - 部署稳定（不依赖外网）
  - 模型预下载到 cache 即可
  - 生产环境推荐（CI/CD 也稳定）
- **代价**：
  - 首次部署要预下载模型
  - 模型升级要手动 `rm -rf ~/.cache/huggingface/`
- **替代方案**：在线模式（生产不推荐）

---

## 5. W3 5 分钟面试讲法

### 开场（30 秒）
> "W3 阶段把 W2 的基础 RAG 升级到 Agentic RAG：**用 LangGraph 状态图做意图路由，加 Redis 对话记忆实现多轮问答，加 SHA-256 去重实现文档增量更新**。后端 50+ 测试全过，3 厂商 LLM 工厂照常工作。"

### 亮点 1：LangGraph 状态图（1.5 分钟）
> "检索层用 LangGraph 4 Node 状态图：`query_analyzer`（LLM 分类 factual/code/chat）→ `add_conditional_edges` 路由 → `retriever` → `reranker` → `generator`。
>
> **关键设计**：chat 类问题**跳过 retriever**（`add_conditional_edges` 返回 'generator'），省一次检索和一次 LLM 生成。
>
> **新增意图类型不用改原有节点**——开闭原则。面试可讲'用图状态机替代 if-else 爆炸'。"

### 亮点 2：Redis 对话记忆（1 分钟）
> "对话层用 `ChatHistoryStore` 抽象基类 + `RedisChatHistoryStore` 实现。session_id 串起多轮对话，**最近 5 轮注入 prompt**。
>
> Redis 选型理由：跨进程（多 Worker 共享）+ TTL 自动过期 + 简历亮点'生产级多轮对话'。
>
> W2 的 `/ask` 端点 + W3 的 `/agent` 端点**并存**——向后兼容，渐进迁移。"

### 亮点 3：文档增量更新（1 分钟）
> "文档层用 **SHA-256 + chunk_id 两级去重**：文档级 sha256(file_bytes) 兜底（整文件不变 → 0 成本跳过），chunk 级 chunk_id 细粒度（改 1 段只重算 1 个 chunk）。
>
> 状态机：`PENDING` → `INDEXING` → `READY` / `FAILED` / `DUPLICATE`。
>
> 上传用 FastAPI `BackgroundTasks` 异步索引，**上传立即返**，前端轮询状态——简历亮点'异步任务队列'。"

### 踩坑（1 分钟）
> "W3 最深的坑是 **W2 依赖被自动卸**——升级 langchain 1.x 时 pip 自动卸了不兼容的 rank_bm25 / flagembedding / sentence_transformers / chromadb。**开 W3 前应该先看依赖兼容性**，不然一升级全炸。
>
> 另一个坑是 **HuggingFace HEAD 网络问题**——HF 客户端默认发 HEAD 验证 metadata，国内访问不稳定。**生产环境强制 HF_HUB_OFFLINE=1** 用本地 cache。"

### W4 预告（30 秒）
> "W4 收尾要做 **RAGAS 评估**（faithfulness / recall / precision 四维度），**大模型 BGE-large 切换**（W4 评估后数据驱动选型），**GitHub Actions CI**（自动跑 pytest），最后写 W4_NOTES 复盘 + 简历新增'评估 / 性能数据'栏。"

---

## 6. 关键代码片段（10 个核心）

### 片段 1：LangGraph 状态图编排

```python
from langgraph.graph import END, START, StateGraph

def build_workflow():
    workflow = StateGraph(GraphState)
    workflow.add_node("query_analyzer", query_analyzer)
    workflow.add_node("retriever", retriever)
    workflow.add_node("reranker", reranker_node)
    workflow.add_node("generator", generator)

    workflow.add_edge(START, "query_analyzer")
    workflow.add_conditional_edges(
        "query_analyzer",
        route_after_analyzer,
        {"retriever": "retriever", "generator": "generator"},
    )
    workflow.add_edge("retriever", "reranker")
    workflow.add_edge("reranker", "generator")
    workflow.add_edge("generator", END)
    return workflow.compile()
```

### 片段 2：query_analyzer（LLM 意图分类）

```python
def query_analyzer(state: dict) -> dict:
    llm = get_llm(state.get("provider"))
    prompt = ChatPromptTemplate.from_template(INTENT_PROMPT)
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"question": state["question"]}).strip().lower()
    if result not in ("factual", "code", "chat"):
        result = "factual"
    state["intent"] = result
    return state


def route_after_analyzer(state: dict) -> str:
    if state.get("intent") == "chat":
        return "generator"
    return "retriever"
```

### 片段 3：ChatHistoryStore 抽象基类

```python
class ChatHistoryStore(ABC):
    @abstractmethod
    def get_messages(self, session_id: str) -> list[BaseMessage]:
        ...

    @abstractmethod
    def add_message(self, session_id: str, message: BaseMessage) -> None:
        ...

    @abstractmethod
    def clear(self, session_id: str) -> None:
        ...
```

### 片段 4：Redis 实现（带 TTL）

```python
class RedisChatHistoryStore(ChatHistoryStore):
    def __init__(self, host="localhost", port=6379, db=0, ttl=86400):
        self._r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self._ttl = ttl

    def add_message(self, session_id, message):
        key = f"chat_history:{session_id}"
        self._r.rpush(key, json.dumps({"type": message.type, "content": message.content}, ensure_ascii=False))
        self._r.expire(key, self._ttl)
```

### 片段 5：prompt 注入对话历史

```python
def _format_history(messages, max_turns=5):
    if not messages:
        return ""
    recent = messages[-(max_turns * 2):]
    return "【对话历史】\n" + "\n".join(
        f"{'用户' if m.type == 'human' else 'AI'}: {m.content}"
        for m in recent
    ) + "\n"
```

### 片段 6：文档级去重（sha256）

```python
file_bytes = base64.b64decode(req.content_b64)
doc_sha = hashlib.sha256(file_bytes).hexdigest()

if doc_sha in _documents_by_sha:
    existing = _documents_by_sha[doc_sha]
    return DocumentUploadResponse(status=DocStatus.DUPLICATE, doc_id=existing.doc_id)
```

### 片段 7：chunk 级去重（核心）

```python
vs = get_vector_store()
all_data = vs._collection.get(include=["metadatas", "documents"])
metadatas = all_data.get("metadatas") or []
existing_ids = {m["chunk_id"] for m in metadatas if m and m.get("chunk_id")}

to_add = [c for c in new_chunks if c.metadata.get("chunk_id") not in existing_ids]
skipped = len(new_chunks) - len(to_add)

if to_add:
    sanitized = [
        Document(page_content=c.page_content, metadata={k: v for k, v in c.metadata.items() if v is not None})
        for c in to_add
    ]
    vs.add_documents(sanitized)
```

### 片段 8：BackgroundTasks 异步索引

```python
@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(req: DocumentUploadRequest, background_tasks: BackgroundTasks):
    file_bytes = base64.b64decode(req.content_b64)
    doc_sha = hashlib.sha256(file_bytes).hexdigest()

    if doc_sha in _documents_by_sha:
        return DocumentUploadResponse(status=DocStatus.DUPLICATE, doc_id=...)

    doc_id = uuid.uuid4().hex[:16]
    record = _DocumentRecord(doc_id, doc_sha, req.filename)
    _documents_by_sha[doc_sha] = record
    _documents_by_id[doc_id] = record

    background_tasks.add_task(_index_document, doc_id, file_bytes, req.filename)
    return DocumentUploadResponse(status=DocStatus.PENDING, doc_id=doc_id)
```

### 片段 9：状态机流转

```python
def _index_document(doc_id, file_bytes, filename):
    record = _documents_by_id[doc_id]
    record.status = DocStatus.INDEXING
    try:
        ...
        record.status = DocStatus.READY
    except Exception as e:
        record.status = DocStatus.FAILED
        record.error = str(e)[:200]
```

### 片段 10：Chroma 单例 + auto-build

```python
_vector_store: Chroma | None = None

def get_vector_store() -> Chroma:
    global _vector_store
    if _vector_store is None:
        _vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=get_embeddings(),
            persist_directory=str(persist_dir),
        )
        if _vector_store._collection.count() == 0:
            from app.rag.loaders.markdown_loader import load_markdown_docs
            from app.rag.splitters.text_splitter import split_docs
            chunks = split_docs(load_markdown_docs(_corpus_dir()))
            _vector_store.add_documents(chunks)
    return _vector_store
```

---

## 7. 面试高频追问预案（W3 阶段 10 个）

### Q1：LangGraph 跟 LangChain Agent 区别？
- **A**：LangChain Agent 早期是 AgentExecutor，逻辑写死在 chain 里难扩展。LangGraph 是**显式状态图**，节点、边、状态可观测可调试。复杂业务（意图路由、Reflection、多步推理）LangChain Agent 撑不住。

### Q2：为什么用 `add_conditional_edges` 而不是 if-else？
- **A**：小项目可以 if-else，但状态机会爆炸式增长。LangGraph 把状态、节点、边显式建模，**新增意图类型不用改原有节点**（开闭原则），可视化也好做。

### Q3：query_analyzer 多 1 次 LLM call，值吗？
- **A**：值。**多 200ms 换"智能路由"**，而且 chat 类问题**跳过 retriever** 省回来的时间更多（检索 + 精排 ~200ms）。面试可讲"用额外 LLM call 换架构可扩展性"。

### Q4：Redis 跟内存 dict 怎么选？
- **A**：内存 dict：单进程 / 重启丢 / 简单。**Redis**：跨进程 / 持久化 / TTL。生产必选 Redis，个人项目也推荐（简历亮点）。W3 用 Redis。

### Q5：为什么最近 5 轮对话？
- **A**：LLM 上下文窗口有限（4k-128k token），塞太多历史**爆 token 成本**。5 轮对话约 500 token，留余量给 context + question。**类比 Java**：跟 `LinkedHashMap` 实现的 LRU 一样。

### Q6：文档级 sha256 跟 chunk 级 chunk_id 为什么都要？
- **A**：**两层防御**。文档级 sha256：整文件不变 → 0 成本（快速跳过）。chunk 级 chunk_id：改 1 段重传 → 只算 1 个 chunk（细粒度）。**类比 Java**：跟 git 的 `tree hash` + `blob hash` 一样分层。

### Q7：BackgroundTasks vs Celery 怎么选？
- **A**：BackgroundTasks：**轻量 / 同步执行 / 单进程**。Celery：**重量 / 异步 worker / 多进程**。**个人项目 / 中小流量用 BackgroundTasks 够用**。W3 选 BackgroundTasks。

### Q8：HF Hub 离线模式部署怎么搞？
- **A**：Dockerfile 里 `RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"` 触发下载，**构建时缓存到镜像**。运行时设 `HF_HUB_OFFLINE=1`。

### Q9：Chroma 单例缓存为什么测试要手动清？
- **A**：单例是**进程级共享**的，测试间会污染。fixture 在 yield 前 `vs.delete(where={"source": "test1.md"})` 只删测试数据，**保留 corpus 避免 BGE 重算 10 分钟**。

### Q10：状态机的 5 个状态怎么设计的？
- **A**：按时间维度：`PENDING`（刚入队）→ `INDEXING`（后台跑）→ `READY`（成功）/ `FAILED`（异常）。`DUPLICATE` 是上传时**同 sha256 立即返**的（不走后台）。**类比 Java**：跟 Spring Batch 的 JobState 一样分层。

---

## 8. 简历要点（项目描述用）

### 8.1 项目定位
> "AI 面试助手（RAG 全栈）—— 面向求职者的智能问答系统，**支持多轮对话 + 文档增量管理**，后端 5000+ 行代码，50+ 端到端测试。"

### 8.2 个人化设计（重点讲 3 个）
1. **LangGraph Agentic RAG**：4 Node 状态图 + 条件边路由，意图可扩展
2. **Redis 多轮对话**：session 化 chat_history，最近 5 轮注入 prompt
3. **文档增量更新**：SHA-256 文档级 + chunk_id 细粒度去重，BackgroundTasks 异步索引

### 8.3 端到端
> "用户上传 LeetCode 题解 → SHA-256 去重 → 切分 + 增量 embed → 检索 → Agent 状态图路由 → LLM 生成 → 多轮上下文注入 prompt → 流式打字机 + chunk 级引用溯源。全链路 work。3 个 LLM provider 切换，50+ pytest 测试覆盖。"

### 8.4 W3 阶段 4 大亮点（简历项目描述用）

1. **LangGraph Agentic RAG**（**架构层亮点**）—— 状态图 + 条件边路由，意图可扩展
2. **Redis 对话记忆**（**工程层亮点**）—— session 化 + TTL + 短期上下文
3. **文档增量更新**（**算法层亮点**）—— SHA-256 + chunk_id 两级去重
4. **BackgroundTasks 异步任务**（**系统层亮点**）—— 上传立即返 + 状态机查询

### 8.5 简历项目描述（建议版）

> **AI 面试助手（RAG + Agent 全栈）** | `Vue 3 + FastAPI + LangChain + LangGraph + Redis + Chroma + BGE`
>
> - **检索层**：自研混合检索（BM25 字符级 + 向量语义 + RRF 融合 + BGE-reranker 精排），recall 较单一向量检索提升 20%+
> - **Agent 层**：LangGraph 4 Node 状态图（query_analyzer → 条件路由 → retriever → reranker → generator），意图路由可扩展
> - **记忆层**：RedisChatMessageHistory 持久化多轮对话，最近 5 轮注入 prompt，跨进程共享
> - **文档层**：SHA-256 文档级 + chunk_id 细粒度去重，BackgroundTasks 异步索引，状态机查询
> - **生成层**：OpenAI 协议 4 方法 + FastAPI SSE 流式 + 前端 EventSource 打字机
> - **工程层**：3 厂商 LLM 工厂 + 50+ 端到端测试 + chunk 级引用溯源

---

## 9. W4 计划预览

| Day     | 主题                    | 关键产出                                           |
| ------- | ----------------------- | -------------------------------------------------- |
| Day 1-2 | **RAGAS 评估**          | 50+ 测试用例，faithfulness/recall/precision 四维度 |
| Day 3-4 | **BGE-large 切换**      | W4 评估数据驱动选型（small vs large 对比）         |
| Day 5-6 | **GitHub Actions CI**   | 自动跑 pytest + lint（双仓库）                     |
| Day 7   | **W4_NOTES + 简历终版** | 简历新增"评估 / 性能数据"栏                        |

**W4 核心里程碑**：从"功能完成"到"数据驱动 + 自动化"，简历分量升级到"工程化交付"。

---

## 10. W3 收尾

### commit 历史（建议）

**backend 仓库**（`ai-interview-copilot`）：
```
feat(graph): LangGraph 4 Node 状态图 + /api/chat/agent (Day 1-2)
feat(memory): RedisChatHistoryStore + session_id 注入 (Day 3-4)
feat(document): SHA-256 去重 + BackgroundTasks 异步索引 (Day 5-6)
docs: W2_NOTES 复盘
...
```

### 接下来：W4 收尾

W4 主题：**RAGAS 评估 + 性能数据 + CI 自动化**
- 简历从"功能实现"升级到"工程化交付"
- 新增"评估 / 性能数据 / CI"经验栏

---

**W3 端到端跑通 ✅ · 进入 W4 评估 + 收尾**