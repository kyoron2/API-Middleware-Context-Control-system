# 流式传输功能文档

## 概述

API Middleware 现在支持流式传输（Streaming）功能，允许客户端实时接收 LLM 的响应内容，而不是等待完整响应生成后再返回。这提供了更好的用户体验，特别是对于长文本生成场景。

## 功能特性

- ✅ OpenAI 兼容的流式 API
- ✅ Server-Sent Events (SSE) 格式
- ✅ 自动内容累积和会话历史更新
- ✅ 完整的错误处理
- ✅ Token 使用统计
- ✅ 支持思考模型（DeepSeek-R1、OpenAI o1 等）

## 使用方法

### 基本用法

要启用流式传输，只需在请求中设置 `stream: true` 参数：

```python
import httpx
import json

async def stream_chat():
    url = "http://localhost:8000/v1/chat/completions"
    
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "user", "content": "请介绍一下Python"}
        ],
        "stream": True,  # 启用流式传输
        "temperature": 0.7
    }
    
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    
                    if data.strip() == "[DONE]":
                        break
                    
                    chunk = json.loads(data)
                    content = chunk["choices"][0]["delta"].get("content", "")
                    print(content, end="", flush=True)
```

### JavaScript/TypeScript 示例

```javascript
async function streamChat() {
  const response = await fetch('http://localhost:8000/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'deepseek/deepseek-chat',
      messages: [
        { role: 'user', content: '请介绍一下Python' }
      ],
      stream: true,
      temperature: 0.7
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        
        if (data.trim() === '[DONE]') {
          return;
        }

        try {
          const parsed = JSON.parse(data);
          const content = parsed.choices[0]?.delta?.content || '';
          process.stdout.write(content);
        } catch (e) {
          // Skip invalid JSON
        }
      }
    }
  }
}
```

### cURL 示例

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek/deepseek-chat",
    "messages": [
      {"role": "user", "content": "请介绍一下Python"}
    ],
    "stream": true,
    "temperature": 0.7
  }' \
  --no-buffer
```

## 响应格式

### 流式响应块（Chunk）

每个流式响应块都是一个 SSE（Server-Sent Events）格式的消息：

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1234567890,"model":"deepseek-chat","choices":[{"index":0,"delta":{"role":"assistant","content":"Python"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1234567890,"model":"deepseek-chat","choices":[{"index":0,"delta":{"content":"是一种"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1234567890,"model":"deepseek-chat","choices":[{"index":0,"delta":{"content":"高级编程语言"},"finish_reason":"stop"}]}

data: [DONE]
```

### 响应块结构

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion.chunk",
  "created": 1234567890,
  "model": "deepseek-chat",
  "choices": [
    {
      "index": 0,
      "delta": {
        "role": "assistant",    // 仅在第一个块中出现
        "content": "文本内容"    // 增量内容
      },
      "finish_reason": null     // 最后一个块为 "stop"
    }
  ]
}
```

### 结束标记

流式传输结束时会发送特殊的 `[DONE]` 消息：

```
data: [DONE]
```

## 与非流式模式的对比

### 非流式模式

```python
response = await client.post(url, json={
    "model": "deepseek/deepseek-chat",
    "messages": [...],
    "stream": False  # 或省略此参数
})

data = response.json()
content = data["choices"][0]["message"]["content"]
print(content)  # 一次性输出完整内容
```

### 流式模式

```python
async with client.stream("POST", url, json={
    "model": "deepseek/deepseek-chat",
    "messages": [...],
    "stream": True
}) as response:
    async for line in response.aiter_lines():
        # 实时处理每个内容块
        ...
```

## 内部实现

### 流程图

```
Client Request (stream=true)
    ↓
API Endpoint (/v1/chat/completions)
    ↓
Context Management (应用上下文策略)
    ↓
Provider Manager (stream_request)
    ↓
Provider API (流式请求)
    ↓
SSE Stream Processing
    ↓
Content Accumulation (累积内容)
    ↓
Session Update (更新会话历史)
    ↓
Client Response (SSE chunks)
```

### 关键组件

1. **endpoints.py**
   - `chat_completions()`: 检测 `stream` 参数
   - `_stream_chat_completion()`: 处理流式响应生成

2. **provider_manager.py**
   - `stream_request()`: 向上游 API 发起流式请求
   - SSE 解析和转换

3. **openai.py**
   - `ChatCompletionStreamResponse`: 流式响应数据模型
   - `StreamChoice`: 流式选择数据模型

## 特性说明

### 自动内容累积

流式传输过程中，系统会自动累积所有内容块，并在流结束后：
- 将完整响应添加到会话历史
- 更新 token 使用统计
- 记录完成日志

### 错误处理

流式传输中的错误会以 SSE 格式返回：

```
data: {"error":{"message":"错误信息","type":"stream_error","code":"500"}}
```

### Token 统计

流式模式下的 token 统计使用估算方法：
- 提示 tokens: `sum(len(msg.content) for msg in messages) // 4`
- 完成 tokens: `len(accumulated_content) // 4`

注意：这是粗略估算，实际 token 数可能有差异。

## 性能考虑

### 优势
- ✅ 更好的用户体验（实时反馈）
- ✅ 降低首字节时间（TTFB）
- ✅ 适合长文本生成场景

### 注意事项
- ⚠️ 需要保持连接直到流结束
- ⚠️ 客户端需要正确处理 SSE 格式
- ⚠️ Token 统计为估算值

## 测试

运行流式传输测试：

```bash
# 单元测试
pytest tests/test_streaming.py -v

# 手动测试
python test_streaming.py
```

## 兼容性

### OpenAI API 兼容性

流式传输功能完全兼容 OpenAI API 规范：
- ✅ 相同的请求格式
- ✅ 相同的响应格式
- ✅ 相同的 SSE 协议

可以直接替换 OpenAI API 端点使用。

### 思考模型支持

✅ **支持推理/思考模型（Reasoning Models）**：
- **DeepSeek-R1**: 支持 `reasoning_content` 字段
- **OpenAI o1**: 支持 `thinking` 字段
- **其他思考模型**: 自动识别和处理额外的 delta 字段

这些模型在流式输出时会先输出思考过程，然后输出最终答案。中间件会：
1. ✅ 正确转发所有 delta 字段（包括 `reasoning_content`、`thinking` 等）
2. ✅ 分别累积思考内容和最终答案
3. ✅ 在 token 统计中包含思考内容的长度
4. ✅ 记录思考内容的存在（用于监控和调试）

**示例流式输出**：
```
data: {"choices":[{"delta":{"reasoning_content":"让我分析一下这个问题..."}}]}
data: {"choices":[{"delta":{"reasoning_content":"首先，我需要考虑..."}}]}
data: {"choices":[{"delta":{"content":"答案是"}}]}
data: {"choices":[{"delta":{"content":"42"}}]}
data: [DONE]
```

**会话历史存储**：
- 默认只存储最终答案（`content` 字段）
- 思考过程会被记录到日志中
- Token 统计包含思考内容和最终答案的总长度

## 故障排除

### 问题：流式响应中断

**原因**：网络超时或连接断开

**解决**：
- 增加客户端超时设置
- 检查网络连接稳定性
- 查看服务器日志

### 问题：内容乱码

**原因**：编码问题

**解决**：
- 确保使用 UTF-8 编码
- 正确解码 SSE 数据

### 问题：无法解析 JSON

**原因**：SSE 格式错误

**解决**：
- 检查是否正确提取 `data:` 后的内容
- 跳过空行和注释行
- 处理 `[DONE]` 特殊消息

## 未来改进

- [ ] 支持多个并发流
- [ ] 更精确的 token 计数
- [ ] 流式传输性能监控
- [ ] 断点续传支持

## 参考资料

- [OpenAI Streaming API](https://platform.openai.com/docs/api-reference/streaming)
- [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
