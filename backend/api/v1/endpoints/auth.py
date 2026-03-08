"""
Authentication endpoints for NextGen AI Tutor
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator

from ...core.config import settings
from ...core.database import AsyncSession, get_db, User
from ...core.redis import redis_manager
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Pydantic models
class UserCreate(BaseModel):
    """User registration model"""
    email: EmailStr
    username: str
    full_name: str
    password: str
    role: str = "student"
    
    @validator("username")
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if len(v) > 100:
            raise ValueError("Username must be less than 100 characters")
        return v
    
    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v
    
    @validator("role")
    def validate_role(cls, v):
        if v not in ["student", "teacher", "admin"]:
            raise ValueError("Role must be student, teacher, or admin")
        return v

class UserLogin(BaseModel):
    """User login model"""
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    email: str
    role: str

class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""
    refresh_token: str

# Helper functions
def hash_password(password: str) -> str:
    """Hash password (placeholder - implement proper hashing)"""
    # TODO: Implement proper password hashing with bcrypt or argon2
    return f"hashed_{password}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password (placeholder)"""
    # TODO: Implement proper password verification
    return hashed_password == f"hashed_{plain_password}"

def create_access_token(user_id: str, email: str, role: str) -> str:
    """Create JWT access token (placeholder)"""
    # TODO: Implement proper JWT token creation
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return f"access_token_{user_id}"

def create_refresh_token(user_id: str) -> str:
    """Create JWT refresh token (placeholder)"""
    # TODO: Implement proper JWT token creation
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    }
    return f"refresh_token_{user_id}"

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token (placeholder)"""
    # TODO: Implement proper JWT token verification
    if token.startswith("access_token_"):
        user_id = token.replace("access_token_", "")
        return {
            "user_id": user_id,
            "email": f"{user_id}@example.com",
            "role": "student"
        }
    return None

# Endpoints
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    """
    try:
        # Check if user already exists
        result = await db.execute(
            select(User).where(
                (User.email == user_data.email) | (User.username == user_data.username)
            )
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email or username already exists"
            )
        
        # Create new user
        hashed_password = hash_password(user_data.password)
        
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            role=user_data.role,
            is_active=True,
            is_verified=False,
            preferences={},
            metadata_={"registration_source": "api"}
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Create tokens
        access_token = create_access_token(
            user_id=str(new_user.id),
            email=new_user.email,
            role=new_user.role
        )
        refresh_token = create_refresh_token(str(new_user.id))
        
        # Store refresh token in Redis
        await redis_manager.set_cache(
            f"refresh_token:{str(new_user.id)}",
            refresh_token,
            ttl=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
        )
        
        logger.info(f"New user registered: {new_user.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=str(new_user.id),
            email=new_user.email,
            role=new_user.role
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=TokenResponse)
async def login_user(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Login user and return tokens
    """
    try:
        # Find user by email
        result = await db.execute(
            select(User).where(User.email == login_data.email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        # Create tokens
        access_token = create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role
        )
        refresh_token = create_refresh_token(str(user.id))
        
        # Store refresh token in Redis
        await redis_manager.set_cache(
            f"refresh_token:{str(user.id)}",
            refresh_token,
            ttl=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
        )
        
        # Update last login (would need to add this field to User model)
        # user.last_login = datetime.now(timezone.utc)
        # await db.commit()
        
        logger.info(f"User logged in: {user.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=str(user.id),
            email=user.email,
            role=user.role
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest
):
    """
    Refresh access token using refresh token
    """
    try:
        # Verify refresh token (placeholder)
        # In real implementation, verify JWT signature and expiration
        if not refresh_request.refresh_token.startswith("refresh_token_"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = refresh_request.refresh_token.replace("refresh_token_", "")
        
        # Check if refresh token exists in Redis
        stored_token = await redis_manager.get_cache(f"refresh_token:{user_id}")
        
        if not stored_token or stored_token != refresh_request.refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Get user info (would need to fetch from database in real implementation)
        # For now, use mock data
        user_info = {
            "email": f"{user_id}@example.com",
            "role": "student"
        }
        
        # Create new access token
        access_token = create_access_token(
            user_id=user_id,
            email=user_info["email"],
            role=user_info["role"]
        )
        
        # Optionally rotate refresh token
        new_refresh_token = create_refresh_token(user_id)
        await redis_manager.set_cache(
            f"refresh_token:{user_id}",
            new_refresh_token,
            ttl=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
        )
        
        logger.info(f"Token refreshed for user: {user_id}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user_id,
            email=user_info["email"],
            role=user_info["role"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/logout")
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Logout user and invalidate tokens
    """
    try:
        # Verify access token
        token_data = verify_token(credentials.credentials)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user_id = token_data["user_id"]
        
        # Remove refresh token from Redis
        await redis_manager.delete_cache(f"refresh_token:{user_id}")
        
        # Add access token to blacklist (would need Redis blacklist implementation)
        # For now, just log the logout
        
        logger.info(f"User logged out: {user_id}")
        
        return {
            "message": "Successfully logged out"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.get("/me")
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user information
    """
    try:
        # Verify access token
        token_data = verify_token(credentials.credentials)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user_id = token_data["user_id"]
        
        # Get user from database
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
            "preferences": user.preferences
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )

# Export router
__all__ = ["router"]