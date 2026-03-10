import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..auth import verify_token
from ....conversational_ai import conversational_ai
from ....core.database import get_db, ChatMessage
from ....bkt_lite import bkt_lite
from ....unified_adaptive_engine import record_chat_interaction, get_ai_memory_prompt, get_adaptation_context
from .knowledge_library import detect_enthusiasm_topics, _get_or_create_profile, _upsert_passion_topic

# Claude AI service — primary (Anthropic claude-opus-4-6 with adaptive thinking)
from ....claude_ai_service import (
    generate_tutor_response as claude_generate_tutor_response,
    stream_tutor_response,
    generate_quiz_claude,
    analyze_student_error,
    generate_personalized_problem,
    generate_metacognitive_coaching,
    generate_whiteboard_instructions,
)
from ....multi_agent_tutor import multi_agent_respond, AgentRole
from ....metacognitive_coach import (
    get_or_create_profile,
    update_profile,
    get_coaching_recommendation,
    get_profile_summary,
)
from ....causal_error_analysis import (
    diagnose_error,
    generate_remediation_plan,
    format_remediation_for_student,
    error_tracker,
)

# Fallback to OpenAI service if Claude is not configured
try:
    from ....ai_service import generate_tutor_response as openai_generate_tutor_response
    from ....ai_service import generate_quiz_ai, generate_whiteboard_instructions as openai_whiteboard
    _has_openai_fallback = True
except ImportError:
    _has_openai_fallback = False

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


class ChatContext(BaseModel):
    subject: Optional[str] = None
    difficulty: Optional[str] = None
    session_id: Optional[str] = None
    student_age: Optional[int] = None
    emotion: Optional[str] = None
    socratic_mode: Optional[bool] = None


class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    topic: Optional[str] = "general"
    subject: Optional[str] = None
    difficulty: Optional[str] = "intermediate"
    age: Optional[int] = 8
    emotion: Optional[str] = "neutral"
    socratic_mode: Optional[bool] = False
    context: Optional[ChatContext] = None


class QuizRequest(BaseModel):
    topic: str = "math"
    difficulty: str = "intermediate"
    num_questions: int = 3
    age: int = 8


class WhiteboardRequest(BaseModel):
    concept: str
    subject: str = "math"
    age: int = 8


class TTSRequest(BaseModel):
    text: str
    voice: str = "alloy"


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token_data["user_id"]


@router.post("/message")
async def send_message(request: ChatMessageRequest, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    ctx = request.context
    topic = (ctx.subject if ctx and ctx.subject else None) or request.subject or request.topic or "general"
    difficulty = (ctx.difficulty if ctx and ctx.difficulty else None) or request.difficulty or "intermediate"
    session_id = (ctx.session_id if ctx and ctx.session_id else None) or request.session_id or "default"
    age = (ctx.student_age if ctx and ctx.student_age else None) or request.age or 8
    emotion = (ctx.emotion if ctx and ctx.emotion else None) or request.emotion or "neutral"
    socratic = (ctx.socratic_mode if ctx and ctx.socratic_mode else None) or request.socratic_mode or False

    namespaced_session_id = f"{user_id}_{session_id}"

    try:
        ai_memory = await get_ai_memory_prompt(db, user_id)
    except Exception:
        ai_memory = ""

    # ── Load child's interest profile for Nova context ───────────────────────
    interest_context = ""
    interest_topics: list = []
    try:
        interest_profile = await _get_or_create_profile(db, user_id)
        top = sorted(
            interest_profile.passion_topics or [],
            key=lambda x: x.get("score", 0), reverse=True
        )[:5]
        custom = interest_profile.custom_interests or []
        nova_mem = interest_profile.nova_memory or []
        parts = []
        if top:
            parts.append("Passions: " + ", ".join(f"{t['emoji']} {t['topic']}" for t in top))
        if custom:
            parts.append("Self-chosen interests: " + ", ".join(f"{c.get('emoji','✨')} {c['topic']}" for c in custom[:3]))
        if nova_mem:
            parts.append("Nova remembers: " + "; ".join(nova_mem[:2]))
        interest_context = "\n".join(parts)
        interest_topics = [t["topic"] for t in top[:3]]
    except Exception as e:
        logger.warning("Could not load interest profile: %s", e)

    context = {
        "session_id": namespaced_session_id,
        "topic": topic,
        "difficulty": difficulty,
        "emotion": emotion,
        "age": age,
        "socratic_mode": socratic,
        "user_id": user_id,
        "teaching_strategy": "socratic" if socratic else "explain",
        "student_memory": ai_memory,
        "interest_context": interest_context,
        "student_interests": interest_topics,
    }

    history_stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id, ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    )
    history_result = await db.execute(history_stmt)
    recent_msgs = history_result.scalars().all()
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(recent_msgs)
    ]

    # ── Update metacognitive profile ────────────────────────────────────────
    meta_profile = get_or_create_profile(user_id)
    meta_profile = update_profile(meta_profile, request.message, context)

    # ── Get metacognitive coaching recommendation ────────────────────────────
    coaching_intervention = get_coaching_recommendation(
        meta_profile, request.message, context, conversation_history
    )

    # ── Check for recent errors to route to error analyst ───────────────────
    recent_errors = []
    recent_error_stmt = (
        select(ChatMessage)
        .where(
            ChatMessage.user_id == user_id,
            ChatMessage.session_id == session_id,
            ChatMessage.role == "assistant",
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(3)
    )
    try:
        recent_result = await db.execute(recent_error_stmt)
        recent_msgs = recent_result.scalars().all()
        for msg in recent_msgs:
            meta = msg.metadata_ or {}
            if meta.get("difficulty_adjustment") == "decrease":
                recent_errors.append({
                    "skill": meta.get("concepts", [topic])[0] if meta.get("concepts") else topic,
                })
    except Exception:
        pass

    # ── Multi-agent tutoring response ────────────────────────────────────────
    learning_patterns = get_profile_summary(meta_profile)
    try:
        agent_response = await multi_agent_respond(
            message=request.message,
            context=context,
            conversation_history=conversation_history,
            recent_errors=recent_errors if recent_errors else None,
            learning_patterns=learning_patterns,
        )
        result = {
            "response": agent_response.primary_response,
            "teaching_strategy": agent_response.teaching_strategy,
            "follow_up_questions": agent_response.follow_up_questions,
            "concepts_covered": agent_response.concepts_covered,
            "difficulty_adjustment": agent_response.difficulty_adjustment,
            "session_id": agent_response.session_id,
            "ai_powered": True,
            "model": agent_response.model,
            "agent_used": agent_response.agent_used.value,
            "used_thinking": agent_response.used_thinking,
        }
    except Exception as e:
        logger.warning("Multi-agent system failed, falling back: %s", e)
        # Fallback to direct Claude call
        result = await claude_generate_tutor_response(request.message, context, conversation_history)
        if not result:
            result = conversational_ai.generate_response(request.message, context)

    # ── Inject metacognitive coaching if warranted ───────────────────────────
    if coaching_intervention and coaching_intervention.urgency in ("high", "medium"):
        original_response = result.get("response", "")
        coaching_prefix = f"\n\n---\n💡 **Learning Tip:** {coaching_intervention.response}\n\n*{coaching_intervention.metacognitive_question}*"
        result["response"] = original_response + coaching_prefix
        result["metacognitive_coaching"] = {
            "triggered": True,
            "intervention_type": coaching_intervention.intervention_type,
            "urgency": coaching_intervention.urgency,
            "strategy_tip": coaching_intervention.strategy_tip,
        }

    emotions = _detect_emotion(request.message)

    skill = result["concepts_covered"][0] if result.get("concepts_covered") else topic
    correct = result.get("difficulty_adjustment") != "decrease"
    bkt_update = bkt_lite.update(user_id, skill, correct)

    # ── Enthusiasm detection → update knowledge library ──────────────────────
    try:
        detected_topics = detect_enthusiasm_topics(request.message)
        if detected_topics:
            int_profile = await _get_or_create_profile(db, user_id)
            from datetime import datetime, timezone as tz
            now = datetime.now(tz.utc).isoformat()
            log = list(int_profile.enthusiasm_log or [])
            for item in detected_topics:
                _upsert_passion_topic(
                    int_profile, item["topic"], item["emoji"],
                    item["subject_area"], item["signal"]
                )
                log.insert(0, {"topic": item["topic"], "signal": item["signal"], "detected_at": now})
            int_profile.enthusiasm_log = log[:100]
    except Exception as e:
        logger.warning("Enthusiasm detection failed: %s", e)

    msg_metadata = {"topic": topic, "difficulty": difficulty, "emotion": emotion}
    user_msg = ChatMessage(
        user_id=user_id,
        session_id=session_id,
        role="user",
        content=request.message,
        metadata_=msg_metadata,
    )
    db.add(user_msg)

    assistant_metadata = {
        "teaching_strategy": result["teaching_strategy"],
        "emotion": emotions["primary_emotion"],
        "concepts": result["concepts_covered"],
        "difficulty_adjustment": result["difficulty_adjustment"],
        "ai_powered": result.get("ai_powered", False),
        "agent_used": result.get("agent_used", "unknown"),
        "model": result.get("model", "unknown"),
    }
    assistant_msg = ChatMessage(
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        content=result["response"],
        metadata_=assistant_metadata,
    )
    db.add(assistant_msg)

    try:
        adaptation = await record_chat_interaction(
            db, user_id, topic, emotions["primary_emotion"],
            result["teaching_strategy"], result["concepts_covered"],
            result["difficulty_adjustment"],
        )
    except Exception as e:
        logger.warning("Failed to record adaptive interaction: %s", e)
        adaptation = None

    return {
        "response": result["response"],
        "teaching_strategy": result["teaching_strategy"],
        "follow_up_questions": result["follow_up_questions"],
        "concepts_covered": result["concepts_covered"],
        "difficulty_adjustment": result["difficulty_adjustment"],
        "emotion_analysis": emotions,
        "bkt_update": bkt_update,
        "session_id": result.get("session_id", namespaced_session_id),
        "ai_powered": result.get("ai_powered", False),
        "agent_used": result.get("agent_used", "domain_expert"),
        "model": result.get("model", "claude-opus-4-6"),
        "used_thinking": result.get("used_thinking", False),
        "adaptation": adaptation,
        "metacognitive_coaching": result.get("metacognitive_coaching"),
    }


@router.get("/history/{session_id}")
async def get_history(session_id: str, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id, ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    history = [
        {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.created_at.isoformat() if msg.created_at else None,
            "metadata": msg.metadata_,
        }
        for msg in messages
    ]

    return {"session_id": session_id, "messages": history, "count": len(history)}


@router.post("/stream")
async def stream_message(
    request: ChatMessageRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream a tutoring response token by token using Server-Sent Events.
    Provides real-time text display with no timeout risk for long responses.
    """
    ctx = request.context
    topic = (ctx.subject if ctx and ctx.subject else None) or request.subject or request.topic or "general"
    difficulty = (ctx.difficulty if ctx and ctx.difficulty else None) or request.difficulty or "intermediate"
    age = (ctx.student_age if ctx and ctx.student_age else None) or request.age or 8
    emotion = (ctx.emotion if ctx and ctx.emotion else None) or request.emotion or "neutral"
    session_id = (ctx.session_id if ctx and ctx.session_id else None) or request.session_id or "default"
    socratic = (ctx.socratic_mode if ctx and ctx.socratic_mode else None) or request.socratic_mode or False
    namespaced_session_id = f"{user_id}_{session_id}"

    try:
        ai_memory = await get_ai_memory_prompt(db, user_id)
    except Exception:
        ai_memory = ""

    history_stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id, ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    )
    history_result = await db.execute(history_stmt)
    recent_msgs = history_result.scalars().all()
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(recent_msgs)
    ]

    context = {
        "session_id": namespaced_session_id,
        "topic": topic,
        "difficulty": difficulty,
        "emotion": emotion,
        "age": age,
        "socratic_mode": socratic,
        "user_id": user_id,
        "teaching_strategy": "socratic" if socratic else "explain",
        "student_memory": ai_memory,
    }

    async def generate():
        try:
            async for chunk in stream_tutor_response(request.message, context, conversation_history):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            logger.error("Streaming error: %s", e)
            yield "data: [ERROR]\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/quiz")
async def generate_quiz(request: QuizRequest, user_id: str = Depends(get_current_user_id)):
    # Try Claude quiz generation first (personalized, structured outputs)
    claude_quiz = await generate_quiz_claude(
        topic=request.topic,
        difficulty=request.difficulty,
        num_questions=request.num_questions,
        age=request.age,
    )
    if claude_quiz:
        return claude_quiz

    quiz = conversational_ai.generate_quiz(
        topic=request.topic,
        difficulty=request.difficulty,
        num_questions=request.num_questions,
        age=request.age,
    )
    return quiz


@router.post("/whiteboard")
async def get_whiteboard_content(request: WhiteboardRequest, user_id: str = Depends(get_current_user_id)):
    instructions = await generate_whiteboard_instructions(
        concept=request.concept,
        subject=request.subject,
        age=request.age,
    )

    if instructions:
        return instructions

    return {
        "title": request.concept.title(),
        "steps": [
            {"instruction": f"Let's learn about {request.concept}", "type": "text", "content": request.concept.title(), "x": 400, "y": 50, "color": "#4ecdc4"},
            {"instruction": "Key idea", "type": "text", "content": f"Understanding {request.concept} step by step", "x": 400, "y": 150, "color": "#f8b500"},
        ],
    }


@router.post("/tts")
async def text_to_speech(request: TTSRequest, user_id: str = Depends(get_current_user_id)):
    try:
        import os
        from openai import OpenAI

        base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
        api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
        if not base_url or not api_key:
            raise HTTPException(status_code=503, detail="TTS service not available")

        client = OpenAI(base_url=base_url, api_key=api_key)
        response = client.audio.speech.create(
            model="gpt-audio",
            voice=request.voice,
            input=request.text,
        )

        import base64
        audio_bytes = response.content
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return {"audio": audio_b64, "format": "mp3"}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("TTS failed: %s", e)
        return {"audio": None, "format": None, "fallback": True, "text": request.text}


class ErrorAnalysisRequest(BaseModel):
    question: str
    student_answer: str
    correct_answer: str
    topic: str = "math"
    age: int = 8
    skill_id: Optional[str] = None


class ProblemRequest(BaseModel):
    topic: str
    skill_level: float = 0.5
    age: int = 8
    interests: Optional[List[str]] = None
    problem_type: str = "practice"  # warmup / practice / challenge


class MetacogRequest(BaseModel):
    message: str
    topic: str = "general"
    emotion: str = "neutral"
    age: int = 8


class TrajectoryRequest(BaseModel):
    age: int = 8
    target_skills: Optional[List[str]] = None


@router.post("/analyze-error")
async def analyze_error(
    request: ErrorAnalysisRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Deep causal analysis of a student error.
    Returns root cause, misconception type, and targeted remediation.
    Uses Claude's adaptive thinking for precise diagnosis.
    """
    skill_id = request.skill_id or request.topic

    # Fast local diagnosis first
    misconception_type, description, confidence = diagnose_error(
        question=request.question,
        student_answer=request.student_answer,
        correct_answer=request.correct_answer,
        skill_id=skill_id,
    )

    # Record the error pattern
    from datetime import datetime
    error_tracker.record_error(user_id, skill_id, misconception_type, datetime.now())

    # Generate remediation plan
    plan = generate_remediation_plan(
        misconception_type=misconception_type,
        skill_id=skill_id,
        question=request.question,
        student_answer=request.student_answer,
        correct_answer=request.correct_answer,
        age=request.age,
    )
    student_message = format_remediation_for_student(plan, request.age)

    # Deep Claude analysis for complex errors or low-confidence diagnoses
    claude_analysis = None
    if confidence < 0.7 or misconception_type.value == "unknown":
        claude_analysis = await analyze_student_error(
            student_answer=request.student_answer,
            correct_answer=request.correct_answer,
            question=request.question,
            topic=request.topic,
            age=request.age,
        )

    return {
        "misconception_type": misconception_type.value,
        "misconception_description": description,
        "diagnosis_confidence": confidence,
        "remediation_message": student_message,
        "remediation_steps": {
            "acknowledge": plan.step_1_acknowledge,
            "reveal": plan.step_2_reveal,
            "contrast": plan.step_3_contrast,
            "practice": plan.step_4_practice,
            "verify": plan.step_5_verify,
        },
        "estimated_minutes": plan.estimated_minutes,
        "prerequisite_review": plan.prerequisite_review,
        "deep_analysis": claude_analysis,
        "error_pattern": error_tracker.get_summary(user_id),
    }


@router.post("/generate-problem")
async def generate_problem(
    request: ProblemRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Generate a personalized problem dynamically tailored to the student.
    Uses ZPD targeting, interest-based contexts, and error pattern targeting.
    """
    # Get student's error patterns to target
    error_summary = error_tracker.get_summary(user_id)
    recent_errors = [
        p["skill"] for p in error_summary.get("top_patterns", [])[:2]
    ]

    problem = await generate_personalized_problem(
        topic=request.topic,
        skill_level=request.skill_level,
        student_interests=request.interests or ["science", "sports", "animals"],
        age=request.age,
        recent_errors=recent_errors if recent_errors else None,
        problem_type=request.problem_type,
    )
    return problem


@router.post("/metacognitive-coaching")
async def get_metacognitive_coaching(
    request: MetacogRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Get metacognitive coaching for a student message.
    Detects mindset patterns and provides targeted strategy coaching.
    """
    profile = get_or_create_profile(user_id)
    context = {
        "age": request.age,
        "topic": request.topic,
        "emotion": request.emotion,
    }

    profile = update_profile(profile, request.message, context)
    profile_summary = get_profile_summary(profile)

    coaching = await generate_metacognitive_coaching(
        student_message=request.message,
        context=context,
        learning_patterns=profile_summary,
    )

    return {
        "coaching": coaching,
        "profile_summary": profile_summary,
    }


@router.get("/learning-trajectory")
async def get_learning_trajectory(
    age: int = 8,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a 4-week learning trajectory forecast for the student.
    Predicts mastery timelines, identifies at-risk skills, generates learning plan.
    """
    from ....bkt_lite import bkt_lite
    from ....learning_trajectory import generate_learning_plan

    # Get current skill states from BKT
    skill_states = bkt_lite.get_all_skills(user_id) if hasattr(bkt_lite, 'get_all_skills') else {}

    # Get session history
    history_stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id, ChatMessage.role == "user")
        .order_by(ChatMessage.created_at.desc())
        .limit(50)
    )
    history_result = await db.execute(history_stmt)
    messages = history_result.scalars().all()

    session_history = [
        {
            "correct": msg.metadata_ and msg.metadata_.get("difficulty_adjustment") != "decrease",
            "skill": (msg.metadata_ or {}).get("topic", "general"),
        }
        for msg in messages
    ]

    # Use Claude for trajectory if we have enough data, else use local
    if len(session_history) >= 5:
        try:
            from ....claude_ai_service import generate_learning_trajectory
            trajectory = await generate_learning_trajectory(
                student_id=user_id,
                skill_states=skill_states,
                session_history=session_history,
                age=age,
            )
            return trajectory
        except Exception as e:
            logger.warning("Claude trajectory generation failed: %s", e)

    # Local fallback trajectory
    plan = generate_learning_plan(
        student_id=user_id,
        skill_states=skill_states,
        session_history=session_history,
        age=age,
    )
    return {
        "four_week_plan": plan.weekly_plans,
        "skills_to_review": plan.skills_to_review,
        "skills_to_advance": plan.skills_to_advance,
        "daily_practice_minutes": plan.daily_minutes_recommended,
        "parent_insights": plan.parent_insights,
        "overall_assessment": plan.teacher_notes,
        "confidence": plan.confidence,
        "student_id": user_id,
    }


@router.get("/metacognitive-profile")
async def get_metacognitive_profile(user_id: str = Depends(get_current_user_id)):
    """Get the student's metacognitive learning profile."""
    profile = get_or_create_profile(user_id)
    return get_profile_summary(profile)


@router.get("/error-patterns")
async def get_error_patterns(user_id: str = Depends(get_current_user_id)):
    """Get the student's persistent error patterns and misconceptions."""
    return error_tracker.get_summary(user_id)


def _detect_emotion(text: str) -> Dict[str, Any]:
    text_lower = text.lower()
    emotions = {
        "engaged": 0.3,
        "confident": 0.15,
        "confused": 0.1,
        "frustrated": 0.05,
        "bored": 0.05,
        "excited": 0.15,
        "neutral": 0.2,
    }

    if any(w in text_lower for w in ["confused", "don't understand", "hard", "help"]):
        emotions["confused"] = 0.6
        emotions["frustrated"] = 0.2
        emotions["engaged"] = 0.1
    elif any(w in text_lower for w in ["awesome", "cool", "love", "fun", "excited", "great"]):
        emotions["excited"] = 0.5
        emotions["engaged"] = 0.3
    elif any(w in text_lower for w in ["boring", "bored", "tired", "whatever"]):
        emotions["bored"] = 0.5
        emotions["engaged"] = 0.1
    elif any(w in text_lower for w in ["?", "why", "how", "what"]):
        emotions["engaged"] = 0.5
        emotions["confused"] = 0.2

    primary = max(emotions, key=lambda k: emotions[k])
    return {
        "primary_emotion": primary,
        "confidence": emotions[primary],
        "distribution": emotions,
    }


__all__ = ["router"]
