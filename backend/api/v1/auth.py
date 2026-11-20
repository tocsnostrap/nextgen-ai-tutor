import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.database import get_db

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"

security = HTTPBearer()


def create_access_token(user_id: str, email: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_child_token(child_id: str, parent_id: str) -> str:
    """Token for a child's session. `sub` is the child id; it carries no email."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": child_id,
        "parent": parent_id,
        "role": "child",
        "exp": now + timedelta(hours=settings.CHILD_SESSION_HOURS),
        "iat": now,
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": now,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def _decode(token: str, expected_type: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token: %s", e)
        return None
    if payload.get("type") != expected_type:
        return None
    return payload


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    payload = _decode(token, "access")
    if not payload:
        return None
    return {
        "user_id": payload["sub"],
        "email": payload.get("email", ""),
        "role": payload.get("role", "student"),
        "parent_id": payload.get("parent"),
    }


def verify_refresh_token(token: str) -> Optional[str]:
    payload = _decode(token, "refresh")
    return payload["sub"] if payload else None


def _token_data(credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token_data


async def current_child_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> str:
    """The signed-in child. Every learner endpoint depends on this, so a
    parent's token cannot be used as if it were a child."""
    token_data = _token_data(credentials)
    if token_data["role"] != "child":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="A child session is required")
    from ...bkt_lite import load_mastery
    await load_mastery(db, token_data["user_id"])
    return token_data["user_id"]


async def current_parent(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    token_data = _token_data(credentials)
    if token_data["role"] != "parent":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="A parent account is required")
    return token_data
