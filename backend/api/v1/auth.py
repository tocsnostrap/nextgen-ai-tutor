import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone

import jwt

from ...core.config import settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"

DEMO_TOKEN = "access_token_user_123"
DEMO_USER_ID = "user_123"


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


def create_refresh_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": now,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    # The page's built-in demo child. Only this one token, and only in demo mode.
    if settings.DEMO_MODE and token == DEMO_TOKEN:
        return {
            "user_id": DEMO_USER_ID,
            "email": "demo@example.com",
            "role": "student",
        }

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") not in ("access", None):
            logger.warning("Token type '%s' is not an access token", payload.get("type"))
            return None
        return {
            "user_id": payload["sub"],
            "email": payload.get("email", ""),
            "role": payload.get("role", "student"),
        }
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token: %s", e)
        return None
