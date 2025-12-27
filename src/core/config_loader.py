"""Configuration loader with YAML parsing and environment variable substitution"""

import os
import re
import yaml
from typing import Any, Dict
from pathlib import Path
from dotenv import load_dotenv

from ..models.config import (
    AppConfig,
    SystemConfig,
    StorageConfig,
    ContextDefaultConfig,
    Provider,
    ModelMapping,
)
from ..models.session import ContextConfig


class ConfigLoader:
    """Load and parse configuration from YAML files with environment variable support"""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize configuration loader
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = Path(config_path)
        # Load environment variables from .env file if it exists
        load_dotenv()

    def _substitute_env_vars(self, value: Any) -> Any:
        """
        Recursively substitute environment variables in configuration values
        
        Supports ${VAR_NAME} syntax for environment variable substitution
        
        Args:
            value: Configuration value (can be string, dict, list, etc.)
            
        Returns:
            Value with environment variables substituted
        """
        if isinstance(value, str):
            # Pattern to match ${VAR_NAME}
            pattern = r'\$\{([^}]+)\}'
            
            def replace_env_var(match):
                var_name = match.group(1)
                env_value = os.getenv(var_name)
                if env_value is None:
                    raise ValueError(f"Environment variable '{var_name}' is not set")
                return env_value
            
            return re.sub(pattern, replace_env_var, value)
        
        elif isinstance(value, dict):
            return {k: self._substitute_env_vars(v) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [self._substitute_env_vars(item) for item in value]
        
        else:
            return value

    def load_yaml(self) -> Dict[str, Any]:
        """
        Load YAML configuration file
        
        Returns:
            Raw configuration dictionary
            
        Raises:
            FileNotFoundError: If configuration file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            try:
                config_data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Failed to parse YAML configuration: {e}")
        
        if not config_data:
            raise ValueError("Configuration file is empty")
        
        return config_data

    def _parse_system_config(self, data: Dict[str, Any]) -> SystemConfig:
        """Parse system configuration section"""
        system_data = data.get('system', {})
        
        # Override with environment variables if present
        if os.getenv('MIDDLEWARE_PORT'):
            system_data['port'] = int(os.getenv('MIDDLEWARE_PORT'))
        if os.getenv('MIDDLEWARE_LOG_LEVEL'):
            system_data['log_level'] = os.getenv('MIDDLEWARE_LOG_LEVEL')
        
        return SystemConfig(**system_data)

    def _parse_storage_config(self, data: Dict[str, Any]) -> StorageConfig:
        """Parse storage configuration section"""
        storage_data = data.get('storage', {})
        
        # Override with environment variables if present
        if os.getenv('REDIS_URL'):
            storage_data['redis_url'] = os.getenv('REDIS_URL')
        
        return StorageConfig(**storage_data)

    def _parse_context_config(self, data: Dict[str, Any]) -> ContextDefaultConfig:
        """Parse context configuration section"""
        context_data = data.get('context', {})
        return ContextDefaultConfig(**context_data)

    def _parse_providers(self, data: Dict[str, Any]) -> list[Provider]:
        """Parse providers configuration section"""
        providers_data = data.get('providers', [])
        
        if not providers_data:
            raise ValueError("No providers configured")
        
        providers = []
        for provider_data in providers_data:
            # Substitute environment variables in provider data
            provider_data = self._substitute_env_vars(provider_data)
            providers.append(Provider(**provider_data))
        
        return providers

    def _parse_model_mappings(self, data: Dict[str, Any]) -> list[ModelMapping]:
        """Parse model mappings configuration section"""
        mappings_data = data.get('model_mappings', [])
        
        if not mappings_data:
            raise ValueError("No model mappings configured")
        
        mappings = []
        for mapping_data in mappings_data:
            # Parse context_config if present
            if 'context_config' in mapping_data and mapping_data['context_config']:
                mapping_data['context_config'] = ContextConfig(**mapping_data['context_config'])
            
            mappings.append(ModelMapping(**mapping_data))
        
        return mappings

    def load(self) -> AppConfig:
        """
        Load and parse complete application configuration
        
        Returns:
            Validated AppConfig object
            
        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ValueError: If configuration is invalid
        """
        # Load raw YAML data
        raw_config = self.load_yaml()
        
        # Parse each configuration section
        system_config = self._parse_system_config(raw_config)
        storage_config = self._parse_storage_config(raw_config)
        context_config = self._parse_context_config(raw_config)
        providers = self._parse_providers(raw_config)
        model_mappings = self._parse_model_mappings(raw_config)
        
        # Create and return complete configuration
        return AppConfig(
            system=system_config,
            storage=storage_config,
            context=context_config,
            providers=providers,
            model_mappings=model_mappings
        )


def load_config(config_path: str = None) -> AppConfig:
    """
    Convenience function to load configuration
    
    Args:
        config_path: Path to configuration file (defaults to MIDDLEWARE_CONFIG_PATH env var or config/config.yaml)
        
    Returns:
        Loaded and validated AppConfig
    """
    if config_path is None:
        config_path = os.getenv('MIDDLEWARE_CONFIG_PATH', 'config/config.yaml')
    
    loader = ConfigLoader(config_path)
    return loader.load()
