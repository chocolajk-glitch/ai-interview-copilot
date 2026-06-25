# 动机卡 01 · LangGraph

## 第 1 层（概念）
- **是什么**：把**智能体的执行流程**画成一张有向图
- **解决什么问题**：手写 if-else 维护多 agent 状态时的复杂度爆炸

## 第 2 层（实现）
- **StateGraph**：节点 = 普通函数，边 = 静态 / 条件跳转
- **State**：`TypedDict`，节点返回**增量** dict
- **Channel + Reducer**：合并规则声明在 Type Hint 里（`Annotated[list, add_messages]`）
- **底层**：基于 LangChain 的 `Runnable` 协议，每个节点是 `RunnableLambda`

## 第 3 层（动机）
- **时代背景**：2023 年 LLM agent 爆发，开发者都在手写 `state = {}` + if-else
- **作者痛点**：
  - 智能体迭代 3 版后 if-else 嵌套到 5 层，没人能看懂
  - 加"循环重试"要手写 while + 状态自增
  - 想加"人机交互"得塞 `input()`，状态和 UI 耦合
  - 出问题要 debug，但**每步 state 长啥样回放不出来**
- **设计选择**：
  - 选"图"是因为"图天然能表达条件分支 + 循环"——不是 DAG（有向无环图），是**允许反向边的图**
  - State 用 `TypedDict` 是因为**Python 类型系统零成本**，开发者不用学新概念
  - Reducer 用 `Annotated[...]` 标注是因为**声明式比命令式更声明意图**——"messages 字段用 add_messages 合并"一行就讲清楚
  - 把"checkpoint"和"interrupt"做成一等公民，是因为**生产 agent 必需要这两个**——不是花活

## 一句话设计哲学
> 把"agent 的执行轨迹"和"agent 的状态变化"用图论统一起来，**让 agent 可观测、可回放、可中断**。

## 面试话术示例
"LangGraph 把状态管理和条件跳转封装成图结构，**解决了我手写智能体时最痛的两个点**：①状态在多轮调用间丢失 ②条件分支嵌套深了以后 if-else 难维护。**代价是引入了一层抽象、学习成本比直写代码高**。"
