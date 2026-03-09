"""
Causal Error Analysis Engine

Goes beyond "wrong answer" to understand WHY students make mistakes
and generate targeted, specific remediation.

Research basis:
- Misconception-based learning (Confrey, 1990)
- Knowledge-in-pieces theory (diSessa, 1988)
- Conceptual change theory (Posner et al., 1982)
- Diagnostic teaching (Bell, 1993)

Misconception taxonomy:
- OVERGENERALIZATION: Correct rule applied in wrong context ("add a zero when multiplying by 10")
- PROCEDURE_INVERSION: Steps applied in wrong order
- INCOMPLETE_SCHEMA: Missing a critical sub-concept
- INTERFERENCE: Similar concept bleeding into this one (e.g., + rules applied to ×)
- NOTATION_CONFUSION: Misreading symbols or notation
- PREREQUISITE_GAP: Foundational skill not yet mastered
- RANDOM_GUESS: No strategy visible (surface-level attempt)
- COMPUTATIONAL_ERROR: Correct strategy, arithmetic mistake
- CONCEPTUAL_REVERSAL: Gets concept backwards

Each error type requires a different intervention strategy.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MisconceptionType(str, Enum):
    OVERGENERALIZATION = "overgeneralization"
    PROCEDURE_INVERSION = "procedure_inversion"
    INCOMPLETE_SCHEMA = "incomplete_schema"
    INTERFERENCE = "interference"
    NOTATION_CONFUSION = "notation_confusion"
    PREREQUISITE_GAP = "prerequisite_gap"
    RANDOM_GUESS = "random_guess"
    COMPUTATIONAL_ERROR = "computational_error"
    CONCEPTUAL_REVERSAL = "conceptual_reversal"
    SIGN_ERROR = "sign_error"
    PLACE_VALUE_ERROR = "place_value_error"
    UNKNOWN = "unknown"


@dataclass
class ErrorRecord:
    """A single student error with full diagnostic context."""
    error_id: str
    student_id: str
    skill_id: str
    question: str
    student_answer: str
    correct_answer: str
    misconception_type: MisconceptionType
    misconception_description: str
    root_cause: str
    confidence: float       # How confident we are in this diagnosis
    timestamp: Any          # datetime


@dataclass
class ErrorPattern:
    """A recurring error pattern across multiple interactions."""
    pattern_id: str
    skill_id: str
    misconception_type: MisconceptionType
    frequency: int
    first_seen: Any         # datetime
    last_seen: Any          # datetime
    remediation_attempted: bool
    remediation_successful: Optional[bool]


@dataclass
class RemediationPlan:
    """A targeted plan to fix a specific misconception."""
    target_misconception: MisconceptionType
    skill_id: str
    step_1_acknowledge: str     # Validate what student got RIGHT
    step_2_reveal: str          # Surface the misconception gently
    step_3_contrast: str        # Show correct vs incorrect side by side
    step_4_practice: str        # One targeted practice item
    step_5_verify: str          # Question to confirm fix
    estimated_minutes: int
    prerequisite_review: Optional[str]


# ── Rule-based error diagnosis ────────────────────────────────────────────────

# Pattern-based misconception detectors for math
MATH_ERROR_PATTERNS: List[Dict[str, Any]] = [
    {
        "name": "fraction_add_denominators",
        "pattern": r"adding fractions .* added denominators",
        "description": "Student added denominators instead of finding common denominator",
        "type": MisconceptionType.PROCEDURE_INVERSION,
        "root_cause": (
            "Student overgeneralized the pattern from whole number addition "
            "to fractions. They see two numbers and add both."
        ),
        "example_error": "1/3 + 1/4 = 2/7 (wrong) → should be 7/12",
    },
    {
        "name": "multiply_add_rule",
        "pattern": r"multiplication .* added instead",
        "description": "Student added when they should have multiplied",
        "type": MisconceptionType.INTERFERENCE,
        "root_cause": (
            "Strong addition schema is interfering with multiplication. "
            "Student sees two numbers together and defaults to addition."
        ),
        "example_error": "3 × 4 = 7 (added) instead of 12",
    },
    {
        "name": "decimal_place_value",
        "pattern": r"decimal .* place value",
        "description": "Misunderstanding of decimal place value",
        "type": MisconceptionType.PLACE_VALUE_ERROR,
        "root_cause": (
            "Student treats decimal digits like whole number digits: "
            "thinks 0.12 > 0.9 because 12 > 9."
        ),
        "example_error": "0.12 > 0.9 (wrong) because 12 > 9",
    },
    {
        "name": "negative_sign_error",
        "pattern": r"negative .* (added|subtracted|wrong sign)",
        "description": "Sign error in negative number operations",
        "type": MisconceptionType.SIGN_ERROR,
        "root_cause": (
            "Confusion about sign rules: common error is 'two negatives make positive' "
            "applied incorrectly to subtraction."
        ),
        "example_error": "−3 − (−2) treated as −3 − 2 = −5 instead of −1",
    },
]

# Common misconception remediation templates by type
REMEDIATION_TEMPLATES: Dict[MisconceptionType, Dict[str, str]] = {
    MisconceptionType.OVERGENERALIZATION: {
        "reveal_approach": (
            "A rule you learned in one situation is being used in a new situation "
            "where it works differently. This is super common — even mathematicians do this! "
            "Let me show you the key difference."
        ),
        "contrast_approach": (
            "Let's look at two problems side by side: one where the rule DOES work, "
            "and one where it DOESN'T. Can you spot what's different?"
        ),
        "verify_approach": (
            "Now try this: where does the rule apply, and where doesn't it? "
            "Can you give me an example of each?"
        ),
    },
    MisconceptionType.PROCEDURE_INVERSION: {
        "reveal_approach": (
            "You have the right ingredients, but the steps got mixed up! "
            "This is like putting your socks on after your shoes — "
            "the parts are right but the order matters."
        ),
        "contrast_approach": (
            "Let me show you both ways — your order and the correct order — "
            "and we'll see what breaks when the steps are swapped."
        ),
        "verify_approach": (
            "Let's write out the steps in order. Which step goes first? Why?"
        ),
    },
    MisconceptionType.PREREQUISITE_GAP: {
        "reveal_approach": (
            "This problem needs a skill we haven't fully built yet. "
            "That's totally okay — let's quickly shore up that foundation "
            "and then this problem will make perfect sense."
        ),
        "contrast_approach": (
            "Let's solve a simpler version first, then the harder one will be obvious."
        ),
        "verify_approach": (
            "Let's do one of the foundational problems to make sure it's solid, "
            "then tackle the original one."
        ),
    },
    MisconceptionType.COMPUTATIONAL_ERROR: {
        "reveal_approach": (
            "Great news — your STRATEGY was actually correct! "
            "There was just a small calculation slip along the way. "
            "These happen to everyone, including mathematicians. "
            "Let's trace where the number went wrong."
        ),
        "contrast_approach": (
            "Let's redo just the calculation step slowly. "
            "Your setup was perfect."
        ),
        "verify_approach": (
            "Try the calculation again, and this time double-check each step. "
            "What do you get?"
        ),
    },
    MisconceptionType.INTERFERENCE: {
        "reveal_approach": (
            "Something really interesting happened here — your brain used a rule "
            "from a SIMILAR concept, but this concept has its own rules. "
            "Let's untangle them."
        ),
        "contrast_approach": (
            "Let's put these two concepts side by side. Here's what's the SAME, "
            "and here's the important DIFFERENCE that changes the answer."
        ),
        "verify_approach": (
            "I'll give you two mixed problems — one using each concept. "
            "Can you identify which rule applies to each?"
        ),
    },
    MisconceptionType.CONCEPTUAL_REVERSAL: {
        "reveal_approach": (
            "You understood the pieces, but the direction got flipped. "
            "Think of it like reading a map — if you flip North and South, "
            "you'll always end up in the wrong place!"
        ),
        "contrast_approach": (
            "Let's use a concrete example to set the direction right: "
            "what happens physically/in real life?"
        ),
        "verify_approach": (
            "Let's check with a number that makes the direction obvious: "
            "does your answer make sense?"
        ),
    },
}


def diagnose_error(
    question: str,
    student_answer: str,
    correct_answer: str,
    skill_id: str,
    student_history: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[MisconceptionType, str, float]:
    """
    Rule-based diagnosis of a student error.

    Returns: (misconception_type, description, confidence)
    This provides fast, local diagnosis before Claude's deep analysis.
    """
    student_history = student_history or []
    question_lower = question.lower()
    student_ans_lower = str(student_answer).lower()

    # Check for computational error: right approach but arithmetic mistake
    # (This would need actual computation verification in production)
    if _is_likely_computational_error(question, student_answer, correct_answer, skill_id):
        return (
            MisconceptionType.COMPUTATIONAL_ERROR,
            "Student used the correct strategy but made an arithmetic mistake",
            0.7,
        )

    # Check for sign error
    if _is_sign_error(student_answer, correct_answer):
        return (
            MisconceptionType.SIGN_ERROR,
            "Student got the magnitude right but the sign wrong",
            0.85,
        )

    # Check for place value error with decimals
    if "decimal" in question_lower or "." in str(student_answer):
        if _is_place_value_error(student_answer, correct_answer):
            return (
                MisconceptionType.PLACE_VALUE_ERROR,
                "Student confused decimal place values",
                0.75,
            )

    # Check for fraction addition error
    if "fraction" in skill_id or ("/" in question and "+" in question):
        if _is_fraction_denominator_error(student_answer, correct_answer, question):
            return (
                MisconceptionType.PROCEDURE_INVERSION,
                "Student added denominators instead of finding common denominator",
                0.8,
            )

    # Check for pattern-based rules
    for pattern in MATH_ERROR_PATTERNS:
        combined_text = f"{question_lower} {student_ans_lower}".lower()
        if re.search(pattern["pattern"], combined_text):
            return pattern["type"], pattern["description"], 0.6

    # Check if student has repeated this error
    similar_errors = [
        h for h in student_history[-10:]
        if h.get("skill") == skill_id and not h.get("correct")
    ]
    if len(similar_errors) >= 2:
        return (
            MisconceptionType.INCOMPLETE_SCHEMA,
            f"Student consistently struggles with {skill_id} — likely a schema gap",
            0.65,
        )

    # Default: unknown
    return MisconceptionType.UNKNOWN, "Unable to determine specific misconception type", 0.3


def _is_likely_computational_error(
    question: str, student_answer: str, correct_answer: str, skill_id: str
) -> bool:
    """Check if error is likely a simple computation mistake."""
    try:
        s_num = float(str(student_answer).replace(",", ""))
        c_num = float(str(correct_answer).replace(",", ""))
        # Off by a small amount relative to the answer = likely computational
        relative_error = abs(s_num - c_num) / max(1, abs(c_num))
        return relative_error < 0.3 and relative_error > 0.0
    except (ValueError, ZeroDivisionError):
        return False


def _is_sign_error(student_answer: str, correct_answer: str) -> bool:
    """Check if student got magnitude right but sign wrong."""
    try:
        s_num = float(str(student_answer))
        c_num = float(str(correct_answer))
        return abs(s_num) == abs(c_num) and s_num != c_num
    except ValueError:
        return False


def _is_place_value_error(student_answer: str, correct_answer: str) -> bool:
    """Check for decimal place value confusion."""
    try:
        s_num = float(str(student_answer))
        c_num = float(str(correct_answer))
        # Check if student answer is 10x or 100x off
        return (
            abs(s_num) == abs(c_num * 10) or
            abs(s_num) == abs(c_num / 10) or
            abs(s_num) == abs(c_num * 100) or
            abs(s_num) == abs(c_num / 100)
        )
    except ValueError:
        return False


def _is_fraction_denominator_error(
    student_answer: str, correct_answer: str, question: str
) -> bool:
    """Check if student added denominators when adding fractions."""
    if "/" not in question or "+" not in question:
        return False
    # If student answer has larger denominator than expected
    if "/" in str(student_answer):
        parts = str(student_answer).split("/")
        if len(parts) == 2:
            try:
                student_denom = int(parts[1])
                correct_parts = str(correct_answer).split("/")
                if len(correct_parts) == 2:
                    correct_denom = int(correct_parts[1])
                    return student_denom < correct_denom  # Added denoms = smaller denominator
            except ValueError:
                pass
    return False


def generate_remediation_plan(
    misconception_type: MisconceptionType,
    skill_id: str,
    question: str,
    student_answer: str,
    correct_answer: str,
    age: int = 8,
) -> RemediationPlan:
    """
    Generate a targeted remediation plan for a specific misconception.
    """
    template = REMEDIATION_TEMPLATES.get(
        misconception_type,
        REMEDIATION_TEMPLATES[MisconceptionType.PROCEDURE_INVERSION],
    )

    # Acknowledge what was right
    acknowledge = (
        f"Let's look at your thinking on this problem — "
        f"you showed you understand {skill_id}, and that's real progress!"
    )

    # Check if prerequisite review is needed
    prereq_review = None
    prereq_map = {
        "fractions_operations": "Make sure you can find common denominators first.",
        "algebra_intro": "Let's quickly review solving equations with one variable.",
        "multiplication_advanced": "Let's double-check multiplication facts to 12×12.",
    }
    prereq_review = prereq_map.get(skill_id)

    # Customize timing by age
    minutes = 3 if age <= 7 else 5 if age <= 9 else 7

    return RemediationPlan(
        target_misconception=misconception_type,
        skill_id=skill_id,
        step_1_acknowledge=acknowledge,
        step_2_reveal=template["reveal_approach"],
        step_3_contrast=template["contrast_approach"],
        step_4_practice=(
            f"Now let's try: a problem similar to '{question}' but even simpler, "
            f"so we can isolate exactly what went wrong."
        ),
        step_5_verify=template["verify_approach"],
        estimated_minutes=minutes,
        prerequisite_review=prereq_review,
    )


def format_remediation_for_student(
    plan: RemediationPlan,
    age: int = 8,
) -> str:
    """Format a remediation plan as a student-friendly explanation."""
    if age <= 7:
        return (
            f"Oops! Let's figure this out together. 🧩\n\n"
            f"{plan.step_1_acknowledge}\n\n"
            f"{plan.step_2_reveal}\n\n"
            f"{plan.step_4_practice}\n\n"
            f"{plan.step_5_verify}"
        )
    elif age <= 10:
        return (
            f"{plan.step_1_acknowledge}\n\n"
            f"**Here's what happened:** {plan.step_2_reveal}\n\n"
            f"**Let's compare:** {plan.step_3_contrast}\n\n"
            f"**Your turn:** {plan.step_4_practice}"
        )
    else:
        return (
            f"{plan.step_1_acknowledge}\n\n"
            f"**Diagnosis:** {plan.step_2_reveal}\n\n"
            f"**Side-by-side analysis:** {plan.step_3_contrast}\n\n"
            f"**Targeted practice:** {plan.step_4_practice}\n\n"
            f"**Verification:** {plan.step_5_verify}"
        )


class ErrorPatternTracker:
    """
    Tracks error patterns across sessions to identify persistent misconceptions.
    """

    def __init__(self):
        self._patterns: Dict[str, Dict[str, ErrorPattern]] = {}  # student_id -> skill -> pattern

    def record_error(
        self,
        student_id: str,
        skill_id: str,
        misconception: MisconceptionType,
        timestamp: Any,
    ) -> ErrorPattern:
        """Record an error and update pattern tracking."""
        from datetime import datetime

        now = timestamp or datetime.now()

        if student_id not in self._patterns:
            self._patterns[student_id] = {}

        key = f"{skill_id}_{misconception.value}"
        if key not in self._patterns[student_id]:
            self._patterns[student_id][key] = ErrorPattern(
                pattern_id=key,
                skill_id=skill_id,
                misconception_type=misconception,
                frequency=0,
                first_seen=now,
                last_seen=now,
                remediation_attempted=False,
                remediation_successful=None,
            )

        pattern = self._patterns[student_id][key]
        pattern.frequency += 1
        pattern.last_seen = now
        return pattern

    def get_persistent_misconceptions(
        self, student_id: str, min_frequency: int = 2
    ) -> List[ErrorPattern]:
        """Get misconceptions that have appeared multiple times."""
        if student_id not in self._patterns:
            return []

        return [
            p for p in self._patterns[student_id].values()
            if p.frequency >= min_frequency and not p.remediation_successful
        ]

    def mark_remediation_attempted(
        self, student_id: str, skill_id: str, misconception: MisconceptionType
    ):
        key = f"{skill_id}_{misconception.value}"
        if student_id in self._patterns and key in self._patterns[student_id]:
            self._patterns[student_id][key].remediation_attempted = True

    def mark_remediation_result(
        self,
        student_id: str,
        skill_id: str,
        misconception: MisconceptionType,
        success: bool,
    ):
        key = f"{skill_id}_{misconception.value}"
        if student_id in self._patterns and key in self._patterns[student_id]:
            self._patterns[student_id][key].remediation_successful = success

    def get_summary(self, student_id: str) -> Dict[str, Any]:
        """Get a summary of all tracked error patterns for a student."""
        if student_id not in self._patterns:
            return {"student_id": student_id, "patterns": [], "total_unique_errors": 0}

        patterns = list(self._patterns[student_id].values())
        persistent = [p for p in patterns if p.frequency >= 2]

        return {
            "student_id": student_id,
            "total_unique_errors": len(patterns),
            "persistent_misconceptions": len(persistent),
            "top_patterns": [
                {
                    "skill": p.skill_id,
                    "type": p.misconception_type.value,
                    "frequency": p.frequency,
                    "remediated": p.remediation_successful,
                }
                for p in sorted(patterns, key=lambda x: x.frequency, reverse=True)[:5]
            ],
        }


# Global tracker instance
error_tracker = ErrorPatternTracker()


__all__ = [
    "MisconceptionType",
    "ErrorRecord",
    "ErrorPattern",
    "RemediationPlan",
    "ErrorPatternTracker",
    "diagnose_error",
    "generate_remediation_plan",
    "format_remediation_for_student",
    "error_tracker",
]
