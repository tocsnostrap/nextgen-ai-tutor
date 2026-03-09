import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import verify_token
from ....core.database import get_db
from ....unified_adaptive_engine import (
    get_adaptation_context,
    get_game_difficulty_params,
    get_ai_memory_prompt,
)

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


class OnboardingData(BaseModel):
    name: str
    age: int
    age_group: str
    subjects: List[str]
    avatar: Optional[str] = "robot"


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token_data["user_id"]


@router.get("/profile")
async def get_adaptive_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        context = await get_adaptation_context(db, user_id)
        return context
    except Exception as e:
        logger.error("Failed to get adaptive profile for user %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load adaptive profile",
        )


@router.get("/recommendations")
async def get_recommendations(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        context = await get_adaptation_context(db, user_id)
        return {
            "recommendations": context["recommendations"],
            "enjoyment": context["enjoyment"],
            "mastery": context["mastery"],
            "recent_emotions": context["recent_emotions"],
        }
    except Exception as e:
        logger.error("Failed to get recommendations for user %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load recommendations",
        )


@router.get("/game-difficulty/{game_type}")
async def get_game_difficulty(
    game_type: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        params = await get_game_difficulty_params(db, user_id, game_type)
        return params
    except Exception as e:
        logger.error("Failed to get game difficulty for user %s, game %s: %s", user_id, game_type, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load game difficulty",
        )


@router.get("/memory")
async def get_memory_prompt(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        memory = await get_ai_memory_prompt(db, user_id)
        return {"memory_prompt": memory}
    except Exception as e:
        logger.error("Failed to get memory prompt for user %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load memory prompt",
        )


@router.post("/onboarding")
async def save_onboarding(
    data: OnboardingData,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        from ....unified_adaptive_engine import get_or_create_profile

        profile = await get_or_create_profile(db, user_id)
        profile.age = data.age
        profile.favorite_subjects = data.subjects
        enjoyment = {s: 0.5 for s in ["math", "science", "reading", "coding"]}
        for s in data.subjects:
            if s in enjoyment:
                enjoyment[s] = 0.8
        profile.subject_enjoyment = enjoyment
        if data.age <= 5:
            profile.difficulty_level = "easy"
        elif data.age >= 10:
            profile.difficulty_level = "medium"
        profile.session_stats = {
            **(profile.session_stats or {}),
            "onboarding_name": data.name,
            "onboarding_age": data.age,
            "onboarding_age_group": data.age_group,
            "onboarding_avatar": data.avatar,
        }
        await db.commit()

        logger.info(
            "Onboarding saved to DB for user %s: name=%s, age=%d, group=%s",
            user_id,
            data.name,
            data.age,
            data.age_group,
        )
        return {
            "status": "ok",
            "message": "Onboarding profile saved",
            "profile": {
                "user_id": user_id,
                "name": data.name,
                "age": data.age,
                "age_group": data.age_group,
                "subjects": data.subjects,
                "avatar": data.avatar,
            },
        }
    except Exception as e:
        await db.rollback()
        logger.error("Failed to save onboarding for user %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save onboarding data",
        )
