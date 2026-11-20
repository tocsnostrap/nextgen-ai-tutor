"""A parent's children: create profiles, and start a child's session with a PIN."""
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import settings
from ....core.database import Child, get_db
from ....unified_adaptive_engine import get_or_create_profile
from ..auth import create_child_token, current_parent

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_CHILDREN = 8
MAX_PIN_ATTEMPTS = 5
PIN_LOCK_MINUTES = 5
AVATARS = ["star", "rocket", "cat", "dog", "fox", "owl", "dino", "unicorn", "robot", "football"]


def _clean_name(v: str) -> str:
    v = v.strip()
    if not 1 <= len(v) <= 60:
        raise ValueError("Name must be 1 to 60 characters")
    return v


def _check_pin(v: str) -> str:
    if not re.fullmatch(r"\d{4}", v):
        raise ValueError("PIN must be exactly 4 digits")
    return v


def _check_year(v: int) -> int:
    if not 1 <= v <= 7:
        raise ValueError("School year must be between 1 and 7")
    return v


def _check_avatar(v: str) -> str:
    if v not in AVATARS:
        raise ValueError("Unknown avatar")
    return v


def _check_mode(v: str) -> str:
    if v not in ("tutor", "school"):
        raise ValueError("Mode must be tutor or school")
    return v


class ChildCreate(BaseModel):
    display_name: str
    school_year: int
    pin: str
    avatar: str = "star"
    mode: str = "tutor"

    _name = field_validator("display_name")(_clean_name)
    _year = field_validator("school_year")(_check_year)
    _pin = field_validator("pin")(_check_pin)
    _avatar = field_validator("avatar")(_check_avatar)
    _mode = field_validator("mode")(_check_mode)


class ChildUpdate(BaseModel):
    display_name: Optional[str] = None
    school_year: Optional[int] = None
    pin: Optional[str] = None
    avatar: Optional[str] = None
    mode: Optional[str] = None

    _name = field_validator("display_name")(lambda v: v if v is None else _clean_name(v))
    _year = field_validator("school_year")(lambda v: v if v is None else _check_year(v))
    _pin = field_validator("pin")(lambda v: v if v is None else _check_pin(v))
    _avatar = field_validator("avatar")(lambda v: v if v is None else _check_avatar(v))
    _mode = field_validator("mode")(lambda v: v if v is None else _check_mode(v))


class PinRequest(BaseModel):
    pin: str


def _hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


def _public(child: Child) -> Dict[str, Any]:
    return {
        "id": str(child.id),
        "display_name": child.display_name,
        "school_year": child.school_year,
        "avatar": child.avatar,
        "mode": child.mode,
    }


async def _own_child(db: AsyncSession, parent: Dict[str, Any], child_id: str) -> Child:
    try:
        child_uuid = UUID(child_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")
    child = (await db.execute(select(Child).where(Child.id == child_uuid))).scalar_one_or_none()
    if child is None or str(child.parent_id) != parent["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")
    return child


@router.get("/avatars")
async def list_avatars():
    return {"avatars": AVATARS}


@router.get("/children")
async def list_children(parent: Dict = Depends(current_parent), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Child).where(Child.parent_id == UUID(parent["user_id"])).order_by(Child.created_at)
        )
    ).scalars().all()
    return {"children": [_public(c) for c in rows]}


@router.post("/children", status_code=status.HTTP_201_CREATED)
async def add_child(body: ChildCreate, parent: Dict = Depends(current_parent), db: AsyncSession = Depends(get_db)):
    parent_uuid = UUID(parent["user_id"])
    existing = (await db.execute(select(Child.id).where(Child.parent_id == parent_uuid))).all()
    if len(existing) >= MAX_CHILDREN:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"An account can have up to {MAX_CHILDREN} children")
    child = Child(
        parent_id=parent_uuid,
        display_name=body.display_name,
        school_year=body.school_year,
        avatar=body.avatar,
        mode=body.mode,
        pin_hash=_hash_pin(body.pin),
    )
    db.add(child)
    await db.flush()
    await db.refresh(child)
    return _public(child)


@router.patch("/children/{child_id}")
async def update_child(child_id: str, body: ChildUpdate, parent: Dict = Depends(current_parent), db: AsyncSession = Depends(get_db)):
    child = await _own_child(db, parent, child_id)
    for field in ("display_name", "school_year", "avatar", "mode"):
        value = getattr(body, field)
        if value is not None:
            setattr(child, field, value)
    if body.pin is not None:
        child.pin_hash = _hash_pin(body.pin)
        child.failed_pin_attempts = 0
        child.pin_locked_until = None
    await db.flush()
    return _public(child)


@router.post("/children/{child_id}/session")
async def start_child_session(child_id: str, body: PinRequest, parent: Dict = Depends(current_parent), db: AsyncSession = Depends(get_db)):
    """The child taps their picture and enters their PIN on a device the parent
    has signed in to. Returns a token that acts as that child only."""
    child = await _own_child(db, parent, child_id)
    now = datetime.now(timezone.utc)

    if child.pin_locked_until and child.pin_locked_until > now:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many tries. Ask a grown-up, or try again in a few minutes.")

    if not bcrypt.checkpw(body.pin.encode(), child.pin_hash.encode()):
        child.failed_pin_attempts += 1
        if child.failed_pin_attempts >= MAX_PIN_ATTEMPTS:
            child.pin_locked_until = now + timedelta(minutes=PIN_LOCK_MINUTES)
            child.failed_pin_attempts = 0
        # Commit here: the HTTPException below would otherwise roll the count back.
        await db.commit()
        # 403, not 401: 401 means "the parent's sign-in expired" to the page,
        # which would retry the request and use up a second attempt.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="That PIN isn't right. Have another go.")

    child.failed_pin_attempts = 0
    child.pin_locked_until = None

    # Until the curriculum import (PLAN.md phase 2) the older code works from an age.
    profile = await get_or_create_profile(db, str(child.id))
    profile.age = child.school_year + 5

    return {
        "access_token": create_child_token(str(child.id), parent["user_id"]),
        "token_type": "bearer",
        "expires_in": settings.CHILD_SESSION_HOURS * 3600,
        "child": _public(child),
    }


__all__ = ["router"]
