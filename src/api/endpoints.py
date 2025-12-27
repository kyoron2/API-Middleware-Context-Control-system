"""API endpoints"""

import uuid
import time
from typing import List
from fastapi import Depends, HTTPException

from .app import (
    app,
    get_config,
    get_session_manager,
    get_context_manager,
    get_provider_manager,
)
from ..models.config import AppConfig
from ..models.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelListResponse,
    Message,
    ErrorResponse,
    ErrorDetail,
)
from ..core import SessionManager, ContextManager, ProviderManager


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    config: AppConfig = Depends(get_config),
    session_mgr: SessionManager = Depends(get_session_manager),
    context_mgr: ContextManager = Depends(get_context_manager),
    provider_mgr: ProviderManager = Depends(get_provider_manager),
):
    """
    Create chat completion
    
    OpenAI-compatible endpoint for chat completions
    """
    try:
        # Extract session information from request
        # Use user field as user_id, generate session_id if not provided
        user_id = request.user or "default"
        
        # Generate or extract session_id
        # For now, we'll use a simple approach: hash of user_id
        # In production, this should come from the client or be managed differently
        session_id = f"session_{hash(user_id) % 10000}"
        
        # Get or create session
        session = await session_mgr.get_session(session_id, user_id)
        
        # Add new messages to session history
        for msg in request.messages:
            if msg not in session.conversation_history:
                session.conversation_history.append(msg)
        
        # Get model mapping
        model_mapping = provider_mgr.get_model_mapping(request.model)
        
        # Determine context config
        if model_mapping and model_mapping.context_config:
            context_config = model_mapping.context_config
        else:
            # Use default context config
            from ..models.session import ContextConfig
            context_config = ContextConfig(
                max_turns=config.context.default_max_turns,
                max_tokens=config.context.default_max_tokens,
                reduction_mode=config.context.default_reduction_mode,
            )
        
        # Apply context management
        reduced_messages, summary = await context_mgr.apply_strategy(
            session.conversation_history,
            context_config
        )
        
        # Store summary in memory zone if generated
        if summary and context_config.memory_zone_enabled:
            session.memory_zone.append(summary)
        
        # Update session with reduced messages
        session.conversation_history = reduced_messages
        await session_mgr.update_session(session)
        
        # Route request to provider
        response = await provider_mgr.route_request(
            model=request.model,
            messages=reduced_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            n=request.n,
            stop=request.stop,
            presence_penalty=request.presence_penalty,
            frequency_penalty=request.frequency_penalty,
            logit_bias=request.logit_bias,
            user=request.user,
        )
        
        # Add assistant response to session history
        if response.choices:
            assistant_message = response.choices[0].message
            session.conversation_history.append(assistant_message)
            session.total_tokens_used += response.usage.total_tokens
            await session_mgr.update_session(session)
        
        return response
        
    except ValueError as e:
        # Handle known errors (model not found, provider errors, etc.)
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": str(e),
                    "type": "invalid_request_error",
                    "code": "400"
                }
            }
        )
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Internal server error: {str(e)}",
                    "type": "internal_error",
                    "code": "500"
                }
            }
        )


@app.get("/v1/models", response_model=ModelListResponse)
async def list_models(
    provider_mgr: ProviderManager = Depends(get_provider_manager),
):
    """
    List available models
    
    OpenAI-compatible endpoint for listing models
    """
    try:
        models = await provider_mgr.get_available_models()
        return ModelListResponse(
            object="list",
            data=models
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Failed to list models: {str(e)}",
                    "type": "internal_error",
                    "code": "500"
                }
            }
        )
