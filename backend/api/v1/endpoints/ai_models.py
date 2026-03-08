"""
AI Model serving endpoints for NextGen AI Tutor
"""

import logging
from typing import List, Dict, Any, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, validator
import numpy as np

from ...core.config import settings
from ..auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Pydantic models
class BKTRequest(BaseModel):
    """BKT (Bayesian Knowledge Tracing) request model"""
    skill_id: str
    skill_name: str
    attempts: int
    successes: int
    previous_mastery: Optional[float] = None
    bkt_parameters: Optional[Dict[str, float]] = None
    
    @validator("previous_mastery")
    def validate_mastery(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError("Mastery probability must be between 0 and 1")
        return v
    
    @validator("attempts")
    def validate_attempts(cls, v):
        if v < 0:
            raise ValueError("Attempts cannot be negative")
        return v
    
    @validator("successes")
    def validate_successes(cls, v, values):
        if "attempts" in values and v > values["attempts"]:
            raise ValueError("Successes cannot exceed attempts")
        return v

class BKTResponse(BaseModel):
    """BKT response model"""
    skill_id: str
    skill_name: str
    mastery_probability: float
    attempts: int
    successes: int
    bkt_parameters: Dict[str, float]
    confidence: float
    recommendation: str

class EmotionRequest(BaseModel):
    """Emotion detection request model"""
    text: Optional[str] = None
    audio_features: Optional[List[float]] = None
    video_features: Optional[List[float]] = None
    source: str = "text"
    
    @validator("source")
    def validate_source(cls, v):
        valid_sources = ["text", "audio", "video", "multimodal"]
        if v not in valid_sources:
            raise ValueError(f"Source must be one of: {', '.join(valid_sources)}")
        return v
    
    @validator("audio_features")
    def validate_audio_features(cls, v):
        if v is not None and len(v) != 128:  # Example feature size
            raise ValueError("Audio features must be 128-dimensional vector")
        return v
    
    @validator("video_features")
    def validate_video_features(cls, v):
        if v is not None and len(v) != 256:  # Example feature size
            raise ValueError("Video features must be 256-dimensional vector")
        return v

class EmotionResponse(BaseModel):
    """Emotion detection response model"""
    emotion: str
    confidence: float
    emotions_distribution: Dict[str, float]
    source: str
    metadata: Dict[str, Any]

class AdaptationRequest(BaseModel):
    """Adaptation request model"""
    user_id: str
    session_id: str
    current_topic: str
    current_difficulty: str
    performance_history: List[Dict[str, Any]]
    emotion_history: List[Dict[str, Any]]
    learning_style: Optional[str] = None

class AdaptationResponse(BaseModel):
    """Adaptation response model"""
    recommended_topic: str
    recommended_difficulty: str
    teaching_strategy: str
    pacing: str
    content_type: str
    confidence: float
    explanation: str

class ModelInfo(BaseModel):
    """AI model information"""
    model_id: str
    model_name: str
    model_type: str
    version: str
    status: str
    accuracy: Optional[float] = None
    latency_ms: Optional[float] = None
    last_updated: str
    parameters: Dict[str, Any]

# Mock AI models (in production, these would connect to actual model servers)
class MockBKTTModel:
    """Mock BKT model for demonstration"""
    
    def __init__(self):
        self.default_params = {
            "L0": 0.3,  # Initial probability of knowing the skill
            "T": 0.2,   # Probability of learning the skill
            "G": 0.1,   # Probability of guessing correctly
            "S": 0.1    # Probability of slipping (incorrect when known)
        }
    
    def predict(self, skill_id: str, attempts: int, successes: int, 
                previous_mastery: float = None, params: Dict[str, float] = None) -> Dict[str, Any]:
        """Predict mastery probability using BKT"""
        
        # Use provided parameters or defaults
        params = params or self.default_params
        L0 = params.get("L0", 0.3)
        T = params.get("T", 0.2)
        G = params.get("G", 0.1)
        S = params.get("S", 0.1)
        
        # Start with initial mastery or previous mastery
        if previous_mastery is not None:
            current_mastery = previous_mastery
        else:
            current_mastery = L0
        
        # Simulate BKT updates based on attempts
        for i in range(attempts):
            # Determine if this attempt was a success
            is_success = i < successes
            
            if is_success:
                # Success: P(know) * (1 - S) / [P(know) * (1 - S) + (1 - P(know)) * G]
                numerator = current_mastery * (1 - S)
                denominator = numerator + (1 - current_mastery) * G
                if denominator > 0:
                    current_mastery = numerator / denominator
            else:
                # Failure: P(know) * S / [P(know) * S + (1 - P(know)) * (1 - G)]
                numerator = current_mastery * S
                denominator = numerator + (1 - current_mastery) * (1 - G)
                if denominator > 0:
                    current_mastery = numerator / denominator
            
            # Learning occurs whether success or failure
            current_mastery = current_mastery + (1 - current_mastery) * T
        
        # Calculate confidence based on number of attempts
        confidence = min(attempts / 10, 1.0)  # More attempts = more confidence
        
        # Generate recommendation
        if current_mastery >= 0.8:
            recommendation = "Mastered. Ready for next skill."
        elif current_mastery >= 0.6:
            recommendation = "Proficient. Practice with variations."
        elif current_mastery >= 0.4:
            recommendation = "Developing. Continue practice."
        elif current_mastery >= 0.2:
            recommendation = "Beginning. Needs more foundational practice."
        else:
            recommendation = "Novice. Start with basics."
        
        return {
            "mastery_probability": round(current_mastery, 4),
            "confidence": round(confidence, 4),
            "recommendation": recommendation,
            "parameters": params
        }

class MockEmotionModel:
    """Mock emotion detection model for demonstration"""
    
    def __init__(self):
        self.emotions = ["happy", "sad", "confused", "engaged", "bored", "frustrated", "neutral", "excited", "anxious"]
        
    def predict_from_text(self, text: str) -> Dict[str, Any]:
        """Predict emotion from text"""
        # Simple keyword-based emotion detection
        text_lower = text.lower()
        
        emotion_scores = {
            "happy": 0.1,
            "sad": 0.1,
            "confused": 0.1,
            "engaged": 0.1,
            "bored": 0.1,
            "frustrated": 0.1,
            "neutral": 0.1,
            "excited": 0.1,
            "anxious": 0.1
        }
        
        # Update scores based on keywords
        happy_keywords = ["good", "great", "excellent", "love", "enjoy", "fun"]
        sad_keywords = ["bad", "terrible", "hate", "sad", "upset", "disappointed"]
        confused_keywords = ["confused", "don't understand", "what", "how", "why", "help"]
        engaged_keywords = ["interesting", "fascinating", "learn", "understand", "clear", "yes"]
        bored_keywords = ["boring", "tired", "sleepy", "repeat", "again", "monotonous"]
        frustrated_keywords = ["frustrated", "angry", "annoyed", "difficult", "hard", "stuck"]
        excited_keywords = ["excited", "wow", "amazing", "cool", "awesome", "fantastic"]
        anxious_keywords = ["nervous", "anxious", "worried", "scared", "afraid", "pressure"]
        
        for keyword in happy_keywords:
            if keyword in text_lower:
                emotion_scores["happy"] += 0.3
                
        for keyword in sad_keywords:
            if keyword in text_lower:
                emotion_scores["sad"] += 0.3
                
        for keyword in confused_keywords:
            if keyword in text_lower:
                emotion_scores["confused"] += 0.3
                
        for keyword in engaged_keywords:
            if keyword in text_lower:
                emotion_scores["engaged"] += 0.3
                
        for keyword in bored_keywords:
            if keyword in text_lower:
                emotion_scores["bored"] += 0.3
                
        for keyword in frustrated_keywords:
            if keyword in text_lower:
                emotion_scores["frustrated"] += 0.3
                
        for keyword in excited_keywords:
            if keyword in text_lower:
                emotion_scores["excited"] += 0.3
                
        for keyword in anxious_keywords:
            if keyword in text_lower:
                emotion_scores["anxious"] += 0.3
        
        # Normalize scores
        total = sum(emotion_scores.values())
        if total > 0:
            emotion_scores = {k: v/total for k, v in emotion_scores.items()}
        
        # Get dominant emotion
        dominant_emotion = max(emotion_scores.items(), key=lambda x: x[1])
        
        return {
            "emotion": dominant_emotion[0],
            "confidence": round(dominant_emotion[1], 4),
            "emotions_distribution": {k: round(v, 4) for k, v in emotion_scores.items()},
            "metadata": {
                "text_length": len(text),
                "has_question": "?" in text,
                "has_exclamation": "!" in text
            }
        }
    
    def predict_from_audio(self, features: List[float]) -> Dict[str, Any]:
        """Predict emotion from audio features (mock)"""
        # In real implementation, this would use actual audio processing
        return {
            "emotion": "neutral",
            "confidence": 0.7,
            "emotions_distribution": {"neutral": 0.7, "happy": 0.2, "sad": 0.1},
            "metadata": {"feature_dim": len(features), "source": "audio"}
        }
    
    def predict_from_video(self, features: List[float]) -> Dict[str, Any]:
        """Predict emotion from video features (mock)"""
        # In real implementation, this would use actual video processing
        return {
            "emotion": "engaged",
            "confidence": 0.65,
            "emotions_distribution": {"engaged": 0.65, "neutral": 0.25, "confused": 0.1},
            "metadata": {"feature_dim": len(features), "source": "video"}
        }

class MockAdaptationModel:
    """Mock adaptation model for personalized learning"""
    
    def predict(self, request: AdaptationRequest) -> Dict[str, Any]:
        """Generate personalized learning adaptations"""
        
        # Analyze performance history
        if request.performance_history:
            recent_performance = request.performance_history[-5:]  # Last 5 interactions
            success_rate = sum(1 for p in recent_performance if p.get("correct", False)) / len(recent_performance)
        else:
            success_rate = 0.5
        
        # Analyze emotion history
        if request.emotion_history:
            recent_emotions = [e.get("emotion", "neutral") for e in request.emotion_history[-5:]]
            dominant_emotion = max(set(recent_emotions), key=recent_emotions.count)
        else:
            dominant_emotion = "neutral"
        
        # Determine difficulty adjustment
        if success_rate >= 0.8:
            # High success: increase difficulty
            if request.current_difficulty == "beginner":
                recommended_difficulty = "intermediate"
            elif request.current_difficulty == "intermediate":
                recommended_difficulty = "advanced"
            elif request.current_difficulty == "advanced":
                recommended_difficulty = "expert"
            else:
                recommended_difficulty = "expert"
        elif success_rate <= 0.4:
            # Low success: decrease difficulty
            if request.current_difficulty == "expert":
                recommended_difficulty = "advanced"
            elif request.current_difficulty == "advanced":
                recommended_difficulty = "intermediate"
            elif request.current_difficulty == "intermediate":
                recommended_difficulty = "beginner"
            else:
                recommended_difficulty = "beginner"
        else:
            # Moderate success: maintain difficulty
            recommended_difficulty = request.current_difficulty
        
        # Determine teaching strategy based on emotion and learning style
        if dominant_emotion == "confused" or dominant_emotion == "frustrated":
            teaching_strategy = "scaffolded"
            pacing = "slow"
            content_type = "visual" if request.learning_style == "visual" else "step_by_step"
        elif dominant_emotion == "bored":
            teaching_strategy = "challenge_based"
            pacing = "fast"
            content_type = "interactive"
        elif dominant_emotion == "engaged" or dominant_emotion == "excited":
            teaching_strategy = "exploratory"
            pacing = "moderate"
            content_type = "project_based"
        else:
            teaching_strategy = "direct_instruction"
            pacing = "moderate"
            content_type = "mixed"
        
        # Determine topic (in real implementation, this would use knowledge graph)
        recommended_topic = request.current_topic
        
        # Generate explanation
        explanation = f"Based on your recent performance ({success_rate*100:.0f}% success rate) "
        explanation += f"and emotional state ({dominant_emotion}), "
        explanation += f"we recommend {recommended_difficulty} difficulty with {teaching_strategy} teaching."
        
        return {
            "recommended_topic": recommended_topic,
            "recommended_difficulty": recommended_difficulty,
            "teaching_strategy": teaching_strategy,
            "pacing": pacing,
            "content_type": content_type,
            "confidence": 0.75,
            "explanation": explanation
        }

# Initialize mock models
bkt_model = MockBKTTModel()
emotion_model = MockEmotionModel()
adaptation_model = MockAdaptationModel()

# Helper functions
async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Get current user ID from token"""
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return token_data["user_id"]

# Endpoints
@router.post("/bkt/predict", response_model=BKTResponse)
async def predict_bkt(
    bkt_request: BKTRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Predict mastery probability using Bayesian Knowledge Tracing
    """
    try:
        # Call BKT model
        result = bkt_model.predict(
            skill_id=bkt_request.skill_id,
            attempts=bkt_request.attempts,
            successes=bkt_request.successes,
            previous_mastery=bkt_request.previous_mastery,
            params=bkt_request.bkt_parameters
        )
        
        return BKTResponse(
            skill_id=bkt_request.skill_id,
            skill_name=bkt_request.skill_name,
            mastery_probability=result["mastery_probability"],
            attempts=bkt_request.attempts,
            successes=bkt_request.successes,
            bkt_parameters=result["parameters"],
            confidence=result["confidence"],
            recommendation=result["recommendation"]
        )
        
    except Exception as e:
        logger.error(f"BKT prediction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="BKT prediction failed"
        )

@router.post("/emotion/detect", response_model=EmotionResponse)
async def detect_emotion(
    emotion_request: EmotionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Detect emotion from text, audio, or video
    """
    try:
        # Route to appropriate model based on source
        if emotion_request.source == "text" and emotion_request.text:
            result = emotion_model.predict_from_text(emotion_request.text)
            source = "text"
        elif emotion_request.source == "audio" and emotion_request.audio_features:
            result = emotion_model.predict_from_audio(emotion_request.audio_features)
            source = "audio"
        elif emotion_request.source == "video" and emotion_request.video_features:
            result = emotion_model.predict_from_video(emotion_request.video_features)
            source = "video"
        elif emotion_request.source == "multimodal":
            # In real implementation