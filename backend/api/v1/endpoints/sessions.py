"""
Session management endpoints for NextGen AI Tutor
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, validator
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db, LearningSession, SessionInteraction, EmotionDetection
from ...models.session import session_manager
from ..auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Pydantic models
class SessionCreate(BaseModel):
    """Session creation model"""
    topic: str = "general"
    difficulty_level: str = "beginner"
    
    @validator("difficulty_level")
    def validate_difficulty(cls, v):
        valid_levels = ["beginner", "intermediate", "advanced", "expert"]
        if v not in valid_levels:
            raise ValueError(f"Difficulty level must be one of: {', '.join(valid_levels)}")
        return v

class SessionResponse(BaseModel):
    """Session response model"""
    session_id: str
    session_token: str
    status: str
    start_time: str
    end_time: Optional[str]
    duration_seconds: Optional[int]
    topic: str
    difficulty_level: str
    ai_model_used: str
    interaction_count: int
    last_interaction: Optional[str]
    metadata: Dict[str, Any]

class InteractionResponse(BaseModel):
    """Interaction response model"""
    id: str
    timestamp: str
    interaction_type: str
    content: str
    ai_response: Optional[str]
    response_time_ms: Optional[int]
    confidence_score: Optional[float]
    correctness: Optional[bool]
    metadata: Dict[str, Any]

class EmotionResponse(BaseModel):
    """Emotion detection response model"""
    id: str
    timestamp: str
    emotion: str
    confidence: float
    source: str
    metadata: Dict[str, Any]

class SessionAnalytics(BaseModel):
    """Session analytics model"""
    session_id: str
    total_interactions: int
    total_emotions: int
    average_response_time_ms: Optional[float]
    correctness_rate: Optional[float]
    emotion_distribution: Dict[str, int]
    engagement_score: float
    start_time: str
    end_time: Optional[str]
    duration_seconds: Optional[int]

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

async def verify_session_ownership(
    session_token: str,
    user_id: str,
    db: AsyncSession
) -> LearningSession:
    """Verify that user owns the session"""
    result = await db.execute(
        select(LearningSession).where(
            and_(
                LearningSession.session_token == session_token,
                LearningSession.user_id == user_id
            )
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )
    
    return session

# Endpoints
@router.post("/", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new learning session
    """
    try:
        # Create session using session manager
        session = await session_manager.create_session(
            user_id=user_id,
            topic=session_data.topic,
            difficulty_level=session_data.difficulty_level
        )
        
        # Get session details from database
        result = await db.execute(
            select(LearningSession).where(
                LearningSession.session_token == session["session_token"]
            )
        )
        db_session = result.scalar_one_or_none()
        
        if not db_session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session"
            )
        
        # Get interaction count
        interaction_count = await session_manager.get_interaction_count(str(db_session.id))
        last_interaction = await session_manager.get_last_interaction(str(db_session.id))
        
        return SessionResponse(
            session_id=str(db_session.id),
            session_token=db_session.session_token,
            status=db_session.status,
            start_time=db_session.start_time.isoformat(),
            end_time=db_session.end_time.isoformat() if db_session.end_time else None,
            duration_seconds=db_session.duration_seconds,
            topic=db_session.topic,
            difficulty_level=db_session.difficulty_level,
            ai_model_used=db_session.ai_model_used,
            interaction_count=interaction_count,
            last_interaction=last_interaction.isoformat() if last_interaction else None,
            metadata=db_session.metadata_
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create session for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session"
        )

@router.get("/", response_model=List[SessionResponse])
async def get_sessions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    status: Optional[str] = Query(None, description="Filter by session status"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's learning sessions
    """
    try:
        # Get sessions using session manager
        sessions = await session_manager.get_user_sessions(
            user_id=user_id,
            limit=limit,
            offset=skip
        )
        
        # Filter by status and topic if provided
        filtered_sessions = sessions
        
        if status:
            filtered_sessions = [s for s in filtered_sessions if s["status"] == status]
        
        if topic:
            filtered_sessions = [s for s in filtered_sessions if topic.lower() in s["topic"].lower()]
        
        # Get detailed session information
        session_responses = []
        
        for session in filtered_sessions:
            # Get session from database for full details
            result = await db.execute(
                select(LearningSession).where(
                    LearningSession.session_token == session["session_token"]
                )
            )
            db_session = result.scalar_one_or_none()
            
            if db_session:
                session_responses.append(
                    SessionResponse(
                        session_id=str(db_session.id),
                        session_token=db_session.session_token,
                        status=db_session.status,
                        start_time=db_session.start_time.isoformat(),
                        end_time=db_session.end_time.isoformat() if db_session.end_time else None,
                        duration_seconds=db_session.duration_seconds,
                        topic=db_session.topic,
                        difficulty_level=db_session.difficulty_level,
                        ai_model_used=db_session.ai_model_used,
                        interaction_count=session["interaction_count"],
                        last_interaction=None,  # Would need to fetch this
                        metadata=db_session.metadata_
                    )
                )
        
        return session_responses
        
    except Exception as e:
        logger.error(f"Failed to get sessions for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sessions"
        )

@router.get("/{session_token}", response_model=SessionResponse)
async def get_session(
    session_token: str = Path(..., description="Session token"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get session by token
    """
    try:
        # Verify session ownership
        session = await verify_session_ownership(session_token, user_id, db)
        
        # Get session details
        session_data = await session_manager.get_session(session_token)
        
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return SessionResponse(
            session_id=session_data["session_id"],
            session_token=session_data["session_token"],
            status=session_data["status"],
            start_time=session_data["start_time"],
            end_time=session_data["end_time"],
            duration_seconds=session.duration_seconds,
            topic=session_data["topic"],
            difficulty_level=session_data["difficulty_level"],
            ai_model_used=session.ai_model_used,
            interaction_count=session_data.get("interaction_count", 0),
            last_interaction=session_data.get("last_interaction"),
            metadata=session.metadata_
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_token}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session"
        )

@router.post("/{session_token}/pause")
async def pause_session(
    session_token: str = Path(..., description="Session token"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Pause a session
    """
    try:
        # Verify session ownership
        await verify_session_ownership(session_token, user_id, db)
        
        # Pause session
        success = await session_manager.pause_session(session_token, user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to pause session"
            )
        
        return {
            "message": "Session paused successfully",
            "session_token": session_token,
            "status": "paused"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause session {session_token}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause session"
        )

@router.post("/{session_token}/resume")
async def resume_session(
    session_token: str = Path(..., description="Session token"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Resume a paused session
    """
    try:
        # Resume session using session manager
        session_data = await session_manager.resume_session(session_token, user_id)
        
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or cannot be resumed"
            )
        
        return {
            "message": "Session resumed successfully",
            "session_token": session_token,
            "status": "active"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume session {session_token}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume session"
        )

@router.post("/{session_token}/end")
async def end_session(
    session_token: str = Path(..., description="Session token"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    End a session
    """
    try:
        # Verify session ownership
        await verify_session_ownership(session_token, user_id, db)
        
        # End session
        success = await session_manager.end_session(session_token, user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to end session"
            )
        
        return {
            "message": "Session ended successfully",
            "session_token": session_token,
            "status": "completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to end session {session_token}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to end session"
        )

@router.get("/{session_token}/interactions", response_model=List[InteractionResponse])
async def get_session_interactions(
    session_token: str = Path(..., description="Session token"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Number of records to return"),
    interaction_type: Optional[str] = Query(None, description="Filter by interaction type"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get session interactions
    """
    try:
        # Verify session ownership
        session = await verify_session_ownership(session_token, user_id, db)
        
        # Get interactions
        interactions = await session_manager.get_session_interactions(
            session_id=str(session.id),
            limit=limit,
            offset=skip
        )
        
        # Filter by type if provided
        if interaction_type:
            interactions = [i for i in interactions if i["interaction_type"] == interaction_type]
        
        return [
            InteractionResponse(
                id=interaction["id"],
                timestamp=interaction["timestamp"].isoformat(),
                interaction_type=interaction["interaction_type"],
                content=interaction["content"],
                ai_response=interaction.get("ai_response"),
                response_time_ms=interaction.get("response_time_ms"),
                confidence_score=interaction.get("confidence_score"),
                correctness=interaction.get("correctness"),
                metadata=interaction.get("metadata", {})
            )
            for interaction in interactions
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get interactions for session {session_token}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session interactions"
        )

@router.get("/{session_token}/emotions", response_model=List[EmotionResponse])
async def get_session_emotions(
    session_token: str = Path(..., description="Session token"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Number of records to return"),
    emotion: Optional[str] = Query(None, description="Filter by emotion"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get session emotion detections
    """
    try:
        # Verify session ownership
        session = await verify_session_ownership(session_token, user_id, db)
        
        # Get emotions
        emotions = await session_manager.get_session_emotions(
            session_id=str(session.id),
            limit=limit,
            offset=skip
        )
        
        # Filter by emotion if provided
        if emotion:
            emotions = [e for e in emotions if e["emotion"] == emotion]
        
        return [
            EmotionResponse(
                id=emotion_data["id"],
                timestamp=emotion_data["timestamp"].isoformat(),
                emotion=emotion_data["emotion"],
                confidence=emotion_data["confidence"],
                source=emotion_data["source"],
                metadata=emotion_data.get("metadata", {})
            )
            for emotion_data in emotions
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get emotions for session {session_token}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session emotions"
        )

@router.get("/{session_token}/analytics", response_model=SessionAnalytics)
async def get_session_analytics(
    session_token: str = Path(..., description="Session token"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get session analytics
    """
    try:
        # Verify session ownership
        session = await verify_session_ownership(session_token, user_id, db)
        
        # Get interactions
        interactions = await session_manager.get_session_interactions(
            session_id=str(session.id),
            limit=1000  # Get all interactions for analytics
        )
        
        # Get emotions
        emotions = await session_manager.get_session_emotions(
            session_id=str(session.id),
            limit=1000  # Get all emotions for analytics
        )
        
        # Calculate analytics
        total_interactions = len(interactions)
        total_emotions = len(emotions)
        
        # Calculate average response time
        response_times = [i.get("response_time_ms") for i in interactions if i.get("response_time_ms")]
        average_response_time = sum(response_times) / len(response_times) if response_times else None
        
        # Calculate correctness rate
        correctness_values = [i.get("correctness") for i in interactions if i.get("correctness") is not None]
        if correctness_values:
            correctness_rate = sum(1 for c in correctness_values if c) / len(correctness_values)
        else:
            correctness_rate = None
        
        # Calculate emotion distribution
        emotion_distribution = {}
        for emotion_data in emotions:
            emotion = emotion_data["emotion"]
            emotion_distribution[emotion] = emotion_distribution.get(emotion, 0) + 1
        
        # Calculate engagement score (simplified)
        engagement_score = 0.0
        if total_interactions > 0:
            # Base score on interaction frequency