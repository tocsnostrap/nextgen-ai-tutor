import logging
import math
import random
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from ..auth import verify_token
from ....core.database import get_db, GamificationProfile

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

ACHIEVEMENTS = [
    {"id": "first_lesson", "name": "First Steps", "description": "Complete your first lesson", "icon": "🎯", "category": "learning", "xp_reward": 50, "requirement": {"type": "lessons_completed", "count": 1}},
    {"id": "five_lessons", "name": "Getting Started", "description": "Complete 5 lessons", "icon": "📚", "category": "learning", "xp_reward": 100, "requirement": {"type": "lessons_completed", "count": 5}},
    {"id": "ten_lessons", "name": "Dedicated Learner", "description": "Complete 10 lessons", "icon": "🏆", "category": "learning", "xp_reward": 200, "requirement": {"type": "lessons_completed", "count": 10}},
    {"id": "twenty_five_lessons", "name": "Knowledge Seeker", "description": "Complete 25 lessons", "icon": "🌟", "category": "learning", "xp_reward": 500, "requirement": {"type": "lessons_completed", "count": 25}},
    {"id": "fifty_lessons", "name": "Lesson Master", "description": "Complete 50 lessons", "icon": "👑", "category": "learning", "xp_reward": 1000, "requirement": {"type": "lessons_completed", "count": 50}},
    {"id": "first_mastery", "name": "First Mastery", "description": "Master your first concept", "icon": "💎", "category": "mastery", "xp_reward": 150, "requirement": {"type": "concepts_mastered", "count": 1}},
    {"id": "five_mastery", "name": "Skill Builder", "description": "Master 5 concepts", "icon": "🔥", "category": "mastery", "xp_reward": 300, "requirement": {"type": "concepts_mastered", "count": 5}},
    {"id": "ten_mastery", "name": "Expert in Training", "description": "Master 10 concepts", "icon": "⚡", "category": "mastery", "xp_reward": 600, "requirement": {"type": "concepts_mastered", "count": 10}},
    {"id": "twenty_mastery", "name": "Knowledge Master", "description": "Master 20 concepts", "icon": "🧠", "category": "mastery", "xp_reward": 1200, "requirement": {"type": "concepts_mastered", "count": 20}},
    {"id": "streak_3", "name": "On a Roll", "description": "Maintain a 3-day streak", "icon": "🔥", "category": "streak", "xp_reward": 75, "requirement": {"type": "streak_days", "count": 3}},
    {"id": "streak_7", "name": "Week Warrior", "description": "Maintain a 7-day streak", "icon": "💪", "category": "streak", "xp_reward": 200, "requirement": {"type": "streak_days", "count": 7}},
    {"id": "streak_14", "name": "Two Week Titan", "description": "Maintain a 14-day streak", "icon": "🏅", "category": "streak", "xp_reward": 500, "requirement": {"type": "streak_days", "count": 14}},
    {"id": "streak_30", "name": "Monthly Champion", "description": "Maintain a 30-day streak", "icon": "🏆", "category": "streak", "xp_reward": 1000, "requirement": {"type": "streak_days", "count": 30}},
    {"id": "perfect_quiz", "name": "Perfect Score", "description": "Get 100% on a quiz", "icon": "💯", "category": "learning", "xp_reward": 100, "requirement": {"type": "perfect_quizzes", "count": 1}},
    {"id": "five_perfect", "name": "Accuracy King", "description": "Get 100% on 5 quizzes", "icon": "🎯", "category": "learning", "xp_reward": 300, "requirement": {"type": "perfect_quizzes", "count": 5}},
    {"id": "first_chat", "name": "Conversation Starter", "description": "Send your first chat message", "icon": "💬", "category": "social", "xp_reward": 25, "requirement": {"type": "messages_sent", "count": 1}},
    {"id": "fifty_chats", "name": "Chatty Learner", "description": "Send 50 chat messages", "icon": "🗣️", "category": "social", "xp_reward": 200, "requirement": {"type": "messages_sent", "count": 50}},
    {"id": "hundred_chats", "name": "Deep Thinker", "description": "Send 100 chat messages", "icon": "🤔", "category": "social", "xp_reward": 400, "requirement": {"type": "messages_sent", "count": 100}},
    {"id": "math_explorer", "name": "Math Explorer", "description": "Complete 10 math lessons", "icon": "🔢", "category": "mastery", "xp_reward": 250, "requirement": {"type": "subject_lessons", "subject": "math", "count": 10}},
    {"id": "science_explorer", "name": "Science Explorer", "description": "Complete 10 science lessons", "icon": "🔬", "category": "mastery", "xp_reward": 250, "requirement": {"type": "subject_lessons", "subject": "science", "count": 10}},
    {"id": "reading_explorer", "name": "Reading Explorer", "description": "Complete 10 reading lessons", "icon": "📖", "category": "mastery", "xp_reward": 250, "requirement": {"type": "subject_lessons", "subject": "reading", "count": 10}},
    {"id": "coding_explorer", "name": "Coding Explorer", "description": "Complete 10 coding lessons", "icon": "💻", "category": "mastery", "xp_reward": 250, "requirement": {"type": "subject_lessons", "subject": "coding", "count": 10}},
]

TITLES = [
    {"level": 1, "title": "Curious Beginner"},
    {"level": 5, "title": "Eager Learner"},
    {"level": 10, "title": "Rising Scholar"},
    {"level": 15, "title": "Knowledge Apprentice"},
    {"level": 20, "title": "Bright Mind"},
    {"level": 25, "title": "Skilled Student"},
    {"level": 30, "title": "Dedicated Scholar"},
    {"level": 40, "title": "Expert Learner"},
    {"level": 50, "title": "Master Scholar"},
    {"level": 60, "title": "Grand Intellectual"},
    {"level": 75, "title": "Legendary Mind"},
    {"level": 90, "title": "Supreme Sage"},
    {"level": 100, "title": "Transcendent Genius"},
]

DEFAULT_STATS = {
    "lessons_completed": 0,
    "concepts_mastered": 0,
    "streak_days": 0,
    "perfect_quizzes": 0,
    "messages_sent": 0,
    "subject_lessons": {"math": 0, "science": 0, "reading": 0, "coding": 0},
    "total_learning_time_minutes": 0,
}


def _xp_for_level(level: int) -> int:
    return int(100 * (level ** 1.5))


def _level_from_xp(xp: int) -> int:
    level = 1
    while _xp_for_level(level + 1) <= xp and level < 100:
        level += 1
    return level


def _get_title(level: int) -> str:
    title = "Curious Beginner"
    for t in TITLES:
        if level >= t["level"]:
            title = t["title"]
    return title


async def _get_or_create_profile(db: AsyncSession, user_id: str) -> GamificationProfile:
    result = await db.execute(
        select(GamificationProfile).where(GamificationProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        try:
            profile = GamificationProfile(
                user_id=user_id,
                xp=0,
                streak=0,
                longest_streak=0,
                achievements_unlocked=[],
                stats=dict(DEFAULT_STATS),
                last_active=datetime.now(timezone.utc),
            )
            db.add(profile)
            await db.flush()
        except IntegrityError:
            await db.rollback()
            result = await db.execute(
                select(GamificationProfile).where(GamificationProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            if profile is None:
                raise HTTPException(status_code=500, detail="Failed to create gamification profile")
    return profile


class AwardXPRequest(BaseModel):
    amount: int
    reason: str = "general"
    metadata: Dict[str, Any] = {}


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token_data["user_id"]


@router.get("/profile")
async def get_profile(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    profile = await _get_or_create_profile(db, user_id)
    level = _level_from_xp(profile.xp)
    current_level_min_xp = _xp_for_level(level) if level > 1 else 0
    next_level_xp = _xp_for_level(level + 1) if level < 100 else _xp_for_level(100)

    stats = profile.stats if profile.stats else dict(DEFAULT_STATS)

    return {
        "user_id": profile.user_id,
        "xp": profile.xp,
        "level": level,
        "title": _get_title(level),
        "streak": profile.streak,
        "longest_streak": profile.longest_streak,
        "xp_for_current_level": current_level_min_xp,
        "xp_for_next_level": next_level_xp,
        "xp_progress": profile.xp - current_level_min_xp,
        "xp_needed": next_level_xp - profile.xp,
        "achievements_unlocked": profile.achievements_unlocked or [],
        "achievements_count": len(profile.achievements_unlocked or []),
        "total_achievements": len(ACHIEVEMENTS),
        "stats": stats,
    }


@router.post("/award-xp")
async def award_xp(request: AwardXPRequest, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    profile = await _get_or_create_profile(db, user_id)
    old_level = _level_from_xp(profile.xp)
    profile.xp += request.amount
    new_level = _level_from_xp(profile.xp)
    profile.last_active = datetime.now(timezone.utc)

    leveled_up = new_level > old_level
    new_achievements = _check_achievements(profile)

    await db.flush()

    result = {
        "xp_awarded": request.amount,
        "total_xp": profile.xp,
        "level": new_level,
        "title": _get_title(new_level),
        "leveled_up": leveled_up,
        "new_achievements": new_achievements,
    }

    if leveled_up:
        result["level_up_message"] = f"🎉 Congratulations! You've reached Level {new_level}!"
        result["new_title"] = _get_title(new_level)
        old_title = _get_title(old_level)
        if result["new_title"] != old_title:
            result["title_unlocked"] = result["new_title"]

    return result


def _check_achievements(profile: GamificationProfile) -> List[Dict]:
    unlocked = []
    stats = profile.stats if profile.stats else dict(DEFAULT_STATS)
    already_unlocked = set(profile.achievements_unlocked or [])

    achievements_list = list(profile.achievements_unlocked or [])

    for ach in ACHIEVEMENTS:
        if ach["id"] in already_unlocked:
            continue
        req = ach["requirement"]
        req_type = req["type"]
        met = False

        if req_type == "lessons_completed":
            met = stats.get("lessons_completed", 0) >= req["count"]
        elif req_type == "concepts_mastered":
            met = stats.get("concepts_mastered", 0) >= req["count"]
        elif req_type == "streak_days":
            met = stats.get("streak_days", 0) >= req["count"]
        elif req_type == "perfect_quizzes":
            met = stats.get("perfect_quizzes", 0) >= req["count"]
        elif req_type == "messages_sent":
            met = stats.get("messages_sent", 0) >= req["count"]
        elif req_type == "subject_lessons":
            subject = req.get("subject", "")
            met = stats.get("subject_lessons", {}).get(subject, 0) >= req["count"]

        if met:
            achievements_list.append(ach["id"])
            already_unlocked.add(ach["id"])
            profile.xp += ach["xp_reward"]
            unlocked.append({
                "id": ach["id"],
                "name": ach["name"],
                "description": ach["description"],
                "icon": ach["icon"],
                "xp_reward": ach["xp_reward"],
            })

    profile.achievements_unlocked = achievements_list

    return unlocked


@router.get("/achievements")
async def get_achievements(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    profile = await _get_or_create_profile(db, user_id)
    unlocked_ids = set(profile.achievements_unlocked or [])
    stats = profile.stats if profile.stats else dict(DEFAULT_STATS)

    result = []
    for ach in ACHIEVEMENTS:
        progress = _get_achievement_progress(ach, stats)
        result.append({
            "id": ach["id"],
            "name": ach["name"],
            "description": ach["description"],
            "icon": ach["icon"],
            "category": ach["category"],
            "xp_reward": ach["xp_reward"],
            "unlocked": ach["id"] in unlocked_ids,
            "progress": progress,
        })

    return {"achievements": result, "total": len(ACHIEVEMENTS), "unlocked": len(unlocked_ids)}


def _get_achievement_progress(ach: Dict, stats: Dict) -> Dict:
    req = ach["requirement"]
    req_type = req["type"]
    target = req["count"]
    current = 0

    if req_type == "lessons_completed":
        current = stats.get("lessons_completed", 0)
    elif req_type == "concepts_mastered":
        current = stats.get("concepts_mastered", 0)
    elif req_type == "streak_days":
        current = stats.get("streak_days", 0)
    elif req_type == "perfect_quizzes":
        current = stats.get("perfect_quizzes", 0)
    elif req_type == "messages_sent":
        current = stats.get("messages_sent", 0)
    elif req_type == "subject_lessons":
        subject = req.get("subject", "")
        current = stats.get("subject_lessons", {}).get(subject, 0)

    return {"current": min(current, target), "target": target, "percentage": round(min(current / max(target, 1), 1.0) * 100, 1)}


@router.get("/leaderboard")
async def get_leaderboard(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    leaderboard = [
        {"rank": 1, "username": "StarLearner42", "xp": 15200, "level": 28, "title": "Dedicated Scholar", "avatar": "🌟"},
        {"rank": 2, "username": "MathWizard", "xp": 12800, "level": 24, "title": "Skilled Student", "avatar": "🧙"},
        {"rank": 3, "username": "ScienceGuru", "xp": 11500, "level": 22, "title": "Skilled Student", "avatar": "🔬"},
        {"rank": 4, "username": "BookWorm99", "xp": 9800, "level": 19, "title": "Knowledge Apprentice", "avatar": "📚"},
        {"rank": 5, "username": "CodeNinja", "xp": 8500, "level": 17, "title": "Knowledge Apprentice", "avatar": "🥷"},
        {"rank": 6, "username": "CuriousCat", "xp": 7200, "level": 15, "title": "Knowledge Apprentice", "avatar": "🐱"},
        {"rank": 7, "username": "BrainStorm", "xp": 5600, "level": 12, "title": "Rising Scholar", "avatar": "⚡"},
        {"rank": 8, "username": "SmartPanda", "xp": 4200, "level": 10, "title": "Rising Scholar", "avatar": "🐼"},
        {"rank": 9, "username": "LearnFast", "xp": 3100, "level": 8, "title": "Eager Learner", "avatar": "🚀"},
        {"rank": 10, "username": "NewExplorer", "xp": 1500, "level": 5, "title": "Eager Learner", "avatar": "🌍"},
    ]

    profile = await _get_or_create_profile(db, user_id)
    user_level = _level_from_xp(profile.xp)
    user_rank = 1
    for entry in leaderboard:
        if profile.xp < entry["xp"]:
            user_rank = entry["rank"] + 1

    return {
        "leaderboard": leaderboard,
        "user_position": {
            "rank": user_rank,
            "username": f"You ({user_id})",
            "xp": profile.xp,
            "level": user_level,
            "title": _get_title(user_level),
        },
    }


__all__ = ["router"]
