# 思考模型支持文档

## 概述

API Middleware 现在完全支持思考模型（Reasoning Models），如 DeepSeek-R1、OpenAI o1 等。这些模型在生成响应时会先输出思考过程，然后输出最终答案，提供更透明的推理过程。

## 支持的模型

| 模型 | 思考字段 | 状态 |
|------|---------|------|
| DeepSeek-R1 | `reasoning_content` | ✅ 完全支持 |
| OpenAI o1 | `thinking` | ✅ 完全支持 |
| 其他思考模型 | 任意字段 | ✅ 自动识别 |

## 工作原理

### 流式输出格式

思考模型的流式输出通常包含两个阶段：

**阶段 1: 思考过程**
```
data: {"choices":[{"delta":{"reasoning_content":"让我分析一下..."}}]}
data: {"choices":[{"delta":{"reasoning_content":"首先需要考虑..."}}]}
data: {"choices":[{"delta":{"reasoning_content":"然后..."}}]}
```

**阶段 2: 最终答案**
```
data: {"choices":[{"delta":{"content":"答案是"}}]}
data: {"choices":[{"delta":{"content":"42"}}]}
data: [DONE]
```

### 中间件处理

中间件会自动：

1. **识别字段**: 自动识别 `reasoning_content`、`thinking` 或其他思考字段
2. **完整转发**: 将所有字段完整转发给客户端
3. **分别累积**: 分别累积思考内容和最终答案
4. **智能存储**: 只存储最终答案到会话历史（避免上下文膨胀）
5. **完整统计**: Token 统计包含思考内容和答案的总长度

## 使用方法

### Python 客户端

#### 选项 1: 只显示最终答案

```python
import httpx
import json

async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        "http://localhost:8000/v1/chat/completions",
        json={
            "model": "deepseek/deepseek-reasoner",
            "messages": [{"role": "user", "content": "计算 123 * 456"}],
            "stream": True
        }
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data.strip() == "[DONE]":
                    break
                
                chunk = json.loads(data)
                delta = chunk["choices"][0]["delta"]
                
                # 只处理最终答案
                if delta.get("content"):
                    print(delta["content"], end="", flush=True)
```

#### 选项 2: 分别显示思考和答案

```python
async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        "http://localhost:8000/v1/chat/completions",
        json={
            "model": "deepseek/deepseek-reasoner",
            "messages": [{"role": "user", "content": "计算 123 * 456"}],
            "stream": True
        }
    ) as response:
        print("💭 思考过程:")
        
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data.strip() == "[DONE]":
                    break
                
                chunk = json.loads(data)
                delta = chunk["choices"][0]["delta"]
                
                # 显示思考过程（灰色）
                if delta.get("reasoning_content"):
                    print(f"\033[90m{delta['reasoning_content']}\033[0m", end="")
                
                # 显示最终答案（正常颜色）
                if delta.get("content"):
                    if not answer_started:
                        print("\n\n✅ 最终答案:")
                        answer_started = True
                    print(delta["content"], end="")
```

### JavaScript 客户端

```javascript
const response = await fetch('http://localhost:8000/v1/chat/completions', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    model: 'deepseek/deepseek-reasoner',
    messages: [{role: 'user', content: '计算 123 * 456'}],
    stream: true
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

let reasoning = '';
let answer = '';

while (true) {
  const {done, value} = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6);
      if (data.trim() === '[DONE]') break;
      
      try {
        const parsed = JSON.parse(data);
        const delta = parsed.choices[0]?.delta || {};
        
        // 处理思考内容
        if (delta.reasoning_content) {
          reasoning += delta.reasoning_content;
          console.log(`[思考] ${delta.reasoning_content}`);
        }
        
        // 处理最终答案
        if (delta.content) {
          answer += delta.content;
          console.log(`[答案] ${delta.content}`);
        }
      } catch (e) {
        // Skip invalid JSON
      }
    }
  }
}

console.log('\n统计:');
console.log(`思考长度: ${reasoning.length}`);
console.log(`答案长度: ${answer.length}`);
```

## 会话历史管理

### 存储策略

中间件采用智能存储策略：

**默认行为**:
- ✅ 存储最终答案（`content` 字段）到会话历史
- ✅ 思考过程记录到日志
- ✅ Token 统计包含思考和答案的总长度

**特殊情况**:
- 如果只有思考内容没有最终答案，则存储思考内容
- 这确保会话历史始终有内容

### 为什么不存储思考内容？

1. **避免上下文膨胀**: 思考内容通常很长，会快速消耗上下文窗口
2. **保持对话连贯**: 后续对话只需要最终答案，不需要思考过程
3. **降低成本**: 减少发送给 LLM 的 token 数量

### 如何访问思考内容？

思考内容会记录到日志中：

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "message": "Reasoning model output detected",
  "session_id": "session_1234",
  "reasoning_length": 500,
  "content_length": 50
}
```

## Token 统计

### 计算方法

```python
# 思考内容长度
reasoning_tokens = len(accumulated_reasoning) // 4

# 最终答案长度
content_tokens = len(accumulated_content) // 4

# 总 token 数（包含思考和答案）
total_tokens = (len(accumulated_reasoning) + len(accumulated_content)) // 4
```

### 示例

假设：
- 思考内容: "让我分析一下这个问题..." (100 字符)
- 最终答案: "答案是 42" (10 字符)

Token 统计：
- 思考 tokens: 100 / 4 = 25
- 答案 tokens: 10 / 4 = 2.5 ≈ 3
- 总 tokens: 110 / 4 = 27.5 ≈ 28

## 性能考虑

### 优势

✅ **透明推理**: 用户可以看到模型的思考过程
✅ **更高质量**: 思考模型通常给出更准确的答案
✅ **灵活显示**: 客户端可以选择是否显示思考过程

### 注意事项

⚠️ **更长延迟**: 思考过程会增加首字节时间
⚠️ **更多 Token**: 思考内容会消耗额外的 token
⚠️ **需要处理**: 客户端需要正确处理两种内容类型

## 测试

### 运行测试

```bash
# 思考模型单元测试
pytest tests/test_reasoning_models.py -v

# 完整测试套件
pytest tests/ -v
```

### 手动测试

```bash
# 运行示例脚本
python examples/reasoning_model_example.py
```

## 故障排除

### 问题：只看到思考内容，没有最终答案

**原因**: 模型可能只输出了思考过程

**解决**:
- 检查模型配置
- 查看完整的流式输出
- 确认模型是否支持最终答案输出

### 问题：思考内容显示乱码

**原因**: 编码问题

**解决**:
- 确保使用 UTF-8 编码
- 正确解码 SSE 数据

### 问题：Token 统计不准确

**原因**: 使用字符数估算

**解决**:
- 这是粗略估算，实际 token 数可能有差异
- 可以集成 tiktoken 库获得更准确的统计

## 配置选项

### 未来可能的配置

```yaml
reasoning_models:
  # 是否存储思考内容到会话历史
  store_reasoning: false
  
  # 思考内容的最大长度（字符）
  max_reasoning_length: 10000
  
  # 是否在日志中记录思考内容
  log_reasoning: true
  
  # 思考内容的上下文管理策略
  reasoning_context_strategy: "discard"  # "discard", "summarize", "keep"
```

## 示例场景

### 场景 1: 数学计算

**输入**: "计算 123 * 456"

**思考过程**:
```
让我计算 123 * 456
首先，我可以将其分解：
123 * 456 = 123 * (400 + 50 + 6)
= 123 * 400 + 123 * 50 + 123 * 6
= 49200 + 6150 + 738
= 56088
```

**最终答案**: "123 * 456 = 56088"

### 场景 2: 逻辑推理

**输入**: "如果所有的猫都怕水，而 Tom 是一只猫，那么 Tom 怕水吗？"

**思考过程**:
```
这是一个经典的三段论推理问题。
前提1：所有的猫都怕水
前提2：Tom 是一只猫
根据演绎推理，如果前提都为真，那么结论必然为真。
因此，Tom 怕水。
```

**最终答案**: "是的，Tom 怕水。"

### 场景 3: 复杂问题

**输入**: "设计一个高效的算法来查找数组中的第 k 大元素"

**思考过程**:
```
这个问题有几种解决方案：
1. 排序后取第 k 个元素 - O(n log n)
2. 使用堆 - O(n log k)
3. 快速选择算法 - 平均 O(n)

快速选择算法是最优的，因为：
- 平均时间复杂度为 O(n)
- 空间复杂度为 O(1)
- 基于快速排序的分区思想

让我详细说明这个算法...
```

**最终答案**: "推荐使用快速选择算法（QuickSelect）..."

## 相关资源

### 文档
- [流式传输文档](docs/STREAMING.md)
- [API 文档](docs/API.md)
- [实现总结](STREAMING_IMPLEMENTATION.md)

### 代码
- `src/api/endpoints.py` - 思考内容处理逻辑
- `tests/test_reasoning_models.py` - 单元测试
- `examples/reasoning_model_example.py` - 使用示例

### 外部资源
- [DeepSeek-R1 文档](https://github.com/deepseek-ai/DeepSeek-R1)
- [OpenAI o1 文档](https://platform.openai.com/docs/models/o1)

## 总结

API Middleware 现在完全支持思考模型，提供：

✅ 自动识别和处理思考字段
✅ 完整转发所有内容给客户端
✅ 智能的会话历史管理
✅ 准确的 token 统计
✅ 灵活的客户端处理选项
✅ 完整的测试覆盖

这使得用户可以充分利用思考模型的强大推理能力，同时保持系统的高效和可维护性。
