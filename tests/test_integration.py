"""Integration tests for the API middleware"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import os

# Set test environment variables before importing app
os.environ["MIDDLEWARE_CONFIG_PATH"] = "config/config.yaml"
os.environ["OPENAI_API_KEY"] = "test-key"

from src.api.app import app
from src.api import endpoints  # Import to register endpoints


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def mock_provider_response():
    """Mock provider API response"""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you today?"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 9,
            "total_tokens": 19
        }
    }


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self, client):
        """Test health endpoint returns 200"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data


class TestModelsEndpoint:
    """Test models listing endpoint"""
    
    def test_list_models(self, client):
        """Test models endpoint returns available models"""
        response = client.get("/v1/models")
        assert response.status_code == 200
        
        data = response.json()
        assert "object" in data
        assert data["object"] == "list"
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0
        
        # Check model structure
        model = data["data"][0]
        assert "id" in model
        assert "object" in model
        assert model["object"] == "model"


class TestChatCompletionsEndpoint:
    """Test chat completions endpoint"""
    
    def test_basic_chat_completion(self, client, mock_provider_response):
        """Test basic chat completion request"""
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock the provider API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_provider_response
            mock_post.return_value = mock_response
            
            request_data = {
                "model": "official/gpt-4",
                "messages": [
                    {"role": "user", "content": "Hello!"}
                ]
            }
            
            response = client.post("/v1/chat/completions", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            assert "id" in data
            assert "object" in data
            assert data["object"] == "chat.completion"
            assert "choices" in data
            assert len(data["choices"]) > 0
            assert "usage" in data
    
    def test_invalid_model(self, client):
        """Test chat completion with invalid model"""
        request_data = {
            "model": "invalid/model",
            "messages": [
                {"role": "user", "content": "Hello!"}
            ]
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        assert response.status_code in [400, 404, 500]
        
        data = response.json()
        # Error response can be in different formats
        assert "error" in data or "detail" in data
    
    def test_missing_messages(self, client):
        """Test chat completion without messages"""
        request_data = {
            "model": "official/gpt-4"
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_empty_messages(self, client):
        """Test chat completion with empty messages"""
        request_data = {
            "model": "official/gpt-4",
            "messages": []
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        assert response.status_code == 422  # Validation error


class TestContextManagement:
    """Test context management functionality"""
    
    def test_multi_turn_conversation(self, client, mock_provider_response):
        """Test multiple turns in a conversation"""
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock the provider API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_provider_response
            mock_post.return_value = mock_response
            
            # First turn
            request_data = {
                "model": "official/gpt-4",
                "messages": [
                    {"role": "user", "content": "What is 2+2?"}
                ]
            }
            
            response1 = client.post("/v1/chat/completions", json=request_data)
            assert response1.status_code == 200
            
            # Second turn - add assistant response and new user message
            request_data["messages"].append({
                "role": "assistant",
                "content": "2+2 equals 4."
            })
            request_data["messages"].append({
                "role": "user",
                "content": "What about 3+3?"
            })
            
            response2 = client.post("/v1/chat/completions", json=request_data)
            assert response2.status_code == 200


class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_json(self, client):
        """Test handling of invalid JSON"""
        response = client.post(
            "/v1/chat/completions",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_missing_model(self, client):
        """Test handling of missing model parameter"""
        request_data = {
            "messages": [
                {"role": "user", "content": "Hello!"}
            ]
        }
        
        response = client.post("/v1/chat/completions", json=request_data)
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
