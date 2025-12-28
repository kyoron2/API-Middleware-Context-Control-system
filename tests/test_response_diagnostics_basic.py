"""Basic tests for response diagnostics module"""

import pytest
from src.utils.response_diagnostics import ResponseDiagnostics, ResponseType


class TestResponseClassification:
    """Test response classification"""
    
    def test_classify_text_only_response(self):
        """Test classification of text-only response"""
        response_data = {
            "id": "test-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "test-model",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello, world!"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        
        result = ResponseDiagnostics.classify_response(response_data)
        assert result == ResponseType.TEXT_ONLY
    
    def test_classify_tool_calls_only_response(self):
        """Test classification of tool-calls-only response"""
        response_data = {
            "id": "test-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "test-model",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "search",
                            "arguments": "{\"query\": \"test\"}"
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        
        result = ResponseDiagnostics.classify_response(response_data)
        assert result == ResponseType.TOOL_CALLS_ONLY
    
    def test_classify_mixed_response(self):
        """Test classification of mixed response"""
        response_data = {
            "id": "test-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "test-model",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Let me search for that.",
                    "tool_calls": [{
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "search",
                            "arguments": "{\"query\": \"test\"}"
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        
        result = ResponseDiagnostics.classify_response(response_data)
        assert result == ResponseType.MIXED
    
    def test_classify_empty_response(self):
        """Test classification of empty response"""
        response_data = {
            "id": "test-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "test-model",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": []
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 0,
                "total_tokens": 10
            }
        }
        
        result = ResponseDiagnostics.classify_response(response_data)
        assert result == ResponseType.EMPTY


class TestResponseValidation:
    """Test response validation"""
    
    def test_validate_complete_response(self):
        """Test validation of complete response"""
        response_data = {
            "id": "test-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "test-model",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello!"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        
        is_valid, missing_fields = ResponseDiagnostics.validate_response_structure(
            response_data
        )
        assert is_valid is True
        assert len(missing_fields) == 0
    
    def test_validate_missing_choices(self):
        """Test validation of response missing choices"""
        response_data = {
            "id": "test-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "test-model",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        
        is_valid, missing_fields = ResponseDiagnostics.validate_response_structure(
            response_data
        )
        assert is_valid is False
        assert "choices" in missing_fields


class TestContentExtraction:
    """Test content extraction"""
    
    def test_extract_from_valid_response(self):
        """Test extraction from valid response"""
        response_data = {
            "id": "test-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "test-model",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello!"
                },
                "finish_reason": "stop"
            }]
        }
        
        extracted = ResponseDiagnostics.extract_response_content(response_data)
        assert extracted["has_choices"] is True
        assert extracted["choices_count"] == 1
        assert extracted["role"] == "assistant"
        assert extracted["content"] == "Hello!"
        assert extracted["finish_reason"] == "stop"


class TestTruncation:
    """Test content truncation"""
    
    def test_truncate_short_content(self):
        """Test truncation of short content"""
        content = "Short message"
        result = ResponseDiagnostics.truncate_for_logging(content, max_length=100)
        assert result == content
        assert "[TRUNCATED]" not in result
    
    def test_truncate_long_content(self):
        """Test truncation of long content"""
        content = "A" * 3000
        result = ResponseDiagnostics.truncate_for_logging(content, max_length=2000)
        assert len(result) == 2000 + len(" [TRUNCATED]")
        assert result.endswith(" [TRUNCATED]")
        assert result.startswith("A" * 2000)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
