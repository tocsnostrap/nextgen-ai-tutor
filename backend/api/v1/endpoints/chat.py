import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..auth import verify_token
from ....conversational_ai import conversational_ai
from ....core.database import get_db, ChatMessage
from ....bkt_lite import bkt_lite
from ....ai_service import generate_tutor_response, generate_quiz_ai, generate_whiteboard_instructions
from ....unified_adaptive_engine import record_chat_interaction, get_ai_memory_prompt, get_adaptation_context

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

    ai_result = await generate_tutor_response(request.message, context, conversation_history)

    if ai_result:
        result = ai_result
    else:
        result = conversational_ai.generate_response(request.message, context)

    emotions = _detect_emotion(request.message)

    skill = result["concepts_covered"][0] if result.get("concepts_covered") else topic
    correct = result.get("difficulty_adjustment") != "decrease"
    bkt_update = bkt_lite.update(user_id, skill, correct)

    msg_metadata = {
        "topic": topic,
        "difficulty": difficulty,
        "emotion": emotion,
    }
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
        "adaptation": adaptation,
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


@router.post("/quiz")
async def generate_quiz(request: QuizRequest, user_id: str = Depends(get_current_user_id)):
    ai_quiz = await generate_quiz_ai(
        topic=request.topic,
        difficulty=request.difficulty,
        num_questions=request.num_questions,
        age=request.age,
    )

    if ai_quiz:
        return ai_quiz

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
