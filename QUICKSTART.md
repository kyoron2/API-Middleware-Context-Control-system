# Quick Start Guide

Get the API Middleware Context Control system up and running in 5 minutes.

## Prerequisites

- Python 3.11+ installed
- Docker and Docker Compose (optional, for containerized deployment)
- At least one LLM API key (e.g., OpenAI)

## Option 1: Local Development Setup

### Step 1: Install Dependencies

```bash
# Activate your Python environment
# For conda users:
activate django

# Install dependencies using uv
uv add fastapi pydantic httpx pyyaml python-dotenv uvicorn redis
uv add --dev pytest pytest-asyncio
```

### Step 2: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
# Example:
# OPENAI_API_KEY=sk-your-key-here
```

### Step 3: Configure Providers

Edit `config/config.yaml` to add your API providers:

```yaml
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
```

### Step 4: Test the Setup

```bash
# Run the manual test script
python test_manual.py

# You should see:
# ✓ All manual tests passed!
```

### Step 5: Start the Server

```bash
# Start the middleware server
python -m src.main

# Server will start on http://localhost:8000
```

### Step 6: Verify It Works

```bash
# Test health endpoint
curl http://localhost:8000/health

# List available models
curl http://localhost:8000/v1/models

# Test chat completion (replace with your actual API key in config)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "official/gpt-4",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

## Option 2: Docker Deployment

### Step 1: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
```

### Step 2: Configure Providers

Edit `config/config.yaml` as shown in Option 1.

### Step 3: Start with Docker Compose

```bash
# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f middleware

# Server will start on http://localhost:8000
```

### Step 4: Verify It Works

```bash
# Test health endpoint
curl http://localhost:8000/health

# List available models
curl http://localhost:8000/v1/models
```

## Integrate with OpenWebUI

### Step 1: Open OpenWebUI Settings

Navigate to your OpenWebUI instance (usually http://localhost:3000 or your deployment URL).

### Step 2: Add API Connection

1. Go to Settings → Connections (or similar menu)
2. Click "Add Connection" or "Add API"
3. Fill in the details:
   - **Name**: API Middleware
   - **API Base URL**: `http://localhost:8000/v1`
   - **API Key**: `dummy` (not used by middleware)
4. Save the connection

### Step 3: Select Models

In OpenWebUI's model selector, you should now see models from your middleware:
- `official/gpt-4`
- `official/gpt-3.5-turbo`
- (any other models you configured)

### Step 4: Start Chatting

Select a model and start chatting! The middleware will automatically:
- Manage conversation context
- Reduce token usage when limits are reached
- Route requests to the appropriate provider

## Configuration Tips

### Context Management

Choose a reduction strategy based on your needs:

**Truncation** (simplest):
```yaml
context_config:
  max_turns: 10
  reduction_mode: truncation
```

**Sliding Window** (token-based):
```yaml
context_config:
  max_tokens: 4000
  reduction_mode: sliding_window
```

**Summarization** (most intelligent):
```yaml
context_config:
  max_turns: 10
  reduction_mode: summarization
  summarization_model: gpt-3.5-turbo
```

### Multiple Providers

Add multiple API providers for redundancy or cost optimization:

```yaml
providers:
  - name: official
    base_url: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}
    models:
      - gpt-4
  
  - name: proxy1
    base_url: https://proxy.example.com/v1
    api_key: ${PROXY1_API_KEY}
    models:
      - claude-3-opus
      - claude-3-sonnet

model_mappings:
  - display_name: official/gpt-4
    provider_name: official
    actual_model_name: gpt-4
  
  - display_name: proxy1/claude-opus
    provider_name: proxy1
    actual_model_name: claude-3-opus
```

### Redis for Production

For production deployments, use Redis for session storage:

```yaml
storage:
  type: redis
  redis_url: redis://localhost:6379
  redis_db: 0
```

Then start Redis:
```bash
# With Docker Compose (already included)
docker-compose up -d

# Or standalone
docker run -d -p 6379:6379 redis:alpine
```

## Monitoring

### View Logs

Logs are output in JSON format for easy parsing:

```bash
# Local development
python -m src.main | jq .

# Docker
docker-compose logs -f middleware | jq .
```

### Key Metrics to Monitor

- **Token Usage**: Look for `event_type: "api_completion"` with `tokens` field
- **Context Reductions**: Look for `event_type: "context_reduction"`
- **Errors**: Look for `level: "ERROR"` or `event_type: "provider_error"`

## Troubleshooting

### Issue: "Configuration loading failed"

**Solution**: Check that `config/config.yaml` exists and is valid YAML.

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"
```

### Issue: "Provider returned error: Unauthorized"

**Solution**: Check your API key in `.env` file.

```bash
# Verify environment variable is set
echo $OPENAI_API_KEY  # Linux/Mac
echo %OPENAI_API_KEY%  # Windows CMD
```

### Issue: "Model not found"

**Solution**: Ensure the model is listed in both `providers.models` and `model_mappings`.

```bash
# List available models
curl http://localhost:8000/v1/models
```

### Issue: "Connection refused"

**Solution**: Ensure the server is running.

```bash
# Check if server is running
curl http://localhost:8000/health

# Check Docker containers
docker-compose ps
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [docs/API.md](docs/API.md) for complete API reference
- Explore configuration options in `config/config.yaml`
- Monitor logs to optimize token usage

## Getting Help

- Check the [README.md](README.md) for detailed documentation
- Review [docs/API.md](docs/API.md) for API details
- Check logs for error messages
- Verify configuration with `python test_manual.py`

## Success!

You now have a working API middleware that:
- ✅ Manages conversation context automatically
- ✅ Reduces token costs through intelligent strategies
- ✅ Routes requests to multiple providers
- ✅ Integrates seamlessly with OpenWebUI

Happy chatting! 🚀
