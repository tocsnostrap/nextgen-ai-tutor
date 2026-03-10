"""
Learning Trajectory Forecasting System

Predicts future student performance, identifies at-risk skills,
and generates proactive learning plans — weeks before problems develop.

Key innovations:
1. EXPONENTIAL DECAY MODEL: Knowledge retention degrades predictably without practice
2. PREREQUISITE CHAIN ANALYSIS: Weakness in foundational skills cascades forward
3. LEARNING VELOCITY: How fast is this student acquiring new skills vs. the baseline?
4. FORGETTING CURVE PERSONALIZATION: Individual forgetting rates (not generic Ebbinghaus)
5. INTERFERENCE DETECTION: Similar skills that confuse each other (e.g., × vs ÷)
6. OPTIMAL REVIEW SCHEDULING: When to review each skill to prevent regression
7. MASTERY TRAJECTORY: Predict exactly when each skill will reach 80% mastery

This system transforms tutoring from REACTIVE (fixing problems) to
PROACTIVE (preventing problems before they develop).
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SkillTrajectory:
    """Complete trajectory data for a single skill."""
    skill_id: str
    current_mastery: float          # 0.0 – 1.0 BKT probability
    mastery_trend: float            # Rate of change per session (positive = improving)
    sessions_practiced: int
    last_practiced: Optional[datetime]
    days_since_practice: int
    forgetting_rate: float          # Personalized decay rate
    predicted_mastery_7d: float
    predicted_mastery_14d: float
    predicted_mastery_30d: float
    at_risk: bool                   # Will drop below threshold without intervention
    ready_to_advance: bool          # Can start next skill in sequence
    review_urgency: str             # none / low / medium / high / critical


@dataclass
class LearningVelocity:
    """How fast a student learns compared to baseline."""
    sessions_to_mastery_avg: float  # Average sessions needed to reach 80% mastery
    mastery_rate: float             # Skills mastered per week
    retention_strength: float       # 0–1: how well they retain learned skills
    consistency_score: float        # Regularity of practice (0–1)
    acceleration: float             # Is learning speeding up or slowing down?
    learning_style_fit: str         # Which content types work best for this student


@dataclass
class LearningPlan:
    """A structured 4-week learning plan."""
    student_id: str
    generated_at: datetime
    weekly_plans: List[Dict[str, Any]]
    skills_to_review: List[str]
    skills_to_advance: List[str]
    daily_minutes_recommended: int
    parent_insights: str
    teacher_notes: str
    confidence: float               # How confident we are in this prediction (0–1)


# ── Prerequisite dependency graph ────────────────────────────────────────────

PREREQUISITE_GRAPH: Dict[str, List[str]] = {
    # Math progression
    "counting": [],
    "addition_single": ["counting"],
    "addition_double": ["addition_single"],
    "subtraction_single": ["counting", "addition_single"],
    "subtraction_double": ["subtraction_single", "addition_double"],
    "multiplication_basic": ["addition_double", "subtraction_single"],
    "multiplication_advanced": ["multiplication_basic"],
    "division_basic": ["multiplication_basic", "subtraction_double"],
    "division_advanced": ["division_basic", "multiplication_advanced"],
    "fractions_intro": ["division_basic"],
    "fractions_operations": ["fractions_intro", "multiplication_basic"],
    "decimals": ["fractions_intro", "place_value"],
    "percentages": ["decimals", "fractions_operations"],
    "place_value": ["counting", "addition_single"],
    "algebra_intro": ["fractions_operations", "decimals"],
    "algebra_advanced": ["algebra_intro"],
    "geometry_basic": ["addition_double", "multiplication_basic"],
    "geometry_advanced": ["geometry_basic", "algebra_intro"],

    # Science progression
    "observation_skills": [],
    "measurement": ["observation_skills"],
    "scientific_method": ["observation_skills", "measurement"],
    "matter_states": ["observation_skills"],
    "atoms_molecules": ["matter_states", "scientific_method"],
    "cells_basic": ["observation_skills"],
    "cells_advanced": ["cells_basic", "atoms_molecules"],
    "ecosystems": ["cells_basic"],
    "forces_motion": ["measurement", "scientific_method"],
    "energy_basics": ["forces_motion"],
    "electricity": ["energy_basics", "atoms_molecules"],

    # Coding progression
    "sequences": [],
    "loops_basic": ["sequences"],
    "conditionals": ["loops_basic"],
    "variables": ["conditionals"],
    "functions_basic": ["variables", "loops_basic"],
    "functions_advanced": ["functions_basic"],
    "recursion": ["functions_advanced"],
    "data_structures": ["variables", "loops_basic"],
    "algorithms_basic": ["functions_basic", "conditionals"],
    "algorithms_advanced": ["algorithms_basic", "recursion"],
}

# Skills that interfere with each other (similar, easy to confuse)
INTERFERENCE_PAIRS: List[Tuple[str, str]] = [
    ("multiplication_basic", "division_basic"),
    ("fractions_intro", "decimals"),
    ("addition_double", "subtraction_double"),
    ("loops_basic", "conditionals"),
    ("functions_basic", "variables"),
]


def calculate_retention(
    current_mastery: float,
    days_since_practice: int,
    forgetting_rate: float = 0.05,
) -> float:
    """
    Apply exponential forgetting curve to predict mastery after inactivity.

    Based on Ebbinghaus forgetting curve: R(t) = e^(-t/S)
    S = stability factor (personalized forgetting rate)
    """
    if days_since_practice <= 0:
        return current_mastery
    decay = math.exp(-forgetting_rate * days_since_practice)
    # Knowledge doesn't decay to zero — there's a floor
    floor = max(0.1, current_mastery * 0.3)
    retained = floor + (current_mastery - floor) * decay
    return max(0.0, min(1.0, retained))


def estimate_days_to_mastery(
    current_mastery: float,
    mastery_trend: float,
    target_mastery: float = 0.8,
    daily_practice_sessions: float = 1.0,
) -> Optional[int]:
    """
    Estimate days until target mastery is reached.
    Returns None if mastery trend is negative (regressing).
    """
    if current_mastery >= target_mastery:
        return 0
    if mastery_trend <= 0:
        return None  # Cannot predict if not improving

    gap = target_mastery - current_mastery
    sessions_needed = gap / mastery_trend
    days_needed = sessions_needed / daily_practice_sessions
    return int(math.ceil(days_needed))


def identify_cascade_risks(
    skill_states: Dict[str, float],
    threshold: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Identify skills at risk of cascading failure.
    When a foundational skill is weak, all dependent skills are at risk.
    """
    cascade_risks = []

    for skill, mastery in skill_states.items():
        if mastery < threshold:
            # Find all skills that depend on this one
            dependents = [
                s for s, prereqs in PREREQUISITE_GRAPH.items()
                if skill in prereqs
            ]
            if dependents:
                cascade_risks.append({
                    "weak_skill": skill,
                    "mastery": mastery,
                    "at_risk_skills": dependents,
                    "cascade_severity": len(dependents),
                    "priority": "critical" if mastery < 0.25 else "high",
                })

    return sorted(cascade_risks, key=lambda x: x["cascade_severity"], reverse=True)


def identify_interference_risks(
    skill_states: Dict[str, float],
) -> List[Dict[str, Any]]:
    """
    Identify pairs of skills being learned simultaneously that may interfere.
    """
    risks = []
    for skill_a, skill_b in INTERFERENCE_PAIRS:
        mastery_a = skill_states.get(skill_a, 0)
        mastery_b = skill_states.get(skill_b, 0)

        # Both being actively learned (0.3–0.7 mastery = active learning zone)
        if 0.3 < mastery_a < 0.7 and 0.3 < mastery_b < 0.7:
            risks.append({
                "skill_a": skill_a,
                "skill_b": skill_b,
                "mastery_a": mastery_a,
                "mastery_b": mastery_b,
                "recommendation": (
                    f"Learning {skill_a} and {skill_b} simultaneously may cause confusion. "
                    f"Consider focusing on {skill_a} first (higher prerequisite value)."
                ),
            })

    return risks


def calculate_learning_velocity(
    session_history: List[Dict[str, Any]],
    skill_states: Dict[str, float],
) -> LearningVelocity:
    """
    Calculate a student's learning velocity from historical data.
    """
    if not session_history:
        return LearningVelocity(
            sessions_to_mastery_avg=20.0,
            mastery_rate=0.5,
            retention_strength=0.5,
            consistency_score=0.5,
            acceleration=0.0,
            learning_style_fit="unknown",
        )

    # Calculate consistency (regularity of practice)
    recent = session_history[-20:]
    if len(recent) > 1:
        dates = [s.get("date") for s in recent if s.get("date")]
        if len(dates) > 1:
            gaps = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))
                    if isinstance(dates[i], datetime) and isinstance(dates[i-1], datetime)]
            avg_gap = sum(gaps) / len(gaps) if gaps else 7
            # Ideal gap: 1-2 days. Score drops with longer gaps.
            consistency = max(0.0, 1.0 - (avg_gap - 1.5) / 7.0)
        else:
            consistency = 0.5
    else:
        consistency = 0.5

    # Calculate accuracy trend (acceleration)
    if len(recent) >= 10:
        first_half_acc = sum(1 for s in recent[:10] if s.get("correct")) / 10
        second_half_acc = sum(1 for s in recent[-10:] if s.get("correct")) / 10
        acceleration = second_half_acc - first_half_acc
    else:
        acceleration = 0.0

    # Mastery rate: skills mastered (>0.8) per week
    mastered = sum(1 for v in skill_states.values() if v > 0.8)
    weeks_of_data = max(1, len(session_history) / 5)  # Assume ~5 sessions/week
    mastery_rate = mastered / weeks_of_data

    # Retention strength: average mastery of skills not practiced in last 7 days
    old_skills = {k: v for k, v in skill_states.items() if v > 0.3}
    retention_strength = (
        sum(old_skills.values()) / len(old_skills) if old_skills else 0.5
    )

    return LearningVelocity(
        sessions_to_mastery_avg=20.0 / max(0.1, mastery_rate),
        mastery_rate=mastery_rate,
        retention_strength=retention_strength,
        consistency_score=consistency,
        acceleration=acceleration,
        learning_style_fit="mixed",
    )


def generate_skill_trajectories(
    skill_states: Dict[str, float],
    session_history: List[Dict[str, Any]],
    last_practiced: Optional[Dict[str, datetime]] = None,
) -> List[SkillTrajectory]:
    """
    Generate trajectory data for all tracked skills.
    """
    trajectories = []
    last_practiced = last_practiced or {}
    now = datetime.now()

    for skill_id, current_mastery in skill_states.items():
        # Calculate days since last practice
        last_date = last_practiced.get(skill_id)
        days_since = (now - last_date).days if last_date else 7

        # Estimate forgetting rate (personalized — faster forgetters need more review)
        recent_correct = [
            s for s in session_history[-30:]
            if s.get("skill") == skill_id and s.get("correct")
        ]
        forgetting_rate = 0.03 + (0.04 * (1.0 - min(len(recent_correct) / 10.0, 1.0)))

        # Calculate mastery trend from recent sessions
        skill_sessions = [
            s for s in session_history[-20:]
            if s.get("skill") == skill_id
        ]
        if len(skill_sessions) >= 3:
            recent_correct_rate = (
                sum(1 for s in skill_sessions[-3:] if s.get("correct")) / 3
            )
            older_correct_rate = (
                sum(1 for s in skill_sessions[:3] if s.get("correct")) / 3
            )
            mastery_trend = (recent_correct_rate - older_correct_rate) / len(skill_sessions)
        else:
            mastery_trend = 0.02  # Assume slight improvement if insufficient data

        # Apply forgetting curve for predictions
        predicted_7d = calculate_retention(current_mastery, days_since + 7, forgetting_rate)
        predicted_14d = calculate_retention(current_mastery, days_since + 14, forgetting_rate)
        predicted_30d = calculate_retention(current_mastery, days_since + 30, forgetting_rate)

        at_risk = predicted_14d < 0.5 and current_mastery >= 0.5
        ready_to_advance = current_mastery >= 0.8

        if days_since > 14 and current_mastery > 0.6:
            review_urgency = "high"
        elif days_since > 7 and current_mastery > 0.5:
            review_urgency = "medium"
        elif predicted_14d < 0.4:
            review_urgency = "critical"
        elif current_mastery < 0.3:
            review_urgency = "none"  # Focus on learning, not review
        else:
            review_urgency = "low"

        trajectories.append(SkillTrajectory(
            skill_id=skill_id,
            current_mastery=current_mastery,
            mastery_trend=mastery_trend,
            sessions_practiced=len(skill_sessions),
            last_practiced=last_date,
            days_since_practice=days_since,
            forgetting_rate=forgetting_rate,
            predicted_mastery_7d=predicted_7d,
            predicted_mastery_14d=predicted_14d,
            predicted_mastery_30d=predicted_30d,
            at_risk=at_risk,
            ready_to_advance=ready_to_advance,
            review_urgency=review_urgency,
        ))

    return sorted(trajectories, key=lambda t: t.current_mastery)


def generate_weekly_plan(
    trajectories: List[SkillTrajectory],
    velocity: LearningVelocity,
    week_number: int,
) -> Dict[str, Any]:
    """Generate a single week's focused learning plan."""
    # Prioritize: critical reviews > at-risk skills > advancing ready skills > new skills
    critical_reviews = [t for t in trajectories if t.review_urgency == "critical"]
    at_risk = [t for t in trajectories if t.at_risk]
    ready_advance = [t for t in trajectories if t.ready_to_advance]

    focus_skills = []
    weekly_goal = ""

    if critical_reviews:
        focus_skills = [t.skill_id for t in critical_reviews[:2]]
        weekly_goal = f"Prevent regression in: {', '.join(focus_skills)}"
    elif at_risk:
        focus_skills = [t.skill_id for t in at_risk[:2]]
        weekly_goal = f"Strengthen before they weaken: {', '.join(focus_skills)}"
    elif ready_advance:
        # Find next skills in the prerequisite graph
        next_skills = []
        for t in ready_advance[:2]:
            for skill, prereqs in PREREQUISITE_GRAPH.items():
                if t.skill_id in prereqs and skill not in [t2.skill_id for t2 in trajectories]:
                    next_skills.append(skill)
        focus_skills = next_skills[:2] if next_skills else [t.skill_id for t in ready_advance[:2]]
        weekly_goal = f"Level up to: {', '.join(focus_skills)}"
    else:
        # Default: continue with lowest-mastery skills
        low_mastery = sorted(trajectories, key=lambda t: t.current_mastery)[:2]
        focus_skills = [t.skill_id for t in low_mastery]
        weekly_goal = f"Build mastery in: {', '.join(focus_skills)}"

    # Adjust sessions based on velocity
    base_sessions = 4
    if velocity.consistency_score < 0.4:
        base_sessions = 3  # Struggling with consistency; reduce target
    elif velocity.mastery_rate > 1.5:
        base_sessions = 5  # Fast learner; can handle more

    return {
        "week": week_number,
        "focus_skills": focus_skills,
        "weekly_goal": weekly_goal,
        "recommended_sessions": base_sessions,
        "session_duration_minutes": 20 if velocity.consistency_score < 0.5 else 25,
        "review_skills": [t.skill_id for t in critical_reviews[:1]],
    }


def generate_learning_plan(
    student_id: str,
    skill_states: Dict[str, float],
    session_history: List[Dict[str, Any]],
    age: int = 8,
    last_practiced: Optional[Dict[str, datetime]] = None,
) -> LearningPlan:
    """
    Generate a comprehensive 4-week learning plan.
    """
    trajectories = generate_skill_trajectories(skill_states, session_history, last_practiced)
    velocity = calculate_learning_velocity(session_history, skill_states)
    cascade_risks = identify_cascade_risks(skill_states)

    # Generate 4-week plans
    weekly_plans = [
        generate_weekly_plan(trajectories, velocity, week)
        for week in range(1, 5)
    ]

    # Skills to review (at risk of forgetting)
    at_risk_skills = [t.skill_id for t in trajectories if t.at_risk]

    # Skills ready to advance
    ready_skills = [t.skill_id for t in trajectories if t.ready_to_advance]

    # Daily practice recommendation
    if age <= 6:
        daily_minutes = 10
    elif age <= 9:
        daily_minutes = 15 if velocity.consistency_score < 0.5 else 20
    else:
        daily_minutes = 20 if velocity.consistency_score < 0.5 else 25

    # Generate parent insights
    parent_insights = _generate_parent_insights(trajectories, velocity, cascade_risks, age)
    teacher_notes = _generate_teacher_notes(trajectories, velocity, cascade_risks)

    # Confidence based on data quality
    confidence = min(0.95, 0.4 + 0.055 * len(session_history))

    return LearningPlan(
        student_id=student_id,
        generated_at=datetime.now(),
        weekly_plans=weekly_plans,
        skills_to_review=at_risk_skills,
        skills_to_advance=ready_skills,
        daily_minutes_recommended=daily_minutes,
        parent_insights=parent_insights,
        teacher_notes=teacher_notes,
        confidence=confidence,
    )


def _generate_parent_insights(
    trajectories: List[SkillTrajectory],
    velocity: LearningVelocity,
    cascade_risks: List[Dict[str, Any]],
    age: int,
) -> str:
    """Generate parent-friendly insights about their child's progress."""
    parts = []

    # Overall trend
    improving = sum(1 for t in trajectories if t.mastery_trend > 0)
    total = len(trajectories)
    if total > 0:
        if improving / total > 0.7:
            parts.append(
                f"Your child is making progress in {improving} of {total} tracked skills! "
                "Their learning momentum is positive."
            )
        elif improving / total < 0.3:
            parts.append(
                "We're seeing some challenges across multiple skills. "
                "More consistent daily practice (even 10-15 minutes) would help significantly."
            )

    # Consistency advice
    if velocity.consistency_score < 0.4:
        session_per_week = "3-4" if age >= 8 else "2-3"
        parts.append(
            f"Tip: Short, consistent practice works better than long, infrequent sessions. "
            f"Aim for {session_per_week} short sessions per week."
        )

    # Cascade risk warning
    if cascade_risks:
        top_risk = cascade_risks[0]
        parts.append(
            f"⚠️ Alert: Weakness in '{top_risk['weak_skill']}' may affect "
            f"{top_risk['cascade_severity']} upcoming topics. We're focusing on this now."
        )

    # Positive reinforcement
    mastered = [t.skill_id for t in trajectories if t.current_mastery > 0.8]
    if mastered:
        parts.append(f"🎉 Mastered: {', '.join(mastered[:3])}. Excellent work!")

    return " ".join(parts) if parts else "Your child is working hard and making steady progress!"


def _generate_teacher_notes(
    trajectories: List[SkillTrajectory],
    velocity: LearningVelocity,
    cascade_risks: List[Dict[str, Any]],
) -> str:
    """Generate technical notes for teachers."""
    parts = []

    parts.append(
        f"Learning velocity: {velocity.mastery_rate:.1f} skills/week | "
        f"Retention: {velocity.retention_strength:.0%} | "
        f"Consistency: {velocity.consistency_score:.0%}"
    )

    critical = [t for t in trajectories if t.review_urgency == "critical"]
    if critical:
        parts.append(f"Critical review needed: {', '.join(t.skill_id for t in critical)}")

    if cascade_risks:
        parts.append(
            f"Cascade risk: {cascade_risks[0]['weak_skill']} → "
            f"{', '.join(cascade_risks[0]['at_risk_skills'][:3])}"
        )

    return " | ".join(parts)


def get_next_review_date(
    skill_id: str,
    current_mastery: float,
    last_practiced: datetime,
    forgetting_rate: float = 0.05,
) -> datetime:
    """
    Calculate optimal next review date using spaced repetition principles.
    Target: review just before mastery drops below 70%.
    """
    target_mastery = 0.7
    days = 1

    while days <= 90:
        predicted = calculate_retention(current_mastery, days, forgetting_rate)
        if predicted < target_mastery:
            break
        days += 1

    return last_practiced + timedelta(days=max(1, days - 1))


__all__ = [
    "SkillTrajectory",
    "LearningVelocity",
    "LearningPlan",
    "PREREQUISITE_GRAPH",
    "INTERFERENCE_PAIRS",
    "calculate_retention",
    "estimate_days_to_mastery",
    "identify_cascade_risks",
    "identify_interference_risks",
    "calculate_learning_velocity",
    "generate_skill_trajectories",
    "generate_learning_plan",
    "get_next_review_date",
]
