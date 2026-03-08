"""
Analytics endpoints for NextGen AI Tutor
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db, User, LearningSession, SessionInteraction, EmotionDetection, LearningProgress, Assessment, AnalyticsEvent
from ..auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Pydantic models
class LearningAnalytics(BaseModel):
    """Learning analytics response model"""
    user_id: str
    period: str
    total_sessions: int
    total_interactions: int
    total_learning_time_seconds: int
    average_session_duration_seconds: float
    topics_covered: List[str]
    skill_mastery: Dict[str, float]
    engagement_score: float
    emotion_distribution: Dict[str, int]
    assessment_scores: Dict[str, float]

class SystemAnalytics(BaseModel):
    """System analytics response model (admin only)"""
    period: str
    total_users: int
    active_users: int
    total_sessions: int
    active_sessions: int
    total_interactions: int
    average_response_time_ms: float
    system_load: Dict[str, float]
    error_rate: float
    popular_topics: List[Dict[str, Any]]

class TimeSeriesData(BaseModel):
    """Time series data point"""
    timestamp: str
    value: float
    label: Optional[str] = None

class AnalyticsRequest(BaseModel):
    """Analytics request model"""
    start_date: str
    end_date: str
    metrics: List[str]
    group_by: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

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

async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> str:
    """Require admin role"""
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    if token_data["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return token_data["user_id"]

def parse_date_range(period: str) -> tuple[datetime, datetime]:
    """Parse period string into date range"""
    now = datetime.now(timezone.utc)
    
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif period == "yesterday":
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif period == "week":
        start_date = now - timedelta(days=7)
        end_date = now
    elif period == "month":
        start_date = now - timedelta(days=30)
        end_date = now
    elif period == "quarter":
        start_date = now - timedelta(days=90)
        end_date = now
    elif period == "year":
        start_date = now - timedelta(days=365)
        end_date = now
    else:
        # Default to last 7 days
        start_date = now - timedelta(days=7)
        end_date = now
    
    return start_date, end_date

# Endpoints
@router.get("/learning", response_model=LearningAnalytics)
async def get_learning_analytics(
    period: str = Query("week", description="Time period: today, yesterday, week, month, quarter, year"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get learning analytics for current user
    """
    try:
        # Parse date range
        start_date, end_date = parse_date_range(period)
        
        # Get user sessions in period
        sessions_query = select(LearningSession).where(
            and_(
                LearningSession.user_id == user_id,
                LearningSession.start_time >= start_date,
                LearningSession.start_time <= end_date
            )
        )
        
        sessions_result = await db.execute(sessions_query)
        sessions = sessions_result.scalars().all()
        
        # Calculate metrics
        total_sessions = len(sessions)
        total_learning_time = sum(s.duration_seconds or 0 for s in sessions)
        average_session_duration = total_learning_time / total_sessions if total_sessions > 0 else 0
        
        # Get unique topics
        topics_covered = list(set(s.topic for s in sessions))
        
        # Get total interactions
        total_interactions = 0
        for session in sessions:
            interactions_query = select(func.count(SessionInteraction.id)).where(
                SessionInteraction.session_id == session.id
            )
            interactions_result = await db.execute(interactions_query)
            total_interactions += interactions_result.scalar() or 0
        
        # Get skill mastery
        progress_query = select(LearningProgress).where(
            LearningProgress.user_id == user_id
        )
        progress_result = await db.execute(progress_query)
        progress_records = progress_result.scalars().all()
        
        skill_mastery = {
            record.skill_id: record.mastery_probability
            for record in progress_records
        }
        
        # Get emotion distribution
        emotion_distribution = {}
        for session in sessions:
            emotions_query = select(EmotionDetection).where(
                EmotionDetection.session_id == session.id
            )
            emotions_result = await db.execute(emotions_query)
            emotions = emotions_result.scalars().all()
            
            for emotion in emotions:
                emotion_distribution[emotion.emotion] = emotion_distribution.get(emotion.emotion, 0) + 1
        
        # Get assessment scores
        assessments_query = select(Assessment).where(
            and_(
                Assessment.user_id == user_id,
                Assessment.completed_at >= start_date,
                Assessment.completed_at <= end_date
            )
        )
        assessments_result = await db.execute(assessments_query)
        assessments = assessments_result.scalars().all()
        
        assessment_scores = {}
        for assessment in assessments:
            if assessment.topic not in assessment_scores:
                assessment_scores[assessment.topic] = []
            assessment_scores[assessment.topic].append(assessment.score)
        
        # Calculate average scores per topic
        avg_assessment_scores = {
            topic: sum(scores) / len(scores)
            for topic, scores in assessment_scores.items()
        }
        
        # Calculate engagement score (simplified)
        engagement_score = 0.0
        if total_sessions > 0:
            # Factor 1: Session frequency
            days_in_period = (end_date - start_date).days or 1
            session_frequency = total_sessions / days_in_period
            
            # Factor 2: Session duration
            avg_duration_score = min(average_session_duration / 1800, 1.0)  # 30 minutes max
            
            # Factor 3: Interaction density
            interactions_per_session = total_interactions / total_sessions if total_sessions > 0 else 0
            interaction_density = min(interactions_per_session / 20, 1.0)  # 20 interactions per session max
            
            engagement_score = (session_frequency * 0.3 + avg_duration_score * 0.4 + interaction_density * 0.3) * 100
        
        return LearningAnalytics(
            user_id=user_id,
            period=period,
            total_sessions=total_sessions,
            total_interactions=total_interactions,
            total_learning_time_seconds=total_learning_time,
            average_session_duration_seconds=average_session_duration,
            topics_covered=topics_covered,
            skill_mastery=skill_mastery,
            engagement_score=engagement_score,
            emotion_distribution=emotion_distribution,
            assessment_scores=avg_assessment_scores
        )
        
    except Exception as e:
        logger.error(f"Failed to get learning analytics for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get learning analytics"
        )

@router.get("/system", response_model=SystemAnalytics)
async def get_system_analytics(
    period: str = Query("day", description="Time period: today, yesterday, week, month"),
    admin_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get system analytics (admin only)
    """
    try:
        # Parse date range
        start_date, end_date = parse_date_range(period)
        
        # Get total users
        total_users_query = select(func.count(User.id))
        total_users_result = await db.execute(total_users_query)
        total_users = total_users_result.scalar() or 0
        
        # Get active users (users with sessions in period)
        active_users_query = select(func.count(func.distinct(LearningSession.user_id))).where(
            and_(
                LearningSession.start_time >= start_date,
                LearningSession.start_time <= end_date
            )
        )
        active_users_result = await db.execute(active_users_query)
        active_users = active_users_result.scalar() or 0
        
        # Get total sessions in period
        total_sessions_query = select(func.count(LearningSession.id)).where(
            and_(
                LearningSession.start_time >= start_date,
                LearningSession.start_time <= end_date
            )
        )
        total_sessions_result = await db.execute(total_sessions_query)
        total_sessions = total_sessions_result.scalar() or 0
        
        # Get active sessions (sessions started but not ended)
        active_sessions_query = select(func.count(LearningSession.id)).where(
            and_(
                LearningSession.start_time >= start_date,
                LearningSession.status == "active"
            )
        )
        active_sessions_result = await db.execute(active_sessions_query)
        active_sessions = active_sessions_result.scalar() or 0
        
        # Get total interactions in period
        total_interactions_query = select(func.count(SessionInteraction.id)).where(
            and_(
                SessionInteraction.timestamp >= start_date,
                SessionInteraction.timestamp <= end_date
            )
        )
        total_interactions_result = await db.execute(total_interactions_query)
        total_interactions = total_interactions_result.scalar() or 0
        
        # Get average response time
        avg_response_time_query = select(func.avg(SessionInteraction.response_time_ms)).where(
            and_(
                SessionInteraction.timestamp >= start_date,
                SessionInteraction.timestamp <= end_date,
                SessionInteraction.response_time_ms.isnot(None)
            )
        )
        avg_response_time_result = await db.execute(avg_response_time_query)
        avg_response_time = avg_response_time_result.scalar() or 0
        
        # Get popular topics
        popular_topics_query = select(
            LearningSession.topic,
            func.count(LearningSession.id).label("session_count"),
            func.avg(LearningSession.duration_seconds).label("avg_duration")
        ).where(
            and_(
                LearningSession.start_time >= start_date,
                LearningSession.start_time <= end_date
            )
        ).group_by(LearningSession.topic).order_by(func.count(LearningSession.id).desc()).limit(10)
        
        popular_topics_result = await db.execute(popular_topics_query)
        popular_topics = [
            {
                "topic": row.topic,
                "session_count": row.session_count,
                "average_duration_seconds": row.avg_duration or 0
            }
            for row in popular_topics_result
        ]
        
        # Get error rate from analytics events
        error_events_query = select(func.count(AnalyticsEvent.id)).where(
            and_(
                AnalyticsEvent.event_time >= start_date,
                AnalyticsEvent.event_time <= end_date,
                AnalyticsEvent.event_type.like("%error%")
            )
        )
        error_events_result = await db.execute(error_events_query)
        error_events = error_events_result.scalar() or 0
        
        total_events_query = select(func.count(AnalyticsEvent.id)).where(
            and_(
                AnalyticsEvent.event_time >= start_date,
                AnalyticsEvent.event_time <= end_date
            )
        )
        total_events_result = await db.execute(total_events_query)
        total_events = total_events_result.scalar() or 1  # Avoid division by zero
        
        error_rate = (error_events / total_events) * 100
        
        # System load (simplified - would need actual system metrics)
        system_load = {
            "database_connections": 0,  # TODO: Implement
            "redis_memory_used_mb": 0,  # TODO: Implement
            "api_request_rate": 0,  # TODO: Implement
            "websocket_connections": 0  # TODO: Implement
        }
        
        return SystemAnalytics(
            period=period,
            total_users=total_users,
            active_users=active_users,
            total_sessions=total_sessions,
            active_sessions=active_sessions,
            total_interactions=total_interactions,
            average_response_time_ms=avg_response_time,
            system_load=system_load,
            error_rate=error_rate,
            popular_topics=popular_topics
        )
        
    except Exception as e:
        logger.error(f"Failed to get system analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system analytics"
        )

@router.get("/timeseries")
async def get_time_series_data(
    metric: str = Query(..., description="Metric to track: sessions, interactions, users, assessments"),
    period: str = Query("week", description="Time period: day, week, month, quarter"),
    interval: str = Query("day", description="Time interval: hour, day, week, month"),
    user_id: Optional[str] = Query(None, description="Filter by user ID (admin only)"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get time series data for analytics
    """
    try:
        # Check permissions if filtering by user_id
        if user_id and user_id != current_user_id:
            # Check if current user is admin
            user_query = select(User).where(User.id == current_user_id)
            user_result = await db.execute(user_query)
            current_user = user_result.scalar_one_or_none()
            
            if not current_user or current_user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot access other user's analytics"
                )
        
        # Parse date range
        start_date, end_date = parse_date_range(period)
        
        # Determine time bucket based on interval
        if interval == "hour":
            time_bucket = "1 hour"
            date_trunc = "hour"
        elif interval == "day":
            time_bucket = "1 day"
            date_trunc = "day"
        elif interval == "week":
            time_bucket = "1 week"
            date_trunc = "week"
        elif interval == "month":
            time_bucket = "1 month"
            date_trunc = "month"
        else:
            time_bucket = "1 day"
            date_trunc = "day"
        
        # Build query based on metric
        time_series_data = []
        
        if metric == "sessions":
            # Get sessions over time
            query = text(f"""
                SELECT 
                    time_bucket('{time_bucket}', start_time) as bucket,
                    COUNT(*) as count,
                    AVG(duration_seconds) as avg_duration
                FROM learning_sessions
                WHERE start_time >= :start_date 
                    AND start_time <= :end_date
                    {"AND user_id = :user_id" if user_id else ""}
                GROUP BY bucket
                ORDER BY bucket
            """)
            
            params = {"start_date": start_date, "end_date": end_date}
            if user_id:
                params["user_id"] = user_id
            
            result = await db.execute(query, params)
            rows = result.fetchall()
            
            time_series_data = [
                TimeSeriesData(
                    timestamp=row.bucket.isoformat(),
                    value=float(row.count),
                    label=f"Sessions: {row.count}, Avg Duration: {row.avg_duration or 0:.0f}s"
                )
                for row in rows
            ]
        
        elif metric == "interactions":
            # Get interactions over time
            query = text(f"""
                SELECT 
                    time_bucket('{time_bucket}', timestamp) as bucket,
                    COUNT(*) as count,
                    AVG(response_time_ms) as avg_response_time
                FROM session_interactions
                WHERE timestamp >= :start_date 
                    AND timestamp <= :end_date
                GROUP BY bucket
                ORDER BY bucket
            """)
            
            result = await db.execute(query, {"start_date": start_date, "end_date": end_date})
            rows = result.fetchall()
            
            time_series_data = [
                TimeSeriesData(
                    timestamp=row.bucket.isoformat(),
                    value=float(row.count),
                    label=f"Interactions: {row.count}, Avg Response: {row.avg_response_time or 0:.0f}ms"
                )
                for row in rows
            ]
        
        elif metric == "users":
            # Get user