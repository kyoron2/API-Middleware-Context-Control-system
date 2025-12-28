# Summarization 模式配置指南

## 概述

本文档说明如何正确配置 `summarization`（摘要）模式，包括全局配置和模型级别配置。

## 关键要点

⚠️ **使用 summarization 模式时，必须指定用于生成摘要的 AI 模型！**

- **全局配置**：使用 `default_summarization_model` 字段
- **模型级别配置**：使用 `summarization_model` 字段
- 模型级别配置会覆盖全局配置

---

## 配置方式

### 方式 1：全局配置（推荐用于统一策略）

适用于所有模型使用相同的摘要策略。

```yaml
context:
  default_max_turns: 10
  default_max_tokens: 4000
  default_reduction_mode: summarization  # 使用摘要模式
  default_summarization_model: openai/gpt-3.5-turbo  # ⚠️ 必须配置！
  summarization_prompt: |
    你是一个对话摘要助手。请简洁地总结以下对话，
    保留关键信息、用户意图和重要上下文。
    将摘要控制在 {max_tokens} 个 Token 以内。
    
    对话内容：
    {conversation_text}
    
    摘要：

providers:
  - name: openai
    base_url: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}
    models:
      - gpt-4
      - gpt-3.5-turbo

model_mappings:
  - display_name: openai/gpt-4
    provider_name: openai
    actual_model_name: gpt-4
    # 不配置 context_config，使用全局默认配置
  
  - display_name: openai/gpt-3.5-turbo
    provider_name: openai
    actual_model_name: gpt-3.5-turbo
    # 不配置 context_config，使用全局默认配置
```

**说明**：
- 所有模型都会使用 `summarization` 模式
- 所有模型都会使用 `openai/gpt-3.5-turbo` 来生成摘要
- 节省配置，统一管理

---

### 方式 2：模型级别配置（推荐用于差异化策略）

适用于不同模型使用不同的上下文策略。

```yaml
context:
  default_max_turns: 10
  default_max_tokens: 4000
  default_reduction_mode: truncation  # 全局默认使用截断
  default_summarization_model: openai/gpt-3.5-turbo  # 可选，作为后备

providers:
  - name: openai
    base_url: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}
    models:
      - gpt-4
      - gpt-3.5-turbo

model_mappings:
  # GPT-4：使用摘要模式（保留更多上下文）
  - display_name: openai/gpt-4
    provider_name: openai
    actual_model_name: gpt-4
    context_config:
      max_turns: 20
      max_tokens: 8000
      reduction_mode: summarization  # 模型级别配置
      summarization_model: openai/gpt-3.5-turbo  # ⚠️ 必须配置！
      memory_zone_enabled: true
  
  # GPT-3.5：使用截断模式（快速响应）
  - display_name: openai/gpt-3.5-turbo
    provider_name: openai
    actual_model_name: gpt-3.5-turbo
    context_config:
      max_turns: 10
      max_tokens: 4000
      reduction_mode: truncation  # 不需要 summarization_model
```

**说明**：
- GPT-4 使用摘要模式，需要配置 `summarization_model`
- GPT-3.5 使用截断模式，不需要配置 `summarization_model`
- 灵活控制每个模型的行为

---

### 方式 3：混合配置（全局 + 模型覆盖）

全局设置摘要模式，个别模型覆盖。

```yaml
context:
  default_max_turns: 15
  default_max_tokens: 6000
  default_reduction_mode: summarization  # 全局使用摘要
  default_summarization_model: openai/gpt-3.5-turbo  # 全局摘要模型

providers:
  - name: openai
    base_url: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}
    models:
      - gpt-4
      - gpt-3.5-turbo
  
  - name: proxy
    base_url: https://api.proxy.com/v1
    api_key: ${PROXY_API_KEY}
    models:
      - claude-3-opus

model_mappings:
  # 使用全局配置
  - display_name: openai/gpt-4
    provider_name: openai
    actual_model_name: gpt-4
  
  # 覆盖全局配置，使用截断
  - display_name: openai/gpt-3.5-turbo
    provider_name: openai
    actual_model_name: gpt-3.5-turbo
    context_config:
      max_turns: 10
      max_tokens: 4000
      reduction_mode: truncation  # 覆盖全局的 summarization
  
  # 使用全局配置
  - display_name: proxy/claude-3-opus
    provider_name: proxy
    actual_model_name: claude-3-opus
```

**说明**：
- `openai/gpt-4` 和 `proxy/claude-3-opus` 使用全局摘要配置
- `openai/gpt-3.5-turbo` 覆盖为截断模式
- 最灵活的配置方式

---

## 跨供应商摘要

摘要模型可以来自不同的供应商！

```yaml
providers:
  - name: openai
    base_url: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}
    models:
      - gpt-4
      - gpt-3.5-turbo
  
  - name: proxy
    base_url: https://api.proxy.com/v1
    api_key: ${PROXY_API_KEY}
    models:
      - claude-3-opus
      - qwen-plus

model_mappings:
  # 使用 OpenAI 的 gpt-3.5-turbo 来摘要 Proxy 的 claude-3-opus 对话
  - display_name: proxy/claude-3-opus
    provider_name: proxy
    actual_model_name: claude-3-opus
    context_config:
      max_turns: 20
      max_tokens: 10000
      reduction_mode: summarization
      summarization_model: openai/gpt-3.5-turbo  # 跨供应商！
  
  # 使用 Proxy 的 qwen-plus 来摘要 OpenAI 的 gpt-4 对话
  - display_name: openai/gpt-4
    provider_name: openai
    actual_model_name: gpt-4
    context_config:
      max_turns: 20
      max_tokens: 8000
      reduction_mode: summarization
      summarization_model: proxy/qwen-plus  # 跨供应商！
```

**优势**：
- 使用便宜的模型做摘要，节省成本
- 灵活选择最适合的摘要模型

---

## 配置验证

系统会自动验证配置的正确性：

### 验证规则

1. **全局验证**：
   - 如果 `default_reduction_mode: summarization`
   - 则 `default_summarization_model` 必须配置
   - 否则报错：`Global context uses summarization mode but default_summarization_model is not configured`

2. **模型级别验证**：
   - 如果 `context_config.reduction_mode: summarization`
   - 则 `context_config.summarization_model` 必须配置
   - 否则报错：`Model mapping 'xxx' uses summarization mode but summarization_model is not configured`

### 验证示例

❌ **错误配置**：
```yaml
context:
  default_reduction_mode: summarization
  # 缺少 default_summarization_model！
```

✅ **正确配置**：
```yaml
context:
  default_reduction_mode: summarization
  default_summarization_model: openai/gpt-3.5-turbo  # 正确！
```

---

## 成本优化建议

### 1. 使用便宜的模型做摘要

```yaml
# 用 gpt-3.5-turbo 摘要 gpt-4 的对话
model_mappings:
  - display_name: openai/gpt-4
    provider_name: openai
    actual_model_name: gpt-4
    context_config:
      reduction_mode: summarization
      summarization_model: openai/gpt-3.5-turbo  # 便宜！
```

### 2. 根据模型价格选择策略

```yaml
model_mappings:
  # 昂贵的模型：使用摘要（保留更多信息）
  - display_name: openai/gpt-4
    context_config:
      reduction_mode: summarization
      summarization_model: openai/gpt-3.5-turbo
  
  # 便宜的模型：使用截断（快速响应）
  - display_name: openai/gpt-3.5-turbo
    context_config:
      reduction_mode: truncation
```

### 3. 调整摘要触发阈值

```yaml
context_config:
  max_turns: 20  # 更大的阈值，减少摘要频率
  max_tokens: 8000
  reduction_mode: summarization
  summarization_model: openai/gpt-3.5-turbo
```

---

## 常见问题

### Q1: 必须配置 summarization_model 吗？

**A**: 只有在使用 `summarization` 模式时才必须配置。如果使用 `truncation` 或 `sliding_window` 模式，不需要配置。

### Q2: 可以使用不同供应商的模型做摘要吗？

**A**: 可以！`summarization_model` 可以指向任何已配置的模型，不限于同一供应商。

### Q3: 全局配置和模型配置哪个优先？

**A**: 模型级别的 `context_config` 会完全覆盖全局配置。

### Q4: 如何选择摘要模型？

**A**: 建议：
- 使用便宜的模型（如 gpt-3.5-turbo）
- 使用响应快的模型
- 使用中文能力强的模型（如果对话是中文）

### Q5: summarization_prompt 是必需的吗？

**A**: 不是必需的，但强烈建议配置。好的提示词可以提高摘要质量。

---

## 完整配置示例

```yaml
system:
  port: 8000
  log_level: INFO
  session_ttl: 3600

storage:
  type: memory

context:
  default_max_turns: 15
  default_max_tokens: 6000
  default_reduction_mode: summarization
  default_summarization_model: openai/gpt-3.5-turbo
  summarization_prompt: |
    你是一个专业的对话摘要助手。
    
    任务：总结以下对话，提取关键信息：
    - 用户的主要问题和需求
    - 已经讨论的重要话题
    - 待解决的问题
    - 重要的决策或结论
    
    要求：
    - 保持客观和准确
    - 使用简洁的语言
    - 控制在 {max_tokens} 个 Token 以内
    - 使用中文输出
    
    对话内容：
    {conversation_text}
    
    摘要输出：

providers:
  - name: openai
    base_url: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}
    timeout: 30
    models:
      - gpt-4
      - gpt-3.5-turbo

model_mappings:
  - display_name: openai/gpt-4
    provider_name: openai
    actual_model_name: gpt-4
    context_config:
      max_turns: 20
      max_tokens: 8000
      reduction_mode: summarization
      summarization_model: openai/gpt-3.5-turbo
      memory_zone_enabled: true
  
  - display_name: openai/gpt-3.5-turbo
    provider_name: openai
    actual_model_name: gpt-3.5-turbo
    context_config:
      max_turns: 10
      max_tokens: 4000
      reduction_mode: truncation
```

---

## 总结

✅ **使用 summarization 模式时，必须配置摘要模型**
✅ **全局配置使用 `default_summarization_model`**
✅ **模型配置使用 `summarization_model`**
✅ **可以跨供应商使用摘要模型**
✅ **建议使用便宜的模型做摘要**
✅ **系统会自动验证配置正确性**

---

**相关文档**：
- [配置详解](配置详解.md)
- [多供应商配置指南](docs/MULTI_PROVIDER_CONFIG.md)
