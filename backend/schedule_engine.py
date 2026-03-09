import logging
from datetime import date, datetime, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .core.database import (
    CurriculumStandard,
    DailySchedule,
    SubjectTimeLog,
    StudentAdaptiveProfile,
    LearningProgress,
    ProgressReport,
)
from .unified_adaptive_engine import get_or_create_profile

logger = logging.getLogger(__name__)

AGE_SCHEDULE_TEMPLATES = {
    "tiny": {
        "total_minutes": 90,
        "blocks": [
            {"subject": "math", "duration": 15, "types": ["game", "lesson"]},
            {"subject": "reading", "duration": 15, "types": ["lesson", "video"]},
            {"subject": "break", "duration": 10, "types": ["creative"]},
            {"subject": "science", "duration": 15, "types": ["video", "lesson"]},
            {"subject": "writing", "duration": 10, "types": ["writing", "practice"]},
            {"subject": "break", "duration": 10, "types": ["creative"]},
            {"subject": "social_studies", "duration": 15, "types": ["lesson", "video"]},
        ],
    },
    "junior": {
        "total_minutes": 150,
        "blocks": [
            {"subject": "math", "duration": 30, "types": ["lesson", "practice", "game"]},
            {"subject": "reading", "duration": 25, "types": ["lesson", "practice"]},
            {"subject": "break", "duration": 10, "types": ["creative"]},
            {"subject": "writing", "duration": 20, "types": ["writing", "lesson"]},
            {"subject": "science", "duration": 25, "types": ["lesson", "practice", "video"]},
            {"subject": "break", "duration": 10, "types": ["creative"]},
            {"subject": "social_studies", "duration": 20, "types": ["lesson", "video"]},
            {"subject": "review", "duration": 10, "types": ["review", "game"]},
        ],
    },
    "rising": {
        "total_minutes": 210,
        "blocks": [
            {"subject": "math", "duration": 45, "types": ["lesson", "practice", "game"]},
            {"subject": "reading", "duration": 30, "types": ["lesson", "practice"]},
            {"subject": "writing", "duration": 25, "types": ["writing", "lesson"]},
            {"subject": "break", "duration": 10, "types": ["creative"]},
            {"subject": "science", "duration": 30, "types": ["lesson", "practice", "video"]},
            {"subject": "social_studies", "duration": 25, "types": ["lesson", "practice"]},
            {"subject": "break", "duration": 10, "types": ["creative"]},
            {"subject": "review", "duration": 15, "types": ["review", "game"]},
            {"subject": "enrichment", "duration": 20, "types": ["chat", "practice"]},
        ],
    },
}

SUBJECT_LABELS = {
    "math": "Mathematics",
    "reading": "Reading & Language Arts",
    "writing": "Writing",
    "science": "Science",
    "social_studies": "Social Studies",
    "break": "Creative Break",
    "review": "Review & Practice",
    "enrichment": "Enrichment",
}

ACTIVITY_LABELS = {
    "lesson": "Lesson",
    "practice": "Practice",
    "game": "Learning Game",
    "video": "Video Lesson",
    "writing": "Writing Activity",
    "review": "Review",
    "creative": "Free Explore",
    "chat": "AI Tutor Chat",
}


def _get_age_group(age: int) -> str:
    if age <= 5:
        return "tiny"
    elif age <= 8:
        return "junior"
    return "rising"


def _get_grade_level(age: int) -> int:
    grade = age - 5
    return max(0, min(6, grade))


async def _get_next_standard(
    db: AsyncSession, user_id: str, subject: str, grade_level: int
) -> Optional[Dict[str, Any]]:
    for gl in [grade_level] + list(range(grade_level - 1, -1, -1)) + list(range(grade_level + 1, 7)):
        result = await db.execute(
            select(CurriculumStandard)
            .where(
                and_(
                    CurriculumStandard.subject == subject,
                    CurriculumStandard.grade_level == gl,
                )
            )
            .order_by(CurriculumStandard.sequence_order)
        )
        standards = result.scalars().all()
        if not standards:
            continue

        for standard in standards:
            return {
                "id": standard.id,
                "title": standard.title,
                "description": standard.description,
                "objectives": standard.learning_objectives,
                "strand": standard.strand,
                "activity_types": standard.activity_types or ["lesson", "practice"],
            }

    return None


async def generate_daily_schedule(
    db: AsyncSession, user_id: str, schedule_date: date
) -> Dict[str, Any]:
    existing = await db.execute(
        select(DailySchedule).where(
            and_(
                DailySchedule.user_id == user_id,
                DailySchedule.schedule_date == schedule_date,
            )
        )
    )
    existing_schedule = existing.scalar_one_or_none()
    if existing_schedule:
        return {
            "id": str(existing_schedule.id),
            "date": str(existing_schedule.schedule_date),
            "blocks": existing_schedule.blocks,
            "total_planned_minutes": existing_schedule.total_planned_minutes,
            "total_completed_minutes": existing_schedule.total_completed_minutes,
        }

    profile = await get_or_create_profile(db, user_id)
    age = profile.age or 8
    age_group = _get_age_group(age)
    grade_level = _get_grade_level(age)

    template = AGE_SCHEDULE_TEMPLATES.get(age_group, AGE_SCHEDULE_TEMPLATES["junior"])

    blocks = []
    block_index = 0
    for tmpl in template["blocks"]:
        subject = tmpl["subject"]
        duration = tmpl["duration"]
        activity_types = tmpl["types"]

        if subject in ("break", "review", "enrichment"):
            activity_type = activity_types[0] if activity_types else "creative"
            blocks.append({
                "index": block_index,
                "subject": subject,
                "subject_label": SUBJECT_LABELS.get(subject, subject.title()),
                "standard_id": None,
                "title": SUBJECT_LABELS.get(subject, subject.title()),
                "description": "Take a break and recharge!" if subject == "break"
                    else "Review what you've learned today" if subject == "review"
                    else "Explore a topic that interests you",
                "activity_type": activity_type,
                "activity_label": ACTIVITY_LABELS.get(activity_type, activity_type.title()),
                "duration_minutes": duration,
                "completed": False,
                "completed_at": None,
                "time_spent_seconds": 0,
            })
        else:
            standard = await _get_next_standard(db, user_id, subject, grade_level)
            chosen_type = activity_types[block_index % len(activity_types)] if activity_types else "lesson"

            title = standard["title"] if standard else f"{SUBJECT_LABELS.get(subject, subject.title())} Practice"
            desc = standard["description"] if standard else "Continue learning"

            blocks.append({
                "index": block_index,
                "subject": subject,
                "subject_label": SUBJECT_LABELS.get(subject, subject.title()),
                "standard_id": standard["id"] if standard else None,
                "title": title,
                "description": desc,
                "activity_type": chosen_type,
                "activity_label": ACTIVITY_LABELS.get(chosen_type, chosen_type.title()),
                "duration_minutes": duration,
                "completed": False,
                "completed_at": None,
                "time_spent_seconds": 0,
            })

        block_index += 1

    total_planned = sum(b["duration_minutes"] for b in blocks)

    schedule = DailySchedule(
        user_id=user_id,
        schedule_date=schedule_date,
        blocks=blocks,
        total_planned_minutes=total_planned,
        total_completed_minutes=0,
        created_by="ai",
    )
    db.add(schedule)
    await db.flush()

    return {
        "id": str(schedule.id),
        "date": str(schedule.schedule_date),
        "blocks": blocks,
        "total_planned_minutes": total_planned,
        "total_completed_minutes": 0,
    }


async def complete_block(
    db: AsyncSession, user_id: str, schedule_date: date,
    block_index: int, time_spent_seconds: int
) -> Dict[str, Any]:
    result = await db.execute(
        select(DailySchedule).where(
            and_(
                DailySchedule.user_id == user_id,
                DailySchedule.schedule_date == schedule_date,
            )
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise ValueError("No schedule found for this date")

    blocks = list(schedule.blocks)
    if block_index < 0 or block_index >= len(blocks):
        raise ValueError("Invalid block index")

    block = blocks[block_index]
    if block["completed"]:
        return {"status": "already_completed", "block": block}

    block["completed"] = True
    block["completed_at"] = datetime.now(timezone.utc).isoformat()
    block["time_spent_seconds"] = time_spent_seconds
    blocks[block_index] = block

    completed_minutes = sum(
        b["duration_minutes"] for b in blocks if b["completed"]
    )
    schedule.blocks = blocks
    schedule.total_completed_minutes = completed_minutes

    subject = block["subject"]
    if subject not in ("break", "review", "enrichment"):
        time_log = SubjectTimeLog(
            user_id=user_id,
            subject=subject,
            log_date=schedule_date,
            seconds_spent=time_spent_seconds,
            activity_type=block.get("activity_type", "lesson"),
        )
        db.add(time_log)

    await db.flush()

    total_blocks = len(blocks)
    done_blocks = sum(1 for b in blocks if b["completed"])

    return {
        "status": "completed",
        "block": block,
        "day_progress": {
            "completed": done_blocks,
            "total": total_blocks,
            "completed_minutes": completed_minutes,
            "total_minutes": schedule.total_planned_minutes,
        },
    }


async def get_time_logs(
    db: AsyncSession, user_id: str, period: str = "week"
) -> Dict[str, Any]:
    from datetime import timedelta
    today = date.today()
    if period == "month":
        start_date = today.replace(day=1)
    else:
        start_date = today - timedelta(days=today.weekday())

    result = await db.execute(
        select(SubjectTimeLog).where(
            and_(
                SubjectTimeLog.user_id == user_id,
                SubjectTimeLog.log_date >= start_date,
                SubjectTimeLog.log_date <= today,
            )
        )
    )
    logs = result.scalars().all()

    by_subject: Dict[str, int] = {}
    by_date: Dict[str, Dict[str, int]] = {}
    for log in logs:
        subj = log.subject
        by_subject[subj] = by_subject.get(subj, 0) + log.seconds_spent
        d = str(log.log_date)
        if d not in by_date:
            by_date[d] = {}
        by_date[d][subj] = by_date[d].get(subj, 0) + log.seconds_spent

    total_seconds = sum(by_subject.values())
    by_subject_hours = {k: round(v / 3600, 1) for k, v in by_subject.items()}

    return {
        "period": period,
        "start_date": str(start_date),
        "end_date": str(today),
        "total_hours": round(total_seconds / 3600, 1),
        "by_subject": by_subject_hours,
        "by_date": by_date,
    }


async def get_week_schedules(
    db: AsyncSession, user_id: str
) -> List[Dict[str, Any]]:
    from datetime import timedelta
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    days = []
    for i in range(7):
        d = monday + timedelta(days=i)
        result = await db.execute(
            select(DailySchedule).where(
                and_(
                    DailySchedule.user_id == user_id,
                    DailySchedule.schedule_date == d,
                )
            )
        )
        sched = result.scalar_one_or_none()
        if sched:
            total = len(sched.blocks)
            done = sum(1 for b in sched.blocks if b.get("completed"))
            days.append({
                "date": str(d),
                "has_schedule": True,
                "total_blocks": total,
                "completed_blocks": done,
                "completed_minutes": sched.total_completed_minutes,
                "total_minutes": sched.total_planned_minutes,
                "is_today": d == today,
            })
        else:
            days.append({
                "date": str(d),
                "has_schedule": False,
                "total_blocks": 0,
                "completed_blocks": 0,
                "completed_minutes": 0,
                "total_minutes": 0,
                "is_today": d == today,
            })

    return days


async def generate_progress_report(
    db: AsyncSession, user_id: str, period: str
) -> Dict[str, Any]:
    existing = await db.execute(
        select(ProgressReport).where(
            and_(
                ProgressReport.user_id == user_id,
                ProgressReport.report_period == period,
            )
        )
    )
    report = existing.scalar_one_or_none()
    if report:
        return {
            "period": report.report_period,
            "grade_equivalencies": report.grade_equivalencies,
            "standards_mastered": report.standards_mastered,
            "standards_in_progress": report.standards_in_progress,
            "total_hours": report.total_hours,
            "ai_summary": report.ai_summary,
            "generated_at": str(report.generated_at),
        }

    profile = await get_or_create_profile(db, user_id)
    age = profile.age or 8
    expected_grade = _get_grade_level(age)

    subjects = ["math", "reading", "writing", "science", "social_studies"]
    grade_eq = {}
    mastered_list = []
    in_progress_list = []

    for subject in subjects:
        best_grade = 0
        for g in range(7):
            std_result = await db.execute(
                select(CurriculumStandard).where(
                    and_(
                        CurriculumStandard.subject == subject,
                        CurriculumStandard.grade_level == g,
                    )
                ).order_by(CurriculumStandard.sequence_order)
            )
            standards = std_result.scalars().all()
            if not standards:
                continue

            std_ids = [s.id for s in standards]
            try:
                from uuid import UUID as _UUID
                uid = _UUID(user_id) if not isinstance(user_id, _UUID) else user_id
                prog_result = await db.execute(
                    select(LearningProgress).where(
                        and_(
                            LearningProgress.user_id == uid,
                            LearningProgress.skill_id.in_(std_ids),
                        )
                    )
                )
                progress_items = prog_result.scalars().all()
            except Exception:
                await db.rollback()
                progress_items = []

            mastered_count = 0
            for p in progress_items:
                if (p.mastery_probability or 0.0) >= 0.8:
                    mastered_count += 1
                    mastered_list.append(p.skill_id)
                else:
                    in_progress_list.append(p.skill_id)

            if mastered_count >= len(standards) * 0.5:
                best_grade = g + 0.5
            if mastered_count >= len(standards) * 0.8:
                best_grade = g + 1.0

        grade_eq[subject] = round(best_grade, 1)

    time_data = await get_time_logs(db, user_id, "month")

    summary = f"Student (age {age}, expected grade {expected_grade}). "
    for subj in subjects:
        eq = grade_eq.get(subj, 0)
        label = SUBJECT_LABELS.get(subj, subj)
        hrs = time_data["by_subject"].get(subj, 0)
        if eq >= expected_grade:
            summary += f"{label}: On track (grade {eq}). "
        elif eq >= expected_grade - 1:
            summary += f"{label}: Approaching grade level (grade {eq}). "
        else:
            summary += f"{label}: Needs support (grade {eq}). "
        summary += f"({hrs}h this month). "

    new_report = ProgressReport(
        user_id=user_id,
        report_period=period,
        grade_equivalencies=grade_eq,
        standards_mastered=mastered_list,
        standards_in_progress=in_progress_list,
        total_hours=time_data["by_subject"],
        ai_summary=summary,
    )
    db.add(new_report)
    await db.flush()

    return {
        "period": period,
        "grade_equivalencies": grade_eq,
        "standards_mastered": mastered_list,
        "standards_in_progress": in_progress_list,
        "total_hours": time_data["by_subject"],
        "ai_summary": summary,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
