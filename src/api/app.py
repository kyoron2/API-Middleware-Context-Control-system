"""FastAPI application setup"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from ..core import (
    load_config,
    validate_config,
    SessionManager,
    create_session_manager,
    ContextManager,
    ProviderManager,
)
from ..models.config import AppConfig
from ..models.openai import ErrorResponse, ErrorDetail
from ..utils import setup_logging, logger


# Global instances
app_config: AppConfig = None
session_manager: SessionManager = None
context_manager: ContextManager = None
provider_manager: ProviderManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global app_config, session_manager, context_manager, provider_manager
    
    # Startup
    print("Starting API Middleware...")
    
    # Load and validate configuration
    try:
        app_config = load_config()
        validate_config(app_config)
        
        # Set up logging
        setup_logging(app_config.system.log_level)
        logger.info("Configuration loaded successfully",
                   providers=len(app_config.providers),
                   models=len(app_config.model_mappings))
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        raise
    
    # Initialize managers
    session_manager = create_session_manager(
        storage_type=app_config.storage.type,
        redis_url=app_config.storage.redis_url,
        redis_db=app_config.storage.redis_db,
        session_ttl=app_config.system.session_ttl
    )
    
    context_manager = ContextManager()
    provider_manager = ProviderManager(app_config)
    
    # Start session cleanup task
    await session_manager.start_cleanup_task()
    
    logger.info("API Middleware started", port=app_config.system.port)
    
    yield
    
    # Shutdown
    logger.info("Shutting down API Middleware")
    
    # Stop cleanup task
    await session_manager.stop_cleanup_task()
    
    # Close provider manager HTTP client
    await provider_manager.close()
    
    logger.info("API Middleware stopped")


# Create FastAPI app
app = FastAPI(
    title="API Middleware Context Control",
    description="Intelligent API middleware for managing LLM conversation context",
    version="0.1.0",
    lifespan=lifespan
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection functions
def get_config() -> AppConfig:
    """Get application configuration"""
    return app_config


def get_session_manager() -> SessionManager:
    """Get session manager"""
    return session_manager


def get_context_manager() -> ContextManager:
    """Get context manager"""
    return context_manager


def get_provider_manager() -> ProviderManager:
    """Get provider manager"""
    return provider_manager


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    error_response = ErrorResponse(
        error=ErrorDetail(
            message=str(exc),
            type="internal_error",
            code="500"
        )
    )
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump()
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "api-middleware-context-control",
        "version": "0.1.0"
    }
