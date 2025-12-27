# Deployment Checklist

Use this checklist to ensure a smooth deployment of the API Middleware Context Control system.

## Pre-Deployment

### ✅ Environment Setup

- [ ] Python 3.11+ installed (for local deployment)
- [ ] Docker and Docker Compose installed (for containerized deployment)
- [ ] Network access to LLM provider APIs
- [ ] Redis available (optional, for production)

### ✅ Configuration

- [ ] Copy `.env.example` to `.env`
- [ ] Add all required API keys to `.env`
- [ ] Review and customize `config/config.yaml`
- [ ] Verify provider URLs are correct
- [ ] Configure context reduction strategies per model
- [ ] Set appropriate session TTL
- [ ] Choose storage backend (memory or redis)

### ✅ Testing

- [ ] Run manual test script: `python test_manual.py`
- [ ] Verify all tests pass
- [ ] Test configuration loading
- [ ] Verify API keys are valid

## Deployment Options

### Option A: Local Development

#### Setup
- [ ] Activate Python environment
- [ ] Install dependencies: `uv add fastapi pydantic httpx pyyaml python-dotenv uvicorn redis`
- [ ] Verify configuration: `python test_manual.py`

#### Start
- [ ] Run: `python -m src.main`
- [ ] Verify health: `curl http://localhost:8000/health`
- [ ] Test models endpoint: `curl http://localhost:8000/v1/models`

#### Monitor
- [ ] Check console logs for errors
- [ ] Verify JSON log format
- [ ] Monitor token usage in logs

### Option B: Docker Deployment

#### Build
- [ ] Review `Dockerfile`
- [ ] Review `docker-compose.yml`
- [ ] Build image: `docker-compose build`

#### Start
- [ ] Start services: `docker-compose up -d`
- [ ] Check status: `docker-compose ps`
- [ ] View logs: `docker-compose logs -f middleware`

#### Verify
- [ ] Health check: `curl http://localhost:8000/health`
- [ ] Models endpoint: `curl http://localhost:8000/v1/models`
- [ ] Redis connection (if using): `docker-compose exec redis redis-cli ping`

## OpenWebUI Integration

### Configuration
- [ ] Access OpenWebUI settings
- [ ] Add new API connection
- [ ] Set API Base URL: `http://localhost:8000/v1` (or your deployment URL)
- [ ] Set API Key: `dummy` (not used by middleware)
- [ ] Save connection

### Verification
- [ ] Verify models appear in OpenWebUI
- [ ] Test chat with a simple message
- [ ] Check middleware logs for request
- [ ] Verify response is received

### Testing
- [ ] Test single-turn conversation
- [ ] Test multi-turn conversation
- [ ] Test context reduction (send 15+ messages)
- [ ] Check logs for context_reduction events
- [ ] Verify token usage is logged

## Production Considerations

### Security
- [ ] Use HTTPS in production (configure reverse proxy)
- [ ] Secure API keys (use secrets management)
- [ ] Configure CORS appropriately (update `src/api/app.py`)
- [ ] Consider adding authentication
- [ ] Review and restrict network access

### Performance
- [ ] Use Redis for session storage
- [ ] Configure appropriate session TTL
- [ ] Set reasonable timeout values
- [ ] Monitor memory usage
- [ ] Consider horizontal scaling if needed

### Monitoring
- [ ] Set up log aggregation (e.g., ELK stack)
- [ ] Configure log level appropriately (INFO for production)
- [ ] Monitor key metrics:
  - Request rate
  - Token usage
  - Context reduction frequency
  - Error rate
  - Response time
- [ ] Set up alerts for errors

### Backup and Recovery
- [ ] Document configuration
- [ ] Backup `.env` file securely
- [ ] Backup `config/config.yaml`
- [ ] Document provider credentials
- [ ] Test recovery procedure

## Post-Deployment

### Verification
- [ ] Health endpoint responds: `GET /health`
- [ ] Models endpoint works: `GET /v1/models`
- [ ] Chat completions work: `POST /v1/chat/completions`
- [ ] Logs are being generated
- [ ] Token usage is tracked
- [ ] Context reduction triggers correctly

### Performance Testing
- [ ] Test with single user
- [ ] Test with multiple concurrent users
- [ ] Test long conversations (20+ turns)
- [ ] Verify context reduction works
- [ ] Check memory usage
- [ ] Monitor response times

### Integration Testing
- [ ] Test with OpenWebUI
- [ ] Test with other clients (if applicable)
- [ ] Verify all configured models work
- [ ] Test error handling (invalid model, network errors)
- [ ] Test session management

## Monitoring and Maintenance

### Daily
- [ ] Check error logs
- [ ] Monitor token usage
- [ ] Verify service health

### Weekly
- [ ] Review context reduction effectiveness
- [ ] Analyze token cost savings
- [ ] Check for any performance issues
- [ ] Review and rotate logs if needed

### Monthly
- [ ] Review and update configuration
- [ ] Update dependencies if needed
- [ ] Review security settings
- [ ] Optimize context strategies based on usage

## Troubleshooting

### Common Issues

**Service won't start**
- [ ] Check configuration file syntax
- [ ] Verify environment variables are set
- [ ] Check port 8000 is available
- [ ] Review startup logs

**Models not appearing**
- [ ] Verify provider configuration
- [ ] Check API keys are valid
- [ ] Review model_mappings section
- [ ] Check logs for errors

**Context not reducing**
- [ ] Verify context_config settings
- [ ] Check max_turns and max_tokens values
- [ ] Review logs for context_reduction events
- [ ] Test with longer conversations

**Provider errors**
- [ ] Verify API keys are correct
- [ ] Check provider URLs
- [ ] Verify network connectivity
- [ ] Check provider API status
- [ ] Review timeout settings

**Redis connection failed**
- [ ] Verify Redis is running
- [ ] Check REDIS_URL in configuration
- [ ] Test Redis connection: `redis-cli ping`
- [ ] Consider using memory storage for testing

## Rollback Plan

If issues occur:

1. **Stop the service**
   ```bash
   # Docker
   docker-compose down
   
   # Local
   # Press Ctrl+C or kill process
   ```

2. **Review logs**
   ```bash
   # Docker
   docker-compose logs middleware
   
   # Local
   # Check console output
   ```

3. **Restore previous configuration**
   - Restore `.env` from backup
   - Restore `config/config.yaml` from backup

4. **Restart with previous version**
   ```bash
   docker-compose up -d
   ```

## Success Criteria

Deployment is successful when:

- [x] Service starts without errors
- [x] Health endpoint returns 200 OK
- [x] Models endpoint lists configured models
- [x] Chat completions work correctly
- [x] Logs are generated in JSON format
- [x] Context reduction triggers as expected
- [x] Token usage is tracked
- [x] OpenWebUI integration works
- [x] No errors in logs
- [x] Performance is acceptable

## Support

If you encounter issues:

1. Check logs for error messages
2. Review configuration files
3. Run manual test: `python test_manual.py`
4. Check documentation:
   - README.md
   - QUICKSTART.md
   - docs/API.md
5. Verify all prerequisites are met

---

**Deployment Date**: _________________

**Deployed By**: _________________

**Environment**: [ ] Development [ ] Staging [ ] Production

**Notes**:
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

---

✅ **Deployment Complete!**

Your API Middleware Context Control system is now running and ready to reduce token costs while managing conversation context intelligently.
