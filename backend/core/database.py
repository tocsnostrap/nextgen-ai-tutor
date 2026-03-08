"""
Database configuration and models for NextGen AI Tutor
Uses PostgreSQL with TimescaleDB for time-series data
"""

import logging
from typing import AsyncGenerator, Optional
from datetime import datetime, timezone

from sqlalchemy import (
    create_engine, MetaData, Column, Integer, String, 
    Float, Boolean, DateTime, Text, JSON, ForeignKey,
    Index, UniqueConstraint, CheckConstraint, func
)
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, declared_attr
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from .config import settings

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for all models
Base = declarative_base()

class TimeStampedModel:
    """Mixin for adding created_at and updated_at timestamps"""
    
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

class User(Base, TimeStampedModel):
    """User model for students and teachers"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="student")  # student, teacher, admin
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    preferences = Column(JSON, default=dict)
    metadata_ = Column("metadata", JSON, default=dict)
    
    # Relationships
    sessions = relationship("LearningSession", back_populates="user", cascade="all, delete-orphan")
    progress = relationship("LearningProgress", back_populates="user", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        CheckConstraint("role IN ('student', 'teacher', 'admin')", name="ck_user_role"),
    )

class LearningSession(Base, TimeStampedModel):
    """Learning session model for real-time interactions"""
    __tablename__ = "learning_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(50), nullable=False, default="active")  # active, paused, completed, terminated
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, default=0)
    topic = Column(String(255), nullable=False)
    difficulty_level = Column(String(50), nullable=False, default="beginner")
    ai_model_used = Column(String(100), nullable=False)
    metadata_ = Column("metadata", JSON, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    interactions = relationship("SessionInteraction", back_populates="session", cascade="all, delete-orphan")
    emotions = relationship("EmotionDetection", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_sessions_user_status", "user_id", "status"),
        Index("idx_sessions_start_time", "start_time"),
        Index("idx_sessions_topic", "topic"),
        CheckConstraint("status IN ('active', 'paused', 'completed', 'terminated')", name="ck_session_status"),
        CheckConstraint("difficulty_level IN ('beginner', 'intermediate', 'advanced', 'expert')", name="ck_difficulty_level"),
    )

class SessionInteraction(Base, TimeStampedModel):
    """Individual interactions within a learning session"""
    __tablename__ = "session_interactions"
    __table_args__ = (
        # TimescaleDB hypertable for time-series data
        {"postgresql_partition_by": "RANGE (timestamp)"},
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    session_id = Column(UUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    interaction_type = Column(String(50), nullable=False)  # question, answer, explanation, hint, feedback
    content = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)
    correctness = Column(Boolean, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    
    # Relationships
    session = relationship("LearningSession", back_populates="interactions")
    
    __table_args__ = (
        Index("idx_interactions_timestamp", "timestamp"),
        Index("idx_interactions_session_timestamp", "session_id", "timestamp"),
        CheckConstraint("interaction_type IN ('question', 'answer', 'explanation', 'hint', 'feedback')", name="ck_interaction_type"),
    )

class EmotionDetection(Base, TimeStampedModel):
    """Emotion detection data during learning sessions"""
    __tablename__ = "emotion_detections"
    __table_args__ = (
        # TimescaleDB hypertable for time-series data
        {"postgresql_partition_by": "RANGE (timestamp)"},
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    session_id = Column(UUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    emotion = Column(String(50), nullable=False)  # happy, sad, confused, engaged, bored, frustrated
    confidence = Column(Float, nullable=False)
    source = Column(String(50), nullable=False)  # audio, video, text
    metadata_ = Column("metadata", JSON, default=dict)
    
    # Relationships
    session = relationship("LearningSession", back_populates="emotions")
    
    __table_args__ = (
        Index("idx_emotions_timestamp", "timestamp"),
        Index("idx_emotions_session_emotion", "session_id", "emotion"),
        CheckConstraint("emotion IN ('happy', 'sad', 'confused', 'engaged', 'bored', 'frustrated', 'neutral', 'excited', 'anxious')", name="ck_emotion"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_confidence_range"),
    )

class LearningProgress(Base, TimeStampedModel):
    """Learning progress tracking using BKT (Bayesian Knowledge Tracing)"""
    __tablename__ = "learning_progress"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(String(100), nullable=False, index=True)
    skill_name = Column(String(255), nullable=False)
    mastery_probability = Column(Float, nullable=False, default=0.0)
    attempts = Column(Integer, nullable=False, default=0)
    successes = Column(Integer, nullable=False, default=0)
    last_practice = Column(DateTime(timezone=True), nullable=True)
    bkt_parameters = Column(JSON, nullable=True)  # L0, T, G, S parameters
    metadata_ = Column("metadata", JSON, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="progress")
    
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),
        Index("idx_progress_user_skill", "user_id", "skill_id"),
        Index("idx_progress_mastery", "mastery_probability"),
        CheckConstraint("mastery_probability >= 0 AND mastery_probability <= 1", name="ck_mastery_range"),
        CheckConstraint("attempts >= 0", name="ck_attempts_nonnegative"),
        CheckConstraint("successes >= 0 AND successes <= attempts", name="ck_successes_range"),
    )

class Assessment(Base, TimeStampedModel):
    """Assessment results and quizzes"""
    __tablename__ = "assessments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_type = Column(String(50), nullable=False)  # quiz, test, exam, practice
    topic = Column(String(255), nullable=False)
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=False)
    detailed_results = Column(JSON, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="assessments")
    
    __table_args__ = (
        Index("idx_assessments_user_completed", "user_id", "completed_at"),
        Index("idx_assessments_topic_score", "topic", "score"),
        CheckConstraint("assessment_type IN ('quiz', 'test', 'exam', 'practice')", name="ck_assessment_type"),
        CheckConstraint("total_questions > 0", name="ck_total_questions_positive"),
        CheckConstraint("correct_answers >= 0 AND correct_answers <= total_questions", name="ck_correct_answers_range"),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_score_range"),
    )

class AnalyticsEvent(Base, TimeStampedModel):
    """Analytics events for learning insights"""
    __tablename__ = "analytics_events"
    __table_args__ = (
        # TimescaleDB hypertable for time-series analytics
        {"postgresql_partition_by": "RANGE (event_time)"},
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_time = Column(DateTime(timezone=True), nullable=False, index=True)
    event_data = Column(JSON, nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="SET NULL"), nullable=True)
    source = Column(String(50), nullable=False)  # web, mobile, api
    
    __table_args__ = (
        Index("idx_analytics_event_time", "event_time"),
        Index("idx_analytics_user_event", "user_id", "event_type"),
    )

# Database dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """
    Initialize database - create tables and set up TimescaleDB
    """
    try:
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
            # Create TimescaleDB hypertables if they don't exist
            await conn.execute(
                """
                SELECT create_hypertable(
                    'session_interactions', 
                    'timestamp',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 day'
                )
                """
            )
            await conn.execute(
                """
                SELECT create_hypertable(
                    'emotion_detections', 
                    'timestamp',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 day'
                )
                """
            )
            await conn.execute(
                """
                SELECT create_hypertable(
                    'analytics_events', 
                    'event_time',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 day'
                )
                """
            )
            
            # Create indexes for better query performance
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_interactions_session_timestamp_desc 
                ON session_interactions (session_id, timestamp DESC)
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_emotions_session_timestamp_desc 
                ON emotion_detections (session_id, timestamp DESC)
                """
            )
            
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

# Export
__all__ = [
    "Base",
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "init_db",
    "User",
    "LearningSession",
    "SessionInteraction",
    "EmotionDetection",
    "LearningProgress",
    "Assessment",
    "AnalyticsEvent",
]