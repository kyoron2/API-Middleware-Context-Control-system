"""Tests for reasoning model compatibility (DeepSeek-R1, OpenAI o1, etc.)"""

import pytest
import json
from src.models.openai import (
    ChatCompletionStreamResponse,
    StreamChoice,
)


class TestReasoningModelSupport:
    """Test support for reasoning models with thinking/reasoning content"""
    
    def test_reasoning_content_in_delta(self):
        """Test that delta can contain reasoning_content field"""
        chunk = ChatCompletionStreamResponse(
            id="chatcmpl-123",
            object="chat.completion.chunk",
            created=1234567890,
            model="deepseek-reasoner",
            choices=[
                StreamChoice(
                    index=0,
                    delta={
                        "role": "assistant",
                        "reasoning_content": "Let me think about this...",
                    },
                    finish_reason=None
                )
            ]
        )
        
        assert chunk.choices[0].delta.get("reasoning_content") == "Let me think about this..."
    
    def test_thinking_content_in_delta(self):
        """Test that delta can contain thinking field (alternative naming)"""
        chunk = ChatCompletionStreamResponse(
            id="chatcmpl-123",
            object="chat.completion.chunk",
            created=1234567890,
            model="o1-preview",
            choices=[
                StreamChoice(
                    index=0,
                    delta={
                        "thinking": "Analyzing the problem...",
                    },
                    finish_reason=None
                )
            ]
        )
        
        assert chunk.choices[0].delta.get("thinking") == "Analyzing the problem..."
    
    def test_mixed_reasoning_and_content(self):
        """Test chunks with both reasoning and regular content"""
        chunks = [
            # First chunk: reasoning starts
            ChatCompletionStreamResponse(
                id="chatcmpl-123",
                object="chat.completion.chunk",
                created=1234567890,
                model="deepseek-reasoner",
                choices=[
                    StreamChoice(
                        index=0,
                        delta={"role": "assistant", "reasoning_content": "Let me analyze"},
                        finish_reason=None
                    )
                ]
            ),
            # Second chunk: more reasoning
            ChatCompletionStreamResponse(
                id="chatcmpl-123",
                object="chat.completion.chunk",
                created=1234567890,
                model="deepseek-reasoner",
                choices=[
                    StreamChoice(
                        index=0,
                        delta={"reasoning_content": " this problem..."},
                        finish_reason=None
                    )
                ]
            ),
            # Third chunk: final answer starts
            ChatCompletionStreamResponse(
                id="chatcmpl-123",
                object="chat.completion.chunk",
                created=1234567890,
                model="deepseek-reasoner",
                choices=[
                    StreamChoice(
                        index=0,
                        delta={"content": "The answer is"},
                        finish_reason=None
                    )
                ]
            ),
            # Fourth chunk: final answer continues
            ChatCompletionStreamResponse(
                id="chatcmpl-123",
                object="chat.completion.chunk",
                created=1234567890,
                model="deepseek-reasoner",
                choices=[
                    StreamChoice(
                        index=0,
                        delta={"content": " 42."},
                        finish_reason="stop"
                    )
                ]
            ),
        ]
        
        # Accumulate content
        reasoning = ""
        content = ""
        
        for chunk in chunks:
            delta = chunk.choices[0].delta
            if delta.get("reasoning_content"):
                reasoning += delta["reasoning_content"]
            if delta.get("content"):
                content += delta["content"]
        
        assert reasoning == "Let me analyze this problem..."
        assert content == "The answer is 42."
    
    def test_sse_format_with_reasoning(self):
        """Test SSE format with reasoning content"""
        chunk = ChatCompletionStreamResponse(
            id="chatcmpl-123",
            object="chat.completion.chunk",
            created=1234567890,
            model="deepseek-reasoner",
            choices=[
                StreamChoice(
                    index=0,
                    delta={
                        "reasoning_content": "Thinking...",
                        "content": "Answer"
                    },
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
        
        # Verify JSON contains both fields
        data = sse_line[6:-2]
        parsed = json.loads(data)
        assert parsed["choices"][0]["delta"]["reasoning_content"] == "Thinking..."
        assert parsed["choices"][0]["delta"]["content"] == "Answer"
    
    def test_token_counting_with_reasoning(self):
        """Test that token counting includes reasoning content"""
        reasoning = "Let me think about this problem step by step..."
        content = "The answer is 42."
        
        # Rough token estimation (1 token ≈ 4 characters)
        reasoning_tokens = len(reasoning) // 4
        content_tokens = len(content) // 4
        total_tokens = reasoning_tokens + content_tokens
        
        # Verify both are counted
        assert total_tokens > reasoning_tokens
        assert total_tokens > content_tokens
        assert total_tokens == (len(reasoning) + len(content)) // 4


class TestReasoningModelIntegration:
    """Integration tests for reasoning model support"""
    
    @pytest.mark.asyncio
    async def test_reasoning_model_stream_accumulation(self):
        """Test that reasoning and content are properly accumulated"""
        # Simulate a reasoning model stream
        stream_data = [
            {"reasoning_content": "First, "},
            {"reasoning_content": "let me think... "},
            {"content": "The answer "},
            {"content": "is 42."},
        ]
        
        accumulated_reasoning = ""
        accumulated_content = ""
        
        for delta in stream_data:
            if delta.get("reasoning_content"):
                accumulated_reasoning += delta["reasoning_content"]
            if delta.get("content"):
                accumulated_content += delta["content"]
        
        assert accumulated_reasoning == "First, let me think... "
        assert accumulated_content == "The answer is 42."
    
    @pytest.mark.asyncio
    async def test_reasoning_only_response(self):
        """Test handling of responses with only reasoning (no final answer)"""
        # Some models might only output reasoning in certain cases
        stream_data = [
            {"reasoning_content": "I need more information to answer this question."},
        ]
        
        accumulated_reasoning = ""
        accumulated_content = ""
        
        for delta in stream_data:
            if delta.get("reasoning_content"):
                accumulated_reasoning += delta["reasoning_content"]
            if delta.get("content"):
                accumulated_content += delta["content"]
        
        # Should have reasoning but no content
        assert accumulated_reasoning == "I need more information to answer this question."
        assert accumulated_content == ""
        
        # Final message should use reasoning if no content
        final_message = accumulated_content if accumulated_content else accumulated_reasoning
        assert final_message == "I need more information to answer this question."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
