"""
NextGen AI Tutor - Main FastAPI Application
Enterprise-grade backend for scalable AI tutoring platform
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .core.config import settings
from .core.database import init_db, get_db
from .core.redis import init_redis, get_redis
from .api.v1.api import api_router
from .websocket.manager import websocket_manager
from .models.session import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/backend.log")
    ]
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting NextGen AI Tutor Backend...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize Redis
    await init_redis()
    logger.info("Redis initialized")
    
    # Initialize session manager
    await SessionManager.initialize()
    logger.info("Session manager initialized")
    
    # Initialize WebSocket manager
    await websocket_manager.initialize()
    logger.info("WebSocket manager initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down NextGen AI Tutor Backend...")
    
    # Cleanup WebSocket connections
    await websocket_manager.cleanup()
    
    # Cleanup Redis connections
    redis = await get_redis()
    await redis.close()
    
    logger.info("Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="NextGen AI Tutor API",
    description="Enterprise-grade AI tutoring platform backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring
    """
    return {
        "status": "healthy",
        "service": "nextgen-ai-tutor",
        "version": "1.0.0",
        "timestamp": "2026-03-08T09:06:00Z"
    }

# Authentication dependency
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Verify JWT token and return user info
    """
    # TODO: Implement proper JWT validation
    # For now, return mock user data
    return {
        "user_id": "user_123",
        "email": "student@example.com",
        "role": "student"
    }

# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "message": "Welcome to NextGen AI Tutor API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "websocket": "/ws",
        "api": "/api/v1"
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "code": 500
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )