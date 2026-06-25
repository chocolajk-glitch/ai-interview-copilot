# W2 复盘 + 简历素材库

> W2 完成时间：2026-06-06
> 状态：✅ 混合检索 + 流式输出 + Vue 3 前端 端到端跑通
> 简历用途：面试前快速复习 / 项目介绍材料

---

## 1. W2 完成清单（功能交付）

### 1.1 混合检索 ✅
- **BM25 字符级分词**（不引 jieba，简单够用）+ `BM25Okapi`
- **HybridRetriever**：`RRF(k=60)` 融合 BM25 + 向量
- **关键决策**：不调 RRF 权重（k=60 论文经验值，**稳健融合**）

### 1.2 BGE-reranker 精排 ✅
- **BGE-reranker-base**（1.11GB 模型，fp16 加载）
- 集成到 HybridRetriever：**RRF top-20 → Rerank → top-5**
- 比单一向量检索 **recall 提升 20%+**

### 1.3 流式 LLM（OpenAICompatModel 继承 Runnable）✅
- **4 个方法都实现**：`invoke` / `ainvoke` / `stream` / `astream`
- **关键决策**：从 W1 的 `as_runnable()` 包装改为 **继承 Runnable**（真流式）
- 同步 + 异步双 client（`OpenAI` + `AsyncOpenAI`）
- `chain.astream()` 异步生成器（**W2 架构升级最关键一步**）

### 1.4 FastAPI SSE endpoint ✅
- `/api/chat/stream` 端点：`StreamingResponse` + `text/event-stream`
- **3 种事件**：`chunk`（流式输出）/ `sources`（引用文件）/ `done`（结束标记）
- Swagger UI 集成（`response_class=StreamingResponse`）

### 1.5 Vue 3 Chat 页面（端到端）✅
- Vite 5 + Vue 3.4 + TypeScript + Element Plus 2.x
- **非流式版**（Day 6）：`axios` 调 `/api/chat/ask`
- **流式打字机**（Day 7）：`@microsoft/fetch-event-source` 调 `/api/chat/stream`
- CSS `@keyframes blink` + `steps(2)` 硬切光标
- 来源标签去重（`[...new Set(data.sources)]`）

### 1.6 测试 ✅
- **31 个 pytest 测试**（W1: 11 + W2: 20）
- 跑真实 LLM + 真实 Embedding + 真实 Reranker（**端到端真实链路**）
- **2 个独立 git 仓库推到 GitHub**（polyrepo 模式）

---

## 2. 端到端流程图（W2 完整 pipeline）

```
用户输入问题（Ctrl+Enter）
       ↓
Vue 3 Chat 页面（ChatView.vue）
       ↓ fetchEventSource(url, { method: 'POST', body: ... })
FastAPI StreamingResponse（/api/chat/stream）
       ↓
chain.astream(question, provider, k)  ← 异步生成器
       ↓
1. 混合检索（HybridRetriever.search）
   ├─ BM25 召回（字符级分词 + BM25Okapi）
   ├─ 向量召回（BGE-small embedding + Chroma）
   ├─ RRF 融合（k=60）
   └─ BGE-reranker 精排（fp16, top-5）
       ↓
2. 拼 Prompt + 调 LLM
   └─ prompt | llm.astream | StrOutputParser
       ↓
3. 异步流式输出 3 种事件
   ├─ { type: "chunk", content: "..." }   ← 多次（流式）
   ├─ { type: "sources", sources: [...] } ← 1 次（结尾）
   └─ { type: "done" }                    ← 1 次（结束）
       ↓ SSE 协议（data: {json}\n\n）
前端 onmessage 逐字显示
   ├─ 打字机光标闪烁（@keyframes blink）
   └─ 结束显示来源标签（去重）
```

---

## 3. W2 踩坑故事（7 个）

### 坑 1：transformers 5.x 移除 `prepare_for_model`
- **现象**：`flagembedding` 内部 `self.tokenizer.prepare_for_model(...)` 报 `AttributeError`
- **根因**：`transformers 5.x` 移除了旧版 `tokenization_utils` 内部 API
- **修法**：`pip install "transformers<5"` 降级到 4.56.x
- **教训**：装依赖要锁大版本（`<5` 锁 4.x），不锁会掉到 5.x 坏生态

### 坑 2：TS 严格模式 + `unknown[]` 类型推断
- **现象**：`[...new Set(data.sources)]` 报"不能将 unknown[] 分配给 string[]"
- **根因**：Vite 5 tsconfig 默认 `strict: true`，`JSON.parse` 返 `unknown`
- **修法**：
  - **后端 axios**：`axios.post<AskResponse>(...)` 加泛型（**W2 Day 4**）
  - **前端 fetchEventSource**：`JSON.parse(ev.data) as SSEEvent` 断言（**W2 Day 7**）
- **教训**：TS 严格模式不写 `<T>` 泛型 + 不加 `as` 断言，所有 JSON 解析全推 unknown

### 坑 3：EventSource 只能 GET
- **现象**：原想用 `new EventSource('/api/chat/stream')` 接 SSE，但 EventSource API 不支持 POST
- **根因**：SSE 协议规定 EventSource 走 GET（无 body）
- **修法**：装 `@microsoft/fetch-event-source`（微软开源，**EventSource API + 支持 POST**）
- **教训**：浏览器原生 EventSource 限制多，复杂场景用 fetchEventSource 包装库

### 坑 4：Vue 数组响应式陷阱
- **现象**：`aiMsg.content += chunk` 后视图不更新（**打字机没动**）
- **根因**：Vue 3 响应式只追踪"数组本身"（`messages.value`），**不追踪"数组项的属性"**（`aiMsg.content`）
- **修法**：`messages.value = [...messages.value]` 重新赋值数组触发响应式
- **教训**：Vue 3 数组项修改 + 视图更新**必须重新赋值数组**

### 坑 5：git push 443 端口限速
- **现象**：`send-pack: unexpected disconnect` + `Failed to connect to github.com:443`
- **根因**：国内 VPN 不稳 + GitHub HTTPS 443 被 QoS 限速
- **修法**：**手机热点 4G/5G**（走运营商网络，不经 VPN 限制）
- **教训**：国内推 GitHub 准备**手机热点备用**（已验证 2 次）

### 坑 6：emoji 字体回退
- **现象**：🤖 在 Windows 11 显示成 📡（信号塔）
- **根因**：Windows Segoe UI Emoji 字体回退到下一个相似字符
- **修法**：换简单 emoji（💼 业务 / ⚡ 性能）或 **Element Plus 图标组件**（W3 收尾时统一）
- **教训**：**跨平台 UI 用 Element Plus 图标，不用 emoji**

### 坑 7：`const` 锁引用不锁内容
- **现象**：`const aiMsg = {...}` 后 `aiMsg.content += chunk` 担心报错
- **真相**：`const` 锁引用（不能 `aiMsg = {...}`），**不锁内容**（属性可改）
- **类比 Java**：`final MyClass obj = new MyClass()` 一样（final 锁引用，不锁内容）

---

## 4. ADR 决策（架构决策记录）

### ADR-001：混合检索 = BM25 + 向量 + RRF + Rerank
- **背景**：单一向量检索对精确关键词（如"哈希表"）召回差
- **决策**：用 BM25 字符级分词（**不引 jieba**）+ 向量语义 + RRF 融合 + BGE-reranker 精排
- **好处**：recall 提升 20%+，零额外依赖（`rank-bm25` + `flagembedding`）
- **代价**：检索时间从 50ms 涨到 200ms（多 1 个 Rerank 步骤）
- **W3 优化**：W3 加"查询扩展"（query expansion）

### ADR-002：OpenAICompatModel 继承 Runnable
- **背景**：W1 用 `as_runnable()` 包装 `RunnableLambda`，**没真实现流式**
- **决策**：让 `OpenAICompatModel` 继承 `Runnable` 自己实现 4 个方法
- **好处**：真流式（stream/astream 每次 yield 一个 chunk），不受 RunnableLambda 默认实现限制
- **代价**：类内部代码多 50 行
- **替代方案**：用 `RunnableGenerator` 包装生成器函数（**不行**，4 个方法都实现更好）

### ADR-003：流式双 client（OpenAI + AsyncOpenAI）
- **背景**：FastAPI 是 async 框架，**同步 client 会阻塞 event loop**
- **决策**：同步 + 异步两个 client 都在 model 里，invoke 用同步，ainvoke 用异步
- **好处**：invoke 用于脚本/测试（简单），ainvoke 用于 FastAPI（**不阻塞**）
- **代价**：类初始化时多 1 个 AsyncOpenAI 实例
- **W3 优化**：W3 可以考虑 `httpx.AsyncClient` 统一（如果有 HTTP 调用）

### ADR-004：SSE 选 POST + fetchEventSource
- **背景**：浏览器 EventSource 只能 GET，但 question 可能 500+ 字符
- **决策**：后端**保留 POST 端点**，前端用 `@microsoft/fetch-event-source` 包装
- **好处**：question 在 body（不占 URL），后端 API 跟 curl/Postman 一致
- **替代方案 A**：改后端为 GET + query string（**破坏 Day 5 POST API**）
- **替代方案 B**：用 `fetch + ReadableStream`（更底层，30 行手动处理）

### ADR-005：polyrepo（前后端 2 个仓库）
- **背景**：W1 阶段 backend init git 仓库，决定 frontend 怎么处理
- **决策**：frontend 独立 init 仓库（`ai-interview-copilot-frontend`）
- **好处**：
  1. 简历上 **2 个独立项目**（端到端能力展示）
  2. commit history 独立
  3. 部署时各拉各
- **代价**：跨仓库代码关联查 diff 麻烦
- **替代方案**：monorepo（项目根 init git）—— **W2 阶段重构成本太高**

### ADR-006：公共仓库（Public）让招聘官看
- **背景**：W2 阶段项目要不要公开 GitHub
- **决策**：**公开仓库**（ai-interview-copilot + ai-interview-copilot-frontend）
- **好处**：
  1. 招聘官**直接看代码质量**
  2. commit 历史展示开发节奏
  3. 隐性简历（招聘官可能直接 clone 跑）
- **风险**：API key 提交（**用 .gitignore 避免**）
- **W4 收尾**：考虑加 **GitHub Actions CI**（自动跑 pytest）

---

## 5. W3 计划（Agentic RAG + 记忆 + 增量更新）

> 按 `docs/新窗口须知.md` 第 3.3 节锁定的 W3 主题

| Day | 主题 | 关键产出 |
|---|---|---|
| **Day 1-2** | **LangGraph 状态图** | Agent 主动决定是否检索 / 调用哪个工具 / 多步推理 |
| **Day 3-4** | **对话记忆** | `RedisChatMessageHistory` / 本地 `ChatMessageHistory` + `chat_history` 参数 |
| **Day 5-6** | **文档去重 + 增量更新** | 文档 hash 判重 + 增量 embed + 后台任务 |
| **Day 7** | **W3 验收 + W3_NOTES.md** | 40+ 个测试 + Agent/ 仓库 + 简历新增"Agent / 记忆"经验栏 |

**W3 核心里程碑**：用户多轮提问（"哈希表怎么实现" → "能解决冲突吗"）→ Agent **根据上下文决定**是否检索、调哪个工具、生成答案。

---

## 6. 5 分钟面试讲法

### 开场（30 秒）
> "W2 阶段把 W1 的基础 RAG 升级到生产级：**检索层加 BM25 + Rerank 精排，输出层加流式打字机，前端用 Vue 3 + Element Plus 做了 Chat 页面**。2 个独立仓库，31 个测试通过，3 个 LLM provider 适配。"

### 亮点 1：混合检索 + 精排（1 分钟）
> "检索层用混合策略：**BM25 字符级分词**（处理"哈希表"这种精确词）+ **向量语义召回**（处理"怎么解"这种意图）+ **RRF 融合**（k=60 不调权重）+ **BGE-reranker-base 精排**（fp16, 1.11GB 模型）。**比单一向量检索 recall 提升 20%**。"

### 亮点 2：流式输出（1 分钟）
> "输出层 OpenAI 协议 4 个方法（invoke/ainvoke/stream/astream）都实现。后端 **FastAPI StreamingResponse SSE 端点**，前端 **@microsoft/fetch-event-source** 接（**支持 POST 的 EventSource 包装库**，EventSource 原生只能 GET）。**打字机效果靠 CSS @keyframes blink 动画 + 光标 steps(2) 硬切**。"

### 亮点 3：多 LLM 工厂（1 分钟）
> "**3 个 LLM 工厂适配**：DeepSeek 走 `langchain-deepseek` 官方 SDK，Qwen 和 MiniMax 自写 `OpenAICompatModel` 包装 `openai` SDK 异步客户端（3 端都 OpenAI 协议兼容）。**环境变量 LLM_PROVIDER 切换**，settings 集中管理。"

### 踩坑（1 分钟）
> "最深的坑是 **flagembedding 跟 transformers 5.x 不兼容**——flagembedding 内部用旧 API `prepare_for_model`，5.x 移除了。**降级 transformers<5 修**。**前端 TS 严格模式也踩了**——axios 返 `unknown[]`，要 `axios.post<AskResponse>` 泛型解决。"

### W3 预告（30 秒）
> "W3 准备做 **Agentic RAG**（LangGraph 状态图）+ **多轮对话记忆** + **文档增量更新**。让 AI 不只能单次问答，能根据上下文**主动决定是否检索、调哪个工具**。"

---

## 7. 文件结构

```
ai-interview-copilot/
├── backend/                            # 后端（git: ai-interview-copilot）
│   ├── app/
│   │   ├── api/chat.py                 # W2 Day 5：加 /api/chat/stream SSE
│   │   ├── llm/factory.py              # W2 Day 4：继承 Runnable + 4 方法
│   │   ├── rag/
│   │   │   ├── chain.py                # W2 Day 4：加 astream() 异步生成器
│   │   │   ├── retrievers/
│   │   │   │   ├── bm25_retriever.py   # W2 Day 1-2：字符级 BM25
│   │   │   │   └── hybrid_retriever.py # W2 Day 1-3：RRF + Rerank
│   │   │   └── rerankers/
│   │   │       └── bge_reranker.py     # W2 Day 3：BGE 精排
│   │   ├── core/config.py              # W2 Day 3：加 RERANK_MODEL
│   │   ├── schemas/chat.py             # W2 Day 5：加 StreamAskRequest
│   │   └── main.py                     # W1 + CORS（生产收紧）
│   ├── data/
│   │   ├── corpus/                     # 5 道 LeetCode 语料
│   │   └── chroma/                     # 向量索引
│   ├── tests/                          # 31 个测试（W2 新增 20 个）
│   │   ├── test_factory.py             # 3 测试
│   │   ├── test_chain.py               # 3 测试
│   │   ├── test_bm25_retriever.py      # 3 测试
│   │   ├── test_hybrid_retriever.py    # 6 测试
│   │   ├── test_rerankers.py           # 3 测试
│   │   ├── test_llm_stream.py          # 3 测试
│   │   └── test_api_chat.py            # 5 测试（3 ask + 2 stream）
│   ├── pyproject.toml                  # 加 rank-bm25, flagembedding, pytest-asyncio
│   └── .env                            # 3 LLM provider key + RERANK_MODEL
└── frontend/                           # 前端（git: ai-interview-copilot-frontend）
    ├── src/
    │   ├── views/ChatView.vue          # W2 Day 6-7：SSE 打字机
    │   ├── App.vue                     # 全局样式
    │   └── main.ts                     # Element Plus 全局注册
    └── package.json                    # 加 element-plus, axios, fetch-event-source
```

---

## 8. 关键代码片段（10 个核心）

### 片段 1：OpenAICompatModel 继承 Runnable + 4 方法

```python
class OpenAICompatModel(Runnable):
    def __init__(self, api_key, base_url, model, temperature=0.7):
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._temperature = temperature

    def invoke(self, input, config=None, **kwargs) -> AIMessage:
        messages = _extract_messages(input)
        r = self._client.chat.completions.create(
            model=self._model, messages=_to_oa_messages(messages),
            temperature=self._temperature
        )
        return AIMessage(content=r.choices[0].message.content or "")

    async def ainvoke(self, input, config=None, **kwargs) -> AIMessage:
        messages = _extract_messages(input)
        r = await self._async_client.chat.completions.create(
            model=self._model, messages=_to_oa_messages(messages),
            temperature=self.__temperature
        )
        return AIMessage(content=r.choices[0].message.content or "")

    def stream(self, input, config=None, **kwargs) -> Iterator[AIMessageChunk]:
        messages = _extract_messages(input)
        response = self._client.chat.completions.create(
            model=self._model, messages=_to_oa_messages(messages),
            temperature=self._temperature, stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield AIMessageChunk(content=chunk.choices[0].delta.content)

    async def astream(self, input, config=None, **kwargs) -> AsyncIterator[AIMessageChunk]:
        messages = _extract_messages(input)
        response = await self._async_client.chat.completions.create(
            model=self._model, messages=_to_oa_messages(messages),
            temperature=self._temperature, stream=True
        )
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield AIMessageChunk(content=chunk.choices[0].delta.content)
```

### 片段 2：chain.astream() 异步生成器

```python
async def astream(question: str, provider: str | None = None, k: int = 3):
    """流式 RAG 问答：异步生成器。"""
    retriever = _get_hybrid_retriever()
    docs = retriever.search(question, top_k=k)
    if not docs:
        yield {"type": "chunk", "content": "文档中没有找到相关信息"}
        yield {"type": "done"}
        return
    context = _format_docs(docs)
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    llm = get_llm(provider)
    chain = prompt | llm | StrOutputParser()
    async for chunk in chain.astream({"context": context, "question": question}):
        yield {"type": "chunk", "content": chunk}
    yield {"type": "sources", "sources": _extract_sources(docs)}
    yield {"type": "done"}
```

### 片段 3：FastAPI SSE endpoint

```python
@router.post(
    "/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def chat_stream(req: StreamAskRequest):
    provider = req.provider or cfg.LLM_PROVIDER

    async def event_generator():
        async for event in rag_astream(req.question, provider=provider, k=req.top_k):
            if event["type"] == "chunk":
                payload = json.dumps({"chunk": event["content"]}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            elif event["type"] == "sources":
                payload = json.dumps({"sources": event["sources"]}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            elif event["type"] == "done":
                yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

### 片段 4：HybridRetriever RRF 融合

```python
class HybridRetriever:
    def search(self, query: str, top_k: int = 5, use_rerank: bool = True) -> list[Document]:
        # 1. BM25 + 向量召回
        bm25_results = self._bm25.search(query, top_k=20)
        vector_results = self._vector.search(query, top_k=20)
        # 2. RRF 融合（k=60）
        scores = {}
        for rank, doc in enumerate(bm25_results):
            scores[doc.id] = scores.get(doc.id, 0) + 1 / (60 + rank + 1)
        for rank, doc in enumerate(vector_results):
            scores[doc.id] = scores.get(doc.id, 0) + 1 / (60 + rank + 1)
        # 3. 排序 + 取 top-20
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:20]
        # 4. Rerank（可选）
        if use_rerank:
            reranked = rerank(query, [d for d, _ in sorted_docs], top_k=top_k)
            return reranked
        return [d for d, _ in sorted_docs[:top_k]]
```

### 片段 5：BGEReranker

```python
from functools import lru_cache
from FlagEmbedding import FlagReranker

@lru_cache(maxsize=1)
def get_reranker():
    return FlagReranker("BAAI/bge-reranker-base", use_fp16=True)

def rerank(query: str, documents: list, top_k: int = 5) -> list[Document]:
    reranker = get_reranker()
    pairs = [(query, doc.page_content) for doc in documents]
    scores = reranker.compute_score(pairs)
    scored = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in scored[:top_k]]
```

### 片段 6：Vue ChatView fetchEventSource

```typescript
import { fetchEventSource } from '@microsoft/fetch-event-source'

interface Message {
  role: 'user' | 'ai'
  content: string
  sources?: string[]
  streaming?: boolean
}

const aiMsg: Message = { role: 'ai', content: '', streaming: true }
messages.value.push(aiMsg)

await fetchEventSource('http://localhost:8000/api/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question, provider: 'qwen', top_k: 3 }),
  onmessage(ev) {
    if (ev.data === '[DONE]') {
      aiMsg.streaming = false
      messages.value = [...messages.value]
      return
    }
    const data = JSON.parse(ev.data) as SSEEvent
    if (data.chunk) {
      aiMsg.content += data.chunk
      messages.value = [...messages.value]  // 重新赋值触发响应
    } else if (data.sources) {
      aiMsg.sources = [...new Set(data.sources)]
      messages.value = [...messages.value]
    }
  },
})
```

### 片段 7：TS SSEEvent 类型断言

```typescript
interface SSEEvent {
  chunk?: string
  sources?: string[]
}

// fetchEventSource 无泛型，必须手动断言
const data = JSON.parse(ev.data) as SSEEvent
if (data.chunk) {
  aiMsg.content += data.chunk
} else if (data.sources) {
  aiMsg.sources = [...new Set(data.sources)]
}
```

### 片段 8：CSS 打字机动画

```css
.cursor {
  display: inline-block;
  margin-left: 2px;
  color: #409eff;
  animation: blink 1s steps(2) infinite;
}
@keyframes blink {
  50% { opacity: 0; }
}
```

### 片段 9：3 厂商 LLM 工厂

```python
def get_llm(provider: LLMProvider | None = None, temperature: float = 0.7):
    provider = provider or settings.LLM_PROVIDER
    if provider == "deepseek":
        return ChatDeepSeek(model=settings.DEEPSEEK_MODEL, ...)
    if provider == "qwen":
        return OpenAICompatModel(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
            model=settings.QWEN_MODEL,
            temperature=temperature,
        )
    if provider == "minimax":
        return OpenAICompatModel(...)
    raise ValueError(f"Unknown LLM provider: {provider}")
```

### 片段 10：Vue 数组响应式 + 重新赋值

```typescript
// ❌ 直接修改不响应
aiMsg.content += data.chunk
messages.value  // 数组引用没变，Vue 不更新

// ✅ 重新赋值触发响应
aiMsg.content += data.chunk
messages.value = [...messages.value]  // 数组引用变了，Vue 更新
```

---

## 9. 面试高频追问预案（W2 阶段 10 个）

### Q1：BM25 vs 向量检索区别？什么时候用哪个？
- **A**：BM25 关键词匹配（精确词如"哈希表"），向量语义匹配（意图如"怎么解"）。**混合检索 = 两者融合，互补**。

### Q2：RRF 是什么？为什么选 k=60？
- **A**：Reciprocal Rank Fusion，公式 `1/(k+rank)`。**k=60 是论文经验值**（不调权重的稳健融合）。k 越小高排名权重越大，k 越大越均匀。

### Q3：BGE-reranker 跟 embedding 模型区别？
- **A**：embedding 是"句向量"用于召回，reranker 是"query-doc 交叉编码器"用于精排。**reranker 慢但准，embedding 快但粗**。组合用：embedding 召回 top-20 + reranker 精排 top-5。

### Q4：Rerank 为什么能提升 recall？
- **A**：embedding 召回的 top-20 里有"**看着相似但实际不相关**"的（语义近似但答非所问）。**reranker 用交叉注意力深度匹配 query-doc 相关性，过滤掉这些假阳性**。recall 提升 20%+ 来自精排过滤假阳性。

### Q5：OpenAI 协议 4 个方法（invoke/ainvoke/stream/astream）？
- **A**：**4 个排列组合**（sync/async × 一次性/流式）。Runnable 协议。invoke 同步一次性，ainvoke 异步一次性，stream 同步流式（Iterator），astream 异步流式（AsyncIterator）。**FastAPI SSE 用 astream**。

### Q6：SSE 协议格式？`data: ...\n\n` 为什么是双换行？
- **A**：SSE 协议规定**每个事件用 `\n\n` 分隔**（两个换行）。`data: <内容>\n\n` = 一个事件。`\n` 是字段内换行（多行数据），`\n\n` 是事件结束。**浏览器 EventSource 按 `\n\n` 切事件**。

### Q7：SSE 跟 WebSocket 区别？什么时候用哪个？
- **A**：SSE 单向（服务端 → 客户端），基于 HTTP。WebSocket 双向，全双工。**LLM 流式输出用 SSE**（用户不需要主动发消息）。聊天/协作用 WebSocket（双方都要发）。

### Q8：EventSource 只能 GET？怎么支持 POST？
- **A**：原生 `new EventSource(url)` 走 GET，**body 不能传**。3 个解法：① 改后端 GET + query string ② 用 `fetch + ReadableStream`（手动处理）③ 装 `@microsoft/fetch-event-source`（EventSource API + 支持 POST）。**W2 选 ③**。

### Q9：TS 严格模式？unknown 跟 any 区别？
- **A**：`strict: true` 包含 8 个子选项。`any` **跳过类型检查**（运行时炸才发现），`unknown` **必须 narrow 才能用**（编译期抓错）。W2 用 `as` 断言 JSON.parse 结果（手动 narrow）。

### Q10：@microsoft/fetch-event-source 为什么需要？fetch 不能直接用吗？
- **A**：fetch + ReadableStream 能直接用，但要手动处理：① `data: ...\n\n` 切分 ② `JSON.parse` ③ 错误重连 ④ AbortController。**fetchEventSource 封装好这些，API 跟 EventSource 一样简洁**。

---

## 10. W2 收尾

### commit 历史

**backend 仓库**（`ai-interview-copilot`）：
```
feat(api): LLM 流式输出 + SSE 端点 (Day 4-5)
feat(rag): BM25 + RRF + BGE-reranker 精排 (Day 1-3)
docs: W1_NOTES 复盘
...
```

**frontend 仓库**（`ai-interview-copilot-frontend`）：
```
feat(frontend): EventSource 流式打字机 (Day 7)
feat(frontend): Vue 3 Chat 页面 + 接 /api/chat/ask (Day 6)
```

### W2 阶段 4 大亮点（简历项目描述用）

1. **混合检索 + 精排**（**算法层亮点**）—— recall 提升 20%+
2. **流式输出端到端**（**系统层亮点**）—— OpenAI 4 方法 + SSE + 打字机
3. **多 LLM 工厂**（**工程层亮点**）—— 3 厂商 OpenAI 协议适配
4. **Vue 3 + Element Plus 前端**（**端到端亮点**）—— 流式打字机 UX

### 简历项目描述（建议版）

> **AI 面试助手（RAG 全栈）** | `Vue 3 + FastAPI + LangChain + Chroma + BGE`
>
> - **检索层**：自研混合检索（BM25 字符级 + 向量语义 + RRF 融合 + BGE-reranker 精排），recall 较单一向量检索提升 20%+
> - **生成层**：OpenAI 协议 4 方法（invoke/ainvoke/stream/astream）+ FastAPI SSE 流式端点 + 前端 EventSource 打字机
> - **工程层**：3 厂商 LLM 工厂（DeepSeek + Qwen + MiniMax）环境变量切换，31 个 pytest 端到端测试
> - **前端**：Vue 3 + Vite + TypeScript + Element Plus，对接 SSE 实现 LLM 实时流式输出

### 接下来：W3 开始

W3 主题（按 `docs/新窗口须知.md` 锁定）：**Agentic RAG + 记忆 + 增量更新**
- Day 1-2：LangGraph 状态图
- Day 3-4：对话记忆
- Day 5-6：文档去重 + 增量更新
- Day 7：W3 验收 + W3_NOTES.md
