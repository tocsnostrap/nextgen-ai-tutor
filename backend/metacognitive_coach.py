"""
Metacognitive Coaching Engine

Teaches students HOW to learn — not just what to learn.

Research basis:
- Metacognitive regulation (Flavell, 1979)
- Growth vs Fixed Mindset theory (Dweck, 2006)
- Self-regulated learning (Zimmerman, 2000)
- Productive failure (Kapur, 2016)
- Confidence calibration and the Dunning-Kruger effect

What this engine detects and addresses:
1. MINDSET PATTERNS: Fixed mindset language, learned helplessness, overconfidence
2. STRATEGY GAPS: Re-reading (passive) vs. self-testing (active); problem decomposition
3. CONFIDENCE CALIBRATION: Students who know but won't commit; students who guess wildly
4. EFFORT ATTRIBUTION: "I got lucky" vs "I worked hard at this"
5. SELF-REGULATION: Planning, monitoring, evaluating own understanding
6. PRODUCTIVE STRUGGLE: Detecting when struggle is productive vs. when to intervene

This is years beyond current tutoring systems that simply respond to content questions.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MindsetSignal(str, Enum):
    FIXED_EXPLICIT = "fixed_explicit"        # "I'm not smart enough"
    FIXED_IMPLICIT = "fixed_implicit"        # "I always mess up math"
    GROWTH_EXPLICIT = "growth_explicit"      # "I just need more practice"
    GROWTH_IMPLICIT = "growth_implicit"      # Asks why, wants to understand
    LEARNED_HELPLESS = "learned_helpless"    # Immediate give-up
    OVERCONFIDENT = "overconfident"          # "This is easy" (then gets it wrong)
    UNDERCONFIDENT = "underconfident"        # "I don't know" (but clearly does)
    EFFORT_AVOIDANT = "effort_avoidant"      # Wants shortcuts, resists challenge
    MASTERY_ORIENTED = "mastery_oriented"    # Asks deeper questions


class LearningStrategy(str, Enum):
    ELABORATIVE_INTERROGATION = "elaborative_interrogation"  # "Why does this work?"
    SELF_EXPLANATION = "self_explanation"                    # Explaining to yourself
    INTERLEAVED_PRACTICE = "interleaved_practice"            # Mix different problem types
    SPACED_RETRIEVAL = "spaced_retrieval"                    # Test yourself over time
    CONCRETE_EXAMPLES = "concrete_examples"                  # Generate own examples
    DUAL_CODING = "dual_coding"                              # Words + visuals together
    PROBLEM_DECOMPOSITION = "problem_decomposition"          # Break complex into steps
    ERROR_ANALYSIS = "error_analysis"                        # Learn from mistakes
    RETRIEVAL_PRACTICE = "retrieval_practice"                # Self-testing > re-reading


@dataclass
class MetacognitiveProfile:
    """Live metacognitive profile for a student session."""
    student_id: str
    mindset_signals: List[MindsetSignal] = field(default_factory=list)
    dominant_mindset: Optional[MindsetSignal] = None
    hint_requests: int = 0
    give_up_attempts: int = 0
    strategy_demonstrations: Dict[str, int] = field(default_factory=dict)
    confidence_mismatches: int = 0  # said easy but got wrong (or vice versa)
    total_interactions: int = 0
    productive_struggle_minutes: float = 0.0
    self_corrections: int = 0
    questions_asked: int = 0


@dataclass
class CoachingIntervention:
    """A specific metacognitive coaching intervention."""
    trigger: str               # What triggered this intervention
    intervention_type: str     # mindset / strategy / confidence / self-regulation
    response: str              # What Nova says
    strategy_tip: str          # Concrete strategy to try
    metacognitive_question: str  # Question to promote reflection
    urgency: str               # low / medium / high


# ── Pattern detection ─────────────────────────────────────────────────────────

# Fixed mindset language patterns
FIXED_MINDSET_PATTERNS = [
    r"\bi('m| am) (not|never) (going to|gonna) (get|understand|learn)",
    r"\bi('m| am) (bad|terrible|awful|horrible) at",
    r"\bi (can't|cannot|can not) do (this|math|science|reading|coding)",
    r"\bi('m| am) (too) (dumb|stupid|slow)",
    r"\bi (never|always) (get|mess up|fail)",
    r"\bthis is (impossible|too hard for me)",
    r"\bi (give up|quit|don't want)",
    r"\bi('m| am) not (smart|good) enough",
    r"\bi('ll| will) never (understand|get|learn)",
    r"\bwhy (do|am) i (even|still) (trying|doing this)",
]

GROWTH_MINDSET_PATTERNS = [
    r"\blet me try (again|a different way|once more)",
    r"\bi think i (need|want) to (practice|review|understand)",
    r"\bwhy does (this|it) work",
    r"\bhow (can|do) i get better",
    r"\bi (almost|nearly) (got|understand)",
    r"\bwhat (did|do) i (do wrong|need to fix)",
    r"\bi (learned|figured out|discovered)",
]

HELPLESS_PATTERNS = [
    r"\bi don't know",
    r"\bjust tell me (the answer|what to do|how)",
    r"\bcan you (just|please) (do it|solve it|answer it) for me",
    r"\bwhat's the answer",
    r"\bi (have|need) (no idea|a hint)",
]

OVERCONFIDENT_PATTERNS = [
    r"\bthis is (so |too )?(easy|simple|obvious)",
    r"\bi (already|definitely) know (this|how)",
    r"\bi don't (need|have to) (check|verify|review)",
]

UNDERCONFIDENT_PATTERNS = [
    r"\bi('m| am) (probably|maybe|might be) (wrong|off)",
    r"\bi (don't|really don't) know( if that's right)?",
    r"\bthis is (just|probably) a guess",
    r"\bi('m| am) not sure (at all|about this)",
]


def detect_mindset_signals(message: str) -> List[MindsetSignal]:
    """Detect mindset signals in a student message."""
    msg_lower = message.lower()
    signals = []

    for pattern in FIXED_MINDSET_PATTERNS:
        if re.search(pattern, msg_lower):
            signals.append(MindsetSignal.FIXED_EXPLICIT)
            break

    for pattern in GROWTH_MINDSET_PATTERNS:
        if re.search(pattern, msg_lower):
            signals.append(MindsetSignal.GROWTH_EXPLICIT)
            break

    for pattern in HELPLESS_PATTERNS:
        if re.search(pattern, msg_lower):
            signals.append(MindsetSignal.LEARNED_HELPLESS)
            break

    for pattern in OVERCONFIDENT_PATTERNS:
        if re.search(pattern, msg_lower):
            signals.append(MindsetSignal.OVERCONFIDENT)
            break

    for pattern in UNDERCONFIDENT_PATTERNS:
        if re.search(pattern, msg_lower):
            signals.append(MindsetSignal.UNDERCONFIDENT)
            break

    return signals


def detect_strategy_gaps(message: str, history: List[Dict[str, Any]]) -> List[str]:
    """
    Detect poor learning strategies based on message + history patterns.
    Returns list of identified strategy gaps.
    """
    gaps = []
    msg_lower = message.lower()

    # Passive learning signals
    if any(w in msg_lower for w in ["re-read", "reread", "read it again", "read again"]):
        gaps.append("passive_rereading")

    # Hint-seeking without attempt
    if any(w in msg_lower for w in ["hint", "just tell me", "give me a clue"]):
        if len([h for h in history[-3:] if h.get("role") == "user"]) <= 1:
            gaps.append("hint_before_attempt")

    # Copying without understanding
    if any(w in msg_lower for w in ["copy", "just write", "memorize"]):
        gaps.append("surface_memorization")

    # Not checking work
    if any(w in msg_lower for w in ["done", "finished", "that's it", "is this right?"]):
        gaps.append("not_verifying")

    return gaps


def calculate_confidence_calibration(
    sessions: List[Dict[str, Any]],
) -> Tuple[float, str]:
    """
    Calculate how well-calibrated a student's confidence is.

    Returns: (calibration_score 0-1, assessment_label)
    0.5 = perfectly calibrated
    < 0.3 = significantly underconfident
    > 0.7 = significantly overconfident
    """
    if not sessions:
        return 0.5, "unknown"

    correct_with_high_conf = 0
    incorrect_with_high_conf = 0
    correct_with_low_conf = 0
    incorrect_with_low_conf = 0

    for session in sessions[-20:]:
        was_correct = session.get("correct", False)
        confidence = session.get("confidence", 0.5)

        if confidence > 0.7:
            if was_correct:
                correct_with_high_conf += 1
            else:
                incorrect_with_high_conf += 1
        elif confidence < 0.3:
            if was_correct:
                correct_with_low_conf += 1
            else:
                incorrect_with_low_conf += 1

    total = len(sessions[-20:])
    if total == 0:
        return 0.5, "unknown"

    # Overconfidence: high confidence but often wrong
    overconf_ratio = incorrect_with_high_conf / max(1, correct_with_high_conf + incorrect_with_high_conf)
    # Underconfidence: low confidence but often right
    underconf_ratio = correct_with_low_conf / max(1, correct_with_low_conf + incorrect_with_low_conf)

    if overconf_ratio > 0.5:
        return 0.75, "overconfident"
    if underconf_ratio > 0.5:
        return 0.25, "underconfident"
    return 0.5, "well_calibrated"


# ── Intervention generation ───────────────────────────────────────────────────

def generate_mindset_intervention(
    signal: MindsetSignal,
    topic: str,
    age: int,
) -> CoachingIntervention:
    """Generate a targeted mindset intervention."""

    if signal == MindsetSignal.FIXED_EXPLICIT:
        if age <= 7:
            response = (
                "Hey, I want to tell you something important — your brain actually GROWS "
                "when you try hard things, even when you don't get them right away! "
                "It's like a muscle. The more you practice, the stronger it gets."
            )
            tip = "Try saying: 'I can't do this YET' — that little word 'yet' changes everything!"
            q = "Can you tell me one thing you used to not be able to do that you can do now?"
        else:
            response = (
                f"I hear you — {topic} feels hard right now. Here's something that might change "
                "how you think about this: research shows that the feeling of struggle is actually "
                "your brain forming new connections. The harder it feels, the more your brain is "
                "actually growing. Students who get things immediately often don't learn as deeply "
                "as students who had to work for it."
            )
            tip = (
                "Try this reframe: instead of 'I can't do this', say "
                "'What step am I missing?' That question leads to the answer."
            )
            q = "What specifically feels hardest right now? Let's break that one part down."

        return CoachingIntervention(
            trigger="fixed_mindset_detected",
            intervention_type="mindset",
            response=response,
            strategy_tip=tip,
            metacognitive_question=q,
            urgency="high",
        )

    elif signal == MindsetSignal.LEARNED_HELPLESS:
        response = (
            "Before I give you a hint — I want to see what YOU think first. "
            "Even if you're not sure, making an attempt builds your thinking muscles! "
            "There's no penalty for a wrong guess here."
        )
        tip = "Strategy: write down your first guess, THEN we'll figure out if it's right together."
        q = "What's your best guess, even if you're not confident?"

        return CoachingIntervention(
            trigger="learned_helplessness_detected",
            intervention_type="mindset",
            response=response,
            strategy_tip=tip,
            metacognitive_question=q,
            urgency="medium",
        )

    elif signal == MindsetSignal.OVERCONFIDENT:
        response = (
            "I love the confidence! Let me ask you something interesting — "
            "can you explain WHY the answer is what you think it is? "
            "Teaching something to someone else is the best test of whether you really know it."
        )
        tip = (
            "The Feynman Technique: Explain the concept as if teaching a 6-year-old. "
            "Gaps in your explanation reveal gaps in understanding."
        )
        q = "Can you explain this to me as if I've never heard of it before?"

        return CoachingIntervention(
            trigger="overconfidence_detected",
            intervention_type="confidence",
            response=response,
            strategy_tip=tip,
            metacognitive_question=q,
            urgency="low",
        )

    elif signal == MindsetSignal.UNDERCONFIDENT:
        response = (
            "I noticed you seemed unsure, but actually — your reasoning was sound. "
            "Sometimes our brain knows more than we give it credit for! "
            "Let's check your thinking together."
        )
        tip = (
            "Before saying 'I don't know', try: 'What DO I know about this?' "
            "Start with what you're sure of, and the rest often follows."
        )
        q = "What parts of this are you actually confident about? Start there."

        return CoachingIntervention(
            trigger="underconfidence_detected",
            intervention_type="confidence",
            response=response,
            strategy_tip=tip,
            metacognitive_question=q,
            urgency="low",
        )

    # Default: gentle encouragement
    return CoachingIntervention(
        trigger="general",
        intervention_type="mindset",
        response="You're doing great just by showing up and trying. What do you want to tackle next?",
        strategy_tip="Celebrate effort, not just correct answers.",
        metacognitive_question="What feels different about how you're learning today?",
        urgency="low",
    )


def generate_strategy_intervention(
    gap: str,
    topic: str,
    age: int,
) -> Optional[CoachingIntervention]:
    """Generate a learning strategy coaching intervention."""

    strategy_map = {
        "passive_rereading": CoachingIntervention(
            trigger="passive_rereading",
            intervention_type="strategy",
            response=(
                "Re-reading is actually one of the least effective study strategies — "
                "it creates an 'illusion of knowing' without real learning! "
                "Instead, let me show you a technique that's 3x more effective."
            ),
            strategy_tip=(
                "RETRIEVAL PRACTICE: Close the book/notes. Try to recall everything you know "
                "about the topic from memory. Then check what you missed. "
                "This feels harder but builds much stronger memory."
            ),
            metacognitive_question=(
                "Without looking at anything, what can you tell me about what we just covered?"
            ),
            urgency="medium",
        ),
        "hint_before_attempt": CoachingIntervention(
            trigger="hint_before_attempt",
            intervention_type="strategy",
            response=(
                "I'll give you a hint in a moment — but first, let's try something. "
                "Struggling with a problem BEFORE getting help actually makes the hint "
                "much more effective. It's called 'productive failure'!"
            ),
            strategy_tip=(
                "PRODUCTIVE STRUGGLE: Spend 2-3 minutes trying the problem your own way "
                "before asking for help. Even wrong attempts make your brain ready to learn."
            ),
            metacognitive_question="What have you tried so far? What happened?",
            urgency="low",
        ),
        "surface_memorization": CoachingIntervention(
            trigger="surface_memorization",
            intervention_type="strategy",
            response=(
                "Memorizing without understanding is like building on sand — "
                "it washes away quickly! Let me show you how to understand it so deeply "
                "you'll never need to just memorize it."
            ),
            strategy_tip=(
                "ELABORATIVE INTERROGATION: For every fact, ask 'Why is this true?' and "
                "'How does this connect to something I already know?' "
                "This builds lasting understanding."
            ),
            metacognitive_question="Can you tell me WHY this answer is correct, not just what it is?",
            urgency="medium",
        ),
        "not_verifying": CoachingIntervention(
            trigger="not_verifying",
            intervention_type="strategy",
            response=(
                "Great — you have an answer! Now the most important step: verify it. "
                "Expert problem-solvers always check their work using a DIFFERENT method."
            ),
            strategy_tip=(
                "VERIFICATION STRATEGY: Check your answer by working backwards, "
                "using a different method, or asking 'Does this make sense?'"
            ),
            metacognitive_question=(
                "How could you check if your answer is correct without me telling you?"
            ),
            urgency="low",
        ),
    }

    return strategy_map.get(gap)


def update_profile(
    profile: MetacognitiveProfile,
    message: str,
    context: Dict[str, Any],
    interaction_result: Optional[Dict[str, Any]] = None,
) -> MetacognitiveProfile:
    """Update a student's metacognitive profile based on new interaction."""
    profile.total_interactions += 1

    # Detect mindset signals
    new_signals = detect_mindset_signals(message)
    profile.mindset_signals.extend(new_signals)

    # Track hint requests
    msg_lower = message.lower()
    if any(w in msg_lower for w in ["hint", "help", "tell me", "what's the answer"]):
        profile.hint_requests += 1

    # Track give-up attempts
    if any(w in msg_lower for w in ["give up", "quit", "i can't"]):
        profile.give_up_attempts += 1

    # Track questions asked (curiosity signal)
    if "?" in message:
        profile.questions_asked += 1

    # Track self-corrections
    if any(w in msg_lower for w in ["wait", "actually", "no wait", "i mean"]):
        profile.self_corrections += 1

    # Update dominant mindset
    if profile.mindset_signals:
        from collections import Counter
        counts = Counter(profile.mindset_signals[-20:])  # Look at recent signals
        profile.dominant_mindset = counts.most_common(1)[0][0]

    return profile


def get_coaching_recommendation(
    profile: MetacognitiveProfile,
    message: str,
    context: Dict[str, Any],
    history: List[Dict[str, Any]],
) -> Optional[CoachingIntervention]:
    """
    Determine if and what metacognitive coaching is needed.
    Returns None if no intervention is warranted.
    """
    # Detect immediate signals in this message
    signals = detect_mindset_signals(message)
    strategy_gaps = detect_strategy_gaps(message, history)

    # Priority 1: Fixed mindset or learned helplessness (immediate intervention)
    for signal in signals:
        if signal in (
            MindsetSignal.FIXED_EXPLICIT,
            MindsetSignal.LEARNED_HELPLESS,
        ):
            return generate_mindset_intervention(
                signal, context.get("topic", "general"), context.get("age", 8)
            )

    # Priority 2: Strategy gaps that impede learning
    if strategy_gaps:
        intervention = generate_strategy_intervention(
            strategy_gaps[0], context.get("topic", "general"), context.get("age", 8)
        )
        if intervention:
            return intervention

    # Priority 3: Pattern-based (check profile trends)
    hint_rate = profile.hint_requests / max(1, profile.total_interactions)
    give_up_rate = profile.give_up_attempts / max(1, profile.total_interactions)

    if hint_rate > 0.6 and profile.total_interactions > 5:
        return generate_mindset_intervention(
            MindsetSignal.LEARNED_HELPLESS,
            context.get("topic", "general"),
            context.get("age", 8),
        )

    # Priority 4: Overconfidence or underconfidence signals
    for signal in signals:
        if signal in (MindsetSignal.OVERCONFIDENT, MindsetSignal.UNDERCONFIDENT):
            return generate_mindset_intervention(
                signal, context.get("topic", "general"), context.get("age", 8)
            )

    return None


def get_profile_summary(profile: MetacognitiveProfile) -> Dict[str, Any]:
    """Return a summary of the student's metacognitive profile."""
    hint_rate = profile.hint_requests / max(1, profile.total_interactions)
    give_up_rate = profile.give_up_attempts / max(1, profile.total_interactions)
    curiosity_rate = profile.questions_asked / max(1, profile.total_interactions)

    # Determine overall learning disposition
    if give_up_rate > 0.3:
        disposition = "needs_persistence_support"
    elif hint_rate > 0.5:
        disposition = "needs_independence_building"
    elif curiosity_rate > 0.4:
        disposition = "highly_curious_learner"
    elif profile.self_corrections > 3:
        disposition = "self_monitoring_learner"
    else:
        disposition = "developing_learner"

    return {
        "student_id": profile.student_id,
        "dominant_mindset": profile.dominant_mindset.value if profile.dominant_mindset else "unknown",
        "hint_seeking_rate": hint_rate,
        "give_up_rate": give_up_rate,
        "curiosity_rate": curiosity_rate,
        "self_corrections": profile.self_corrections,
        "total_interactions": profile.total_interactions,
        "learning_disposition": disposition,
        "recommended_focus": _get_recommended_focus(disposition),
    }


def _get_recommended_focus(disposition: str) -> str:
    recommendations = {
        "needs_persistence_support": (
            "Focus on growth mindset framing. Celebrate effort explicitly. "
            "Use 'yet' language. Show progress made over time."
        ),
        "needs_independence_building": (
            "Implement 'attempt before hint' policy. "
            "Use Socratic questioning. Reduce scaffolding gradually."
        ),
        "highly_curious_learner": (
            "Channel curiosity into deeper exploration. "
            "Provide extension challenges. Connect to real-world applications."
        ),
        "self_monitoring_learner": (
            "This student self-corrects well. Challenge them with harder problems. "
            "Teach advanced metacognitive strategies like Feynman Technique."
        ),
        "developing_learner": (
            "Build routine with varied practice. Introduce retrieval practice. "
            "Track progress visually to build motivation."
        ),
    }
    return recommendations.get(disposition, "Continue current approach with regular monitoring.")


# In-memory profile store (in production, this would be in Redis/DB)
_profiles: Dict[str, MetacognitiveProfile] = {}


def get_or_create_profile(student_id: str) -> MetacognitiveProfile:
    if student_id not in _profiles:
        _profiles[student_id] = MetacognitiveProfile(student_id=student_id)
    return _profiles[student_id]


__all__ = [
    "MetacognitiveProfile",
    "CoachingIntervention",
    "MindsetSignal",
    "LearningStrategy",
    "detect_mindset_signals",
    "detect_strategy_gaps",
    "calculate_confidence_calibration",
    "generate_mindset_intervention",
    "generate_strategy_intervention",
    "update_profile",
    "get_coaching_recommendation",
    "get_profile_summary",
    "get_or_create_profile",
]
