"""Structured JSON logging"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
import uuid


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add request ID if available
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Add session ID if available
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        
        # Add model if available
        if hasattr(record, "model"):
            log_data["model"] = record.model
        
        # Add token usage if available
        if hasattr(record, "tokens"):
            log_data["tokens"] = record.tokens
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class MiddlewareLogger:
    """Logger for middleware events"""

    def __init__(self, name: str = "api_middleware"):
        """
        Initialize logger
        
        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
        self.request_id: Optional[str] = None

    def set_request_id(self, request_id: str):
        """Set request ID for current context"""
        self.request_id = request_id

    def generate_request_id(self) -> str:
        """Generate new request ID"""
        self.request_id = str(uuid.uuid4())
        return self.request_id

    def _log(self, level: int, message: str, **kwargs):
        """Internal log method with extra fields"""
        extra = kwargs.copy()
        if self.request_id:
            extra["request_id"] = self.request_id
        
        self.logger.log(level, message, extra={"extra": extra})

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log(logging.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(logging.DEBUG, message, **kwargs)

    def log_api_call(
        self,
        session_id: str,
        model: str,
        message_count: int,
        **kwargs
    ):
        """
        Log API call event
        
        Args:
            session_id: Session identifier
            model: Model name
            message_count: Number of messages in request
            **kwargs: Additional fields
        """
        self.info(
            "API call received",
            event_type="api_call",
            session_id=session_id,
            model=model,
            message_count=message_count,
            **kwargs
        )

    def log_completion(
        self,
        session_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        **kwargs
    ):
        """
        Log API completion event
        
        Args:
            session_id: Session identifier
            model: Model name
            prompt_tokens: Input token count
            completion_tokens: Output token count
            total_tokens: Total token count
            **kwargs: Additional fields
        """
        self.info(
            "API call completed",
            event_type="api_completion",
            session_id=session_id,
            model=model,
            tokens={
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": total_tokens
            },
            **kwargs
        )

    def log_context_reduction(
        self,
        session_id: str,
        reduction_mode: str,
        before_tokens: int,
        after_tokens: int,
        before_messages: int,
        after_messages: int,
        **kwargs
    ):
        """
        Log context reduction event
        
        Args:
            session_id: Session identifier
            reduction_mode: Reduction strategy used
            before_tokens: Token count before reduction
            after_tokens: Token count after reduction
            before_messages: Message count before reduction
            after_messages: Message count after reduction
            **kwargs: Additional fields
        """
        self.info(
            "Context reduced",
            event_type="context_reduction",
            session_id=session_id,
            reduction_mode=reduction_mode,
            tokens_before=before_tokens,
            tokens_after=after_tokens,
            messages_before=before_messages,
            messages_after=after_messages,
            tokens_saved=before_tokens - after_tokens,
            **kwargs
        )

    def log_provider_error(
        self,
        provider_name: str,
        error_type: str,
        error_message: str,
        **kwargs
    ):
        """
        Log provider error event
        
        Args:
            provider_name: Provider name
            error_type: Type of error
            error_message: Error message
            **kwargs: Additional fields
        """
        self.error(
            "Provider error",
            event_type="provider_error",
            provider=provider_name,
            error_type=error_type,
            error_message=error_message,
            **kwargs
        )


def setup_logging(log_level: str = "INFO"):
    """
    Set up logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)
    
    # Set level for third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


# Global logger instance
logger = MiddlewareLogger()
