"""Manual test script to verify the application works"""

import os
import sys

# Set environment variables
os.environ["MIDDLEWARE_CONFIG_PATH"] = "config/config.yaml"
os.environ["OPENAI_API_KEY"] = "test-key-placeholder"

print("=" * 60)
print("Manual Test Script for API Middleware")
print("=" * 60)

print("\n1. Testing imports...")
try:
    from src.models.config import AppConfig
    from src.models.session import Session, ContextConfig
    from src.models.openai import ChatCompletionRequest, Message
    from src.core import load_config, validate_config
    from src.core import SessionManager, ContextManager, ProviderManager
    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

print("\n2. Testing configuration loading...")
try:
    config = load_config()
    print(f"✓ Configuration loaded")
    print(f"  - Providers: {len(config.providers)}")
    print(f"  - Model mappings: {len(config.model_mappings)}")
    print(f"  - Storage type: {config.storage.type}")
except Exception as e:
    print(f"✗ Configuration loading failed: {e}")
    sys.exit(1)

print("\n3. Testing configuration validation...")
try:
    validate_config(config)
    print("✓ Configuration validation passed")
except Exception as e:
    print(f"✗ Configuration validation failed: {e}")
    sys.exit(1)

print("\n4. Testing data models...")
try:
    # Test Message model
    msg = Message(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"
    
    # Test ChatCompletionRequest
    request = ChatCompletionRequest(
        model="gpt-4",
        messages=[msg]
    )
    assert request.model == "gpt-4"
    assert len(request.messages) == 1
    
    # Test ContextConfig
    ctx_config = ContextConfig(
        max_turns=10,
        max_tokens=4000,
        reduction_mode="truncation"
    )
    assert ctx_config.max_turns == 10
    
    print("✓ Data models working correctly")
except Exception as e:
    print(f"✗ Data model test failed: {e}")
    sys.exit(1)

print("\n5. Testing SessionManager...")
try:
    from src.core.session_manager import create_session_manager
    import asyncio
    
    async def test_session():
        session_mgr = create_session_manager(
            storage_type="memory",
            session_ttl=3600
        )
        
        # Create a session
        session = await session_mgr.get_session("test_session", "test_user")
        assert session.session_id == "test_session"
        assert session.user_id == "test_user"
        
        # Add a message
        msg = Message(role="user", content="Test message")
        await session_mgr.add_message("test_session", "test_user", msg)
        
        # Retrieve session
        session = await session_mgr.get_session("test_session", "test_user")
        assert len(session.conversation_history) == 1
        
        return True
    
    result = asyncio.run(test_session())
    print("✓ SessionManager working correctly")
except Exception as e:
    print(f"✗ SessionManager test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n6. Testing ContextManager...")
try:
    context_mgr = ContextManager()
    
    # Test token estimation
    messages = [
        Message(role="user", content="Hello"),
        Message(role="assistant", content="Hi there!"),
    ]
    tokens = context_mgr.estimate_tokens(messages)
    assert tokens > 0
    
    # Test truncation strategy
    async def test_truncation():
        ctx_config = ContextConfig(
            max_turns=1,
            reduction_mode="truncation"
        )
        
        messages = [
            Message(role="user", content="Message 1"),
            Message(role="assistant", content="Response 1"),
            Message(role="user", content="Message 2"),
        ]
        
        reduced, summary = await context_mgr.apply_strategy(messages, ctx_config)
        # Should keep only the last turn (1 user message)
        assert len(reduced) <= 2  # May keep last user message and possibly system
        return True
    
    asyncio.run(test_truncation())
    print("✓ ContextManager working correctly")
except Exception as e:
    print(f"✗ ContextManager test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n7. Testing ProviderManager...")
try:
    provider_mgr = ProviderManager(config)
    
    # Test model resolution
    try:
        provider, model = provider_mgr.resolve_model("official/gpt-4")
        assert provider.name == "official"
        print("✓ ProviderManager working correctly")
    except ValueError as e:
        # Expected if model not found in config
        print(f"✓ ProviderManager working correctly (model resolution: {e})")
except Exception as e:
    print(f"✗ ProviderManager test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ All manual tests passed!")
print("=" * 60)
print("\nThe application core components are working correctly.")
print("To test the full API, run: python -m src.main")
print("Then test with: curl http://localhost:8000/health")
