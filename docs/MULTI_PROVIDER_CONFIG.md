# 多供应商配置指南

## 概述

API Middleware 支持配置多个 API 供应商，即使它们提供相同名称的模型也不会冲突。本文档详细说明如何配置和使用多供应商。

## 核心概念

### 1. Provider（供应商）

供应商是 API 服务提供者，每个供应商有：
- **name**: 唯一标识符（如 `official`、`proxy_a`）
- **base_url**: API 端点地址
- **api_key**: 认证密钥
- **models**: 该供应商支持的模型列表

### 2. Model Mapping（模型映射）

模型映射定义了如何访问模型：
- **display_name**: 用户看到的模型名称（必须唯一）
- **provider_name**: 关联的供应商
- **actual_model_name**: 发送给供应商的实际模型名
- **context_config**: 该模型的上下文配置（可选）

### 3. 命名空间格式

推荐使用 `provider/model` 格式作为 `display_name`：
- `official/gpt-4` - 官方 OpenAI 的 GPT-4
- `proxy_a/gpt-4` - 代理 A 的 GPT-4
- `proxy_b/gpt-4` - 代理 B 的 GPT-4

## 配置相同名称的模型

### 问题场景

假设你有两个供应商都提供 `chatgpt5` 模型：
- **Official OpenAI**: `chatgpt5`
- **Proxy A**: `chatgpt5`

### 解决方案

使用不同的 `display_name` 来区分：

```yaml
providers:
  - name: official
    base_url: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}
    models:
      - chatgpt5

  - name: proxy_a
    base_url: https://api-proxy-a.example.com/v1
    api_key: ${PROXY_A_API_KEY}
    models:
      - chatgpt5

model_mappings:
  # 官方的 chatgpt5
  - display_name: official/chatgpt5
    provider_name: official
    actual_model_name: chatgpt5
    context_config:
      max_turns: 20
      max_tokens: 10000

  # 代理 A 的 chatgpt5
  - display_name: proxy_a/chatgpt5
    provider_name: proxy_a
    actual_model_name: chatgpt5
    context_config:
      max_turns: 15
      max_tokens: 8000
```

### 使用方式

**API 调用**：
```python
# 使用官方的 chatgpt5
response = await client.post(
    "http://localhost:8000/v1/chat/completions",
    json={
        "model": "official/chatgpt5",
        "messages": [{"role": "user", "content": "Hello"}]
    }
)

# 使用代理 A 的 chatgpt5
response = await client.post(
    "http://localhost:8000/v1/chat/completions",
    json={
        "model": "proxy_a/chatgpt5",
        "messages": [{"role": "user", "content": "Hello"}]
    }
)
```

**模型列表**：
```bash
curl http://localhost:8000/v1/models
```

返回：
```json
{
  "object": "list",
  "data": [
    {
      "id": "official/chatgpt5",
      "object": "model",
      "owned_by": "official"
    },
    {
      "id": "proxy_a/chatgpt5",
      "object": "model",
      "owned_by": "proxy_a"
    }
  ]
}
```

## 配置方式对比

### 方式 1: 使用 model_mappings（推荐）✅

**优点**：
- ✅ 每个模型有唯一的 `display_name`
- ✅ 可以为每个模型单独配置 `context_config`
- ✅ 模型会出现在 `GET /v1/models` 列表中
- ✅ 可以将 `display_name` 映射到不同的 `actual_model_name`
- ✅ 更灵活，更易管理

**缺点**：
- ⚠️ 需要为每个模型写配置（稍微繁琐）

**配置示例**：
```yaml
providers:
  - name: provider_a
    base_url: https://api-a.example.com/v1
    api_key: ${API_A_KEY}
    models:
      - chatgpt5

model_mappings:
  - display_name: provider_a/chatgpt5
    provider_name: provider_a
    actual_model_name: chatgpt5
    context_config:
      max_turns: 15
      max_tokens: 8000
```

### 方式 2: 不使用 model_mappings（简化）

**优点**：
- ✅ 配置简单，只需配置 `providers`
- ✅ 仍然可以通过 `provider/model` 格式调用

**缺点**：
- ❌ 无法在 `GET /v1/models` 中列出模型
- ❌ 无法为每个模型单独配置 `context_config`
- ❌ 使用全局默认的上下文配置

**配置示例**：
```yaml
providers:
  - name: provider_a
    base_url: https://api-a.example.com/v1
    api_key: ${API_A_KEY}
    models:
      - chatgpt5

# 不需要 model_mappings
```

**使用**：
```python
# 仍然可以调用
response = await client.post(
    "http://localhost:8000/v1/chat/completions",
    json={
        "model": "provider_a/chatgpt5",  # 自动解析
        "messages": [{"role": "user", "content": "Hello"}]
    }
)
```

## 模型解析流程

中间件按以下顺序解析模型名称：

```
1. 检查 model_mappings 中是否有精确匹配
   ↓ 如果找到
   → 使用 mapping 中的 provider_name 和 actual_model_name
   
   ↓ 如果没找到
   
2. 检查模型名是否包含 '/'
   ↓ 如果包含
   → 解析为 provider/model 格式
   → 查找对应的 provider
   → 使用解析出的 model 作为 actual_model_name
   
   ↓ 如果不包含
   
3. 抛出错误：模型未找到
```

**代码实现**（`src/core/provider_manager.py`）：
```python
def resolve_model(self, model_name: str) -> Tuple[Provider, str]:
    # 1. 检查 model_mappings
    mapping = self.model_mappings.get(model_name)
    
    if mapping is None:
        # 2. 尝试解析 provider/model 格式
        if '/' in model_name:
            provider_name, actual_model = model_name.split('/', 1)
            provider = self.providers.get(provider_name)
            
            if provider is None:
                raise ValueError(f"Provider '{provider_name}' not found")
            
            return provider, actual_model
        else:
            # 3. 找不到模型
            raise ValueError(f"Model '{model_name}' not found")
    
    # 使用 mapping
    provider = self.providers.get(mapping.provider_name)
    return provider, mapping.actual_model_name
```

## 实际使用场景

### 场景 1: 成本优化

使用不同供应商的相同模型来优化成本：

```yaml
model_mappings:
  # 官方 GPT-4（贵但稳定）
  - display_name: official/gpt-4
    provider_name: official
    actual_model_name: gpt-4
    context_config:
      max_turns: 20
      max_tokens: 8000

  # 代理 GPT-4（便宜但可能不稳定）
  - display_name: proxy/gpt-4
    provider_name: proxy_a
    actual_model_name: gpt-4
    context_config:
      max_turns: 15
      max_tokens: 6000
```

用户可以根据需求选择：
- 重要任务 → `official/gpt-4`
- 一般任务 → `proxy/gpt-4`

### 场景 2: 负载均衡

配置多个代理来分散负载：

```yaml
model_mappings:
  - display_name: proxy1/gpt-4
    provider_name: proxy_1
    actual_model_name: gpt-4

  - display_name: proxy2/gpt-4
    provider_name: proxy_2
    actual_model_name: gpt-4

  - display_name: proxy3/gpt-4
    provider_name: proxy_3
    actual_model_name: gpt-4
```

### 场景 3: 不同上下文策略

为不同供应商的相同模型配置不同的上下文策略：

```yaml
model_mappings:
  # 使用截断策略（快速）
  - display_name: fast/gpt-4
    provider_name: proxy_a
    actual_model_name: gpt-4
    context_config:
      max_turns: 10
      reduction_mode: truncation

  # 使用摘要策略（保留更多信息）
  - display_name: smart/gpt-4
    provider_name: proxy_b
    actual_model_name: gpt-4
    context_config:
      max_turns: 20
      reduction_mode: summarization
      summarization_model: proxy_a/gpt-3.5-turbo  # 必须指定！可以跨供应商
      memory_zone_enabled: true
```

### 场景 4: 模型名称映射

将友好的名称映射到实际的模型名：

```yaml
model_mappings:
  # 用户友好的名称
  - display_name: fast-chat
    provider_name: official
    actual_model_name: gpt-3.5-turbo

  - display_name: smart-chat
    provider_name: official
    actual_model_name: gpt-4

  - display_name: reasoning-chat
    provider_name: deepseek
    actual_model_name: deepseek-reasoner
```

## OpenWebUI 集成

在 OpenWebUI 中，用户会看到所有配置的模型：

**配置**：
```yaml
model_mappings:
  - display_name: official/gpt-4
    provider_name: official
    actual_model_name: gpt-4

  - display_name: proxy_a/gpt-4
    provider_name: proxy_a
    actual_model_name: gpt-4

  - display_name: proxy_b/gpt-4
    provider_name: proxy_b
    actual_model_name: gpt-4
```

**OpenWebUI 中的显示**：
```
模型选择：
  ☐ official/gpt-4 (official)
  ☐ proxy_a/gpt-4 (proxy_a)
  ☐ proxy_b/gpt-4 (proxy_b)
```

用户可以清楚地看到每个模型来自哪个供应商。

## 最佳实践

### 1. 命名规范

✅ **推荐**：
```yaml
display_name: provider/model-name
```

❌ **不推荐**：
```yaml
display_name: model-name-provider  # 不清晰
display_name: provider_model       # 难以解析
```

### 2. 供应商命名

✅ **推荐**：
```yaml
name: official      # 官方
name: proxy_a       # 代理 A
name: backup        # 备用
name: fast          # 快速（低成本）
name: premium       # 高级（高质量）
```

❌ **不推荐**：
```yaml
name: api1          # 不清晰
name: test          # 容易混淆
```

### 3. 上下文配置

为不同用途的模型配置合适的上下文：

```yaml
# 快速对话（低成本）
context_config:
  max_turns: 5
  max_tokens: 2000
  reduction_mode: truncation

# 标准对话
context_config:
  max_turns: 10
  max_tokens: 4000
  reduction_mode: truncation

# 长对话（保留更多上下文）
context_config:
  max_turns: 20
  max_tokens: 8000
  reduction_mode: summarization
  summarization_model: provider/gpt-3.5-turbo  # 必须指定！用便宜的模型做摘要
  memory_zone_enabled: true
```

### 4. 环境变量管理

使用环境变量存储敏感信息：

```yaml
providers:
  - name: official
    api_key: ${OPENAI_API_KEY}      # 从环境变量读取

  - name: proxy_a
    api_key: ${PROXY_A_API_KEY}     # 从环境变量读取
```

`.env` 文件：
```bash
OPENAI_API_KEY=sk-...
PROXY_A_API_KEY=pk-...
PROXY_B_API_KEY=ak-...
```

## 故障排除

### 问题 1: 模型未找到

**错误**：
```
ValueError: Model 'chatgpt5' not found in configuration
```

**原因**：
- 没有配置 `model_mappings`
- 没有使用 `provider/model` 格式

**解决**：
```yaml
# 方案 1: 添加 model_mapping
model_mappings:
  - display_name: official/chatgpt5
    provider_name: official
    actual_model_name: chatgpt5

# 方案 2: 使用 provider/model 格式调用
# "model": "official/chatgpt5"
```

### 问题 2: 供应商未找到

**错误**：
```
ValueError: Provider 'proxy_a' not found
```

**原因**：
- `provider_name` 拼写错误
- 供应商未在 `providers` 中配置

**解决**：
```yaml
providers:
  - name: proxy_a  # 确保名称匹配
    base_url: ...
    api_key: ...
```

### 问题 3: 模型列表为空

**问题**：`GET /v1/models` 返回空列表

**原因**：没有配置 `model_mappings`

**解决**：添加 `model_mappings` 配置

### 问题 4: 上下文配置不生效

**问题**：模型使用的是默认配置，而不是自定义配置

**原因**：
- 没有在 `model_mapping` 中配置 `context_config`
- 使用了方式 2（不使用 model_mappings）

**解决**：
```yaml
model_mappings:
  - display_name: official/gpt-4
    provider_name: official
    actual_model_name: gpt-4
    context_config:  # 添加这个
      max_turns: 20
      max_tokens: 8000
```

### 问题 5: summarization_model 未配置

**错误**：
```
Model mapping 'xxx' uses summarization mode but summarization_model is not configured
```

**原因**：使用 `summarization` 模式但未指定用于生成摘要的模型

**解决**：
```yaml
model_mappings:
  - display_name: official/gpt-4
    provider_name: official
    actual_model_name: gpt-4
    context_config:
      reduction_mode: summarization
      summarization_model: official/gpt-3.5-turbo  # 必须添加！
```

## 总结

### 关键要点

1. ✅ **使用 `model_mappings`** 来配置模型（推荐）
2. ✅ **使用 `provider/model` 格式** 作为 `display_name`
3. ✅ **每个模型的 `display_name` 必须唯一**
4. ✅ **可以为每个模型单独配置上下文策略**
5. ✅ **多个供应商可以提供相同名称的模型，不会冲突**

### 配置检查清单

- [ ] 每个供应商有唯一的 `name`
- [ ] 每个模型映射有唯一的 `display_name`
- [ ] `provider_name` 与 `providers` 中的 `name` 匹配
- [ ] API 密钥使用环境变量
- [ ] 为重要模型配置了 `context_config`
- [ ] 测试了所有模型的调用

### 相关文档

- [配置详解](../配置详解.md)
- [API 文档](API.md)
- [快速开始](../QUICKSTART.md)
