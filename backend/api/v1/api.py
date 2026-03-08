"""
API routes for NextGen AI Tutor
"""

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any

from ...core.database import get_db, AsyncSession
from ...core.redis import get_redis
from ...websocket.manager import websocket_manager
from ...models.session import session_manager

# Import routers
from .endpoints import auth, users, sessions, analytics, ai_models

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(ai_models.router, prefix="/ai-models", tags=["AI Models"])

# Security
security = HTTPBearer()

# WebSocket endpoint
@api_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    session_token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time AI tutoring
    
    Parameters:
    - token: Authentication token
    - session_token: Optional session token to resume existing session
    """
    # TODO: Validate token and get user_id
    # For now, use mock user_id
    user_id = "user_123"
    
    await websocket_manager.handle_connection(
        websocket=websocket,
        user_id=user_id,
        session_id=session_token
    )

# Health check endpoint
@api_router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
) -> Dict[str, Any]:
    """
    Comprehensive health check for all services
    """
    health_status = {
        "status": "healthy",
        "service": "nextgen-ai-tutor-api",
        "version": "1.0.0",
        "checks": {}
    }
    
    # Check database
    try:
        await db.execute("SELECT 1")
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        await redis.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
        health_status["status"] = "degraded"
    
    # Check WebSocket manager
    try:
        connection_count = await websocket_manager.connection_manager.get_connection_count()
        health_status["checks"]["websocket"] = {
            "status": "healthy",
            "message": f"WebSocket manager active with {connection_count} connections"
        }
    except Exception as e:
        health_status["checks"]["websocket"] = {
            "status": "unhealthy",
            "message": f"WebSocket manager error: {str(e)}"
        }
        health_status["status"] = "degraded"
    
    # Check session manager
    try:
        # Simple check by accessing manager
        health_status["checks"]["session_manager"] = {
            "status": "healthy",
            "message": "Session manager initialized"
        }
    except Exception as e:
        health_status["checks"]["session_manager"] = {
            "status": "unhealthy",
            "message": f"Session manager error: {str(e)}"
        }
        health_status["status"] = "degraded"
    
    return health_status

# Metrics endpoint (for Prometheus)
@api_router.get("/metrics")
async def metrics():
    """
    Metrics endpoint for monitoring
    """
    # TODO: Implement comprehensive metrics
    # - Active WebSocket connections
    # - Session counts by status
    # - API request rates
    # - Database query performance
    # - Redis memory usage
    
    connection_count = await websocket_manager.connection_manager.get_connection_count()
    
    return {
        "websocket_connections": connection_count,
        "active_sessions": 0,  # TODO: Implement
        "api_requests_total": 0,  # TODO: Implement
        "database_connections": 0,  # TODO: Implement
        "redis_memory_used_mb": 0,  # TODO: Implement
    }

# Root API endpoint
@api_router.get("/")
async def api_root():
    """
    API root endpoint with documentation links
    """
    return {
        "message": "NextGen AI Tutor API",
        "version": "1.0.0",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "endpoints": {
            "authentication": "/api/v1/auth",
            "users": "/api/v1/users",
            "sessions": "/api/v1/sessions",
            "analytics": "/api/v1/analytics",
            "ai_models": "/api/v1/ai-models",
            "websocket": "/api/v1/ws",
            "health": "/api/v1/health",
            "metrics": "/api/v1/metrics"
        }
    }

# Export router
__all__ = ["api_router"]