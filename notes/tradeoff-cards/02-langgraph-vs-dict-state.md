# 权衡卡 02 · LangGraph 状态管理 vs 手动 dict 状态

> 场景：项目里一个 RAG 智能体，最初手写 `state = {}` + 多层 if-else 维护，后来重构到 LangGraph。

---

## 设计 1：手写 dict + if-else 状态管理

```python
state = {"question": q, "retries": 0, "docs": []}
if cond_a:
    state["docs"] = search(state["question"])
    if not state["docs"]:
        state["question"] = rewrite(...)
        state["retries"] += 1
        if state["retries"] > 2:
            return "失败"
        state["docs"] = search(...)
        # 嵌套第 3 层
```

### 收益
- **零依赖**——不引入 LangGraph，包体积小
- **完全可控**——每一步状态怎么改、改哪个 key，全在眼前
- **快速原型**——3-5 步的小智能体写起来比 LangGraph 短

### 代价
- **复杂度爆炸**——7+ 个 if-else 后自己都看不懂
- **状态散落**——`state["x"]` 在哪里被改？搜整个文件
- **不可观测**——出问题时回放不出来
- **循环 / 人机交互要手写**——重跑 + input() 硬塞

### 备选方案
- LangGraph StateGraph

### 为什么没选备选（最初）
- 项目小、3 步就搞定，"没那个必要"
- 团队没学过 LangGraph，学习成本高

---

## 设计 2：LangGraph StateGraph

```python
class State(TypedDict):
    question: str
    docs: list[str]
    retries: Annotated[int, lambda old, new: old + 1]  # 或自定义 reducer

builder = StateGraph(State)
builder.add_node("search", search_node)
builder.add_node("rewrite", rewrite_node)
builder.add_conditional_edges("search", should_rewrite, {...})
builder.add_edge("rewrite", "search")  # 循环
graph = builder.compile()
```

### 收益
- **状态框架管**——节点只返回增量，reducer 合并
- **可观测**——`graph.get_state_history(thread_id)` 看每步 state
- **循环 = 反向边**——不用手写 while
- **人机交互 = `interrupt()`**——框架原生支持

### 代价
- **学习成本**——要懂 TypedDict / Reducer / Channel / 编译
- **额外抽象**——多了一层框架调用，简单场景反而绕
- **调试**——出错时栈要追到 LangGraph 内部，黑盒感

### 备选方案
- 继续手写 if-else

### 为什么没选备选
- 智能体迭代到第 3 版，节点数从 4 个涨到 11 个
- 加一个"重试后调 LLM 反思"的逻辑，if-else 版要改 5 处
- LangGraph 版加一个节点 + 一条边，**改动量下降 60%**

---

## 选型决策树

```
智能体节点数 ≤ 4、迭代 < 2 次 → 手写 if-else（更轻）
智能体节点数 5-10、需要循环/中断 → LangGraph（核心收益点）
智能体节点数 > 10、多 agent → LangGraph + checkpointing（可观测性刚需）
```

---

## 这个权衡教会我什么

1. **抽象的成本是固定的，收益是递增的**——LangGraph 的学习成本只付一次，但"加一个节点比加一层 if 容易"每次迭代都受益
2. **可观测性在出问题时才被意识到值钱**——上线后第一次 debug 才发现 `get_state_history()` 是救命功能
3. **不要过早抽象**——3 个节点时引入 LangGraph 是过度设计；11 个节点时再引入是**必要的工程债清偿**
