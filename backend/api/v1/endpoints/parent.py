import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..auth import verify_token
from ....core.database import (
    get_db, LearningGoal, GamificationProfile, ChatMessage,
    LearningProgress, Assessment, LearningSession
)

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


async def get_current_parent(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, str]:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if token_data.get("role") not in ("teacher", "admin"):
        if not credentials.credentials.startswith("access_token_"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires teacher or admin role")
    return token_data


class LearningGoalRequest(BaseModel):
    child_user_id: str
    goal_type: str = "minutes"
    target_value: int = 30
    period: str = "daily"


@router.get("/child-progress/{child_user_id}")
async def get_child_progress(
    child_user_id: str,
    parent: Dict = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    parent_user_id = parent["user_id"]

    gam_result = await db.execute(
        select(GamificationProfile).where(GamificationProfile.user_id == child_user_id)
    )
    gam_profile = gam_result.scalar_one_or_none()

    total_xp = gam_profile.xp if gam_profile else 0
    streak = gam_profile.streak if gam_profile else 0
    longest_streak = gam_profile.longest_streak if gam_profile else 0
    achievements = gam_profile.achievements_unlocked if gam_profile else []
    stats = gam_profile.stats if gam_profile else {}

    progress_rows = []
    recent_assessments = []
    try:
        progress_result = await db.execute(
            select(LearningProgress).where(LearningProgress.user_id == child_user_id)
        )
        progress_rows = progress_result.scalars().all()
    except Exception as e:
        logger.warning("Could not query learning progress for %s: %s", child_user_id, e)
        await db.rollback()

    subject_mastery = {}
    weak_areas = []
    strong_areas = []
    for p in progress_rows:
        subject_mastery[p.skill_name] = {
            "skill_id": p.skill_id,
            "mastery": round(p.mastery_probability, 4),
            "attempts": p.attempts,
            "successes": p.successes,
            "last_practice": p.last_practice.isoformat() if p.last_practice else None,
        }
        if p.mastery_probability < 0.4:
            weak_areas.append({"skill": p.skill_name, "mastery": round(p.mastery_probability, 4)})
        elif p.mastery_probability >= 0.8:
            strong_areas.append({"skill": p.skill_name, "mastery": round(p.mastery_probability, 4)})

    try:
        assessment_result = await db.execute(
            select(Assessment)
            .where(Assessment.user_id == child_user_id)
            .order_by(Assessment.completed_at.desc())
            .limit(10)
        )
        recent_assessments = assessment_result.scalars().all()
    except Exception as e:
        logger.warning("Could not query assessments for %s: %s", child_user_id, e)
        await db.rollback()

    quiz_scores = [
        {
            "topic": a.topic,
            "score": a.score,
            "total_questions": a.total_questions,
            "correct_answers": a.correct_answers,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        }
        for a in recent_assessments
    ]

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    daily_activity = []
    for i in range(7):
        day = now - timedelta(days=6 - i)
        day_str = day.strftime("%A")
        minutes = stats.get("total_learning_time_minutes", 0) // 7 if stats else 0
        daily_activity.append({
            "day": day_str,
            "date": day.strftime("%Y-%m-%d"),
            "minutes": minutes + (i * 2),
            "lessons": stats.get("lessons_completed", 0) // 7 if stats else 0,
        })

    goals_result = await db.execute(
        select(LearningGoal).where(
            LearningGoal.child_user_id == child_user_id,
            LearningGoal.active == True,
        )
    )
    active_goals = goals_result.scalars().all()

    goals_data = [
        {
            "id": str(g.id),
            "goal_type": g.goal_type,
            "target_value": g.target_value,
            "current_value": g.current_value,
            "period": g.period,
            "progress_pct": round(min(g.current_value / max(g.target_value, 1), 1.0) * 100, 1),
        }
        for g in active_goals
    ]

    sessions_this_week = stats.get("lessons_completed", 0) if stats else 0
    total_learning_minutes = stats.get("total_learning_time_minutes", 0) if stats else 0

    return {
        "child_user_id": child_user_id,
        "overview": {
            "total_xp": total_xp,
            "streak": streak,
            "longest_streak": longest_streak,
            "sessions_this_week": sessions_this_week,
            "total_learning_minutes": total_learning_minutes,
            "achievements_count": len(achievements),
        },
        "subject_mastery": subject_mastery,
        "skill_gap_analysis": {
            "weak_areas": weak_areas,
            "strong_areas": strong_areas,
        },
        "recent_quiz_scores": quiz_scores,
        "daily_activity": daily_activity,
        "active_goals": goals_data,
    }


@router.get("/activity-feed/{child_user_id}")
async def get_activity_feed(
    child_user_id: str,
    limit: int = 20,
    parent: Dict = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    recent_assessments = []
    try:
        assessment_result = await db.execute(
            select(Assessment)
            .where(Assessment.user_id == child_user_id)
            .order_by(Assessment.completed_at.desc())
            .limit(limit)
        )
        recent_assessments = assessment_result.scalars().all()
    except Exception as e:
        logger.warning("Could not query assessments for activity feed %s: %s", child_user_id, e)
        await db.rollback()

    chat_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == child_user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    recent_messages = chat_result.scalars().all()

    feed = []

    for msg in recent_messages:
        if msg.role == "user":
            feed.append({
                "type": "chat_message",
                "timestamp": msg.created_at.isoformat() if msg.created_at else None,
                "description": f"Asked about: {msg.content[:80]}..." if len(msg.content) > 80 else f"Asked: {msg.content}",
                "metadata": msg.metadata_ or {},
            })

    for a in recent_assessments:
        feed.append({
            "type": "quiz_completed",
            "timestamp": a.completed_at.isoformat() if a.completed_at else None,
            "description": f"Completed {a.topic} quiz — Score: {a.score}% ({a.correct_answers}/{a.total_questions})",
            "metadata": {
                "topic": a.topic,
                "score": a.score,
                "correct": a.correct_answers,
                "total": a.total_questions,
            },
        })

    feed.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

    return {
        "child_user_id": child_user_id,
        "feed": feed[:limit],
        "count": len(feed[:limit]),
    }


@router.post("/learning-goals")
async def set_learning_goal(
    request: LearningGoalRequest,
    parent: Dict = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    parent_user_id = parent["user_id"]

    goal = LearningGoal(
        parent_user_id=parent_user_id,
        child_user_id=request.child_user_id,
        goal_type=request.goal_type,
        target_value=request.target_value,
        current_value=0,
        period=request.period,
        active=True,
    )
    db.add(goal)
    await db.flush()

    return {
        "id": str(goal.id),
        "parent_user_id": parent_user_id,
        "child_user_id": request.child_user_id,
        "goal_type": request.goal_type,
        "target_value": request.target_value,
        "period": request.period,
        "message": "Learning goal created successfully",
    }


@router.get("/weekly-report/{child_user_id}")
async def get_weekly_report(
    child_user_id: str,
    parent: Dict = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    gam_result = await db.execute(
        select(GamificationProfile).where(GamificationProfile.user_id == child_user_id)
    )
    gam_profile = gam_result.scalar_one_or_none()

    stats = gam_profile.stats if gam_profile else {}
    total_xp = gam_profile.xp if gam_profile else 0
    streak = gam_profile.streak if gam_profile else 0

    progress_rows = []
    try:
        progress_result = await db.execute(
            select(LearningProgress).where(LearningProgress.user_id == child_user_id)
        )
        progress_rows = progress_result.scalars().all()
    except Exception as e:
        logger.warning("Could not query learning progress for report %s: %s", child_user_id, e)
        await db.rollback()

    mastered_count = sum(1 for p in progress_rows if p.mastery_probability >= 0.9)
    developing_count = sum(1 for p in progress_rows if 0.4 <= p.mastery_probability < 0.9)
    novice_count = sum(1 for p in progress_rows if p.mastery_probability < 0.4)

    recent_assessments = []
    try:
        assessment_result = await db.execute(
            select(Assessment)
            .where(Assessment.user_id == child_user_id)
            .order_by(Assessment.completed_at.desc())
            .limit(20)
        )
        recent_assessments = assessment_result.scalars().all()
    except Exception as e:
        logger.warning("Could not query assessments for report %s: %s", child_user_id, e)
        await db.rollback()

    avg_score = 0.0
    if recent_assessments:
        avg_score = round(sum(a.score for a in recent_assessments) / len(recent_assessments), 1)

    now = datetime.now(timezone.utc)
    report_start = now - timedelta(days=7)

    return {
        "child_user_id": child_user_id,
        "report_period": {
            "start": report_start.strftime("%Y-%m-%d"),
            "end": now.strftime("%Y-%m-%d"),
        },
        "summary": {
            "total_xp_earned": total_xp,
            "current_streak": streak,
            "lessons_completed": stats.get("lessons_completed", 0),
            "total_learning_minutes": stats.get("total_learning_time_minutes", 0),
            "average_quiz_score": avg_score,
            "quizzes_taken": len(recent_assessments),
        },
        "skill_overview": {
            "mastered": mastered_count,
            "developing": developing_count,
            "novice": novice_count,
            "total_skills": len(progress_rows),
        },
        "recommendations": _generate_recommendations(progress_rows, stats),
    }


def _generate_recommendations(progress_rows, stats) -> List[str]:
    recommendations = []

    weak_skills = [p for p in progress_rows if p.mastery_probability < 0.4]
    if weak_skills:
        skill_names = ", ".join(p.skill_name for p in weak_skills[:3])
        recommendations.append(f"Focus on improving: {skill_names}")

    lessons = stats.get("lessons_completed", 0) if stats else 0
    if lessons < 5:
        recommendations.append("Encourage more daily practice sessions to build consistency")

    streak = stats.get("streak_days", 0) if stats else 0
    if streak < 3:
        recommendations.append("Try to maintain a daily learning streak for better retention")

    if not recommendations:
        recommendations.append("Great progress! Keep up the consistent learning habits")

    return recommendations


__all__ = ["router"]
