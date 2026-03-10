"""
AI Model serving endpoints for NextGen AI Tutor
"""

import logging
import random
from typing import List, Dict, Any, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator

from ....core.config import settings
from ..auth import verify_token
from ....bkt_lite import bkt_lite

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


class BKTRequest(BaseModel):
    skill_id: str
    skill_name: str
    attempts: int
    successes: int
    previous_mastery: Optional[float] = None
    bkt_parameters: Optional[Dict[str, float]] = None

    @field_validator("previous_mastery")
    @classmethod
    def validate_mastery(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError("Mastery probability must be between 0 and 1")
        return v


class BKTResponse(BaseModel):
    skill_id: str
    skill_name: str
    mastery_probability: float
    attempts: int
    successes: int
    bkt_parameters: Dict[str, float]
    confidence: float
    recommendation: str


class EmotionRequest(BaseModel):
    text: Optional[str] = None
    source: str = "text"


class EmotionResponse(BaseModel):
    emotion: str
    confidence: float
    emotions_distribution: Dict[str, float]
    source: str
    metadata: Dict[str, Any]


class AdaptationRequest(BaseModel):
    user_id: str
    session_id: str
    current_topic: str
    current_difficulty: str
    performance_history: List[Dict[str, Any]]
    emotion_history: List[Dict[str, Any]]
    learning_style: Optional[str] = None


class AdaptationResponse(BaseModel):
    recommended_topic: str
    recommended_difficulty: str
    teaching_strategy: str
    pacing: str
    content_type: str
    confidence: float
    explanation: str


class ModelInfo(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_id: str
    model_name: str
    model_type: str
    version: str
    status: str
    accuracy: Optional[float] = None
    latency_ms: Optional[float] = None
    last_updated: str
    parameters: Dict[str, Any]


def mock_bkt_predict(skill_id, attempts, successes, previous_mastery=None, params=None):
    default_params = {"L0": 0.3, "T": 0.2, "G": 0.1, "S": 0.1}
    p = params or default_params
    mastery = previous_mastery if previous_mastery is not None else p.get("L0", 0.3)
    success_rate = successes / max(attempts, 1)
    mastery = mastery + (1 - mastery) * p.get("T", 0.2) * success_rate
    mastery = min(max(mastery, 0.0), 1.0)
    confidence = min(0.5 + attempts * 0.05, 0.99)
    if mastery >= 0.9:
        rec = "Mastered! Move to advanced topics."
    elif mastery >= 0.7:
        rec = "Good progress. Continue practicing."
    elif mastery >= 0.4:
        rec = "Keep practicing. Review weak areas."
    else:
        rec = "Needs more practice. Review fundamentals."
    return {
        "mastery_probability": round(mastery, 4),
        "parameters": p,
        "confidence": round(confidence, 4),
        "recommendation": rec
    }


def mock_emotion_detect(text=None):
    emotions = {
        "engaged": 0.35, "confident": 0.2, "confused": 0.1,
        "frustrated": 0.05, "bored": 0.05, "excited": 0.15,
        "neutral": 0.1
    }
    primary = max(emotions, key=emotions.get)
    return {
        "emotion": primary,
        "confidence": emotions[primary],
        "emotions_distribution": emotions,
    }


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token_data["user_id"]


@router.get("/info", response_model=List[ModelInfo])
async def get_models_info(user_id: str = Depends(get_current_user_id)):
    return [
        ModelInfo(
            model_id="bkt-v1", model_name="Bayesian Knowledge Tracing",
            model_type="knowledge_tracing", version="1.0.0", status="active",
            accuracy=0.85, latency_ms=15.0, last_updated="2026-03-08T00:00:00Z",
            parameters={"L0": 0.3, "T": 0.2, "G": 0.1, "S": 0.1}
        ),
        ModelInfo(
            model_id="emotion-v1", model_name="Emotion Detection",
            model_type="emotion_detection", version="1.0.0", status="active",
            accuracy=0.78, latency_ms=25.0, last_updated="2026-03-08T00:00:00Z",
            parameters={"model": "text-based", "classes": 7}
        ),
    ]


@router.post("/bkt/predict", response_model=BKTResponse)
async def predict_bkt(bkt_request: BKTRequest, user_id: str = Depends(get_current_user_id)):
    try:
        if bkt_request.bkt_parameters:
            bkt_lite.initialize_skill(
                bkt_request.skill_id,
                p_init=bkt_request.bkt_parameters.get("L0", 0.3),
                p_learn=bkt_request.bkt_parameters.get("T", 0.2),
                p_guess=bkt_request.bkt_parameters.get("G", 0.15),
                p_slip=bkt_request.bkt_parameters.get("S", 0.1),
            )

        for i in range(bkt_request.attempts):
            correct = i < bkt_request.successes
            bkt_result = bkt_lite.update(user_id, bkt_request.skill_id, correct=correct)

        if bkt_request.attempts == 0:
            mastery = bkt_lite.get_mastery(user_id, bkt_request.skill_id)
            bkt_result = {
                "skill": bkt_request.skill_id,
                "current_mastery": mastery,
                "total_attempts": 0,
                "correct_attempts": 0,
            }

        mastery = bkt_result["current_mastery"]
        confidence = min(0.5 + bkt_request.attempts * 0.05, 0.99)

        if mastery >= 0.9:
            rec = "Mastered! Move to advanced topics."
        elif mastery >= 0.7:
            rec = "Good progress. Continue practicing."
        elif mastery >= 0.4:
            rec = "Keep practicing. Review weak areas."
        else:
            rec = "Needs more practice. Review fundamentals."

        params = bkt_request.bkt_parameters or {"L0": 0.3, "T": 0.2, "G": 0.1, "S": 0.1}

        return BKTResponse(
            skill_id=bkt_request.skill_id,
            skill_name=bkt_request.skill_name,
            mastery_probability=round(mastery, 4),
            attempts=bkt_request.attempts,
            successes=bkt_request.successes,
            bkt_parameters=params,
            confidence=round(confidence, 4),
            recommendation=rec,
        )
    except Exception as e:
        logger.error(f"BKT prediction failed: {e}")
        raise HTTPException(status_code=500, detail="BKT prediction failed")


@router.post("/emotion/detect", response_model=EmotionResponse)
async def detect_emotion(emotion_request: EmotionRequest, user_id: str = Depends(get_current_user_id)):
    try:
        result = mock_emotion_detect(text=emotion_request.text)
        return EmotionResponse(
            emotion=result["emotion"],
            confidence=result["confidence"],
            emotions_distribution=result["emotions_distribution"],
            source=emotion_request.source,
            metadata={"model": "mock-v1", "source": emotion_request.source}
        )
    except Exception as e:
        logger.error(f"Emotion detection failed: {e}")
        raise HTTPException(status_code=500, detail="Emotion detection failed")


@router.post("/adapt", response_model=AdaptationResponse)
async def get_adaptation(adapt_request: AdaptationRequest, user_id: str = Depends(get_current_user_id)):
    difficulty_levels = ["beginner", "intermediate", "advanced", "expert"]
    current_idx = difficulty_levels.index(adapt_request.current_difficulty) if adapt_request.current_difficulty in difficulty_levels else 0
    avg_performance = 0.5
    if adapt_request.performance_history:
        scores = [p.get("score", 0.5) for p in adapt_request.performance_history]
        avg_performance = sum(scores) / len(scores)
    if avg_performance > 0.8 and current_idx < len(difficulty_levels) - 1:
        new_difficulty = difficulty_levels[current_idx + 1]
    elif avg_performance < 0.4 and current_idx > 0:
        new_difficulty = difficulty_levels[current_idx - 1]
    else:
        new_difficulty = adapt_request.current_difficulty

    return AdaptationResponse(
        recommended_topic=adapt_request.current_topic,
        recommended_difficulty=new_difficulty,
        teaching_strategy="interactive" if avg_performance > 0.6 else "guided",
        pacing="normal",
        content_type="mixed",
        confidence=0.75,
        explanation=f"Based on average performance of {avg_performance:.1%}, adjusting difficulty to {new_difficulty}."
    )


__all__ = ["router"]
