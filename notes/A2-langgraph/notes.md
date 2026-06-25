# A2 · LangGraph StateGraph 源码 学习笔记

> 目标：能不看笔记答出 4 题 → 通过
> 资料：langgraph/graph/state.py（`add_node` / `add_conditional_edges`）

---

## 一、为什么要 LangGraph——if-else 链的 4 个痛点

1. **嵌套深、复杂度爆炸**——3 层 if-else 自己都绕晕
2. **不可观测**——每步 state 长啥样，回放不出来
3. **循环 / 人机交互要手写**——重跑节点 + input() 硬塞
4. **多 agent 协作难**——多个 agent 之间共享状态，if-else 写出来是面条

---

## 二、4 个核心概念

### 1. State（TypedDict）

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class State(TypedDict):
    question: str
    docs: list[str]
    retries: int
    messages: Annotated[list, add_messages]   # 带 reducer
```

- **TypedDict** = Python 类型系统里的"有 key 的 dict"
- 每个字段可以有 **Annotated[...]** 标注 reducer

### 2. Node（节点）

```python
def search_node(state: State) -> dict:
    docs = vector_db.search(state["question"])
    return {"docs": docs}   # ← 增量返回
```

- 节点 = 普通 Python 函数
- 输入 = 当前完整 state
- 输出 = dict, **只写要更新的字段**

### 3. Edge（边）

**固定边**:
```python
builder.add_edge("search", "llm")
```

**条件边**:
```python
def should_rewrite(state: State) -> str:
    if len(state["docs"]) < 3:
        return "rewrite"
    return "llm"

builder.add_conditional_edges(
    "search",
    should_rewrite,
    {"rewrite": "rewrite", "llm": "llm"}  # 返回值 → 节点名映射
)
```

**循环**:
```python
builder.add_edge("rewrite", "search")   # 反向边 = 循环
```

### 4. Channel + Reducer

- **Channel** = state 里的一个槽位（对应一个 key）
- **Reducer** = 槽位的合并函数
- 节点返回 dict 时，**Channel 调用对应的 Reducer 合并旧值和新值**

```python
def add_messages(left: list, right: list):
    return left + [m for m in right if m.id not in {x.id for x in left}]
```

---

## 三、整体执行流

```
graph = builder.compile()
result = graph.invoke({"question": "什么是 LangGraph"})

# 内部:
# 1. init state
# 2. 从 START 出发
# 3. 找 outgoing edge (固定 / 条件)
# 4. 调节点 node(state)
# 5. 拿 dict 增量
# 6. 对每个 key: Channel + Reducer 合并
# 7. 有 interrupt 标记 → 暂停
# 8. 跳到下一节点
# 9. 到 END → 返回 state
```

---

## 四、4 题自问自答

### Q1: StateGraph 用什么数据结构存状态？节点传全量还是增量？

- **TypedDict**（Python 标准库 typing）
- **增量**返回——节点返回 dict，**只写要更新的字段**，由 reducer 合并
- 默认 reducer 是**覆盖**，带 `Annotated[..., reducer]` 的是自定义合并

### Q2: 条件边怎么实现？判断函数返回什么？

- 用户写一个判断函数 `def should_x(state) -> str`
- 函数返回**下一个节点的**名字符串****
- 框架通过 `add_conditional_edges` 传入的映射表查表跳转
- 判断逻辑完全在用户函数里，框架不规定

### Q3: LangGraph 比 if-else 强在哪？3 个本质区别？

1. 状态由框架管，节点只返回增量——**不散落**
2. 条件分支变**查表**——**不嵌套**
3. 循环 = **反向边**——**不重写**
4. **interrupt()** 原生支持人机交互
5. **get_state_history()** 原生支持回放

### Q4: Channel 是什么？跟 Reducer 的关系？

- **Channel** = state 里的一个槽位（对应一个 key）
- **Reducer** = 槽位的合并函数
- 节点返回 dict → 找到 key 对应的 Channel → 调用 Channel 里的 Reducer → 合并
- 关系：**Channel 装 Reducer，节点返回时触发合并**

---

## 五、面试可能追问 & 我的回答清单

| 追问 | 一句话 |
|---|---|
| add_node 内部做了什么？ | 把函数包成 `Runnable`，存进 `self.nodes` 字典 |
| START / END 是什么？ | 特殊节点常量，标识图入口和出口 |
| 怎么实现多 agent？ | 每个 agent 是一个节点，共享同一个 State，agent 之间通过 state 字段通信 |
| checkpoint 怎么配？ | `compile(checkpointer=MemorySaver())` 或 `SqliteSaver.from_conn_string(...)` |
| 怎么流式输出？ | `graph.stream(input, stream_mode="values")` 或 `stream_mode="updates"` |
| 跟 LangChain 的 Chain 区别？ | Chain 是 DAG（有向无环图），LangGraph 支持**循环**——这是核心 |

---

## 六、通过自评

- [x] 不看笔记能答 Q1 TypedDict + 增量
- [x] 不看笔记能答 Q2 条件边 + 节点名查表
- [x] 不看笔记能答 Q3 3 个本质区别
- [x] 不看笔记能答 Q4 Channel + Reducer
- [x] 能手画状态流转图
- [x] 能说出 START/END/checkpointer/stream_mode 等关键 API
