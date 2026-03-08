"""
Session management for AI tutoring sessions
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func

from ..core.database import (
    AsyncSessionLocal, 
    LearningSession, 
    SessionInteraction, 
    EmotionDetection,
    User
)
from ..core.redis import redis_manager

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages AI tutoring sessions"""
    
    def __init__(self):
        self.session_cache = {}
    
    @classmethod
    async def initialize(cls):
        """Initialize session manager"""
        logger.info("Session manager initialized")
    
    async def create_session(self, user_id: str, topic: str = "general", 
                           difficulty_level: str = "beginner") -> Dict[str, Any]:
        """Create a new learning session"""
        async with AsyncSessionLocal() as session:
            try:
                # Generate session token
                session_token = str(uuid.uuid4())
                
                # Create session in database
                db_session = LearningSession(
                    user_id=uuid.UUID(user_id),
                    session_token=session_token,
                    status="active",
                    start_time=datetime.now(timezone.utc),
                    topic=topic,
                    difficulty_level=difficulty_level,
                    ai_model_used="default_bkt_model",
                    metadata_={
                        "created_via": "websocket",
                        "topic": topic,
                        "difficulty": difficulty_level
                    }
                )
                
                session.add(db_session)
                await session.commit()
                await session.refresh(db_session)
                
                # Store in Redis for fast access
                session_data = {
                    "session_id": str(db_session.id),
                    "user_id": user_id,
                    "session_token": session_token,
                    "status": "active",
                    "start_time": db_session.start_time.isoformat(),
                    "topic": topic,
                    "difficulty_level": difficulty_level,
                    "interaction_count": 0,
                    "last_interaction": None
                }
                
                await redis_manager.set_session(
                    f"learning_session:{session_token}",
                    session_data,
                    ttl=86400  # 24 hours
                )
                
                # Track active session
                await redis_manager.track_active_session(user_id, session_token)
                
                logger.info(f"Created new session {session_token} for user {user_id}")
                
                return {
                    "session_id": str(db_session.id),
                    "session_token": session_token,
                    "status": "active",
                    "start_time": db_session.start_time,
                    "topic": topic,
                    "difficulty_level": difficulty_level
                }
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to create session for user {user_id}: {e}")
                raise
    
    async def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get session by token"""
        # Try Redis first
        session_data = await redis_manager.get_session(f"learning_session:{session_token}")
        
        if session_data:
            return session_data
        
        # Fall back to database
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(LearningSession).where(
                        LearningSession.session_token == session_token
                    )
                )
                db_session = result.scalar_one_or_none()
                
                if db_session:
                    session_data = {
                        "session_id": str(db_session.id),
                        "user_id": str(db_session.user_id),
                        "session_token": db_session.session_token,
                        "status": db_session.status,
                        "start_time": db_session.start_time.isoformat(),
                        "end_time": db_session.end_time.isoformat() if db_session.end_time else None,
                        "topic": db_session.topic,
                        "difficulty_level": db_session.difficulty_level,
                        "interaction_count": await self.get_interaction_count(str(db_session.id)),
                        "last_interaction": await self.get_last_interaction(str(db_session.id))
                    }
                    
                    # Cache in Redis
                    await redis_manager.set_session(
                        f"learning_session:{session_token}",
                        session_data,
                        ttl=3600
                    )
                    
                    return session_data
                
                return None
                
            except Exception as e:
                logger.error(f"Failed to get session {session_token}: {e}")
                return None
    
    async def resume_session(self, session_token: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Resume an existing session"""
        session_data = await self.get_session(session_token)
        
        if not session_data:
            return None
        
        # Verify user owns this session
        if session_data["user_id"] != user_id:
            logger.warning(f"User {user_id} attempted to access session owned by {session_data['user_id']}")
            return None
        
        # Update session status
        async with AsyncSessionLocal() as session:
            try:
                await session.execute(
                    update(LearningSession)
                    .where(LearningSession.session_token == session_token)
                    .values(
                        status="active",
                        updated_at=datetime.now(timezone.utc)
                    )
                )
                await session.commit()
                
                # Update Redis cache
                session_data["status"] = "active"
                session_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                
                await redis_manager.set_session(
                    f"learning_session:{session_token}",
                    session_data,
                    ttl=86400
                )
                
                logger.info(f"Resumed session {session_token} for user {user_id}")
                
                return session_data
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to resume session {session_token}: {e}")
                return None
    
    async def pause_session(self, session_token: str, user_id: str) -> bool:
        """Pause an active session"""
        session_data = await self.get_session(session_token)
        
        if not session_data or session_data["user_id"] != user_id:
            return False
        
        async with AsyncSessionLocal() as session:
            try:
                await session.execute(
                    update(LearningSession)
                    .where(LearningSession.session_token == session_token)
                    .values(
                        status="paused",
                        updated_at=datetime.now(timezone.utc)
                    )
                )
                await session.commit()
                
                # Update Redis cache
                session_data["status"] = "paused"
                session_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                
                await redis_manager.set_session(
                    f"learning_session:{session_token}",
                    session_data,
                    ttl=86400
                )
                
                logger.info(f"Paused session {session_token} for user {user_id}")
                
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to pause session {session_token}: {e}")
                return False
    
    async def end_session(self, session_token: str, user_id: str) -> bool:
        """End a session"""
        session_data = await self.get_session(session_token)
        
        if not session_data or session_data["user_id"] != user_id:
            return False
        
        async with AsyncSessionLocal() as session:
            try:
                end_time = datetime.now(timezone.utc)
                start_time = datetime.fromisoformat(session_data["start_time"].replace('Z', '+00:00'))
                duration = int((end_time - start_time).total_seconds())
                
                await session.execute(
                    update(LearningSession)
                    .where(LearningSession.session_token == session_token)
                    .values(
                        status="completed",
                        end_time=end_time,
                        duration_seconds=duration,
                        updated_at=end_time
                    )
                )
                await session.commit()
                
                # Remove from Redis cache
                await redis_manager.delete_session(f"learning_session:{session_token}")
                
                # Remove from active sessions
                await redis_manager.remove_active_session(user_id, session_token)
                
                # Calculate session analytics
                await self.calculate_session_analytics(session_token)
                
                logger.info(f"Ended session {session_token} for user {user_id}, duration: {duration}s")
                
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to end session {session_token}: {e}")
                return False
    
    async def add_interaction(self, session_id: str, interaction_type: str, 
                            content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add an interaction to a session"""
        async with AsyncSessionLocal() as session:
            try:
                # Get session
                result = await session.execute(
                    select(LearningSession).where(LearningSession.id == uuid.UUID(session_id))
                )
                db_session = result.scalar_one_or_none()
                
                if not db_session:
                    raise ValueError(f"Session {session_id} not found")
                
                # Create interaction
                interaction = SessionInteraction(
                    session_id=uuid.UUID(session_id),
                    timestamp=datetime.now(timezone.utc),
                    interaction_type=interaction_type,
                    content=content,
                    metadata_=metadata or {}
                )
                
                session.add(interaction)
                await session.commit()
                await session.refresh(interaction)
                
                # Update session in Redis if cached
                session_token = db_session.session_token
                session_data = await redis_manager.get_session(f"learning_session:{session_token}")
                
                if session_data:
                    session_data["interaction_count"] = session_data.get("interaction_count", 0) + 1
                    session_data["last_interaction"] = interaction.timestamp.isoformat()
                    await redis_manager.set_session(
                        f"learning_session:{session_token}",
                        session_data,
                        ttl=86400
                    )
                
                logger.info(f"Added {interaction_type} interaction to session {session_id}")
                
                return {
                    "id": str(interaction.id),
                    "session_id": session_id,
                    "timestamp": interaction.timestamp,
                    "interaction_type": interaction_type,
                    "content": content,
                    "metadata": metadata
                }
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to add interaction to session {session_id}: {e}")
                raise
    
    async def update_interaction(self, interaction_id: str, ai_response: str = None,
                               response_time_ms: int = None, confidence_score: float = None,
                               correctness: bool = None) -> bool:
        """Update an interaction with AI response data"""
        async with AsyncSessionLocal() as session:
            try:
                update_data = {
                    "updated_at": datetime.now(timezone.utc)
                }
                
                if ai_response is not None:
                    update_data["ai_response"] = ai_response
                if response_time_ms is not None:
                    update_data["response_time_ms"] = response_time_ms
                if confidence_score is not None:
                    update_data["confidence_score"] = confidence_score
                if correctness is not None:
                    update_data["correctness"] = correctness
                
                await session.execute(
                    update(SessionInteraction)
                    .where(SessionInteraction.id == uuid.UUID(interaction_id))
                    .values(**update_data)
                )
                await session.commit()
                
                logger.info(f"Updated interaction {interaction_id}")
                
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to update interaction {interaction_id}: {e}")
                return False
    
    async def add_emotion_detection(self, session_id: str, emotion: str, 
                                  confidence: float, source: str, 
                                  metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add emotion detection data to a session"""
        async with AsyncSessionLocal() as session:
            try:
                # Get session
                result = await session.execute(
                    select(LearningSession).where(LearningSession.id == uuid.UUID(session_id))
                )
                db_session = result.scalar_one_or_none()
                
                if not db_session:
                    raise ValueError(f"Session {session_id} not found")
                
                # Create emotion detection
                emotion_detection = EmotionDetection(
                    session_id=uuid.UUID(session_id),
                    timestamp=datetime.now(timezone.utc),
                    emotion=emotion,
                    confidence=confidence,
                    source=source,
                    metadata_=metadata or {}
                )
                
                session.add(emotion_detection)
                await session.commit()
                await session.refresh(emotion_detection)
                
                logger.info(f"Added emotion detection ({emotion}, {confidence}) to session {session_id}")
                
                return {
                    "id": str(emotion_detection.id),
                    "session_id": session_id,
                    "timestamp": emotion_detection.timestamp,
                    "emotion": emotion,
                    "confidence": confidence,
                    "source": source
                }
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to add emotion detection to session {session_id}: {e}")
                raise
    
    async def get_interaction_count(self, session_id: str) -> int:
        """Get number of interactions in a session"""
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(func.count(SessionInteraction.id))
                    .where(SessionInteraction.session_id == uuid.UUID(session_id))
                )
                count = result.scalar()
                return count or 0
                
            except Exception as e:
                logger.error(f"Failed to get interaction count for session {session_id}: {e}")
                return 0
    
    async def get_last_interaction(self, session_id: str) -> Optional[datetime]:
        """Get timestamp of last interaction in a session"""
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(SessionInteraction.timestamp)
                    .where(SessionInteraction.session_id == uuid.UUID(session_id))
                    .order_by(SessionInteraction.timestamp.desc())
                    .limit(1)
                )
                last_interaction = result.scalar_one_or_none()
                return last_interaction
                
            except Exception as e:
                logger.error(f"Failed to get last interaction for session {session_id}: {e}")
                return None
    
    async def get_session_interactions(self, session_id: str, limit: int = 100, 
                                     offset: int = 0) -> List[Dict[str, Any]]:
        """Get interactions for a session"""
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(SessionInteraction)
                    .where(SessionInteraction.session_id == uuid.UUID(session_id))
                    .order_by(SessionInteraction.timestamp.desc())
                    .limit(limit)
                    .offset(offset)
                )
                
                interactions = result.scalars().all()
                
                return [
                    {
                        "id": str(interaction.id),
                        "timestamp": interaction.timestamp,
                        "interaction_type": interaction.interaction_type,
                        "content": interaction.content,
                        "ai_response": interaction.ai_response,
                        "response_time_ms": interaction.response_time_ms,
                        "confidence_score": interaction.confidence_score,
                        "correctness": interaction.correctness,
                        "metadata": interaction.metadata_
                    }
                    for interaction in interactions
                ]
                
            except Exception as e:
                logger.error(f"Failed to get interactions for session {session_id}: {e}")
                return []
    
    async def get_session_emotions(self, session_id: str, limit: int = 100, 
                                 offset: int = 0) -> List[Dict[str, Any]]:
        """Get emotion detections for a session"""
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(EmotionDetection)
                    .where(EmotionDetection.session_id == uuid.UUID(session_id))
                    .order_by(EmotionDetection.timestamp.desc())
                    .limit(limit)
                    .offset(offset)
                )
                
                emotions = result.scalars().all()
                
                return [
                    {
                        "id": str(emotion.id),
                        "timestamp": emotion.timestamp,
                        "emotion": emotion.emotion,
                        "confidence": emotion.confidence,
                        "source": emotion.source,
                        "metadata": emotion.metadata_
                    }
                    for emotion in emotions
                ]
                
            except Exception as e:
                logger.error(f"Failed to get emotions for session {session_id}: {e}")
                return []
    
    async def calculate_session_analytics(self, session_token: str):
        """Calculate analytics for a completed session"""
        # TODO: Implement comprehensive session analytics
        # - Engagement metrics
        # - Learning effectiveness
        # - Emotion patterns
        # - Knowledge gaps
        pass
    
    async def get_user_sessions(self, user_id: str, limit: int = 50, 
                              offset: int = 0) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(LearningSession)
                    .where(LearningSession.user_id == uuid.UUID(user_id))
                    .order_by(LearningSession.start_time.desc())
                    .limit(limit)
                    .offset(offset)
                )
                
                sessions = result.scalars().all()
                
                return [
                    {
                        "id": str(db_session.id),
                        "session_token": db_session.session_token,
                        "status": db_session.status,
                        "start_time": db_session.start_time,
                        "end_time": db_session.end_time,
                        "duration_seconds": db_session.duration_seconds,
                        "topic": db_session.topic,
                        "difficulty_level": db_session.difficulty_level,
                        "interaction_count": await self.get_interaction_count(str(db_session.id))
                    }
                    for db_session in sessions
                ]
                
            except Exception as e:
                logger.error(f"Failed to get sessions for user {user_id}: {e}")
                return []

# Global session manager instance
session_manager = SessionManager()

# Export
__all__ = ["SessionManager", "session_manager"]