import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import verify_token
from ....core.database import get_db, CurriculumStandard
from ....schedule_engine import (
    generate_daily_schedule,
    complete_block,
    get_time_logs,
    get_week_schedules,
    generate_progress_report,
)
from ....ai_service import generate_lesson_content
from ....unified_adaptive_engine import get_or_create_profile
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token_data["user_id"]


class CompleteBlockRequest(BaseModel):
    block_index: int
    time_spent_seconds: int = 0


@router.get("/today")
async def get_today_schedule(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        today = date.today()
        schedule = await generate_daily_schedule(db, user_id, today)
        return schedule
    except Exception as e:
        logger.error("Failed to get today's schedule for %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load today's schedule",
        )


@router.post("/complete-block")
async def complete_schedule_block(
    req: CompleteBlockRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        today = date.today()
        result = await complete_block(db, user_id, today, req.block_index, req.time_spent_seconds)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to complete block for %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not complete block",
        )


@router.get("/week")
async def get_week(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        week = await get_week_schedules(db, user_id)
        return {"days": week}
    except Exception as e:
        logger.error("Failed to get week schedules for %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load weekly schedule",
        )


@router.get("/time-log")
async def get_time_log(
    period: str = Query(default="week", pattern="^(week|month)$"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        logs = await get_time_logs(db, user_id, period)
        return logs
    except Exception as e:
        logger.error("Failed to get time logs for %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load time logs",
        )


@router.get("/progress-report")
async def get_progress_report(
    period: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        if not period:
            period = datetime.now().strftime("%Y-%m")
        report = await generate_progress_report(db, user_id, period)
        return report
    except Exception as e:
        logger.error("Failed to generate progress report for %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate progress report",
        )


@router.get("/curriculum")
async def get_curriculum_standards(
    subject: Optional[str] = None,
    grade: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _user_id: str = Depends(get_current_user_id),
):
    try:
        query = select(CurriculumStandard)
        if subject:
            query = query.where(CurriculumStandard.subject == subject)
        if grade is not None:
            query = query.where(CurriculumStandard.grade_level == grade)
        query = query.order_by(CurriculumStandard.subject, CurriculumStandard.grade_level, CurriculumStandard.sequence_order)

        result = await db.execute(query)
        standards = result.scalars().all()
        return {
            "standards": [
                {
                    "id": s.id,
                    "subject": s.subject,
                    "grade_level": s.grade_level,
                    "strand": s.strand,
                    "title": s.title,
                    "description": s.description,
                    "learning_objectives": s.learning_objectives,
                    "estimated_hours": s.estimated_hours,
                    "sequence_order": s.sequence_order,
                }
                for s in standards
            ],
            "count": len(standards),
        }
    except Exception as e:
        logger.error("Failed to get curriculum standards: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load curriculum",
        )


class LessonRequest(BaseModel):
    block_index: int


@router.post("/lesson")
async def get_lesson_content(
    req: LessonRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        today = date.today()
        schedule = await generate_daily_schedule(db, user_id, today)
        blocks = schedule.get("blocks", [])

        if req.block_index < 0 or req.block_index >= len(blocks):
            raise HTTPException(status_code=400, detail="Invalid block index")

        block = blocks[req.block_index]
        subject = block.get("subject", "general")
        title = block.get("title", "Lesson")
        description = block.get("description", "")
        activity_type = block.get("activity_type", "lesson")

        standard_id = block.get("standard_id")
        objectives = []
        if standard_id:
            result = await db.execute(
                select(CurriculumStandard).where(CurriculumStandard.id == standard_id)
            )
            standard = result.scalar_one_or_none()
            if standard:
                objectives = standard.learning_objectives or []
                if not description:
                    description = standard.description or ""

        profile = await get_or_create_profile(db, user_id)
        age = profile.age or 8

        lesson = await generate_lesson_content(
            title=title,
            description=description,
            subject=subject,
            objectives=objectives,
            age=age,
            activity_type=activity_type,
        )
        lesson["block_index"] = req.block_index
        lesson["activity_type"] = activity_type
        lesson["objectives"] = objectives
        lesson["duration_minutes"] = block.get("duration_minutes", 15)
        return lesson
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate lesson for %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate lesson content",
        )
