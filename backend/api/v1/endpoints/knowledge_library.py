"""
Knowledge Library — child-led interest tracking and discovery logging.

Nova automatically learns from enthusiasm signals in chat messages and builds
a personal knowledge library for each child. Children can also manually add
topics they love. All detected interests feed back into Nova's personality
and teaching context.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import verify_token
from ....core.database import get_db, ChildInterestProfile

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# ── Topic emoji map ──────────────────────────────────────────────────────────

TOPIC_EMOJIS: Dict[str, str] = {
    # Animals & nature
    "dinosaur": "🦕", "dinosaurs": "🦕", "dino": "🦕",
    "shark": "🦈", "sharks": "🦈",
    "dog": "🐕", "dogs": "🐕", "puppy": "🐕",
    "cat": "🐱", "cats": "🐱", "kitten": "🐱",
    "dragon": "🐉", "dragons": "🐉",
    "butterfly": "🦋", "insects": "🐛", "bugs": "🐛",
    "ocean": "🌊", "sea": "🌊", "underwater": "🌊",
    "jungle": "🌴", "rainforest": "🌳", "forest": "🌲",
    "animals": "🐾", "wildlife": "🦁",
    # Space
    "space": "🚀", "stars": "⭐", "star": "⭐",
    "planets": "🪐", "planet": "🪐", "solar system": "☀️",
    "moon": "🌙", "astronaut": "👨‍🚀", "rocket": "🚀",
    "galaxy": "🌌", "universe": "🌌", "astronomy": "🔭",
    "black hole": "🕳️", "meteor": "☄️", "comet": "☄️",
    # Science
    "volcano": "🌋", "volcanoes": "🌋",
    "chemistry": "⚗️", "experiment": "🧪", "science": "🔬",
    "robot": "🤖", "robots": "🤖", "robotics": "🤖",
    "coding": "💻", "programming": "💻", "computers": "💻",
    "electricity": "⚡", "magnets": "🧲",
    "weather": "⛈️", "storm": "⛈️", "tornado": "🌪️",
    "fossils": "🦴", "archaeology": "🏺",
    # Arts & creativity
    "art": "🎨", "drawing": "✏️", "painting": "🖌️",
    "music": "🎵", "singing": "🎤", "guitar": "🎸", "piano": "🎹",
    "dance": "💃", "dancing": "💃",
    "stories": "📖", "books": "📚", "reading": "📖",
    "minecraft": "⛏️", "lego": "🧱", "building": "🏗️",
    # Sports & activities
    "football": "🏈", "soccer": "⚽", "basketball": "🏀",
    "swimming": "🏊", "sport": "🏅", "sports": "🏅",
    "running": "🏃", "gymnastics": "🤸",
    # Food
    "cooking": "🍳", "baking": "🧁", "food": "🍕",
    "pizza": "🍕", "chocolate": "🍫",
    # Math & puzzles
    "math": "🔢", "numbers": "🔢", "puzzles": "🧩",
    "magic": "✨", "tricks": "🎩",
    # History & culture
    "history": "🏛️", "egypt": "🏺", "pyramids": "🏺",
    "knights": "⚔️", "castles": "🏰", "pirates": "🏴‍☠️",
    "superheroes": "🦸", "superhero": "🦸",
}

SUBJECT_MAP: Dict[str, str] = {
    "dinosaur": "science", "dino": "science", "shark": "science",
    "space": "science", "stars": "science", "planets": "science",
    "volcano": "science", "chemistry": "science", "robot": "science",
    "weather": "science", "fossils": "science", "electricity": "science",
    "coding": "coding", "programming": "coding", "computers": "coding",
    "minecraft": "coding", "robot": "coding",
    "math": "math", "numbers": "math", "puzzles": "math",
    "art": "reading", "drawing": "reading", "stories": "reading",
    "books": "reading", "music": "reading",
    "history": "science", "egypt": "science", "knights": "reading",
}

# Enthusiasm signal phrases
ENTHUSIASM_PATTERNS = [
    r"\bi (?:really )?(?:love|like|enjoy|adore)\b (.+?)(?:[.!?]|$)",
    r"\bmy favou?rite\b.{0,20}\b(?:is|are)\b (.+?)(?:[.!?]|$)",
    r"\b(?:tell me more about|i want to know more about|more about)\b (.+?)(?:[.!?]|$)",
    r"\b(?:so cool|so awesome|amazing|wow|omg|whoa)\b.{0,40}\b(.+?)(?:[.!?]|$)",
    r"\b(?:obsessed with|crazy about|into)\b (.+?)(?:[.!?]|$)",
    r"\bwhat about (.+?)\??(?:\s|$)",
    r"\bcan we (?:learn|talk) about (.+?)(?:[.?]|$)",
]


def _get_emoji(topic: str) -> str:
    key = topic.lower().strip()
    for k, v in TOPIC_EMOJIS.items():
        if k in key or key in k:
            return v
    return "✨"


def _get_subject(topic: str) -> str:
    key = topic.lower().strip()
    for k, v in SUBJECT_MAP.items():
        if k in key:
            return v
    return "general"


def detect_enthusiasm_topics(message: str) -> List[Dict[str, str]]:
    """Extract topics the child is enthusiastic about from a message."""
    found = []
    msg_lower = message.lower()

    for pattern in ENTHUSIASM_PATTERNS:
        for m in re.finditer(pattern, msg_lower):
            raw = m.group(1).strip().rstrip(".,!?").strip()
            # Clean up: remove articles, keep 1-4 words
            raw = re.sub(r"^(the|a|an|my|your|our|their)\s+", "", raw)
            words = raw.split()
            if 1 <= len(words) <= 4:
                topic = raw.lower()
                if len(topic) >= 3:
                    found.append({
                        "topic": topic,
                        "emoji": _get_emoji(topic),
                        "subject_area": _get_subject(topic),
                        "signal": m.group(0)[:80],
                    })

    return found[:3]  # max 3 per message


# ── Auth helper ──────────────────────────────────────────────────────────────

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token_data["user_id"]


# ── DB helpers ───────────────────────────────────────────────────────────────

async def _get_or_create_profile(db: AsyncSession, user_id: str) -> ChildInterestProfile:
    result = await db.execute(
        select(ChildInterestProfile).where(ChildInterestProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = ChildInterestProfile(
            user_id=user_id,
            passion_topics=[],
            custom_interests=[],
            discoveries=[],
            nova_memory=[],
            enthusiasm_log=[],
        )
        db.add(profile)
        await db.flush()
    return profile


def _upsert_passion_topic(profile: ChildInterestProfile, topic: str, emoji: str, subject_area: str, signal: str):
    """Increment score for existing topic or add new one."""
    now = datetime.now(timezone.utc).isoformat()
    topics: list = list(profile.passion_topics or [])

    for t in topics:
        if t.get("topic", "").lower() == topic.lower():
            t["score"] = min(1.0, t.get("score", 0.3) + 0.1)
            t["count"] = t.get("count", 1) + 1
            t["last_seen"] = now
            profile.passion_topics = topics
            return

    topics.append({
        "topic": topic,
        "emoji": emoji,
        "subject_area": subject_area,
        "score": 0.4,
        "count": 1,
        "first_seen": now,
        "last_seen": now,
    })
    # Keep top 30 by score
    topics.sort(key=lambda x: x.get("score", 0), reverse=True)
    profile.passion_topics = topics[:30]

    # Refresh nova_memory
    top_topics = [t["topic"] for t in topics[:5]]
    _refresh_nova_memory(profile, top_topics)


def _refresh_nova_memory(profile: ChildInterestProfile, top_topics: list):
    """Rebuild Nova's memory notes from passion topics."""
    memories = []
    if top_topics:
        memories.append(f"loves talking about: {', '.join(top_topics[:3])}")
    custom = [c["topic"] for c in (profile.custom_interests or [])]
    if custom:
        memories.append(f"chose to explore: {', '.join(custom[:3])}")
    profile.nova_memory = memories


# ── Pydantic models ──────────────────────────────────────────────────────────

class AddInterestRequest(BaseModel):
    topic: str
    emoji: Optional[str] = None


class LogDiscoveryRequest(BaseModel):
    concept: str
    subject: str
    short_desc: str
    emoji: Optional[str] = None


class EnthusiasmUpdateRequest(BaseModel):
    """Called by the chat pipeline after processing a message."""
    message: str
    ai_response: str  # used to extract new concepts the child just learned


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/profile")
async def get_library_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get the child's full knowledge library: interests, discoveries, Nova's memory."""
    profile = await _get_or_create_profile(db, user_id)
    return {
        "passion_topics": profile.passion_topics or [],
        "custom_interests": profile.custom_interests or [],
        "discoveries": profile.discoveries or [],
        "nova_memory": profile.nova_memory or [],
        "total_discoveries": len(profile.discoveries or []),
        "total_interests": len(profile.passion_topics or []) + len(profile.custom_interests or []),
    }


@router.post("/interest")
async def add_interest(
    request: AddInterestRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Child manually adds a topic they want to explore."""
    topic = request.topic.strip().lower()[:50]
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty")

    profile = await _get_or_create_profile(db, user_id)
    now = datetime.now(timezone.utc).isoformat()
    emoji = request.emoji or _get_emoji(topic)

    custom: list = list(profile.custom_interests or [])
    # Avoid duplicates
    if not any(c.get("topic", "").lower() == topic for c in custom):
        custom.append({"topic": topic, "emoji": emoji, "added_at": now})
        profile.custom_interests = custom

    # Also boost in passion_topics
    _upsert_passion_topic(profile, topic, emoji, _get_subject(topic), "manual_add")

    await db.commit()
    return {"ok": True, "topic": topic, "emoji": emoji}


@router.delete("/interest/{topic}")
async def remove_interest(
    topic: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Remove a topic from the child's interest library."""
    profile = await _get_or_create_profile(db, user_id)
    profile.custom_interests = [
        c for c in (profile.custom_interests or [])
        if c.get("topic", "").lower() != topic.lower()
    ]
    profile.passion_topics = [
        t for t in (profile.passion_topics or [])
        if t.get("topic", "").lower() != topic.lower()
    ]
    await db.commit()
    return {"ok": True}


@router.post("/discovery")
async def log_discovery(
    request: LogDiscoveryRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Log something the child just discovered/learned."""
    profile = await _get_or_create_profile(db, user_id)
    now = datetime.now(timezone.utc).isoformat()
    emoji = request.emoji or _get_emoji(request.concept)

    discoveries: list = list(profile.discoveries or [])
    discoveries.insert(0, {
        "concept": request.concept[:80],
        "subject": request.subject,
        "short_desc": request.short_desc[:160],
        "emoji": emoji,
        "discovered_at": now,
    })
    profile.discoveries = discoveries[:200]  # keep last 200

    await db.commit()
    return {"ok": True, "total": len(profile.discoveries)}


@router.post("/update-from-chat")
async def update_from_chat(
    request: EnthusiasmUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Called by chat pipeline after each message.
    Detects enthusiasm signals and updates interest scores automatically.
    """
    profile = await _get_or_create_profile(db, user_id)
    now = datetime.now(timezone.utc).isoformat()

    detected = detect_enthusiasm_topics(request.message)
    if not detected:
        return {"ok": True, "detected": []}

    log: list = list(profile.enthusiasm_log or [])
    for item in detected:
        _upsert_passion_topic(
            profile,
            item["topic"],
            item["emoji"],
            item["subject_area"],
            item["signal"],
        )
        log.insert(0, {
            "topic": item["topic"],
            "signal": item["signal"],
            "detected_at": now,
        })

    profile.enthusiasm_log = log[:100]  # rolling window

    await db.commit()
    return {"ok": True, "detected": [d["topic"] for d in detected]}


@router.get("/context")
async def get_interest_context(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a compact interest context string for injecting into Nova's system prompt.
    """
    profile = await _get_or_create_profile(db, user_id)

    top_passions = sorted(
        (profile.passion_topics or []),
        key=lambda x: x.get("score", 0),
        reverse=True,
    )[:5]

    custom = profile.custom_interests or []
    nova_mem = profile.nova_memory or []

    lines = []
    if top_passions:
        topics_str = ", ".join(
            f"{t['emoji']} {t['topic']}" for t in top_passions
        )
        lines.append(f"Passions detected: {topics_str}")
    if custom:
        c_str = ", ".join(f"{c.get('emoji','✨')} {c['topic']}" for c in custom[:4])
        lines.append(f"Self-chosen interests: {c_str}")
    if nova_mem:
        lines.append(f"Nova remembers: {'; '.join(nova_mem[:3])}")

    discoveries = profile.discoveries or []
    if discoveries:
        recent = discoveries[:3]
        d_str = ", ".join(f"{d.get('emoji','🔍')} {d['concept']}" for d in recent)
        lines.append(f"Recently discovered: {d_str}")

    return {
        "context_string": "\n".join(lines) if lines else "",
        "top_topics": [t["topic"] for t in top_passions],
        "has_interests": bool(top_passions or custom),
    }


__all__ = ["router", "detect_enthusiasm_topics", "_get_or_create_profile"]
