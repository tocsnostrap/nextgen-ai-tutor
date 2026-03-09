"""
Session management for AI tutoring sessions
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update, delete, and_, or_, func

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages AI tutoring sessions"""

    def __init__(self):
        self.session_cache = {}

    @classmethod
    async def initialize(cls):
        logger.info("Session manager initialized")

    async def create_session(self, user_id: str, topic: str = "general",
                           difficulty_level: str = "beginner") -> Dict[str, Any]:
        from ..core.database import _get_session_local, LearningSession
        from ..core.redis import redis_manager
        AsyncSessionLocal = _get_session_local()
        async with AsyncSessionLocal() as session:
            try:
                session_token = str(uuid.uuid4())
                db_session = LearningSession(
                    user_id=uuid.UUID(user_id) if isinstance(user_id, str) and len(user_id) > 10 else None,
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

                try:
                    await redis_manager.set_session(
                        f"learning_session:{session_token}",
                        session_data,
                        ttl=86400
                    )
                    await redis_manager.track_active_session(user_id, session_token)
                except Exception:
                    pass

                logger.info(f"Created new session {session_token} for user {user_id}")
                return session_data

            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to create session for user {user_id}: {e}")
                raise

    async def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        from ..core.database import _get_session_local, LearningSession
        from ..core.redis import redis_manager

        session_data = await redis_manager.get_session(f"learning_session:{session_token}")
        if session_data:
            return session_data

        AsyncSessionLocal = _get_session_local()
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
                        "interaction_count": 0,
                        "last_interaction": None
                    }
                    return session_data
                return None
            except Exception as e:
                logger.error(f"Failed to get session {session_token}: {e}")
                return None

    async def resume_session(self, session_token: str, user_id: str) -> Optional[Dict[str, Any]]:
        from ..core.database import _get_session_local, LearningSession
        from ..core.redis import redis_manager

        session_data = await self.get_session(session_token)
        if not session_data:
            return None
        if session_data["user_id"] != user_id:
            return None

        AsyncSessionLocal = _get_session_local()
        async with AsyncSessionLocal() as session:
            try:
                await session.execute(
                    update(LearningSession)
                    .where(LearningSession.session_token == session_token)
                    .values(status="active", updated_at=datetime.now(timezone.utc))
                )
                await session.commit()
                session_data["status"] = "active"
                return session_data
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to resume session {session_token}: {e}")
                return None

    async def pause_session(self, session_token: str, user_id: str) -> bool:
        from ..core.database import _get_session_local, LearningSession

        AsyncSessionLocal = _get_session_local()
        async with AsyncSessionLocal() as session:
            try:
                await session.execute(
                    update(LearningSession)
                    .where(LearningSession.session_token == session_token)
                    .values(status="paused", updated_at=datetime.now(timezone.utc))
                )
                await session.commit()
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to pause session {session_token}: {e}")
                return False

    async def end_session(self, session_token: str, user_id: str) -> bool:
        from ..core.database import _get_session_local, LearningSession

        AsyncSessionLocal = _get_session_local()
        async with AsyncSessionLocal() as session:
            try:
                end_time = datetime.now(timezone.utc)
                await session.execute(
                    update(LearningSession)
                    .where(LearningSession.session_token == session_token)
                    .values(
                        status="completed",
                        end_time=end_time,
                        updated_at=end_time
                    )
                )
                await session.commit()
                logger.info(f"Ended session {session_token}")
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to end session {session_token}: {e}")
                return False

    async def add_interaction(self, session_id: str, interaction_type: str,
                            content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        from ..core.database import _get_session_local, SessionInteraction

        AsyncSessionLocal = _get_session_local()
        async with AsyncSessionLocal() as session:
            try:
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
        from ..core.database import _get_session_local, SessionInteraction

        AsyncSessionLocal = _get_session_local()
        async with AsyncSessionLocal() as session:
            try:
                update_data = {"updated_at": datetime.now(timezone.utc)}
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
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to update interaction {interaction_id}: {e}")
                return False

    async def add_emotion_detection(self, session_id: str, emotion: str,
                                  confidence: float, source: str,
                                  metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        from ..core.database import _get_session_local, EmotionDetection

        AsyncSessionLocal = _get_session_local()
        async with AsyncSessionLocal() as session:
            try:
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
        from ..core.database import _get_session_local, SessionInteraction

        AsyncSessionLocal = _get_session_local()
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(func.count(SessionInteraction.id))
                    .where(SessionInteraction.session_id == uuid.UUID(session_id))
                )
                return result.scalar() or 0
            except Exception as e:
                logger.error(f"Failed to get interaction count: {e}")
                return 0

    async def get_last_interaction(self, session_id: str) -> Optional[datetime]:
        from ..core.database import _get_session_local, SessionInteraction

        AsyncSessionLocal = _get_session_local()
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(SessionInteraction.timestamp)
                    .where(SessionInteraction.session_id == uuid.UUID(session_id))
                    .order_by(SessionInteraction.timestamp.desc())
                    .limit(1)
                )
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"Failed to get last interaction: {e}")
                return None

    async def get_session_interactions(self, session_id: str, limit: int = 100,
                                     offset: int = 0) -> List[Dict[str, Any]]:
        from ..core.database import _get_session_local, SessionInteraction

        AsyncSessionLocal = _get_session_local()
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
                        "id": str(i.id),
                        "timestamp": i.timestamp,
                        "interaction_type": i.interaction_type,
                        "content": i.content,
                        "ai_response": i.ai_response,
                        "response_time_ms": i.response_time_ms,
                        "confidence_score": i.confidence_score,
                        "correctness": i.correctness,
                        "metadata": i.metadata_
                    }
                    for i in interactions
                ]
            except Exception as e:
                logger.error(f"Failed to get interactions: {e}")
                return []

    async def get_session_emotions(self, session_id: str, limit: int = 100,
                                 offset: int = 0) -> List[Dict[str, Any]]:
        from ..core.database import _get_session_local, EmotionDetection

        AsyncSessionLocal = _get_session_local()
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
                        "id": str(e.id),
                        "timestamp": e.timestamp,
                        "emotion": e.emotion,
                        "confidence": e.confidence,
                        "source": e.source,
                        "metadata": e.metadata_
                    }
                    for e in emotions
                ]
            except Exception as e:
                logger.error(f"Failed to get emotions: {e}")
                return []

    async def calculate_session_analytics(self, session_token: str):
        pass

    async def get_user_sessions(self, user_id: str, limit: int = 50,
                              offset: int = 0) -> List[Dict[str, Any]]:
        from ..core.database import _get_session_local, LearningSession

        AsyncSessionLocal = _get_session_local()
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
                        "id": str(s.id),
                        "session_token": s.session_token,
                        "status": s.status,
                        "start_time": s.start_time,
                        "end_time": s.end_time,
                        "duration_seconds": s.duration_seconds,
                        "topic": s.topic,
                        "difficulty_level": s.difficulty_level,
                    }
                    for s in sessions
                ]
            except Exception as e:
                logger.error(f"Failed to get sessions: {e}")
                return []


session_manager = SessionManager()

__all__ = ["SessionManager", "session_manager"]
