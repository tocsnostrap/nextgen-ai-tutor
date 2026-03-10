import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Any


def calculate_next_review(quality: int, easiness: float = 2.5,
                          interval: int = 0, repetitions: int = 0) -> Dict[str, Any]:
    quality = max(0, min(5, quality))

    new_easiness = easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_easiness = max(1.3, new_easiness)

    if quality < 3:
        new_repetitions = 0
        next_interval = 1
    else:
        new_repetitions = repetitions + 1
        if new_repetitions == 1:
            next_interval = 1
        elif new_repetitions == 2:
            next_interval = 6
        else:
            next_interval = max(1, round(interval * new_easiness))

    next_review_date = (datetime.now(timezone.utc) + timedelta(days=next_interval)).isoformat()

    return {
        "next_interval": next_interval,
        "new_easiness": round(new_easiness, 4),
        "new_repetitions": new_repetitions,
        "next_review_date": next_review_date,
    }


def quality_from_score(score: float) -> int:
    if score >= 0.95:
        return 5
    elif score >= 0.8:
        return 4
    elif score >= 0.6:
        return 3
    elif score >= 0.4:
        return 2
    elif score >= 0.2:
        return 1
    return 0


def get_review_priority(items: list) -> list:
    now = datetime.now(timezone.utc)
    scored = []
    for item in items:
        due_str = item.get("next_review_date")
        if due_str:
            due = datetime.fromisoformat(due_str)
            days_overdue = (now - due).total_seconds() / 86400
        else:
            days_overdue = 999

        easiness = item.get("easiness", 2.5)
        priority = days_overdue / max(easiness, 1.3)
        scored.append({**item, "priority": round(priority, 4), "days_overdue": round(days_overdue, 2)})

    scored.sort(key=lambda x: x["priority"], reverse=True)
    return scored


__all__ = ["calculate_next_review", "quality_from_score", "get_review_priority"]
