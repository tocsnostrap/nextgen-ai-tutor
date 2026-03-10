import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .core.database import StudentAdaptiveProfile
from .bkt_lite import bkt_lite

logger = logging.getLogger(__name__)

DIFFICULTY_LEVELS = ["easy", "medium", "hard"]

SUBJECT_SKILLS = {
    "math": ["addition", "subtraction", "multiplication", "division", "fractions", "decimals", "geometry", "algebra", "counting", "patterns", "measurement"],
    "science": ["plants", "animals", "weather", "ecosystems", "matter", "energy", "forces"],
    "reading": ["comprehension", "vocabulary", "phonics", "inference"],
    "coding": ["variables", "loops", "functions", "conditionals", "algorithms"],
}

GAME_TYPE_SUBJECTS = {
    "math_race": "math",
    "science_trivia": "science",
    "spelling_bee": "reading",
    "code_challenge": "coding",
}


async def get_or_create_profile(db: AsyncSession, user_id: str) -> StudentAdaptiveProfile:
    result = await db.execute(
        select(StudentAdaptiveProfile).where(StudentAdaptiveProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = StudentAdaptiveProfile(
            user_id=user_id,
            mastery_scores={},
            subject_enjoyment={"math": 0.5, "science": 0.5, "reading": 0.5, "coding": 0.5},
            topic_engagement={},
            preferred_activities={"chat": 0.5, "games": 0.5, "videos": 0.5, "whiteboard": 0.5},
            emotion_history=[],
            session_stats={},
            strengths=[],
            struggles=[],
            favorite_subjects=[],
            recent_topics=[],
        )
        db.add(profile)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            result = await db.execute(
                select(StudentAdaptiveProfile).where(StudentAdaptiveProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            if not profile:
                raise
    return profile


def _update_enjoyment_score(current: float, signal: float, weight: float = 0.15) -> float:
    return max(0.0, min(1.0, current + (signal - current) * weight))


def _get_mastery_level(score: float) -> str:
    if score >= 0.9:
        return "mastered"
    elif score >= 0.7:
        return "proficient"
    elif score >= 0.4:
        return "developing"
    return "novice"


def _get_recommended_difficulty(mastery: float, emotion: str = "neutral") -> str:
    if emotion in ("frustrated", "confused"):
        if mastery >= 0.7:
            return "medium"
        return "easy"
    if mastery >= 0.75:
        return "hard"
    if mastery >= 0.4:
        return "medium"
    return "easy"


async def record_chat_interaction(
    db: AsyncSession,
    user_id: str,
    subject: str,
    emotion: str,
    teaching_strategy: str,
    concepts: List[str],
    difficulty_adjustment: str,
    response_quality: str = "good",
) -> Dict[str, Any]:
    profile = await get_or_create_profile(db, user_id)

    enjoyment = dict(profile.subject_enjoyment or {})
    engagement = dict(profile.topic_engagement or {})
    emotions = list(profile.emotion_history or [])
    recent = list(profile.recent_topics or [])
    mastery = dict(profile.mastery_scores or {})

    positive_emotions = {"excited", "happy", "engaged", "curious", "confident"}
    negative_emotions = {"frustrated", "confused", "bored"}

    if emotion in positive_emotions:
        enjoyment[subject] = _update_enjoyment_score(enjoyment.get(subject, 0.5), 0.8)
        for concept in concepts:
            engagement[concept] = _update_enjoyment_score(engagement.get(concept, 0.5), 0.85)
    elif emotion in negative_emotions:
        enjoyment[subject] = _update_enjoyment_score(enjoyment.get(subject, 0.5), 0.3)
        for concept in concepts:
            engagement[concept] = _update_enjoyment_score(engagement.get(concept, 0.5), 0.25)

    emotions.append({
        "emotion": emotion,
        "subject": subject,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    if len(emotions) > 50:
        emotions = emotions[-50:]

    for concept in concepts:
        bkt_mastery = bkt_lite.get_mastery(user_id, concept)
        mastery[concept] = bkt_mastery

    for concept in concepts:
        if concept not in recent:
            recent.append(concept)
    if len(recent) > 20:
        recent = recent[-20:]

    strengths = [s for s, m in mastery.items() if m >= 0.7]
    struggles = [s for s, m in mastery.items() if m < 0.4]

    fav_subjects = sorted(enjoyment.items(), key=lambda x: x[1], reverse=True)
    favorites = [s for s, score in fav_subjects if score >= 0.6]

    if difficulty_adjustment == "decrease":
        new_diff_idx = max(0, DIFFICULTY_LEVELS.index(profile.difficulty_level or "medium") - 1)
        profile.difficulty_level = DIFFICULTY_LEVELS[new_diff_idx]
    elif difficulty_adjustment == "increase":
        new_diff_idx = min(2, DIFFICULTY_LEVELS.index(profile.difficulty_level or "medium") + 1)
        profile.difficulty_level = DIFFICULTY_LEVELS[new_diff_idx]

    profile.subject_enjoyment = enjoyment
    profile.topic_engagement = engagement
    profile.emotion_history = emotions
    profile.recent_topics = recent
    profile.mastery_scores = mastery
    profile.strengths = strengths
    profile.struggles = struggles
    profile.favorite_subjects = favorites
    profile.total_sessions = (profile.total_sessions or 0) + 1

    activities = dict(profile.preferred_activities or {})
    activities["chat"] = _update_enjoyment_score(activities.get("chat", 0.5), 0.7)
    profile.preferred_activities = activities

    await db.flush()

    return _build_adaptation_context(profile)


async def record_game_interaction(
    db: AsyncSession,
    user_id: str,
    game_type: str,
    score: int,
    correct_count: int,
    total_questions: int,
    placement: int,
) -> Dict[str, Any]:
    profile = await get_or_create_profile(db, user_id)

    subject = GAME_TYPE_SUBJECTS.get(game_type, "math")
    enjoyment = dict(profile.subject_enjoyment or {})
    activities = dict(profile.preferred_activities or {})
    mastery = dict(profile.mastery_scores or {})

    accuracy = correct_count / max(1, total_questions)

    if accuracy >= 0.7 or placement <= 2:
        enjoyment[subject] = _update_enjoyment_score(enjoyment.get(subject, 0.5), 0.85)
        activities["games"] = _update_enjoyment_score(activities.get("games", 0.5), 0.9)
    elif accuracy < 0.4:
        enjoyment[subject] = _update_enjoyment_score(enjoyment.get(subject, 0.5), 0.35)

    for skill in SUBJECT_SKILLS.get(subject, []):
        bkt_mastery = bkt_lite.get_mastery(user_id, skill)
        mastery[skill] = bkt_mastery

    profile.subject_enjoyment = enjoyment
    profile.preferred_activities = activities
    profile.mastery_scores = mastery
    profile.avg_accuracy = round(
        ((profile.avg_accuracy or 0.5) * (profile.total_sessions or 1) + accuracy) /
        ((profile.total_sessions or 1) + 1), 3
    )
    profile.total_sessions = (profile.total_sessions or 0) + 1

    await db.flush()
    return _build_adaptation_context(profile)


async def record_video_interaction(
    db: AsyncSession,
    user_id: str,
    subject: str,
    topic: str,
    watch_duration_pct: float,
    quiz_score: Optional[float] = None,
) -> Dict[str, Any]:
    profile = await get_or_create_profile(db, user_id)

    enjoyment = dict(profile.subject_enjoyment or {})
    engagement = dict(profile.topic_engagement or {})
    activities = dict(profile.preferred_activities or {})

    if watch_duration_pct >= 0.8:
        enjoyment[subject] = _update_enjoyment_score(enjoyment.get(subject, 0.5), 0.8)
        engagement[topic] = _update_enjoyment_score(engagement.get(topic, 0.5), 0.85)
        activities["videos"] = _update_enjoyment_score(activities.get("videos", 0.5), 0.8)
    elif watch_duration_pct < 0.3:
        engagement[topic] = _update_enjoyment_score(engagement.get(topic, 0.5), 0.2)

    if quiz_score is not None and quiz_score >= 0.7:
        enjoyment[subject] = _update_enjoyment_score(enjoyment.get(subject, 0.5), 0.85)

    profile.subject_enjoyment = enjoyment
    profile.topic_engagement = engagement
    profile.preferred_activities = activities

    await db.flush()
    return _build_adaptation_context(profile)


async def record_whiteboard_interaction(
    db: AsyncSession,
    user_id: str,
    subject: str,
    concept: str,
    duration_seconds: int,
) -> Dict[str, Any]:
    profile = await get_or_create_profile(db, user_id)

    activities = dict(profile.preferred_activities or {})
    engagement = dict(profile.topic_engagement or {})

    if duration_seconds > 60:
        activities["whiteboard"] = _update_enjoyment_score(activities.get("whiteboard", 0.5), 0.8)
        engagement[concept] = _update_enjoyment_score(engagement.get(concept, 0.5), 0.75)

    profile.preferred_activities = activities
    profile.topic_engagement = engagement

    await db.flush()
    return _build_adaptation_context(profile)


def _build_adaptation_context(profile: StudentAdaptiveProfile) -> Dict[str, Any]:
    enjoyment = profile.subject_enjoyment or {}
    engagement = profile.topic_engagement or {}
    mastery = profile.mastery_scores or {}
    activities = profile.preferred_activities or {}

    top_subjects = sorted(enjoyment.items(), key=lambda x: x[1], reverse=True)
    top_topics = sorted(engagement.items(), key=lambda x: x[1], reverse=True)[:5]
    fav_activity = max(activities.items(), key=lambda x: x[1])[0] if activities else "chat"

    avg_mastery = sum(mastery.values()) / max(1, len(mastery)) if mastery else 0.5
    recommended_difficulty = _get_recommended_difficulty(avg_mastery)

    return {
        "student_profile": {
            "age": profile.age or 8,
            "difficulty_level": profile.difficulty_level or "medium",
            "learning_style": profile.learning_style or "visual",
            "total_sessions": profile.total_sessions or 0,
            "avg_accuracy": profile.avg_accuracy or 0.5,
            "streak": profile.current_streak or 0,
        },
        "enjoyment": {
            "favorite_subjects": [s for s, _ in top_subjects[:3]],
            "subject_scores": enjoyment,
            "most_enjoyed_topics": [t for t, _ in top_topics],
            "topic_scores": dict(top_topics),
            "preferred_activity": fav_activity,
            "activity_scores": activities,
        },
        "mastery": {
            "scores": mastery,
            "avg_mastery": round(avg_mastery, 3),
            "strengths": profile.strengths or [],
            "struggles": profile.struggles or [],
            "mastery_levels": {s: _get_mastery_level(m) for s, m in mastery.items()},
        },
        "recommendations": {
            "difficulty": recommended_difficulty,
            "focus_skills": profile.struggles[:3] if profile.struggles else [],
            "reward_skills": profile.strengths[:3] if profile.strengths else [],
            "next_game_type": _recommend_game_type(enjoyment, mastery),
            "next_video_subject": _recommend_video_subject(enjoyment, mastery),
            "teaching_strategy": _recommend_strategy(mastery, enjoyment, profile.emotion_history),
        },
        "recent_emotions": _summarize_emotions(profile.emotion_history or []),
    }


def _recommend_game_type(enjoyment: Dict, mastery: Dict) -> str:
    subject_scores = {}
    for subject, skills in SUBJECT_SKILLS.items():
        subj_mastery = [mastery.get(s, 0.3) for s in skills]
        avg_m = sum(subj_mastery) / max(1, len(subj_mastery))
        enjoy = enjoyment.get(subject, 0.5)
        subject_scores[subject] = enjoy * 0.6 + (1 - avg_m) * 0.4

    best = max(subject_scores.items(), key=lambda x: x[1])[0]
    type_map = {"math": "math_race", "science": "science_trivia", "reading": "spelling_bee", "coding": "code_challenge"}
    return type_map.get(best, "math_race")


def _recommend_video_subject(enjoyment: Dict, mastery: Dict) -> str:
    subject_scores = {}
    for subject in SUBJECT_SKILLS:
        enjoy = enjoyment.get(subject, 0.5)
        skills = SUBJECT_SKILLS[subject]
        subj_mastery = [mastery.get(s, 0.3) for s in skills]
        avg_m = sum(subj_mastery) / max(1, len(subj_mastery))
        subject_scores[subject] = enjoy * 0.5 + (1 - avg_m) * 0.5

    return max(subject_scores.items(), key=lambda x: x[1])[0]


def _recommend_strategy(mastery: Dict, enjoyment: Dict, emotions: List) -> str:
    avg_m = sum(mastery.values()) / max(1, len(mastery)) if mastery else 0.5

    recent_emotions = [e.get("emotion") for e in (emotions or [])[-5:]]
    frustrated_count = sum(1 for e in recent_emotions if e in ("frustrated", "confused"))
    excited_count = sum(1 for e in recent_emotions if e in ("excited", "happy", "curious"))

    if frustrated_count >= 2:
        return "encourage"
    if avg_m < 0.35:
        return "explain"
    if excited_count >= 2 and avg_m >= 0.6:
        return "socratic"
    if avg_m >= 0.7:
        return "quiz"

    top_enjoy = max(enjoyment.values()) if enjoyment else 0.5
    if top_enjoy >= 0.7:
        return "example"

    return "explain"


def _summarize_emotions(emotions: List) -> Dict[str, Any]:
    if not emotions:
        return {"dominant": "neutral", "trend": "stable", "recent": []}

    recent = emotions[-10:]
    emotion_counts = {}
    for e in recent:
        em = e.get("emotion", "neutral")
        emotion_counts[em] = emotion_counts.get(em, 0) + 1

    dominant = max(emotion_counts.items(), key=lambda x: x[1])[0]

    positive = sum(1 for e in recent if e.get("emotion") in ("excited", "happy", "engaged", "curious", "confident"))
    negative = sum(1 for e in recent if e.get("emotion") in ("frustrated", "confused", "bored"))

    if positive > negative + 2:
        trend = "improving"
    elif negative > positive + 2:
        trend = "declining"
    else:
        trend = "stable"

    return {
        "dominant": dominant,
        "trend": trend,
        "recent": [e.get("emotion") for e in recent[-5:]],
        "distribution": emotion_counts,
    }


async def get_adaptation_context(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    profile = await get_or_create_profile(db, user_id)
    return _build_adaptation_context(profile)


async def get_ai_memory_prompt(db: AsyncSession, user_id: str) -> str:
    profile = await get_or_create_profile(db, user_id)
    ctx = _build_adaptation_context(profile)

    parts = []

    favs = ctx["enjoyment"]["favorite_subjects"]
    if favs:
        parts.append(f"This student particularly enjoys {', '.join(favs)}.")

    top_topics = ctx["enjoyment"]["most_enjoyed_topics"]
    if top_topics:
        parts.append(f"Their favorite topics include: {', '.join(top_topics[:5])}.")

    strengths = ctx["mastery"]["strengths"]
    if strengths:
        parts.append(f"They are strong in: {', '.join(strengths[:5])}.")

    struggles = ctx["mastery"]["struggles"]
    if struggles:
        parts.append(f"They need more practice with: {', '.join(struggles[:5])}. Be extra encouraging and patient when covering these topics.")

    emo = ctx["recent_emotions"]
    if emo["trend"] == "declining":
        parts.append("The student's mood has been declining recently. Prioritize encouragement, fun examples, and celebrate small wins.")
    elif emo["trend"] == "improving":
        parts.append("The student has been in a great mood! Channel their energy into deeper challenges.")

    pref_activity = ctx["enjoyment"]["preferred_activity"]
    if pref_activity == "games":
        parts.append("This student loves games. Make lessons game-like with challenges, points, and competitions when possible.")
    elif pref_activity == "videos":
        parts.append("This student enjoys watching videos. Reference visual explanations and suggest video lessons when relevant.")
    elif pref_activity == "whiteboard":
        parts.append("This student likes visual drawing. Suggest whiteboard demonstrations for complex concepts.")

    diff = ctx["student_profile"]["difficulty_level"]
    parts.append(f"Current difficulty level: {diff}.")

    strategy = ctx["recommendations"]["teaching_strategy"]
    strategy_desc = {
        "socratic": "Use Socratic questioning to challenge their thinking.",
        "explain": "Focus on clear, step-by-step explanations.",
        "example": "Teach through concrete, relatable examples.",
        "quiz": "Include quiz-style challenges to test mastery.",
        "encourage": "Be extra encouraging — they need confidence building.",
    }
    parts.append(strategy_desc.get(strategy, "Adapt your teaching to their needs."))

    return "\n".join(parts) if parts else ""


async def get_game_difficulty_params(db: AsyncSession, user_id: str, game_type: str) -> Dict[str, Any]:
    profile = await get_or_create_profile(db, user_id)
    mastery = profile.mastery_scores or {}
    subject = GAME_TYPE_SUBJECTS.get(game_type, "math")
    skills = SUBJECT_SKILLS.get(subject, [])

    subj_mastery = [mastery.get(s, 0.3) for s in skills]
    avg_m = sum(subj_mastery) / max(1, len(subj_mastery))

    if avg_m >= 0.7:
        bot_correct_prob = 0.8
        time_limit_modifier = 0.8
        difficulty_label = "hard"
    elif avg_m >= 0.4:
        bot_correct_prob = 0.65
        time_limit_modifier = 1.0
        difficulty_label = "medium"
    else:
        bot_correct_prob = 0.5
        time_limit_modifier = 1.3
        difficulty_label = "easy"

    return {
        "difficulty": difficulty_label,
        "bot_correct_prob": bot_correct_prob,
        "time_limit_modifier": time_limit_modifier,
        "student_mastery": round(avg_m, 3),
    }


async def get_video_recommendations(db: AsyncSession, user_id: str, available_videos: List[Dict]) -> List[Dict]:
    profile = await get_or_create_profile(db, user_id)
    enjoyment = profile.subject_enjoyment or {}
    mastery = profile.mastery_scores or {}
    engagement = profile.topic_engagement or {}

    scored_videos = []
    for video in available_videos:
        subj = video.get("subject", "math")
        topic = video.get("topic", "")
        diff = video.get("difficulty", "beginner")

        enjoy_score = enjoyment.get(subj, 0.5)
        topic_score = engagement.get(topic, 0.5)

        skills = SUBJECT_SKILLS.get(subj, [])
        subj_mastery = [mastery.get(s, 0.3) for s in skills]
        avg_m = sum(subj_mastery) / max(1, len(subj_mastery))

        diff_match = 1.0
        if diff == "beginner" and avg_m > 0.7:
            diff_match = 0.5
        elif diff == "advanced" and avg_m < 0.4:
            diff_match = 0.4

        total_score = enjoy_score * 0.35 + topic_score * 0.25 + diff_match * 0.25 + (1 - avg_m) * 0.15

        scored_videos.append({
            **video,
            "_score": round(total_score, 3),
            "_reason": f"Matches your interest in {subj}" if enjoy_score >= 0.6 else f"Helps build {subj} skills",
        })

    scored_videos.sort(key=lambda v: v["_score"], reverse=True)
    return scored_videos
