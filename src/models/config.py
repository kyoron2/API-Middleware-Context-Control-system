"""Configuration data models"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from .session import ContextConfig


class Provider(BaseModel):
    """API provider configuration"""
    name: str
    base_url: str
    api_key: str
    provider_type: str = "openai"  # "openai", "azure", "custom"
    models: List[str] = Field(default_factory=list)
    timeout: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=0)

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate base URL format"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('base_url must start with http:// or https://')
        return v.rstrip('/')

    class Config:
        validate_assignment = True


class ModelMapping(BaseModel):
    """Model name mapping configuration"""
    display_name: str
    provider_name: str
    actual_model_name: str
    context_config: Optional[ContextConfig] = None

    class Config:
        validate_assignment = True


class StorageConfig(BaseModel):
    """Storage configuration"""
    type: str = "memory"  # "memory" or "redis"
    redis_url: Optional[str] = None
    redis_db: int = 0

    @field_validator('type')
    @classmethod
    def validate_storage_type(cls, v: str) -> str:
        """Validate storage type"""
        if v not in ["memory", "redis"]:
            raise ValueError('storage type must be "memory" or "redis"')
        return v

    class Config:
        validate_assignment = True


class SystemConfig(BaseModel):
    """System-level configuration"""
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"
    session_ttl: int = Field(default=3600, ge=60)  # seconds
    debug_mode: bool = Field(
        default=False,
        description="Enable detailed diagnostic logging for response analysis"
    )

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v_upper

    class Config:
        validate_assignment = True


class ContextDefaultConfig(BaseModel):
    """Default context configuration"""
    default_max_turns: int = Field(default=10, ge=1)
    default_max_tokens: int = Field(default=4000, ge=100)
    default_reduction_mode: str = "truncation"
    default_summarization_model: Optional[str] = None
    summarization_prompt: str = ""

    @field_validator('default_reduction_mode')
    @classmethod
    def validate_reduction_mode(cls, v: str) -> str:
        """Validate reduction mode"""
        valid_modes = ["truncation", "summarization", "sliding_window"]
        if v not in valid_modes:
            raise ValueError(f'reduction_mode must be one of {valid_modes}')
        return v

    class Config:
        validate_assignment = True


class AppConfig(BaseModel):
    """Complete application configuration"""
    system: SystemConfig
    storage: StorageConfig
    context: ContextDefaultConfig
    providers: List[Provider]
    model_mappings: List[ModelMapping]

    @field_validator('providers')
    @classmethod
    def validate_providers(cls, v: List[Provider]) -> List[Provider]:
        """Validate providers list is not empty"""
        if not v:
            raise ValueError('At least one provider must be configured')
        return v

    @field_validator('model_mappings')
    @classmethod
    def validate_model_mappings(cls, v: List[ModelMapping]) -> List[ModelMapping]:
        """Validate model mappings list is not empty"""
        if not v:
            raise ValueError('At least one model mapping must be configured')
        return v

    def get_provider(self, name: str) -> Optional[Provider]:
        """Get provider by name"""
        for provider in self.providers:
            if provider.name == name:
                return provider
        return None

    def get_model_mapping(self, display_name: str) -> Optional[ModelMapping]:
        """Get model mapping by display name"""
        for mapping in self.model_mappings:
            if mapping.display_name == display_name:
                return mapping
        return None

    class Config:
        validate_assignment = True
