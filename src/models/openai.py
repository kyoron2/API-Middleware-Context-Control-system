"""OpenAI API compatible data models"""

from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Chat message model"""
    role: Literal["system", "user", "assistant", "function"]
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None


class ChatCompletionRequest(BaseModel):
    """Request model for chat completions endpoint"""
    model: str
    messages: List[Message]
    temperature: Optional[float] = Field(default=1.0, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    n: Optional[int] = Field(default=1, ge=1)
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = Field(default=None, ge=1)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None


class Usage(BaseModel):
    """Token usage information"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class Choice(BaseModel):
    """Single completion choice"""
    index: int
    message: Message
    finish_reason: Optional[str] = None
    logprobs: Optional[Dict[str, Any]] = None


class ChatCompletionResponse(BaseModel):
    """Response model for chat completions endpoint"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage
    system_fingerprint: Optional[str] = None


class StreamChoice(BaseModel):
    """Single streaming choice"""
    index: int
    delta: Dict[str, Any]
    finish_reason: Optional[str] = None


class ChatCompletionStreamResponse(BaseModel):
    """Streaming response chunk"""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[StreamChoice]


class ModelInfo(BaseModel):
    """Model information"""
    id: str
    object: str = "model"
    created: int
    owned_by: str


class ModelListResponse(BaseModel):
    """Response for models list endpoint"""
    object: str = "list"
    data: List[ModelInfo]


class ErrorDetail(BaseModel):
    """Error detail information"""
    message: str
    type: str
    param: Optional[str] = None
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response model"""
    error: ErrorDetail
