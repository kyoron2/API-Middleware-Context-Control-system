"""Provider management and API routing"""

import httpx
import time
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from ..models.config import AppConfig, Provider, ModelMapping
from ..models.openai import (
    Message,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    Usage,
    ModelInfo,
    ErrorResponse,
    ErrorDetail,
)


class ProviderManager:
    """Manage API providers and route requests"""

    def __init__(self, config: AppConfig):
        """
        Initialize provider manager
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.providers: Dict[str, Provider] = {
            p.name: p for p in config.providers
        }
        self.model_mappings: Dict[str, ModelMapping] = {
            m.display_name: m for m in config.model_mappings
        }
        self.http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True
            )
        return self.http_client

    async def close(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    def resolve_model(self, model_name: str) -> Tuple[Provider, str]:
        """
        Resolve model name to provider and actual model name
        
        Args:
            model_name: Display model name (may include namespace)
            
        Returns:
            Tuple of (Provider, actual_model_name)
            
        Raises:
            ValueError: If model or provider not found
        """
        # Check if model is in mappings
        mapping = self.model_mappings.get(model_name)
        
        if mapping is None:
            # Try to parse namespace format: provider/model
            if '/' in model_name:
                provider_name, actual_model = model_name.split('/', 1)
                provider = self.providers.get(provider_name)
                
                if provider is None:
                    raise ValueError(f"Provider '{provider_name}' not found")
                
                return provider, actual_model
            else:
                raise ValueError(f"Model '{model_name}' not found in configuration")
        
        # Get provider from mapping
        provider = self.providers.get(mapping.provider_name)
        if provider is None:
            raise ValueError(
                f"Provider '{mapping.provider_name}' not found for model '{model_name}'"
            )
        
        return provider, mapping.actual_model_name

    async def route_request(
        self,
        model: str,
        messages: List[Message],
        **kwargs
    ) -> ChatCompletionResponse:
        """
        Route chat completion request to appropriate provider
        
        Args:
            model: Model name
            messages: List of messages
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            ChatCompletionResponse
            
        Raises:
            ValueError: If model or provider not found
            httpx.HTTPError: If API request fails
        """
        # Resolve model to provider
        provider, actual_model_name = self.resolve_model(model)
        
        # Build request payload
        payload = {
            "model": actual_model_name,
            "messages": [msg.model_dump() for msg in messages],
            **kwargs
        }
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        # Make API request
        client = await self._get_http_client()
        url = f"{provider.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
                timeout=provider.timeout
            )
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            
            # Convert to our response model
            return ChatCompletionResponse(**response_data)
            
        except httpx.HTTPStatusError as e:
            # Handle HTTP errors
            error_detail = ErrorDetail(
                message=f"Provider API error: {e.response.status_code} - {e.response.text}",
                type="api_error",
                code=str(e.response.status_code)
            )
            raise ValueError(f"Provider '{provider.name}' returned error: {error_detail.message}")
        
        except httpx.TimeoutException:
            error_detail = ErrorDetail(
                message=f"Request to provider '{provider.name}' timed out",
                type="timeout_error"
            )
            raise ValueError(error_detail.message)
        
        except httpx.RequestError as e:
            error_detail = ErrorDetail(
                message=f"Failed to connect to provider '{provider.name}': {str(e)}",
                type="connection_error"
            )
            raise ValueError(error_detail.message)

    async def get_available_models(self) -> List[ModelInfo]:
        """
        Get list of all available models
        
        Returns:
            List of ModelInfo objects
        """
        models = []
        
        for mapping in self.config.model_mappings:
            model_info = ModelInfo(
                id=mapping.display_name,
                object="model",
                created=int(datetime.utcnow().timestamp()),
                owned_by=mapping.provider_name
            )
            models.append(model_info)
        
        return models

    def get_model_mapping(self, display_name: str) -> Optional[ModelMapping]:
        """
        Get model mapping by display name
        
        Args:
            display_name: Model display name
            
        Returns:
            ModelMapping or None if not found
        """
        return self.model_mappings.get(display_name)

    def get_provider(self, name: str) -> Optional[Provider]:
        """
        Get provider by name
        
        Args:
            name: Provider name
            
        Returns:
            Provider or None if not found
        """
        return self.providers.get(name)
