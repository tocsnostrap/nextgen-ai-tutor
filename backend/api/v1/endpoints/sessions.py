"""
Session management endpoints for NextGen AI Tutor
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db, LearningSession, SessionInteraction, EmotionDetection
from ....models.session import session_manager
from ..auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


class SessionCreate(BaseModel):
    topic: str = "general"
    difficulty_level: str = "beginner"

    @field_validator("difficulty_level")
    @classmethod
    def validate_difficulty(cls, v):
        valid_levels = ["beginner", "intermediate", "advanced", "expert"]
        if v not in valid_levels:
            raise ValueError(f"Difficulty level must be one of: {', '.join(valid_levels)}")
        return v


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token_data["user_id"]


@router.get("/")
async def get_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(LearningSession)
            .order_by(LearningSession.start_time.desc())
            .offset(skip).limit(limit)
        )
        sessions = result.scalars().all()
        return [
            {
                "id": str(s.id),
                "session_token": s.session_token,
                "status": s.status,
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "topic": s.topic,
                "difficulty_level": s.difficulty_level,
            }
            for s in sessions
        ]
    except Exception as e:
        logger.error(f"Failed to get sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sessions")


@router.get("/{session_token}")
async def get_session(session_token: str = Path(...), db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(LearningSession).where(LearningSession.session_token == session_token)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "id": str(session.id),
            "session_token": session.session_token,
            "status": session.status,
            "start_time": session.start_time.isoformat() if session.start_time else None,
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "topic": session.topic,
            "difficulty_level": session.difficulty_level,
            "ai_model_used": session.ai_model_used,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session")


@router.get("/{session_token}/interactions")
async def get_session_interactions(
    session_token: str = Path(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(LearningSession).where(LearningSession.session_token == session_token)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        interactions = await session_manager.get_session_interactions(
            session_id=str(session.id), limit=limit, offset=skip
        )
        return interactions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get interactions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get interactions")


__all__ = ["router"]
