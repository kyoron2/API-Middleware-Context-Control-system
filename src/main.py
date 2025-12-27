"""Main application entry point"""

import uvicorn
import os

from .api.app import app
from .api import endpoints  # Import to register endpoints


def main():
    """Run the application"""
    port = int(os.getenv("MIDDLEWARE_PORT", "8000"))
    host = os.getenv("MIDDLEWARE_HOST", "0.0.0.0")
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
