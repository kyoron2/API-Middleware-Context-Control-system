"""Configuration validation"""

from typing import List, Set
from ..models.config import AppConfig, Provider, ModelMapping


class ConfigValidator:
    """Validate application configuration for consistency and completeness"""

    def __init__(self, config: AppConfig):
        """
        Initialize validator with configuration
        
        Args:
            config: Application configuration to validate
        """
        self.config = config
        self.errors: List[str] = []

    def validate_provider_references(self) -> None:
        """Validate that all provider references in model mappings exist"""
        provider_names = {p.name for p in self.config.providers}
        
        for mapping in self.config.model_mappings:
            if mapping.provider_name not in provider_names:
                self.errors.append(
                    f"Model mapping '{mapping.display_name}' references "
                    f"non-existent provider '{mapping.provider_name}'"
                )

    def validate_model_references(self) -> None:
        """Validate that mapped models exist in their providers"""
        # Build provider -> models mapping
        provider_models: dict[str, Set[str]] = {}
        for provider in self.config.providers:
            provider_models[provider.name] = set(provider.models)
        
        for mapping in self.config.model_mappings:
            provider_name = mapping.provider_name
            actual_model = mapping.actual_model_name
            
            if provider_name in provider_models:
                if actual_model not in provider_models[provider_name]:
                    self.errors.append(
                        f"Model mapping '{mapping.display_name}' references "
                        f"model '{actual_model}' which is not in provider '{provider_name}'"
                    )

    def validate_unique_display_names(self) -> None:
        """Validate that all model display names are unique"""
        display_names = [m.display_name for m in self.config.model_mappings]
        duplicates = [name for name in display_names if display_names.count(name) > 1]
        
        if duplicates:
            unique_duplicates = set(duplicates)
            self.errors.append(
                f"Duplicate model display names found: {', '.join(unique_duplicates)}"
            )

    def validate_unique_provider_names(self) -> None:
        """Validate that all provider names are unique"""
        provider_names = [p.name for p in self.config.providers]
        duplicates = [name for name in provider_names if provider_names.count(name) > 1]
        
        if duplicates:
            unique_duplicates = set(duplicates)
            self.errors.append(
                f"Duplicate provider names found: {', '.join(unique_duplicates)}"
            )

    def validate_redis_config(self) -> None:
        """Validate Redis configuration if storage type is redis"""
        if self.config.storage.type == "redis":
            if not self.config.storage.redis_url:
                self.errors.append(
                    "Storage type is 'redis' but redis_url is not configured"
                )

    def validate_summarization_config(self) -> None:
        """Validate summarization configuration"""
        # Check global default config
        if self.config.context.default_reduction_mode == "summarization":
            if not self.config.context.default_summarization_model:
                self.errors.append(
                    "Global context uses summarization mode but default_summarization_model is not configured"
                )
        
        # Check if any model mapping uses summarization mode
        for mapping in self.config.model_mappings:
            if mapping.context_config and mapping.context_config.reduction_mode == "summarization":
                if not mapping.context_config.summarization_model:
                    self.errors.append(
                        f"Model mapping '{mapping.display_name}' uses summarization mode "
                        f"but summarization_model is not configured"
                    )

    def validate_all(self) -> List[str]:
        """
        Run all validation checks
        
        Returns:
            List of validation error messages (empty if valid)
        """
        self.errors = []
        
        self.validate_unique_provider_names()
        self.validate_unique_display_names()
        self.validate_provider_references()
        self.validate_model_references()
        self.validate_redis_config()
        self.validate_summarization_config()
        
        return self.errors

    def is_valid(self) -> bool:
        """
        Check if configuration is valid
        
        Returns:
            True if valid, False otherwise
        """
        errors = self.validate_all()
        return len(errors) == 0


def validate_config(config: AppConfig) -> None:
    """
    Validate configuration and raise exception if invalid
    
    Args:
        config: Configuration to validate
        
    Raises:
        ValueError: If configuration is invalid
    """
    validator = ConfigValidator(config)
    errors = validator.validate_all()
    
    if errors:
        error_message = "Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
        raise ValueError(error_message)
