"""
User management endpoints for NextGen AI Tutor
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db, User, LearningSession, LearningProgress, Assessment
from ...core.redis import redis_manager
from ..auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Pydantic models
class UserUpdate(BaseModel):
    """User update model"""
    full_name: Optional[str] = None
    username: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    
    @validator("username")
    def validate_username(cls, v):
        if v is not None:
            if len(v) < 3:
                raise ValueError("Username must be at least 3 characters long")
            if len(v) > 100:
                raise ValueError("Username must be less than 100 characters")
        return v

class UserResponse(BaseModel):
    """User response model"""
    id: str
    email: str
    username: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: str
    updated_at: str
    preferences: Dict[str, Any]

class UserProgressResponse(BaseModel):
    """User learning progress response"""
    skill_id: str
    skill_name: str
    mastery_probability: float
    attempts: int
    successes: int
    last_practice: Optional[str]
    bkt_parameters: Optional[Dict[str, Any]]

class UserSessionResponse(BaseModel):
    """User session response"""
    id: str
    session_token: str
    status: str
    start_time: str
    end_time: Optional[str]
    duration_seconds: Optional[int]
    topic: str
    difficulty_level: str
    interaction_count: int

class UserAssessmentResponse(BaseModel):
    """User assessment response"""
    id: str
    assessment_type: str
    topic: str
    total_questions: int
    correct_answers: int
    score: float
    duration_seconds: int
    completed_at: str

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

# Endpoints
@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    role: Optional[str] = Query(None, description="Filter by role"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    admin_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all users (admin only)
    """
    try:
        query = select(User)
        
        # Apply filters
        if role:
            query = query.where(User.role == role)
        if active is not None:
            query = query.where(User.is_active == active)
        
        # Apply pagination
        query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        users = result.scalars().all()
        
        return [
            UserResponse(
                id=str(user.id),
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                role=user.role,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at.isoformat(),
                updated_at=user.updated_at.isoformat(),
                preferences=user.preferences
            )
            for user in users
        ]
        
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get users"
        )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str = Path(..., description="User ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user by ID (users can only get their own info unless admin)
    """
    try:
        # Check permissions
        if user_id != current_user_id:
            # Check if current user is admin
            result = await db.execute(
                select(User).where(User.id == current_user_id)
            )
            current_user = result.scalar_one_or_none()
            
            if not current_user or current_user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot access other user's information"
                )
        
        # Get user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
            preferences=user.preferences
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user"
        )

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_update: UserUpdate,
    user_id: str = Path(..., description="User ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user information
    """
    try:
        # Check permissions
        if user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update other user's information"
            )
        
        # Get user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check username uniqueness if updating username
        if user_update.username and user_update.username != user.username:
            result = await db.execute(
                select(User).where(
                    and_(
                        User.username == user_update.username,
                        User.id != user_id
                    )
                )
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Prepare update data
        update_data = {}
        if user_update.full_name is not None:
            update_data["full_name"] = user_update.full_name
        if user_update.username is not None:
            update_data["username"] = user_update.username
        if user_update.preferences is not None:
            update_data["preferences"] = user_update.preferences
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data provided for update"
            )
        
        # Update user
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(**update_data)
        )
        await db.commit()
        
        # Get updated user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        updated_user = result.scalar_one_or_none()
        
        logger.info(f"User updated: {user_id}")
        
        return UserResponse(
            id=str(updated_user.id),
            email=updated_user.email,
            username=updated_user.username,
            full_name=updated_user.full_name,
            role=updated_user.role,
            is_active=updated_user.is_active,
            is_verified=updated_user.is_verified,
            created_at=updated_user.created_at.isoformat(),
            updated_at=updated_user.updated_at.isoformat(),
            preferences=updated_user.preferences
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )

@router.delete("/{user_id}")
async def delete_user(
    user_id: str = Path(..., description="User ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user (users can only delete themselves unless admin)
    """
    try:
        # Check permissions
        if user_id != current_user_id:
            # Check if current user is admin
            result = await db.execute(
                select(User).where(User.id == current_user_id)
            )
            current_user = result.scalar_one_or_none()
            
            if not current_user or current_user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot delete other users"
                )
        
        # Get user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Soft delete: deactivate user instead of hard delete
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=False)
        )
        await db.commit()
        
        # Clear user sessions from Redis
        await redis_manager.clear_pattern(f"user:{user_id}:*")
        
        logger.info(f"User deactivated: {user_id}")
        
        return {
            "message": "User deactivated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )

@router.get("/{user_id}/progress", response_model=List[UserProgressResponse])
async def get_user_progress(
    user_id: str = Path(..., description="User ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    skill_id: Optional[str] = Query(None, description="Filter by skill ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user learning progress
    """
    try:
        # Check permissions
        if user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access other user's progress"
            )
        
        query = select(LearningProgress).where(LearningProgress.user_id == user_id)
        
        if skill_id:
            query = query.where(LearningProgress.skill_id == skill_id)
        
        query = query.order_by(LearningProgress.updated_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        progress_records = result.scalars().all()
        
        return [
            UserProgressResponse(
                skill_id=record.skill_id,
                skill_name=record.skill_name,
                mastery_probability=record.mastery_probability,
                attempts=record.attempts,
                successes=record.successes,
                last_practice=record.last_practice.isoformat() if record.last_practice else None,
                bkt_parameters=record.bkt_parameters
            )
            for record in progress_records
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user progress for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user progress"
        )

@router.get("/{user_id}/sessions", response_model=List[UserSessionResponse])
async def get_user_sessions(
    user_id: str = Path(..., description="User ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    status: Optional[str] = Query(None, description="Filter by session status"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user learning sessions
    """
    try:
        # Check permissions
        if user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access other user's sessions"
            )
        
        query = select(LearningSession).where(LearningSession.user_id == user_id)
        
        if status:
            query = query.where(LearningSession.status == status)
        if topic:
            query = query.where(LearningSession.topic.ilike(f"%{topic}%"))
        
        query = query.order_by(LearningSession.start_time.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        sessions = result.scalars().all()
        
        # Get interaction counts
        from ...models.session import session_manager
        session_responses = []
        
        for session in sessions:
            interaction_count = await session_manager.get_interaction_count(str(session.id))
            
            session_responses.append(
                UserSessionResponse(
                    id=str(session.id),
                    session_token=session.session_token,
                    status=session.status,
                    start_time=session.start_time.isoformat(),
                    end_time=session.end_time.isoformat() if session.end_time else None,
                    duration_seconds=session.duration_seconds,
                    topic=session.topic,
                    difficulty_level=session.difficulty_level,
                    interaction_count=interaction_count
                )
            )
        
        return session_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user sessions for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user sessions"
        )

@router.get("/{user_id}/assessments", response_model=List[UserAssessmentResponse])
async def get_user_assessments(
    user_id: str = Path(..., description="User ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    assessment_type: Optional[str] = Query(None, description="Filter by assessment type"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user assessments
    """
    try:
        # Check permissions
        if user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access other user's assessments"
            )
        
        query = select(Assessment).where(Assessment.user_id == user_id)
        
        if assessment_type:
            query = query.where(Assessment.assessment_type == assessment_type)
        if topic:
            query = query.where(Assessment.topic.ilike(f"%{topic}%"))
        
        query = query.order_by(Assessment.completed_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        assessments = result.scalars().all()
        
        return [
            UserAssessmentResponse(
                id=str(assessment.id),
                assessment_type=assessment.assessment_type,
                topic=assessment.topic,
                total_questions=assessment.total_questions,
                correct_answers=assessment.correct_answers,
                score=assessment.score,
                duration_seconds=assessment.duration_seconds,
                completed_at=assessment.completed_at.isoformat()
            )
            for assessment in assessments
        ]
        
    except HTTPException:
        raise
