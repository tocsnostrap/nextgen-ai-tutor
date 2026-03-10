"""
Database configuration and models for NextGen AI Tutor
Uses PostgreSQL with asyncpg
"""

import logging
from typing import AsyncGenerator, Optional
from datetime import datetime, timezone

from sqlalchemy import (
    MetaData, Column, Integer, String,
    Float, Boolean, DateTime, Date, Text, JSON, ForeignKey,
    Index, UniqueConstraint, CheckConstraint, func, text
)
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def get_engine():
    from .config import settings
    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


_engine = None
_AsyncSessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


def _get_session_local():
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _AsyncSessionLocal


@property
def AsyncSessionLocal():
    return _get_session_local()


try:
    from sqlalchemy.dialects.postgresql import UUID, ARRAY
    PG_UUID = UUID(as_uuid=True)
    _has_pg = True
except Exception:
    _has_pg = False


class TimeStampedMixin:
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


class User(Base, TimeStampedMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="student")
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    preferences = Column(JSON, default=dict)
    metadata_ = Column("metadata", JSON, default=dict)

    sessions = relationship("LearningSession", back_populates="user", cascade="all, delete-orphan")
    progress = relationship("LearningProgress", back_populates="user", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        CheckConstraint("role IN ('student', 'teacher', 'admin')", name="ck_user_role"),
    )


class LearningSession(Base, TimeStampedMixin):
    __tablename__ = "learning_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(50), nullable=False, default="active")
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, default=0)
    topic = Column(String(255), nullable=False)
    difficulty_level = Column(String(50), nullable=False, default="beginner")
    ai_model_used = Column(String(100), nullable=False)
    metadata_ = Column("metadata", JSON, default=dict)

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


class SessionInteraction(Base, TimeStampedMixin):
    __tablename__ = "session_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    session_id = Column(UUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    interaction_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)
    correctness = Column(Boolean, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)

    session = relationship("LearningSession", back_populates="interactions")

    __table_args__ = (
        Index("idx_interactions_timestamp", "timestamp"),
        Index("idx_interactions_session_timestamp", "session_id", "timestamp"),
        CheckConstraint("interaction_type IN ('question', 'answer', 'explanation', 'hint', 'feedback')", name="ck_interaction_type"),
    )


class EmotionDetection(Base, TimeStampedMixin):
    __tablename__ = "emotion_detections"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    session_id = Column(UUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    emotion = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    source = Column(String(50), nullable=False)
    metadata_ = Column("metadata", JSON, default=dict)

    session = relationship("LearningSession", back_populates="emotions")

    __table_args__ = (
        Index("idx_emotions_timestamp", "timestamp"),
        Index("idx_emotions_session_emotion", "session_id", "emotion"),
        CheckConstraint("emotion IN ('happy', 'sad', 'confused', 'engaged', 'bored', 'frustrated', 'neutral', 'excited', 'anxious')", name="ck_emotion"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_confidence_range"),
    )


class LearningProgress(Base, TimeStampedMixin):
    __tablename__ = "learning_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(String(100), nullable=False, index=True)
    skill_name = Column(String(255), nullable=False)
    mastery_probability = Column(Float, nullable=False, default=0.0)
    attempts = Column(Integer, nullable=False, default=0)
    successes = Column(Integer, nullable=False, default=0)
    last_practice = Column(DateTime(timezone=True), nullable=True)
    bkt_parameters = Column(JSON, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)

    user = relationship("User", back_populates="progress")

    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),
        Index("idx_progress_user_skill", "user_id", "skill_id"),
        Index("idx_progress_mastery", "mastery_probability"),
        CheckConstraint("mastery_probability >= 0 AND mastery_probability <= 1", name="ck_mastery_range"),
        CheckConstraint("attempts >= 0", name="ck_attempts_nonnegative"),
    )


class Assessment(Base, TimeStampedMixin):
    __tablename__ = "assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_type = Column(String(50), nullable=False)
    topic = Column(String(255), nullable=False)
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=False)
    detailed_results = Column(JSON, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)

    user = relationship("User", back_populates="assessments")

    __table_args__ = (
        Index("idx_assessments_user_completed", "user_id", "completed_at"),
        Index("idx_assessments_topic_score", "topic", "score"),
        CheckConstraint("assessment_type IN ('quiz', 'test', 'exam', 'practice')", name="ck_assessment_type"),
        CheckConstraint("total_questions > 0", name="ck_total_questions_positive"),
        CheckConstraint("correct_answers >= 0 AND correct_answers <= total_questions", name="ck_correct_answers_range"),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_score_range"),
    )


class AnalyticsEvent(Base, TimeStampedMixin):
    __tablename__ = "analytics_events"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_time = Column(DateTime(timezone=True), nullable=False, index=True)
    event_data = Column(JSON, nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="SET NULL"), nullable=True)
    source = Column(String(50), nullable=False)

    __table_args__ = (
        Index("idx_analytics_event_time", "event_time"),
        Index("idx_analytics_user_event", "user_id", "event_type"),
    )


class GamificationProfile(Base, TimeStampedMixin):
    __tablename__ = "gamification_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(String(255), unique=True, nullable=False, index=True)
    xp = Column(Integer, default=0, nullable=False)
    streak = Column(Integer, default=0, nullable=False)
    longest_streak = Column(Integer, default=0, nullable=False)
    achievements_unlocked = Column(JSON, default=list)
    stats = Column(JSON, default=dict)
    last_active = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_gamification_user_id", "user_id"),
    )


class ChatMessage(Base, TimeStampedMixin):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, default=dict)

    __table_args__ = (
        Index("idx_chat_messages_user_session", "user_id", "session_id"),
    )


class VideoLesson(Base, TimeStampedMixin):
    __tablename__ = "video_lessons"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    title = Column(String(500), nullable=False)
    subject = Column(String(50), nullable=False, index=True)
    topic = Column(String(200), nullable=False)
    description = Column(Text, default="")
    video_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), default="")
    duration_seconds = Column(Integer, default=0)
    grade_min = Column(Integer, default=0)
    grade_max = Column(Integer, default=6)
    difficulty = Column(String(20), default="beginner")
    quiz_data = Column(JSON, default=dict)
    view_count = Column(Integer, default=0)


class VideoProgress(Base, TimeStampedMixin):
    __tablename__ = "video_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(String(255), nullable=False, index=True)
    video_id = Column(String(255), nullable=False, index=True)
    watched = Column(Boolean, default=False)
    watch_time_seconds = Column(Integer, default=0)
    quiz_score = Column(Float, nullable=True)
    xp_awarded = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_video_progress_user_video", "user_id", "video_id"),
    )


class LearningGoal(Base, TimeStampedMixin):
    __tablename__ = "learning_goals"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    parent_user_id = Column(String(255), nullable=False, index=True)
    child_user_id = Column(String(255), nullable=False, index=True)
    goal_type = Column(String(50), nullable=False)
    target_value = Column(Integer, nullable=False)
    current_value = Column(Integer, default=0)
    period = Column(String(20), default="daily")
    active = Column(Boolean, default=True)


class StudentAdaptiveProfile(Base, TimeStampedMixin):
    __tablename__ = "student_adaptive_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(String(255), unique=True, nullable=False, index=True)
    age = Column(Integer, default=8)
    mastery_scores = Column(JSON, default=dict)
    subject_enjoyment = Column(JSON, default=dict)
    topic_engagement = Column(JSON, default=dict)
    preferred_activities = Column(JSON, default=dict)
    learning_style = Column(String(50), default="visual")
    emotion_history = Column(JSON, default=list)
    session_stats = Column(JSON, default=dict)
    strengths = Column(JSON, default=list)
    struggles = Column(JSON, default=list)
    favorite_subjects = Column(JSON, default=list)
    recent_topics = Column(JSON, default=list)
    difficulty_level = Column(String(20), default="medium")
    total_sessions = Column(Integer, default=0)
    total_time_minutes = Column(Integer, default=0)
    avg_accuracy = Column(Float, default=0.5)
    current_streak = Column(Integer, default=0)


class LearningPathModel(Base, TimeStampedMixin):
    __tablename__ = "learning_path_enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(String(255), nullable=False, index=True)
    path_id = Column(String(100), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_milestones = Column(JSON, default=list)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    certificate_id = Column(String(100), nullable=True)

    __table_args__ = (
        Index("idx_learning_path_user_path", "user_id", "path_id"),
    )


class CurriculumStandard(Base, TimeStampedMixin):
    __tablename__ = "curriculum_standards"

    id = Column(String(100), primary_key=True)
    subject = Column(String(50), nullable=False, index=True)
    grade_level = Column(Integer, nullable=False, index=True)
    strand = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    learning_objectives = Column(JSON, default=list)
    estimated_hours = Column(Float, default=2.0)
    sequence_order = Column(Integer, default=0)
    prerequisites = Column(JSON, default=list)
    activity_types = Column(JSON, default=list)

    __table_args__ = (
        Index("idx_curriculum_subject_grade", "subject", "grade_level"),
    )


class DailySchedule(Base, TimeStampedMixin):
    __tablename__ = "daily_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(String(255), nullable=False, index=True)
    schedule_date = Column(Date, nullable=False)
    blocks = Column(JSON, default=list)
    total_planned_minutes = Column(Integer, default=0)
    total_completed_minutes = Column(Integer, default=0)
    created_by = Column(String(20), default="ai")

    __table_args__ = (
        UniqueConstraint("user_id", "schedule_date", name="uq_schedule_user_date"),
    )


class SubjectTimeLog(Base, TimeStampedMixin):
    __tablename__ = "subject_time_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(String(255), nullable=False, index=True)
    subject = Column(String(50), nullable=False)
    log_date = Column(Date, nullable=False)
    seconds_spent = Column(Integer, default=0)
    activity_type = Column(String(50), default="lesson")

    __table_args__ = (
        Index("idx_timelog_user_date", "user_id", "log_date"),
    )


class ProgressReport(Base, TimeStampedMixin):
    __tablename__ = "progress_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(String(255), nullable=False, index=True)
    report_period = Column(String(20), nullable=False)
    grade_equivalencies = Column(JSON, default=dict)
    standards_mastered = Column(JSON, default=list)
    standards_in_progress = Column(JSON, default=list)
    total_hours = Column(JSON, default=dict)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    ai_summary = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "report_period", name="uq_report_user_period"),
    )


class ChildInterestProfile(Base):
    """Tracks what each child is passionate about — built automatically from enthusiasm signals."""
    __tablename__ = "child_interest_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(String(255), unique=True, nullable=False, index=True)

    # Detected passion topics: [{topic, emoji, score, subject_area, first_seen, last_seen, count}]
    passion_topics = Column(JSON, default=list)

    # Child-added custom interests: [{topic, emoji, added_at}]
    custom_interests = Column(JSON, default=list)

    # Things the child has discovered/learned: [{concept, subject, emoji, short_desc, discovered_at}]
    discoveries = Column(JSON, default=list)

    # Nova's memory notes about this child: ["loves dinosaurs", "gets excited about space"]
    nova_memory = Column(JSON, default=list)

    # Recent enthusiasm signals (rolling 100): [{topic, signal, message_snippet, detected_at}]
    enthusiasm_log = Column(JSON, default=list)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_factory = _get_session_local()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    engine = _get_engine()
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


__all__ = [
    "Base",
    "get_db",
    "init_db",
    "User",
    "LearningSession",
    "SessionInteraction",
    "EmotionDetection",
    "LearningProgress",
    "Assessment",
    "AnalyticsEvent",
    "GamificationProfile",
    "ChatMessage",
    "VideoLesson",
    "VideoProgress",
    "LearningGoal",
    "StudentAdaptiveProfile",
    "LearningPathModel",
    "CurriculumStandard",
    "DailySchedule",
    "SubjectTimeLog",
    "ProgressReport",
    "ChildInterestProfile",
    "_get_engine",
    "_get_session_local",
]
