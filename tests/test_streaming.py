"""Tests for streaming functionality"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from src.models.openai import (
    ChatCompletionRequest,
    ChatCompletionStreamResponse,
    StreamChoice,
    Message,
)


class TestStreamingResponse:
    """Test streaming response functionality"""
    
    @pytest.mark.asyncio
    async def test_stream_response_format(self):
        """Test that streaming responses are in correct SSE format"""
        # Create a mock streaming chunk
        chunk = ChatCompletionStreamResponse(
            id="chatcmpl-123",
            object="chat.completion.chunk",
            created=1234567890,
            model="gpt-3.5-turbo",
            choices=[
                StreamChoice(
                    index=0,
                    delta={"role": "assistant", "content": "Hello"},
                    finish_reason=None
                )
            ]
        )
        
        # Verify chunk structure
        assert chunk.object == "chat.completion.chunk"
        assert len(chunk.choices) == 1
        assert chunk.choices[0].delta.get("content") == "Hello"
    
    @pytest.mark.asyncio
    async def test_stream_content_accumulation(self):
        """Test that streaming content is properly accumulated"""
        chunks = [
            {"role": "assistant", "content": "Hello"},
            {"content": " world"},
            {"content": "!"},
        ]
        
        accumulated = ""
        for chunk_delta in chunks:
            if "content" in chunk_delta:
                accumulated += chunk_delta["content"]
        
        assert accumulated == "Hello world!"
    
    @pytest.mark.asyncio
    async def test_sse_format(self):
        """Test SSE (Server-Sent Events) format"""
        chunk = ChatCompletionStreamResponse(
            id="chatcmpl-123",
            object="chat.completion.chunk",
            created=1234567890,
            model="gpt-3.5-turbo",
            choices=[
                StreamChoice(
                    index=0,
                    delta={"content": "test"},
                    finish_reason=None
                )
            ]
        )
        
        # Format as SSE
        chunk_json = chunk.model_dump_json()
        sse_line = f"data: {chunk_json}\n\n"
        
        # Verify SSE format
        assert sse_line.startswith("data: ")
        assert sse_line.endswith("\n\n")
        
        # Verify JSON is valid
        data = sse_line[6:-2]  # Remove "data: " and "\n\n"
        parsed = json.loads(data)
        assert parsed["object"] == "chat.completion.chunk"
    
    @pytest.mark.asyncio
    async def test_done_message_format(self):
        """Test [DONE] message format"""
        done_message = "data: [DONE]\n\n"
        
        assert done_message.startswith("data: ")
        assert "[DONE]" in done_message
        assert done_message.endswith("\n\n")


class TestStreamRequest:
    """Test stream_request method in ProviderManager"""
    
    @pytest.mark.asyncio
    async def test_stream_request_basic(self):
        """Test basic streaming request flow"""
        from src.core.provider_manager import ProviderManager
        from src.models.config import AppConfig, Provider, ModelMapping
        
        # Create mock config
        config = AppConfig(
            system={"port": 8000, "log_level": "INFO", "session_ttl": 3600, "debug_mode": False},
            storage={"type": "memory"},
            context={
                "default_max_turns": 10,
                "default_max_tokens": 4000,
                "default_reduction_mode": "truncation"
            },
            providers=[
                Provider(
                    name="test",
                    base_url="https://api.test.com/v1",
                    api_key="test-key",
                    models=["test-model"]
                )
            ],
            model_mappings=[
                ModelMapping(
                    display_name="test/test-model",
                    provider_name="test",
                    actual_model_name="test-model"
                )
            ]
        )
        
        provider_mgr = ProviderManager(config)
        
        # Mock HTTP client
        mock_response = AsyncMock()
        mock_response.aiter_lines = AsyncMock(return_value=iter([
            'data: {"id":"1","object":"chat.completion.chunk","created":123,"model":"test","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}',
            'data: {"id":"1","object":"chat.completion.chunk","created":123,"model":"test","choices":[{"index":0,"delta":{"content":" world"},"finish_reason":null}]}',
            'data: [DONE]'
        ]))
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.stream = MagicMock()
        mock_client.stream.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_client.stream.return_value.__aexit__ = AsyncMock()
        
        provider_mgr.http_client = mock_client
        
        # Test streaming
        messages = [Message(role="user", content="Hi")]
        chunks = []
        
        async for chunk in provider_mgr.stream_request(
            model="test/test-model",
            messages=messages
        ):
            chunks.append(chunk)
        
        # Verify chunks
        assert len(chunks) == 2
        assert chunks[0].choices[0].delta.get("content") == "Hello"
        assert chunks[1].choices[0].delta.get("content") == " world"


class TestStreamingIntegration:
    """Integration tests for streaming"""
    
    @pytest.mark.asyncio
    async def test_streaming_request_parameter(self):
        """Test that stream parameter is properly handled"""
        request = ChatCompletionRequest(
            model="test-model",
            messages=[Message(role="user", content="Hello")],
            stream=True
        )
        
        assert request.stream is True
        assert request.model == "test-model"
    
    @pytest.mark.asyncio
    async def test_non_streaming_request_parameter(self):
        """Test that non-streaming requests work"""
        request = ChatCompletionRequest(
            model="test-model",
            messages=[Message(role="user", content="Hello")],
            stream=False
        )
        
        assert request.stream is False
    
    @pytest.mark.asyncio
    async def test_default_stream_parameter(self):
        """Test default stream parameter is False"""
        request = ChatCompletionRequest(
            model="test-model",
            messages=[Message(role="user", content="Hello")]
        )
        
        assert request.stream is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
