# 权衡卡 05 · Provider 工厂模式：一次创建 vs 懒加载

> 场景：项目要接 3 个 LLM provider（OpenAI / Anthropic / 本地模型），工厂模式怎么设计？

---

## 设计 1：工厂模式一次性创建三个 provider

```python
class ProviderFactory:
    def __init__(self):
        self.openai = OpenAIProvider(api_key=os.environ["OPENAI_API_KEY"])
        self.anthropic = AnthropicProvider(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.local = LocalProvider(model_path="/models/llama-3")
        # 3 个 provider 启动时全建好
```

### 收益
- **调用时零延迟**——直接用，最快
- **fail-fast**——启动时 3 个 provider 任何一个连不上，**立刻报错**，不会等到用户请求才暴露
- **代码最简**——没有 if-else，没有单例缓存

### 代价
- **启动慢**——3 个 provider 连接全建，**冷启动时间 +2-5s**
- **资源浪费**——没用的 provider 也占内存和连接池
- **扩展性差**——加一个 provider 就要改工厂类

### 备选方案
- 懒加载 + 单例

### 为什么没选备选（最初）
- 项目小，3 个 provider 都用
- 启动慢 3s 可以接受（不是 serverless）
- 想 fail-fast，启动时就知道哪个 provider 配错了

---

## 设计 2：懒加载 + 单例

```python
class ProviderFactory:
    def __init__(self):
        self._providers = {}
    
    def get(self, name: str):
        if name not in self._providers:
            if name == "openai":
                self._providers[name] = OpenAIProvider(...)
            elif name == "anthropic":
                self._providers[name] = AnthropicProvider(...)
            elif name == "local":
                self._providers[name] = LocalProvider(...)
        return self._providers[name]
```

### 收益
- **启动快**——只用到一个 provider 时，**只 init 1 个**
- **资源省**——没用的 provider 完全不占资源
- **扩展性好**——加 provider 改一个 dict 即可
- **适配多场景**——大项目、provider 多、调用频率差异大时优势明显

### 代价
- **首次调用慢**——第一次用某个 provider 要 init（500ms+）
- **错误懒暴露**——provider 配错了，**用到时才报错**（不在启动时）
- **代码复杂度上升**——多一层 if/缓存逻辑
- **线程安全**——并发首次调用要锁，否则可能 init 两遍

### 备选方案
- 一次创建

### 为什么没选备选
- 项目从 3 个 provider 涨到 8 个，启动时间从 5s 涨到 20s
- 实际调用统计：3 个 provider 80% 时间根本没人用
- serverless 化后冷启动敏感，懒加载必须上

---

## 关键 trade-off：fail-fast vs 懒暴露

| | 一次创建 | 懒加载 |
|---|---|---|
| **配置错了** | 启动立刻报错（**fail-fast**） | 第一次用到才报错（**懒暴露**） |
| **监控角度** | 启动失败 = 整个服务不可用 | 启动 OK，第一次请求才挂 |
| **CI/CD** | 部署前能跑通 → 一定可用 | 部署前能跑通 ≠ 一定可用 |

**这是一道工程哲学题**：
- **fail-fast 派**：宁愿启动 1s 慢，也要"上线就能用"，发现问题在 dev/staging 阶段
- **懒暴露派**：启动要快，第一次用到时监控告警也行（前提是有完善监控）

---

## 选型决策树

```
provider 数量 ≤ 3 + 都要用 + 启动时间不敏感   → 一次创建
provider 数量 ≥ 5 + 调用频率不均 + 冷启动敏感 → 懒加载
serverless / FaaS 环境                       → 懒加载 (必须)
库 / SDK (被嵌入第三方)                       → 懒加载 (不要替别人 init)
```

---

## 这个权衡教会我什么

1. **fail-fast vs 懒暴露是工程哲学的差异**——没有对错，看团队偏好
2. **"够用就好"是真理**——3 个 provider 时一次创建完全合理，8 个时必须懒加载
3. **可观测性决定选哪个**——如果监控告警到位，懒暴露可接受；否则 fail-fast 更稳
4. **线程安全是被忽略的坑**——懒加载在并发首次调用时可能 init 两遍，要加锁或用 `functools.lru_cache`
