# 动机卡 02 · FastAPI

## 第 1 层（概念）
- **是什么**：高性能 Python Web 框架（2018 年 Sebastián Ramírez 发布）
- **解决什么问题**：Python web 缺一个"现代的"框架——Flask 太老、async 不友好；Django 太重

## 第 2 层（实现）
- **底层**：基于 **Starlette**（ASGI 框架）+ **Pydantic**（数据校验，Rust 实现）
- **路由**：用 Python **类型注解**声明 path operation function 的入参和返回类型
- **数据校验**：Pydantic 自动校验请求体、query、path 参数
- **自动文档**：从类型注解生成 OpenAPI（Swagger）和 ReDoc
- **依赖注入**：`Depends()` 装饰器
- **async/await**：原生支持

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

@app.post("/items")
async def create_item(item: Item):
    return {"name": item.name, "price": item.price}
# ↑ 类型注解 → 自动校验 + 自动文档
```

## 第 3 层（动机）
- **时代背景**：2018 年 Python web 三大痛点：
  1. **Flask**：同步、WSGI（老的 web server 接口）、要手写文档
  2. **Django**：大而全、async 支持弱、ORM 绑定
  3. **类型**：Python 3.5+ 引入类型注解，但**没人把类型注解用在 web 框架的入参声明**
- **作者痛点**：
  - 写 API 时要重复写"参数解析 + 类型校验 + 文档"三遍
  - 想要 async 性能但 Flask 只能上 gevent monkey-patch
- **设计选择**：
  - **站在 Starlette / Pydantic 肩膀上**——不重新发明轮子，专门做"上层封装"——把"路由 + 校验 + 文档"用类型注解统一
  - **类型注解做 API 入参声明**——一个签名，三件事（解析、校验、文档）一次搞定
  - **Pydantic 做数据层**——比手写 `if not isinstance(x, str)` 快 50x（Rust 实现）

## 一句话设计哲学
> **"用类型注解统一三件事：参数解析、数据校验、自动文档"**——把 Python 3.5+ 的新特性变成 web 框架的核心抽象。

## 面试话术示例
"FastAPI 把'参数解析、数据校验、自动文档'三件事合并到 Python 类型注解里——一个函数签名 = 三件事。**解决了我之前用 Flask 写 API 时每个 endpoint 要写 3 遍的痛点**。**代价是绑死了 Pydantic v1/v2，迁移时改字段定义语法要小心**。"
