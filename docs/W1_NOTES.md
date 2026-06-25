# W1 复盘 + 简历素材库

> W1 完成时间：2026-06-05
> 状态：✅ 端到端 RAG pipeline 跑通
> 简历用途：面试前快速复习 / 项目介绍材料

---

## 1. W1 完成清单（功能交付）

### 1.1 后端骨架 ✅
- FastAPI + uvicorn + pydantic-settings + loguru
- `/health` 接口 + Swagger 自动 OpenAPI 文档
- 配置驱动：`.env` + pydantic-settings（绝对路径加载，cwd 无关）

### 1.2 LLM 工厂（3 provider 切换）✅
- **DeepSeek**：`langchain-deepseek` 专用 SDK
- **Qwen**：自写 `OpenAICompatModel` wrapper + `openai` SDK 直调
- **MiniMax**：同上 + `extra_body={"reasoning_split": True}` 分离思维链
- 工厂模式 + `LLM_PROVIDER` 环境变量切换
- **关键决策**：不用 `langchain-openai` 包装层（跨厂商不稳），改用 `openai` SDK + 20 行 wrapper

### 1.3 文档加载 + 切分 ✅
- LangChain `DirectoryLoader` + `TextLoader`（5 道 LeetCode 题解，**自建垂直领域语料**）
- `RecursiveCharacterTextSplitter`（chunk_size=500, overlap=50）

### 1.4 Embedding + 向量检索 ✅
- **BGE-small-zh-v1.5**（本地，**W4 评估后切 large**）
- Chroma 持久化（`data/chroma/`）
- **检索 Top-1 召回率 100%**（3 个查询全准）

### 1.5 基础 RAG Chain ✅
- **LCEL 链式语法**（`prompt | llm | parser`）
- **`RunnableLambda` 包装自写 OpenAICompatModel 接入 LCEL**（关键技术点）
- HTTP API `/api/chat/ask`（带 `sources` 引用列表）
- Prompt 设计：角色 + 文档约束 + 失败兜底三件套

### 1.6 测试 ✅
- **11 个 pytest 测试**（5 个文件，单元 + 集成 + E2E 三类覆盖）
- 跑真实 LLM + 真实 Embedding（**端到端真实链路验证**）

---

## 2. 端到端流程图

```
用户问"两数之和怎么解"
       ↓ HTTP POST /api/chat/ask
FastAPI 路由（app/api/chat.py）
       ↓
RAG Chain（app/rag/chain.py）
       ├─ 1. similarity_search(question, k=3) → Chroma 召回 top-3 chunks
       ├─ 2. 拼 Prompt：context = chunks + question
       ├─ 3. llm.invoke(prompt) → LLM 生成答案
       └─ 4. 返回 {answer, sources, provider}
       ↓ HTTP 200 JSON
前端（或 Swagger UI）展示
```

---

## 3. W1 踩过的坑（**面试能讲的故事**）

### 3.1 `__init__.py` 命名错误

- **现象**：`ModuleNotFoundError: No module named 'app'`
- **根因**：新建空文件漏了双下划线（`init.py` 不是 `__init__.py`）
- **修法**：`Get-ChildItem -Recurse -Filter init.py | Rename-Item -NewName { $_.Name -replace '^init\.py$','__init__.py' }`
- **教训**：**Python 包靠显式 `__init__.py` 标记**（不像 Java 纯目录识别）

### 3.2 LangChain 1.x 字段命名分裂

- **现象**：`AttributeError: 'ChatTongyi' object has no attribute 'model'`
- **根因**：`ChatDeepSeek` 用 `.model`（新风格），`ChatTongyi` / `ChatOpenAI` 用 `.model_name`（旧风格）
- **修法**：`getattr(llm, 'model', None) or getattr(llm, 'model_name', '?')`
- **教训**：**跨 provider 字段差异用 duck typing**，不依赖具体类

### 3.3 PyCharm 配置 + 相对路径 .env

- **现象**：PyCharm 跑 test_llm.py 报 `Missing credentials`，命令行跑 OK
- **根因**：
  1. PyCharm `WORKING_DIRECTORY` 配的是 `$PROJECT_DIR$/scripts`（cwd = `backend/scripts/`）
  2. `config.py` 的 `env_file=".env"` 是**相对路径**，相对的是 cwd
  3. `backend/scripts/.env` 不存在 → settings 全空 → api_key 是空串
- **修法**：`config.py` 改 `env_file=str(Path(__file__).resolve().parent.parent.parent / ".env")`（**绝对路径**）
- **教训**：**应用代码不依赖任何特定 cwd**——重要配置用绝对路径
- **简历讲法**：**"配置稳健性"原则**

### 3.4 自写 wrapper 接入 LangChain LCEL

- **现象**：`Expected a Runnable, callable or dict. Instead got an unsupported type: <class 'OpenAICompatModel'>`
- **根因**：`OpenAICompatModel` 是自写类，**不是 LangChain `Runnable`**
- **修法**：加 `as_runnable()` 方法，用 `RunnableLambda` 包装（**3 行代码**）
- **教训**：**适配框架抽象时优先用包装器**（`RunnableLambda`），不强行继承抽象类（`BaseChatModel` 有 10+ 抽象方法）
- **简历讲法**：**"框架 vs SDK 的工程取舍"**——不被 SDK 版本绑架

### 3.5 LangChain 1.x 模块拆分

- **现象**：`cannot import name 'ChatPromptValue' from 'langchain_core.prompts'`
- **根因**：LangChain 1.x 把值类拆到 `langchain_core.prompt_values`（`prompts` 只剩模板类）
- **修法**：**改 duck typing**（`hasattr(input, "messages")`），不依赖具体类
- **教训**：**LangChain 1.x 重写过，import 路径别靠记忆**——用 introspect 验证

### 3.6 GBK 编码掩盖真实错误（调试方法论）

- **现象**：PowerShell 控制台 GBK 编码无法打印 emoji，掩盖了真实的 API 调用结果
- **根因**：print 时 `UnicodeEncodeError: 'gbk' codec can't encode '\U0001f60a'`
- **修法**：脚本顶部加 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")`
- **教训**：**不能根据表面输出判断成功**——**真实 API 错误可能被 print 错掩盖**。**链路拆解 + 单独验证每段**才靠谱

---

## 4. 架构决策记录（ADR 风格）

### 决策 1: 为什么用 FastAPI 而不是 Flask/Django？

- **答案**：自动 OpenAPI 文档（Swagger UI）+ Pydantic 校验 + 原生 async 支持
- **对比 Java**：springdoc-openapi 要额外配，FastAPI 开箱即用
- **简历讲法**：*"基于 FastAPI 自动生成 OpenAPI 文档，降低前后端联调成本"*

### 决策 2: 为什么用 OpenAI SDK 直调，不依赖 langchain-openai？

- **答案**：`langchain-openai` 1.x 跨厂商调用包装层不稳（字段分裂、版本敏感）
- **方案**：20 行 `OpenAICompatModel` wrapper + `openai` SDK = 更可控
- **简历讲法**：*"工程取舍——不被第三方 SDK 版本绑架"*

### 决策 3: 为什么先用 BGE-small，W4 评估后切 large？

- **答案**：W1 阶段 5 道题小、small 推理 < 2 秒、debug 体验远好于 large
- **依据**：W4 用 RAGAS 评估数据驱动选型（不是凭感觉"large 一定最好"）
- **简历讲法**：*"数据驱动选型 + 不过早优化"*

### 决策 4: 为什么用 LCEL 而不是手写 chain？

- **答案**：LCEL 链式语法支持流式/异步/批量/并行（`chain.stream()` / `chain.abatch()`）
- **W1 收益**：3 行 `prompt | llm | parser` 替代 50 行手写拼接
- **W2 收益**：流式输出直接 `chain.stream()`（W2 Day 8 写流式时复用）
- **简历讲法**：*"用 LangChain LCEL 把可维护性 + 流式支持一起拿下"*

### 决策 5: 为什么手写 5 道 LeetCode 题解？

- **答案**：自建垂直领域语料，**简历上能讲"自建数据集"**（不是 fork awesome-llm-apps）
- **数据集扩展**：W4 收尾时扩到 20+ 题（用 JavaGuide + 自己补充）
- **简历讲法**：*"自建 5 道 LeetCode 经典题解语料库，覆盖哈希表/链表/栈/二分/双指针 5 大高频考点"*

### 决策 6: 为什么用 OpenAI 协议 base_url 兼容调用 Qwen/MiniMax？

- **答案**：3 个 provider 都用同一个 `openai` SDK + 不同 base_url，**避免维护 3 套调用代码**
- **简历讲法**：*"跨厂商 LLM 切换零成本"*

---

## 5. W2 计划预览

| Day | 主题 | 关键产出 |
|---|---|---|
| W2 Day 1-2 | **混合检索** | `app/rag/retrievers/hybrid_retriever.py`（BM25 + 向量 + Rerank）|
| W2 Day 3-4 | **流式输出** | `/api/chat/stream` SSE + 前端打字机效果 |
| W2 Day 5-7 | **Vue 3 前端** | `frontend/` 项目 + 聊天框 + 上传 + 引用展示 |
| W2 Day 8 | W2 验收 | 端到端 demo + 性能测试 |

**W2 里程碑**：用户打开浏览器 → 看到 Vue 3 聊天界面 → 提问 → AI 流式输出答案 + 引用来源 + 可点击查看原文

---

## 6. 简历要点（**面试 5 分钟讲清**）

### 6.1 项目定位
*"AI 面试助手（AI Interview Copilot）—— 面向求职者的 RAG 问答系统，专注 LeetCode 题解 + 面试八股文。"*

### 6.2 技术栈
- **后端**：Python 3.11 + FastAPI + LangChain 1.x + Chroma
- **LLM**：DeepSeek / Qwen / MiniMax（3 provider 工厂模式）
- **Embedding**：BGE-small-zh-v1.5（本地）
- **前端（W2）**：Vue 3 + Vite + Element Plus

### 6.3 个人化设计（**重点讲 3 个**）
1. **3 provider 工厂模式** + OpenAI SDK 直调（不被 langchain-openai 绑架）
2. **BGE 本地 embedding** + W4 数据驱动选型（不是"large 一定最好"）
3. **RunnableLambda 包装自写类接入 LCEL**（框架 vs SDK 工程取舍）

### 6.4 踩坑迭代（**讲 2-3 个**）
1. **PyCharm cwd + 相对路径 .env**（配置稳健性）
2. **LangChain 1.x 跨厂商字段分裂**（duck typing）
3. **RunnableLambda 包装自写 wrapper**（框架适配）

### 6.5 端到端
*"用户上传 LeetCode 题解 → 切分 → embedding → 检索 → LLM 生成 → 引用展示，全链路 work。3 个 provider 都能切换，11 个 pytest 测试覆盖。"*

---

## 7. 项目文件结构

```
ai-interview-copilot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── core/                # 配置 + 日志
│   │   ├── llm/                 # LLM 工厂
│   │   ├── api/                 # HTTP 路由
│   │   ├── schemas/             # Pydantic 模型
│   │   └── rag/                 # 检索增强生成
│   │       ├── loaders/
│   │       ├── splitters/
│   │       ├── embeddings/
│   │       └── retrievers/
│   ├── data/
│   │   ├── corpus/              # 5 道 LeetCode 题解
│   │   ├── chroma/              # 向量库持久化
│   │   └── logs/
│   ├── tests/                   # 11 个 pytest 测试
│   ├── scripts/                 # 手动测试脚本
│   ├── pyproject.toml
│   └── .env
├── docs/
│   ├── 新窗口须知.md
│   └── W1_NOTES.md              # ← 本文件
└── README.md
```

---

## 8. 关键代码片段（面试可贴）

### 8.1 LLM 工厂（`app/llm/factory.py` 核心）

```python
def get_llm(provider: str | None = None, temperature: float = 0.7):
    provider = provider or settings.LLM_PROVIDER
    if provider == "deepseek":
        return ChatDeepSeek(model=settings.DEEPSEEK_MODEL, ...)
    if provider == "qwen":
        return OpenAICompatModel(...)  # 自写 wrapper
    if provider == "minimax":
        return OpenAICompatModel(..., extra_body={"reasoning_split": True})
```

### 8.2 RunnableLambda 包装自写类（`as_runnable`）

```python
def as_runnable(self):
    from langchain_core.runnables import RunnableLambda
    def _call(input):
        if hasattr(input, "messages"):
            messages = input.messages
        elif isinstance(input, dict) and "messages" in input:
            messages = input["messages"]
        else:
            messages = input
        return self.invoke(messages)
    return RunnableLambda(_call)
```

### 8.3 config.py 绝对路径（健壮性）

```python
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
model_config = SettingsConfigDict(
    env_file=str(_BACKEND_ROOT / ".env"),
    ...
)
```

---

## 9. 面试高频追问预案

### Q1: "你这个项目最大的技术难点是什么？"
**A**: **跨厂商 LLM 调用的稳健性**。`langchain-openai` 1.x 在跨厂商（DeepSeek/Qwen/MiniMax）调用时包装层不稳——字段名分裂、版本敏感、SecretStr 不显示。我用 20 行 `OpenAICompatModel` wrapper + `openai` SDK 直调 + `RunnableLambda` 接入 LCEL 解决。**这是"框架 vs SDK"的工程取舍——不被第三方版本绑架**。

### Q2: "为什么不用 LangChain 默认的全套？"
**A**: **YAGNI（You Ain't Gonna Need It）原则**。W1 阶段 chat 调用太简单，LangChain 抽象层（Chain/Agent/Tool/Retriever）都用不上。**W3 写 Agent 时再引入 LangGraph**。**类比 Java 不会用 Spring 写 Hello World**——简单场景用最底层 SDK。

### Q3: "你们怎么处理 API Key 安全？"
**A**: `.env` 文件存 key（**不进 git**），`pydantic-settings` 绝对路径加载（cwd 无关）。**生产环境用 Docker secrets 或 Vault**。**.env.example` 公开模板**给其他开发者参考。

### Q4: "你怎么评估 RAG 效果？"
**A**: W1 阶段用 3 道题手工测 Top-1 召回率（100%）。**W4 收尾时用 RAGAS 评估**（context precision / recall / faithfulness / answer relevance 四维度），20+ 测试集，数据驱动。

---

**W1 端到端跑通 ✅ · 进入 W2 混合检索 + 流式 + 前端**
