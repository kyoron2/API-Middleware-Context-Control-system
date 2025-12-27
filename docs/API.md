# API Documentation

## Overview

The API Middleware Context Control system provides an OpenAI-compatible API that sits between your client (e.g., OpenWebUI) and multiple LLM providers. It manages conversation context, routes requests to appropriate providers, and reduces token costs through intelligent context management.

**Base URL**: `http://localhost:8000`

**API Version**: `v1`

**Authentication**: API keys are configured per provider in the configuration file. The middleware itself does not require authentication from clients.

---

## Endpoints

### 1. Chat Completions

Create a chat completion with automatic context management.

**Endpoint**: `POST /v1/chat/completions`

**OpenAI Compatibility**: ✅ Compatible with OpenAI Chat Completions API

#### Request

**Headers**:
```
Content-Type: application/json
```

**Body**:
```json
{
  "model": "official/gpt-4",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "stream": false
}
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | Yes | Model identifier in format `provider/model-name` or display name |
| `messages` | array | Yes | Array of message objects with `role` and `content` |
| `temperature` | float | No | Sampling temperature (0-2). Default: 1.0 |
| `max_tokens` | integer | No | Maximum tokens to generate |
| `top_p` | float | No | Nucleus sampling parameter (0-1). Default: 1.0 |
| `frequency_penalty` | float | No | Frequency penalty (-2.0 to 2.0). Default: 0.0 |
| `presence_penalty` | float | No | Presence penalty (-2.0 to 2.0). Default: 0.0 |
| `stream` | boolean | No | Whether to stream responses. Default: false |

**Message Object**:
```json
{
  "role": "system" | "user" | "assistant",
  "content": "Message content"
}
```

#### Response

**Success (200 OK)**:
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "official/gpt-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "I'm doing well, thank you for asking! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 15,
    "total_tokens": 35
  }
}
```

**Error Responses**:

```json
{
  "error": {
    "message": "Invalid model specified",
    "type": "invalid_request_error",
    "code": "invalid_model"
  }
}
```

#### Example Usage

**Python**:
```python
import httpx

async def chat_completion():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json={
                "model": "official/gpt-4",
                "messages": [
                    {"role": "user", "content": "What is the capital of France?"}
                ]
            }
        )
        return response.json()
```

**cURL**:
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "official/gpt-4",
    "messages": [
      {"role": "user", "content": "What is the capital of France?"}
    ]
  }'
```

**JavaScript**:
```javascript
const response = await fetch('http://localhost:8000/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: 'official/gpt-4',
    messages: [
      { role: 'user', content: 'What is the capital of France?' }
    ]
  })
});

const data = await response.json();
console.log(data);
```

---

### 2. List Models

Retrieve a list of all available models.

**Endpoint**: `GET /v1/models`

**OpenAI Compatibility**: ✅ Compatible with OpenAI Models API

#### Request

No parameters required.

#### Response

**Success (200 OK)**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "official/gpt-4",
      "object": "model",
      "created": 1677652288,
      "owned_by": "official"
    },
    {
      "id": "official/gpt-3.5-turbo",
      "object": "model",
      "created": 1677652288,
      "owned_by": "official"
    }
  ]
}
```

#### Example Usage

**Python**:
```python
import httpx

async def list_models():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/v1/models")
        return response.json()
```

**cURL**:
```bash
curl http://localhost:8000/v1/models
```

---

### 3. Health Check

Check the health status of the middleware service.

**Endpoint**: `GET /health`

#### Request

No parameters required.

#### Response

**Success (200 OK)**:
```json
{
  "status": "healthy",
  "storage": "memory",
  "redis_connected": false
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Overall health status: "healthy" or "unhealthy" |
| `storage` | string | Storage backend type: "memory" or "redis" |
| `redis_connected` | boolean | Redis connection status (only if using Redis) |

#### Example Usage

**cURL**:
```bash
curl http://localhost:8000/health
```

---

## Session Management

The middleware automatically manages conversation sessions based on user context. Sessions are identified by a combination of user ID and conversation context.

### Session Lifecycle

1. **Creation**: Sessions are created automatically on the first message
2. **Context Management**: Messages are added to the session history
3. **Context Reduction**: When limits are exceeded, context is reduced according to the configured strategy
4. **Expiration**: Sessions expire after the configured TTL (default: 3600 seconds)

### Session Identification

Sessions are identified using a hash-based approach:
- Format: `session_{hash(user_id) % 10000}`
- User ID is extracted from request context or generated

---

## Context Management Strategies

The middleware supports three context reduction strategies:

### 1. Truncation

Removes the oldest messages while preserving system messages.

**Configuration**:
```yaml
context_config:
  max_turns: 10
  reduction_mode: truncation
```

**Behavior**:
- Keeps the most recent N turns
- Always preserves system messages
- Simple and fast

### 2. Sliding Window

Maintains a token budget and keeps the most recent messages that fit.

**Configuration**:
```yaml
context_config:
  max_tokens: 4000
  reduction_mode: sliding_window
```

**Behavior**:
- Estimates token count for each message
- Keeps messages until token budget is exceeded
- Removes oldest messages first
- Preserves system messages

### 3. Summarization

Summarizes old messages and keeps recent ones.

**Configuration**:
```yaml
context_config:
  max_turns: 10
  reduction_mode: summarization
  summarization_model: gpt-3.5-turbo
```

**Behavior**:
- Summarizes messages beyond the turn limit
- Stores summary in memory zone
- Keeps recent messages intact
- Uses configured model for summarization

---

## Model Naming and Routing

### Model Name Format

Models are identified using a namespace format:

```
provider/model-name
```

**Examples**:
- `official/gpt-4`
- `proxy1/claude-3-opus`
- `proxy2/qwen-plus`

### Model Resolution

The middleware resolves model names in the following order:

1. **Exact match**: Looks for exact display name in model mappings
2. **Namespace parsing**: Parses `provider/model` format
3. **Provider lookup**: Finds provider by name
4. **Model mapping**: Maps display name to actual API model name

### Example Configuration

```yaml
providers:
  - name: official
    base_url: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}
    models:
      - gpt-4
      - gpt-3.5-turbo

model_mappings:
  - display_name: official/gpt-4
    provider_name: official
    actual_model_name: gpt-4
    context_config:
      max_turns: 15
      max_tokens: 6000
```

---

## Error Handling

The middleware returns OpenAI-compatible error responses.

### Error Response Format

```json
{
  "error": {
    "message": "Error description",
    "type": "error_type",
    "code": "error_code"
  }
}
```

### Common Error Types

| HTTP Status | Error Type | Description |
|-------------|------------|-------------|
| 400 | `invalid_request_error` | Invalid request parameters |
| 404 | `invalid_request_error` | Model not found |
| 500 | `api_error` | Internal server error |
| 502 | `api_error` | Provider API error |
| 504 | `timeout_error` | Request timeout |

### Example Error Responses

**Invalid Model**:
```json
{
  "error": {
    "message": "Model 'invalid/model' not found",
    "type": "invalid_request_error",
    "code": "model_not_found"
  }
}
```

**Provider Error**:
```json
{
  "error": {
    "message": "Provider 'official' returned error: Rate limit exceeded",
    "type": "api_error",
    "code": "provider_error"
  }
}
```

**Timeout**:
```json
{
  "error": {
    "message": "Request to provider 'official' timed out",
    "type": "timeout_error",
    "code": "timeout"
  }
}
```

---

## Rate Limiting and Quotas

The middleware does not implement its own rate limiting. Rate limits are enforced by the underlying provider APIs.

**Recommendations**:
- Configure appropriate timeouts in provider settings
- Monitor provider API usage through logs
- Implement client-side retry logic with exponential backoff

---

## Logging and Monitoring

### Log Format

All logs are output in JSON format for easy parsing:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "api_middleware",
  "message": "API call completed",
  "event_type": "api_completion",
  "session_id": "session_1234",
  "model": "official/gpt-4",
  "tokens": {
    "prompt": 100,
    "completion": 50,
    "total": 150
  }
}
```

### Event Types

| Event Type | Description |
|------------|-------------|
| `api_call` | Incoming API request received |
| `api_completion` | API request completed successfully |
| `context_reduction` | Context reduction triggered |
| `provider_error` | Error from provider API |

### Monitoring Metrics

Key metrics to monitor:

- **Token Usage**: Track `tokens.total` in completion logs
- **Context Reductions**: Count `context_reduction` events
- **Error Rate**: Count `provider_error` events
- **Response Time**: Calculate from `api_call` to `api_completion`

---

## Integration Examples

### OpenWebUI Integration

1. Open OpenWebUI settings
2. Navigate to "Connections" or "API Settings"
3. Add a new connection:
   - **Name**: API Middleware
   - **API Base URL**: `http://localhost:8000/v1`
   - **API Key**: `dummy` (not used by middleware)
4. Save and select models from the middleware

### LangChain Integration

```python
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

chat = ChatOpenAI(
    openai_api_base="http://localhost:8000/v1",
    openai_api_key="dummy",
    model_name="official/gpt-4"
)

response = chat([HumanMessage(content="Hello!")])
print(response.content)
```

### OpenAI Python SDK

```python
import openai

openai.api_base = "http://localhost:8000/v1"
openai.api_key = "dummy"

response = openai.ChatCompletion.create(
    model="official/gpt-4",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

---

## Best Practices

### 1. Model Selection

- Use namespace format for clarity: `provider/model-name`
- Configure context limits per model based on capabilities
- Use cheaper models for summarization

### 2. Context Management

- Start with truncation strategy for simplicity
- Use sliding window for token-sensitive applications
- Use summarization for long conversations

### 3. Error Handling

- Implement retry logic with exponential backoff
- Handle provider errors gracefully
- Monitor error logs for patterns

### 4. Performance

- Use Redis storage for production deployments
- Configure appropriate session TTL
- Monitor token usage to optimize costs

### 5. Security

- Keep API keys in environment variables
- Use HTTPS in production
- Implement authentication if exposing publicly

---

## Troubleshooting

### Common Issues

**Issue**: Model not found
- **Solution**: Check model name format and configuration
- **Check**: `GET /v1/models` to see available models

**Issue**: Provider timeout
- **Solution**: Increase timeout in provider configuration
- **Check**: Provider API status and network connectivity

**Issue**: Context not reducing
- **Solution**: Verify context configuration and reduction mode
- **Check**: Logs for `context_reduction` events

**Issue**: Redis connection failed
- **Solution**: Verify Redis is running and URL is correct
- **Alternative**: Switch to memory storage for testing

---

## API Versioning

Current API version: `v1`

The API follows semantic versioning principles:
- **Major version** (v1, v2): Breaking changes
- **Minor updates**: Backward-compatible features
- **Patches**: Bug fixes

---

## Support and Resources

- **GitHub**: [Repository URL]
- **Documentation**: See README.md
- **Configuration**: See config/config.yaml
- **Issues**: Report bugs via GitHub Issues

---

## Changelog

### v1.0.0 (Initial Release)

- OpenAI-compatible chat completions endpoint
- Multi-provider routing
- Three context reduction strategies
- Session management with memory and Redis storage
- Structured JSON logging
- Docker deployment support
