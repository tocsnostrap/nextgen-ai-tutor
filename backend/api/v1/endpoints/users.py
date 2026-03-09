"""
User management endpoints for NextGen AI Tutor
"""

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db, User, LearningSession, LearningProgress, Assessment
from ..auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token_data["user_id"]


@router.get("/")
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        query = select(User)
        if role:
            query = query.where(User.role == role)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        users = result.scalars().all()
        return [
            {
                "id": str(u.id),
                "email": u.email,
                "username": u.username,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
            }
            for u in users
        ]
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        raise HTTPException(status_code=500, detail="Failed to get users")


@router.get("/{user_id}")
async def get_user(user_id: str = Path(...), db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "preferences": user.preferences,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user")


@router.get("/{user_id}/progress")
async def get_user_progress(
    user_id: str = Path(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(LearningProgress).where(LearningProgress.user_id == user_id)
        )
        progress = result.scalars().all()
        return [
            {
                "skill_id": p.skill_id,
                "skill_name": p.skill_name,
                "mastery_probability": p.mastery_probability,
                "attempts": p.attempts,
                "successes": p.successes,
            }
            for p in progress
        ]
    except Exception as e:
        logger.error(f"Failed to get user progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to get progress")


__all__ = ["router"]
