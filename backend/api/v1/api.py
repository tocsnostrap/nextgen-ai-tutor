"""
API routes for NextGen AI Tutor
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, Query
from typing import List, Optional, Dict, Any

from .endpoints import auth, family, ai_models, curriculum, gamification, chat, learning_paths, parent, videos, games, adaptive, schedule, knowledge_library
from .auth import verify_token
from ...websocket.manager import websocket_manager

logger = logging.getLogger(__name__)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(family.router, prefix="/family", tags=["Family"])
api_router.include_router(ai_models.router, prefix="/ai-models", tags=["AI Models"])
api_router.include_router(curriculum.router, prefix="/curriculum", tags=["Curriculum"])
api_router.include_router(gamification.router, prefix="/gamification", tags=["Gamification"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(videos.router, prefix="/videos", tags=["Videos"])
api_router.include_router(parent.router, prefix="/parent", tags=["Parent Dashboard"])
api_router.include_router(learning_paths.router, prefix="/learning-paths", tags=["Learning Paths"])
api_router.include_router(games.router, prefix="/games", tags=["Games"])
api_router.include_router(adaptive.router, prefix="/adapt", tags=["Adaptive Engine"])
api_router.include_router(schedule.router, prefix="/schedule", tags=["Schedule & Curriculum"])
api_router.include_router(knowledge_library.router, prefix="/knowledge-library", tags=["Knowledge Library"])


@api_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None),
    session_token: Optional[str] = Query(None)
):
    token_data = verify_token(token) if token else None
    if not token_data or token_data["role"] != "child":
        await websocket.close(code=1008)
        return
    user_id = token_data["user_id"]

    await websocket_manager.handle_connection(
        websocket=websocket,
        user_id=user_id,
        session_id=session_token
    )


@api_router.get("/health")
async def health_check() -> Dict[str, Any]:
    connection_count = await websocket_manager.connection_manager.get_connection_count()
    return {
        "status": "healthy",
        "service": "nextgen-ai-tutor-api",
        "version": "1.0.0",
        "websocket_connections": connection_count
    }


@api_router.get("/")
async def api_root():
    return {
        "message": "NextGen AI Tutor API",
        "version": "1.0.0",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
        },
        "endpoints": {
            "authentication": "/api/v1/auth",
            "ai_models": "/api/v1/ai-models",
            "curriculum": "/api/v1/curriculum",
            "gamification": "/api/v1/gamification",
            "chat": "/api/v1/chat",
            "videos": "/api/v1/videos",
            "parent": "/api/v1/parent",
            "learning_paths": "/api/v1/learning-paths",
            "games": "/api/v1/games",
            "websocket": "/api/v1/ws",
            "health": "/api/v1/health",
        }
    }


__all__ = ["api_router"]
