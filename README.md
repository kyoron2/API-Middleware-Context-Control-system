# API Middleware Context Control

智能 API 中间层，用于管理多个 LLM 提供商的对话上下文，降低 Token 成本。

## 功能特性

- 🔄 **多提供商路由** - 统一管理多个 API 提供商（OpenAI、代理站点等）
- 💬 **智能上下文管理** - 自动压缩和管理对话历史
- 📊 **Token 成本控制** - 通过上下文缩减策略降低 Token 消耗
- 🔌 **OpenAI API 兼容** - 无缝集成 OpenWebUI 和其他客户端
- 📝 **结构化日志** - JSON 格式日志，便于分析和监控
- 🐳 **Docker 部署** - 容器化部署，易于扩展

## 快速开始

### 前置要求

- Python 3.11+
- Docker 和 Docker Compose（可选）
- Redis（可选，用于生产环境）

### 安装

1. 克隆仓库：
```bash
git clone <repository-url>
cd fastapi-wangg
```

2. 激活虚拟环境并安装依赖：
```bash
# Windows
.venv\Scripts\activate

# 使用 uv 安装依赖（如果已安装 uv）
activate django & uv add fastapi pydantic httpx pyyaml python-dotenv uvicorn redis
```

3. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，添加你的 API 密钥
```

4. 配置提供商和模型：
```bash
# 编辑 config/config.yaml
# 添加你的 API 提供商和模型映射
```

### 运行

#### 方式 1：直接运行

```bash
python -m src.main
```

#### 方式 2：使用 Docker Compose

```bash
docker-compose up -d
```

服务将在 `http://localhost:8000` 启动。

### 验证

检查服务健康状态：
```bash
curl http://localhost:8000/health
```

列出可用模型：
```bash
curl http://localhost:8000/v1/models
```

## 配置说明

### 配置文件结构

配置文件位于 `config/config.yaml`：

```yaml
system:
  port: 8000
  log_level: INFO
  session_ttl: 3600  # 会话过期时间（秒）

storage:
  type: memory  # "memory" 或 "redis"
  redis_url: redis://localhost:6379
  redis_db: 0

context:
  default_max_turns: 10  # 最大对话轮次
  default_max_tokens: 4000  # 最大 Token 数
  default_reduction_mode: truncation  # "truncation", "summarization", "sliding_window"

providers:
  - name: official
    base_url: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}
    timeout: 30
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

### 环境变量

在 `.env` 文件中配置：

```bash
# 配置文件路径
MIDDLEWARE_CONFIG_PATH=config/config.yaml

# 服务端口
MIDDLEWARE_PORT=8000

# 日志级别
MIDDLEWARE_LOG_LEVEL=INFO

# Redis 连接（如果使用 Redis 存储）
REDIS_URL=redis://localhost:6379/0

# API 密钥
OPENAI_API_KEY=sk-your-key-here
```

## 使用示例

### 与 OpenWebUI 集成

在 OpenWebUI 中配置：

1. 打开 OpenWebUI 设置
2. 添加新的 API 连接：
   - API Base URL: `http://localhost:8000/v1`
   - API Key: `dummy`（中间层会使用配置的密钥）
3. 选择可用的模型

### API 调用示例

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/v1/chat/completions",
        json={
            "model": "official/gpt-4",
            "messages": [
                {"role": "user", "content": "Hello!"}
            ]
        }
    )
    print(response.json())
```

## 上下文管理策略

### 1. 截断策略 (Truncation)

删除最早的消息，保留最近的 N 轮对话：

```yaml
context_config:
  max_turns: 10
  reduction_mode: truncation
```

### 2. 滑动窗口策略 (Sliding Window)

基于 Token 预算保留最近的消息：

```yaml
context_config:
  max_tokens: 4000
  reduction_mode: sliding_window
```

### 3. 摘要策略 (Summarization)

摘要旧消息，保留最近的对话：

```yaml
context_config:
  max_turns: 10
  reduction_mode: summarization
  summarization_model: gpt-3.5-turbo
```

## Docker 部署

### 构建镜像

```bash
docker build -t api-middleware .
```

### 使用 Docker Compose

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f middleware

# 停止服务
docker-compose down
```

### 环境变量配置

在 `docker-compose.yml` 中或通过 `.env` 文件配置：

```yaml
environment:
  - OPENAI_API_KEY=${OPENAI_API_KEY}
  - MIDDLEWARE_LOG_LEVEL=INFO
  - REDIS_URL=redis://redis:6379/0
```

## 监控和日志

### 日志格式

所有日志以 JSON 格式输出：

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

### 关键事件

- `api_call` - API 调用接收
- `api_completion` - API 调用完成
- `context_reduction` - 上下文缩减事件
- `provider_error` - 提供商错误

## 故障排除

### 常见问题

1. **配置加载失败**
   - 检查 `config/config.yaml` 语法
   - 确保环境变量已设置
   - 查看启动日志

2. **提供商连接失败**
   - 验证 API 密钥
   - 检查网络连接
   - 确认 base_url 正确

3. **Redis 连接失败**
   - 确保 Redis 服务运行
   - 检查 REDIS_URL 配置
   - 或切换到内存存储模式

## 开发

### 项目结构

```
.
├── src/
│   ├── api/          # FastAPI 应用和端点
│   ├── core/         # 核心业务逻辑
│   ├── models/       # 数据模型
│   └── utils/        # 工具函数
├── config/           # 配置文件
├── tests/            # 测试文件
├── Dockerfile        # Docker 镜像定义
└── docker-compose.yml # Docker Compose 配置
```

### 运行测试

```bash
pytest tests/
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
