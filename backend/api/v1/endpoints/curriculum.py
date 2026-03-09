import logging
from typing import Optional, Dict, List, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from ..auth import verify_token
from ....knowledge_graph import knowledge_graph
from ....spaced_repetition import calculate_next_review, quality_from_score, get_review_priority
from ....bkt_lite import bkt_lite

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


class RecommendRequest(BaseModel):
    subject: str
    grade: Optional[int] = None
    mastery_data: Dict[str, float] = {}
    limit: int = 5


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token_data["user_id"]


@router.get("/knowledge-graph")
async def get_knowledge_graph(
    subject: str = Query(..., description="Subject: math, science, reading, coding"),
    grade: Optional[int] = Query(None, description="Grade level (Pre-K=0, 1-6)"),
    user_id: str = Depends(get_current_user_id),
):
    if subject not in ("math", "science", "reading", "coding"):
        raise HTTPException(status_code=400, detail="Subject must be one of: math, science, reading, coding")
    return knowledge_graph.get_knowledge_graph(subject, grade)


@router.get("/lessons")
async def get_lessons(
    subject: str = Query(..., description="Subject: math, science, reading, coding"),
    grade: Optional[int] = Query(None, description="Grade level"),
    user_id: str = Depends(get_current_user_id),
):
    if subject not in ("math", "science", "reading", "coding"):
        raise HTTPException(status_code=400, detail="Subject must be one of: math, science, reading, coding")
    return {"subject": subject, "grade": grade, "lessons": knowledge_graph.get_lessons(subject, grade)}


@router.get("/lesson/{lesson_id}")
async def get_lesson(
    lesson_id: str,
    user_id: str = Depends(get_current_user_id),
):
    lesson = knowledge_graph.get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.get("/review-schedule")
async def get_review_schedule(
    user_id: str = Depends(get_current_user_id),
):
    all_mastery = bkt_lite.get_all_mastery(user_id)

    if not all_mastery:
        all_skills = list(bkt_lite.skill_params.keys())
        for skill_id in all_skills:
            all_mastery[skill_id] = bkt_lite.get_mastery(user_id, skill_id)

    review_items = []
    for skill_id, mastery in all_mastery.items():
        quality = quality_from_score(mastery)
        review_data = calculate_next_review(quality)

        if mastery >= 0.9:
            mastery_level = "mastered"
        elif mastery >= 0.7:
            mastery_level = "proficient"
        elif mastery >= 0.4:
            mastery_level = "developing"
        else:
            mastery_level = "novice"

        review_items.append({
            "skill_id": skill_id,
            "skill_name": skill_id.replace("_", " ").title(),
            "mastery": round(mastery, 4),
            "mastery_level": mastery_level,
            "quality": quality,
            "next_review_date": review_data["next_review_date"],
            "next_interval": review_data["next_interval"],
            "easiness": review_data["new_easiness"],
        })

    prioritized = get_review_priority(review_items)

    return {"user_id": user_id, "schedule": prioritized}


@router.post("/recommend")
async def recommend_lessons(
    request: RecommendRequest,
    user_id: str = Depends(get_current_user_id),
):
    if request.subject not in ("math", "science", "reading", "coding"):
        raise HTTPException(status_code=400, detail="Subject must be one of: math, science, reading, coding")

    mastery_data = dict(request.mastery_data)
    all_mastery = bkt_lite.get_all_mastery(user_id)
    for skill_id, mastery_val in all_mastery.items():
        if skill_id not in mastery_data:
            mastery_data[skill_id] = mastery_val

    recommendations = knowledge_graph.recommend_lessons(
        subject=request.subject,
        mastery_data=mastery_data,
        grade=request.grade,
        limit=request.limit,
    )

    review_items = []
    for skill_id, mastery_val in all_mastery.items():
        quality = quality_from_score(mastery_val)
        review_data = calculate_next_review(quality)
        review_items.append({
            "skill_id": skill_id,
            "next_review_date": review_data["next_review_date"],
            "easiness": review_data["new_easiness"],
        })

    prioritized = get_review_priority(review_items)
    overdue_skills = {item["skill_id"] for item in prioritized if item.get("days_overdue", 0) > 0}

    for rec in recommendations:
        rec_id = rec.get("id", "").lower().replace(" ", "_").replace("-", "_")
        if rec_id in overdue_skills:
            rec["review_overdue"] = True
            rec["priority_boost"] = True

    return {"subject": request.subject, "recommendations": recommendations}


__all__ = ["router"]
