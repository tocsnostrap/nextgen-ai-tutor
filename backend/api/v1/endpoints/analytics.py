"""
Analytics endpoints for NextGen AI Tutor
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import (
    get_db, User, LearningSession, SessionInteraction,
    EmotionDetection, LearningProgress, Assessment, AnalyticsEvent
)
from ..auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token_data["user_id"]


def parse_date_range(period: str):
    now = datetime.now(timezone.utc)
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=7)
    return start_date, now


@router.get("/overview")
async def get_analytics_overview(
    period: str = Query("week", description="Time period"),
    db: AsyncSession = Depends(get_db)
):
    try:
        start_date, end_date = parse_date_range(period)

        users_count = await db.execute(select(func.count(User.id)))
        total_users = users_count.scalar() or 0

        sessions_count = await db.execute(
            select(func.count(LearningSession.id)).where(
                LearningSession.start_time >= start_date
            )
        )
        total_sessions = sessions_count.scalar() or 0

        active_count = await db.execute(
            select(func.count(LearningSession.id)).where(
                LearningSession.status == "active"
            )
        )
        active_sessions = active_count.scalar() or 0

        return {
            "period": period,
            "total_users": total_users,
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get analytics overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to get analytics")


@router.get("/sessions")
async def get_session_analytics(
    period: str = Query("week"),
    db: AsyncSession = Depends(get_db)
):
    try:
        start_date, end_date = parse_date_range(period)
        result = await db.execute(
            select(
                LearningSession.topic,
                func.count(LearningSession.id).label("count"),
                func.avg(LearningSession.duration_seconds).label("avg_duration")
            )
            .where(LearningSession.start_time >= start_date)
            .group_by(LearningSession.topic)
        )
        rows = result.all()
        return [
            {
                "topic": row.topic,
                "session_count": row.count,
                "avg_duration_seconds": float(row.avg_duration) if row.avg_duration else 0
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to get session analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session analytics")


__all__ = ["router"]
