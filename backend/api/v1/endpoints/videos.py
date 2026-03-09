import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..auth import verify_token
from ....core.database import get_db, VideoLesson, VideoProgress
from ....unified_adaptive_engine import record_video_interaction, get_video_recommendations

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

VIDEO_SEED_DATA = [
    {
        "title": "Introduction to Fractions",
        "subject": "math",
        "topic": "Fractions Basics",
        "description": "Learn what fractions are, how to read them, and see real-world examples of fractions all around you!",
        "duration_seconds": 180,
        "grade_min": 2,
        "grade_max": 4,
        "difficulty": "beginner",
        "quiz_data": {
            "questions": [
                {"q": "What does the top number of a fraction represent?", "options": ["How many equal parts total", "How many parts you have", "The size of the whole", "Nothing"], "answer": 1},
                {"q": "What is 1/2 of a pizza?", "options": ["The whole pizza", "One slice out of two equal slices", "Two pizzas", "No pizza"], "answer": 1},
                {"q": "In the fraction 3/4, what is the denominator?", "options": ["3", "4", "7", "1"], "answer": 1},
            ]
        },
    },
    {
        "title": "Addition Basics: Adding Numbers",
        "subject": "math",
        "topic": "Addition",
        "description": "Master the basics of addition with fun examples, number lines, and hands-on counting exercises!",
        "duration_seconds": 150,
        "grade_min": 1,
        "grade_max": 3,
        "difficulty": "beginner",
        "quiz_data": {
            "questions": [
                {"q": "What is 3 + 4?", "options": ["5", "6", "7", "8"], "answer": 2},
                {"q": "If you have 5 apples and get 2 more, how many do you have?", "options": ["5", "6", "7", "3"], "answer": 2},
                {"q": "What is 10 + 0?", "options": ["0", "1", "10", "100"], "answer": 2},
            ]
        },
    },
    {
        "title": "Planets of the Solar System",
        "subject": "science",
        "topic": "Solar System",
        "description": "Take a journey through our solar system! Learn about all 8 planets, their sizes, and what makes each one special.",
        "duration_seconds": 240,
        "grade_min": 2,
        "grade_max": 5,
        "difficulty": "beginner",
        "quiz_data": {
            "questions": [
                {"q": "How many planets are in our solar system?", "options": ["7", "8", "9", "10"], "answer": 1},
                {"q": "Which planet is closest to the Sun?", "options": ["Venus", "Earth", "Mercury", "Mars"], "answer": 2},
                {"q": "Which planet is known as the Red Planet?", "options": ["Jupiter", "Mars", "Saturn", "Venus"], "answer": 1},
            ]
        },
    },
    {
        "title": "Parts of Speech: Nouns & Verbs",
        "subject": "reading",
        "topic": "Grammar",
        "description": "Discover the building blocks of sentences! Learn what nouns and verbs are with fun examples and activities.",
        "duration_seconds": 200,
        "grade_min": 1,
        "grade_max": 4,
        "difficulty": "beginner",
        "quiz_data": {
            "questions": [
                {"q": "Which of these is a noun?", "options": ["Run", "Happy", "Dog", "Quickly"], "answer": 2},
                {"q": "Which of these is a verb?", "options": ["Cat", "Jump", "Blue", "Table"], "answer": 1},
                {"q": "In 'The cat sleeps', what is the verb?", "options": ["The", "cat", "sleeps", "None"], "answer": 2},
            ]
        },
    },
    {
        "title": "Multiplication Made Easy",
        "subject": "math",
        "topic": "Multiplication",
        "description": "Learn multiplication as repeated addition and discover tricks to remember your times tables!",
        "duration_seconds": 210,
        "grade_min": 2,
        "grade_max": 5,
        "difficulty": "intermediate",
        "quiz_data": {
            "questions": [
                {"q": "What is 3 × 4?", "options": ["7", "10", "12", "15"], "answer": 2},
                {"q": "Multiplication is the same as...", "options": ["Repeated subtraction", "Repeated addition", "Division", "Counting backwards"], "answer": 1},
                {"q": "What is 5 × 0?", "options": ["5", "0", "1", "50"], "answer": 1},
            ]
        },
    },
    {
        "title": "Water Cycle Adventure",
        "subject": "science",
        "topic": "Water Cycle",
        "description": "Follow a water droplet on its amazing journey through evaporation, condensation, and precipitation!",
        "duration_seconds": 190,
        "grade_min": 2,
        "grade_max": 5,
        "difficulty": "beginner",
        "quiz_data": {
            "questions": [
                {"q": "What happens when water heats up and turns into vapor?", "options": ["Condensation", "Precipitation", "Evaporation", "Collection"], "answer": 2},
                {"q": "What forms when water vapor cools in the sky?", "options": ["Rivers", "Clouds", "Snow only", "Rocks"], "answer": 1},
                {"q": "Rain, snow, and hail are all forms of...", "options": ["Evaporation", "Condensation", "Precipitation", "Transpiration"], "answer": 2},
            ]
        },
    },
]

SUBJECT_THUMBNAILS = {
    "math": "🔢",
    "science": "🔬",
    "reading": "📖",
    "coding": "💻",
}


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token_data["user_id"]


def _format_duration(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def _video_to_dict(v: VideoLesson, progress=None) -> Dict[str, Any]:
    return {
        "id": str(v.id),
        "title": v.title,
        "subject": v.subject,
        "topic": v.topic,
        "description": v.description,
        "duration_seconds": v.duration_seconds,
        "duration_formatted": _format_duration(v.duration_seconds),
        "grade_min": v.grade_min,
        "grade_max": v.grade_max,
        "difficulty": v.difficulty,
        "thumbnail_icon": SUBJECT_THUMBNAILS.get(v.subject, "📹"),
        "view_count": v.view_count or 0,
        "has_quiz": bool(v.quiz_data and v.quiz_data.get("questions")),
        "watched": progress.watched if progress else False,
        "quiz_score": progress.quiz_score if progress else None,
        "xp_awarded": progress.xp_awarded if progress else 0,
    }


@router.get("/library")
async def get_video_library(
    subject: Optional[str] = None,
    difficulty: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    query = select(VideoLesson)
    if subject:
        query = query.where(VideoLesson.subject == subject)
    if difficulty:
        query = query.where(VideoLesson.difficulty == difficulty)
    query = query.order_by(VideoLesson.created_at)

    result = await db.execute(query)
    videos = result.scalars().all()

    progress_result = await db.execute(
        select(VideoProgress).where(VideoProgress.user_id == user_id)
    )
    progress_map = {p.video_id: p for p in progress_result.scalars().all()}

    video_list = []
    for v in videos:
        prog = progress_map.get(str(v.id))
        video_list.append(_video_to_dict(v, prog))

    subjects = list(set(v.subject for v in videos))
    watched_count = sum(1 for v in video_list if v["watched"])

    return {
        "videos": video_list,
        "total": len(video_list),
        "watched": watched_count,
        "subjects": subjects,
    }


@router.get("/recommended")
async def get_recommended_videos(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    progress_result = await db.execute(
        select(VideoProgress).where(
            VideoProgress.user_id == user_id,
            VideoProgress.watched == True,
        )
    )
    watched_ids = {p.video_id for p in progress_result.scalars().all()}

    result = await db.execute(select(VideoLesson))
    all_videos = result.scalars().all()

    unwatched = [v for v in all_videos if str(v.id) not in watched_ids]
    if not unwatched:
        unwatched = all_videos

    recommended = unwatched[:4]
    return {
        "recommended": [_video_to_dict(v) for v in recommended],
    }


@router.get("/{video_id}")
async def get_video_details(
    video_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VideoLesson).where(VideoLesson.id == video_id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    prog_result = await db.execute(
        select(VideoProgress).where(
            VideoProgress.user_id == user_id,
            VideoProgress.video_id == video_id,
        )
    )
    progress = prog_result.scalar_one_or_none()

    data = _video_to_dict(video, progress)
    data["quiz_data"] = video.quiz_data
    return data


class CompleteVideoRequest(BaseModel):
    quiz_score: Optional[float] = None


@router.post("/{video_id}/complete")
async def complete_video(
    video_id: str,
    request: CompleteVideoRequest = CompleteVideoRequest(),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VideoLesson).where(VideoLesson.id == video_id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    prog_result = await db.execute(
        select(VideoProgress).where(
            VideoProgress.user_id == user_id,
            VideoProgress.video_id == video_id,
        )
    )
    progress = prog_result.scalar_one_or_none()

    xp_earned = 0
    already_watched = False

    if progress and progress.watched:
        already_watched = True
        if request.quiz_score is not None and (progress.quiz_score is None or request.quiz_score > progress.quiz_score):
            progress.quiz_score = request.quiz_score
            bonus_xp = int(request.quiz_score * 30)
            xp_earned = max(0, bonus_xp - progress.xp_awarded)
            progress.xp_awarded += xp_earned
    else:
        xp_earned = 50
        if request.quiz_score is not None:
            xp_earned += int(request.quiz_score * 30)

        if progress:
            progress.watched = True
            progress.quiz_score = request.quiz_score
            progress.xp_awarded = xp_earned
        else:
            progress = VideoProgress(
                user_id=user_id,
                video_id=video_id,
                watched=True,
                watch_time_seconds=video.duration_seconds,
                quiz_score=request.quiz_score,
                xp_awarded=xp_earned,
            )
            db.add(progress)

    video.view_count = (video.view_count or 0) + 1
    await db.flush()

    try:
        await record_video_interaction(
            db, user_id,
            subject=video.subject or "math",
            topic=video.topic or "",
            watch_duration_pct=1.0,
            quiz_score=request.quiz_score,
        )
    except Exception as e:
        logger.warning("Failed to record adaptive video interaction: %s", e)

    return {
        "success": True,
        "video_id": video_id,
        "xp_earned": xp_earned,
        "total_xp_awarded": progress.xp_awarded if progress else xp_earned,
        "already_watched": already_watched,
        "quiz_score": request.quiz_score,
        "message": "Great job watching the video!" if not already_watched else "Video re-watched!",
    }


async def seed_video_lessons(db: AsyncSession):
    result = await db.execute(select(VideoLesson).limit(1))
    if result.scalar_one_or_none() is not None:
        logger.info("Video lessons already seeded")
        return

    for vdata in VIDEO_SEED_DATA:
        video = VideoLesson(
            title=vdata["title"],
            subject=vdata["subject"],
            topic=vdata["topic"],
            description=vdata["description"],
            video_path=f"/videos/{vdata['subject']}_{vdata['topic'].lower().replace(' ', '_')}.mp4",
            thumbnail_path=f"/videos/thumbs/{vdata['subject']}_{vdata['topic'].lower().replace(' ', '_')}.jpg",
            duration_seconds=vdata["duration_seconds"],
            grade_min=vdata["grade_min"],
            grade_max=vdata["grade_max"],
            difficulty=vdata["difficulty"],
            quiz_data=vdata["quiz_data"],
            view_count=0,
        )
        db.add(video)

    await db.flush()
    logger.info(f"Seeded {len(VIDEO_SEED_DATA)} video lessons")


__all__ = ["router", "seed_video_lessons"]
