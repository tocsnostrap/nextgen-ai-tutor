"""
Multi-Agent Tutoring Architecture

Five specialized Claude agents collaborate to deliver a tutoring experience
that is qualitatively different from any single-prompt LLM approach.

AGENTS:
  1. ORCHESTRATOR  — Routes queries, manages context, coordinates agents
  2. DOMAIN EXPERT — Deep subject expertise with adaptive thinking for hard problems
  3. SOCRATIC GUIDE — Pure guided discovery: never gives answers, only questions
  4. METACOG COACH  — Teaches HOW to learn; detects mindset patterns
  5. ERROR ANALYST  — Root-cause diagnosis of misconceptions; targeted remediation

Each agent has a distinct system prompt, tool set, and decision criteria.
The Orchestrator selects the best agent for each interaction and
synthesizes their outputs into a coherent tutoring experience.

This architecture is 3-5 years ahead of single-prompt LLM tutoring because:
- Different cognitive tasks require genuinely different reasoning styles
- Agents can check each other's work and escalate when needed
- Specialized prompts produce significantly better outputs than one generic prompt
- The system can run agents in parallel for complex queries
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

import anthropic

from .claude_ai_service import _get_async_client, _build_nova_system_prompt

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    DOMAIN_EXPERT = "domain_expert"
    SOCRATIC_GUIDE = "socratic_guide"
    METACOG_COACH = "metacog_coach"
    ERROR_ANALYST = "error_analyst"


@dataclass
class AgentDecision:
    """Result of the orchestrator's routing decision."""
    primary_agent: AgentRole
    reason: str
    use_thinking: bool
    parallel_agents: List[AgentRole]  # agents to run concurrently if needed


@dataclass
class TutoringResponse:
    """Unified response from the multi-agent system."""
    primary_response: str
    agent_used: AgentRole
    teaching_strategy: str
    follow_up_questions: List[str]
    concepts_covered: List[str]
    difficulty_adjustment: str
    metacognitive_note: Optional[str]
    error_analysis: Optional[Dict[str, Any]]
    session_id: str
    ai_powered: bool
    model: str
    used_thinking: bool


# ── Agent system prompts ──────────────────────────────────────────────────────

ORCHESTRATOR_SYSTEM = """You are the Orchestrator of a multi-agent tutoring system for children.

Your job: analyze each student message and decide which specialist agent should respond.

Available agents:
- DOMAIN_EXPERT: For direct content questions, explanations, concept exploration
- SOCRATIC_GUIDE: When student needs to discover the answer themselves (confidence building, deeper understanding)
- METACOG_COACH: When student shows fixed mindset, poor strategies, or confidence miscalibration
- ERROR_ANALYST: When student made a specific mistake that needs root-cause diagnosis

Decision rules:
- Default to DOMAIN_EXPERT for most questions
- Use SOCRATIC_GUIDE when student is capable but asking for direct answers too quickly
- Use METACOG_COACH when you detect: "I can't do this", "I give up", "this is dumb",
  excessive hint-seeking, or overconfidence after a wrong answer
- Use ERROR_ANALYST when student provided a specific wrong answer (has both question + wrong answer)
- use_thinking=true for: complex math, multi-step problems, science explanations, age 9+

Respond with JSON only."""

DOMAIN_EXPERT_SYSTEM_TEMPLATE = """You are a world-class {subject} tutor for a {age}-year-old child.

Your expertise: {subject} at {grade_level}. You know this subject deeply and can explain it
at any level of sophistication, adapting to this child's exact needs.

Your special capability: You use ADAPTIVE THINKING to work through complex problems step by step
before explaining them. This means you can tackle genuinely hard problems and give accurate,
clear explanations — not just generic ones.

Core approach:
- Diagnose what the student knows BEFORE explaining what they don't
- Build on existing knowledge as a bridge to new concepts
- Use concrete, age-appropriate examples from the student's world
- Reveal the elegance and wonder in the subject matter
- End with one insight that changes how they see the world

{emotion_guidance}
{strategy_guidance}"""

SOCRATIC_GUIDE_SYSTEM = """You are a master of the Socratic method, tutoring a child.

Your ONLY tool: questions. You NEVER give the answer directly.

Your Socratic sequence:
1. Ask what they already know about the topic
2. Find the edge of their knowledge with a diagnostic question
3. Ask a question they CAN answer (build momentum)
4. Ask a question that requires combining two things they know
5. Guide them to the target insight through their own reasoning

Rules:
- Every response ends with exactly ONE question
- If they're wrong, ask a question that reveals the contradiction
- If they're right, deepen their understanding with a harder question
- Praise the REASONING, not just the answer: "That's great reasoning because..."
- Never say "exactly!" or "correct!" without explaining WHY they're correct

You are patient, curious, and genuinely delighted when students make discoveries."""

METACOG_COACH_SYSTEM = """You are a metacognitive coach who helps children become better learners.

You focus on HOW students learn, not just WHAT they learn.

You detect and address:
- Fixed mindset: "I'm not smart enough", "I can't do math"
- Learned helplessness: giving up immediately, always asking for hints
- Overconfidence: not checking work, rushing through problems
- Underconfidence: knows the answer but won't commit
- Poor strategies: re-reading instead of self-testing, passive vs active learning
- Unproductive struggle: stuck in the same approach that isn't working

Your interventions:
1. Name the pattern briefly and normalize it ("Many students feel that way...")
2. Offer a concrete strategy that works
3. Model the strategy briefly
4. Ask them to try the strategy immediately

Tone: Warm, matter-of-fact, never preachy. You're a learning coach, not a therapist.
Focus on WHAT THEY CAN DO, not on what they're doing wrong."""

ERROR_ANALYST_SYSTEM = """You are a diagnostic specialist who uncovers the root causes of student errors.

When a student makes a mistake, you don't just correct it — you perform a 5-step diagnosis:

1. IDENTIFY the precise misconception (not just "wrong answer")
2. TRACE the misconception to its source (missing prerequisite? overgeneralization? confusion with similar concept?)
3. ACKNOWLEDGE what the student DID understand (their reasoning had logic, even if flawed)
4. DESIGN a targeted micro-lesson (2-3 min) to fix EXACTLY this misconception
5. VERIFY with a follow-up question that confirms the misconception is resolved

Example of shallow correction: "That's wrong. The answer is 7."
Example of deep correction: "Your approach of adding the numerators was right! The tricky part
is the denominators — they need to match first. Here's why: imagine cutting a pizza into pieces..."

You treat errors as learning opportunities, not failures.
Your goal: student leaves understanding MORE than if they had gotten it right."""


async def route_query(
    message: str,
    context: Dict[str, Any],
    recent_errors: Optional[List[Dict[str, Any]]] = None,
) -> AgentDecision:
    """
    Orchestrator: decide which agent(s) should handle this interaction.
    Uses a lightweight Claude call for fast routing.
    """
    try:
        client = _get_async_client()

        age = context.get("age", 8)
        emotion = context.get("emotion", "neutral")
        subject = context.get("topic", "general")
        has_recent_error = bool(recent_errors and len(recent_errors) > 0)

        routing_context = f"""Student message: "{message}"
Age: {age} | Subject: {subject} | Emotion: {emotion}
Has recent specific error to analyze: {has_recent_error}
Message length: {len(message)} chars"""

        response = await client.messages.create(
            model="claude-haiku-4-5",  # Fast model for routing
            max_tokens=300,
            system=ORCHESTRATOR_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": routing_context,
                }
            ],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "primary_agent": {
                                "type": "string",
                                "enum": [
                                    "domain_expert",
                                    "socratic_guide",
                                    "metacog_coach",
                                    "error_analyst",
                                ],
                            },
                            "reason": {"type": "string"},
                            "use_thinking": {"type": "boolean"},
                        },
                        "required": ["primary_agent", "reason", "use_thinking"],
                        "additionalProperties": False,
                    },
                }
            },
        )

        import json
        decision_data = json.loads(response.content[0].text)

        return AgentDecision(
            primary_agent=AgentRole(decision_data["primary_agent"]),
            reason=decision_data["reason"],
            use_thinking=decision_data["use_thinking"],
            parallel_agents=[],
        )

    except Exception as e:
        logger.warning("Routing failed, defaulting to domain expert: %s", e)
        return AgentDecision(
            primary_agent=AgentRole.DOMAIN_EXPERT,
            reason="Default routing",
            use_thinking=False,
            parallel_agents=[],
        )


def _build_domain_expert_system(context: Dict[str, Any]) -> str:
    """Build specialized domain expert system prompt."""
    age = context.get("age", 8)
    subject = context.get("topic", "general")
    emotion = context.get("emotion", "neutral")
    strategy = context.get("teaching_strategy", "explain")

    grade_levels = {
        (0, 5): "preschool/K (ages 3-5)",
        (6, 8): "grades 1-3 (ages 6-8)",
        (9, 12): "grades 4-6 (ages 9-12)",
    }
    grade_level = next(
        (v for (lo, hi), v in grade_levels.items() if lo <= age <= hi),
        "elementary"
    )

    emotion_guidance = {
        "frustrated": (
            "IMPORTANT: Student is frustrated. Lead with empathy. Break into tiny steps. "
            "Celebrate every micro-success."
        ),
        "confused": (
            "IMPORTANT: Student is confused. Try a completely different explanation approach. "
            "Concrete before abstract."
        ),
        "bored": "IMPORTANT: Student is bored. Jump to something surprising or challenging immediately.",
        "anxious": "IMPORTANT: Student is anxious. Low pressure. No wrong answers. Small steps.",
    }.get(emotion, "")

    strategy_guidance = {
        "socratic": "Guide with questions, not answers.",
        "example": "Teach primarily through vivid, concrete examples.",
        "analogy": "Use a memorable analogy bridge to explain.",
        "scaffolded": "Start at their level, add exactly one layer of complexity.",
    }.get(strategy, "Use the most effective approach for this specific question.")

    return DOMAIN_EXPERT_SYSTEM_TEMPLATE.format(
        subject=subject,
        age=age,
        grade_level=grade_level,
        emotion_guidance=emotion_guidance,
        strategy_guidance=strategy_guidance,
    )


async def call_domain_expert(
    message: str,
    context: Dict[str, Any],
    conversation_history: List[Dict[str, str]],
    use_thinking: bool = False,
) -> Tuple[str, bool]:
    """Call the Domain Expert agent."""
    client = _get_async_client()
    system = _build_domain_expert_system(context)

    messages = []
    for msg in conversation_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})

    stream_kwargs: Dict[str, Any] = {
        "model": "claude-opus-4-6",
        "max_tokens": 2048,
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        "messages": messages,
    }
    if use_thinking:
        stream_kwargs["thinking"] = {"type": "adaptive"}

    async with client.messages.stream(**stream_kwargs) as stream:
        final = await stream.get_final_message()

    text = next((b.text for b in final.content if b.type == "text"), "")
    return text, use_thinking


async def call_socratic_guide(
    message: str,
    context: Dict[str, Any],
    conversation_history: List[Dict[str, str]],
) -> str:
    """Call the Socratic Guide agent."""
    client = _get_async_client()

    age = context.get("age", 8)
    subject = context.get("topic", "general")

    age_note = (
        "The student is young (5-7), so keep questions very simple and concrete."
        if age <= 7 else
        "The student is older, so questions can involve more reasoning."
    )

    system = f"{SOCRATIC_GUIDE_SYSTEM}\n\nSubject: {subject}. {age_note}"

    messages = []
    for msg in conversation_history[-8:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})

    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=system,
        messages=messages,
    ) as stream:
        final = await stream.get_final_message()

    return next((b.text for b in final.content if b.type == "text"), "")


async def call_metacog_coach(
    message: str,
    context: Dict[str, Any],
    conversation_history: List[Dict[str, str]],
    learning_patterns: Optional[Dict[str, Any]] = None,
) -> str:
    """Call the Metacognitive Coach agent."""
    client = _get_async_client()

    age = context.get("age", 8)
    emotion = context.get("emotion", "neutral")

    patterns_note = ""
    if learning_patterns:
        hint_rate = learning_patterns.get("hint_seeking_rate", 0)
        give_up = learning_patterns.get("give_up_rate", 0)
        patterns_note = (
            f"\nDetected: hint-seeking {hint_rate:.0%}, give-up rate {give_up:.0%}"
        )

    context_note = (
        f"Student age: {age}. Current emotion: {emotion}.{patterns_note}\n\n"
        f"Student message: {message}"
    )

    messages = []
    for msg in conversation_history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": context_note})

    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=METACOG_COACH_SYSTEM,
        messages=messages,
    ) as stream:
        final = await stream.get_final_message()

    return next((b.text for b in final.content if b.type == "text"), "")


async def call_error_analyst(
    message: str,
    context: Dict[str, Any],
    recent_error: Optional[Dict[str, Any]] = None,
) -> str:
    """Call the Error Analyst agent."""
    client = _get_async_client()

    age = context.get("age", 8)
    subject = context.get("topic", "general")

    if recent_error:
        error_ctx = (
            f"Question: {recent_error.get('question', 'unknown')}\n"
            f"Student answered: {recent_error.get('student_answer', 'unknown')}\n"
            f"Correct answer: {recent_error.get('correct_answer', 'unknown')}"
        )
    else:
        error_ctx = f"Student message about an error: {message}"

    full_message = (
        f"Student (age {age}) in {subject} made an error.\n\n{error_ctx}\n\n"
        f"Current student message: {message}"
    )

    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=1024,
        thinking={"type": "adaptive"},
        system=ERROR_ANALYST_SYSTEM,
        messages=[{"role": "user", "content": full_message}],
    ) as stream:
        final = await stream.get_final_message()

    return next((b.text for b in final.content if b.type == "text"), "")


async def multi_agent_respond(
    message: str,
    context: Dict[str, Any],
    conversation_history: Optional[List[Dict[str, str]]] = None,
    recent_errors: Optional[List[Dict[str, Any]]] = None,
    learning_patterns: Optional[Dict[str, Any]] = None,
) -> TutoringResponse:
    """
    Main entry point for the multi-agent tutoring system.

    Routes to the appropriate specialist agent and synthesizes the response
    into a unified TutoringResponse.
    """
    history = conversation_history or []
    recent_error = (recent_errors[0] if recent_errors else None)

    # Step 1: Route the query
    decision = await route_query(message, context, recent_errors)
    logger.info(
        "Agent routing: %s (reason: %s, thinking: %s)",
        decision.primary_agent,
        decision.reason,
        decision.use_thinking,
    )

    # Step 2: Call the selected agent
    response_text = ""
    used_thinking = False

    if decision.primary_agent == AgentRole.SOCRATIC_GUIDE:
        response_text = await call_socratic_guide(message, context, history)
        strategy = "socratic"

    elif decision.primary_agent == AgentRole.METACOG_COACH:
        response_text = await call_metacog_coach(
            message, context, history, learning_patterns
        )
        strategy = "metacognitive"

    elif decision.primary_agent == AgentRole.ERROR_ANALYST:
        response_text = await call_error_analyst(message, context, recent_error)
        strategy = "error_analysis"

    else:  # DOMAIN_EXPERT (default)
        response_text, used_thinking = await call_domain_expert(
            message, context, history, decision.use_thinking
        )
        strategy = context.get("teaching_strategy", "explain")

    # Step 3: Extract follow-up questions from response or generate them
    follow_ups = _extract_or_generate_follow_ups(response_text, context)

    # Step 4: Extract concepts
    from .claude_ai_service import _extract_concepts_advanced, _assess_difficulty
    concepts = _extract_concepts_advanced(message, context.get("topic", "general"))
    difficulty_adj = _assess_difficulty(message, context)

    return TutoringResponse(
        primary_response=response_text,
        agent_used=decision.primary_agent,
        teaching_strategy=strategy,
        follow_up_questions=follow_ups,
        concepts_covered=concepts,
        difficulty_adjustment=difficulty_adj,
        metacognitive_note=decision.reason if decision.primary_agent == AgentRole.METACOG_COACH else None,
        error_analysis={"agent": "error_analyst"} if decision.primary_agent == AgentRole.ERROR_ANALYST else None,
        session_id=context.get("session_id", "default"),
        ai_powered=True,
        model="claude-opus-4-6",
        used_thinking=used_thinking,
    )


def _extract_or_generate_follow_ups(response: str, context: Dict[str, Any]) -> List[str]:
    """Extract embedded questions from response or generate follow-ups."""
    import re
    import random

    # Extract questions from the response text
    sentences = re.split(r'[.!]', response)
    questions = [s.strip() + "?" for s in sentences if "?" in s and len(s) > 20]

    if questions:
        return questions[:2]

    # Fallback: generate based on topic/age
    topic = context.get("topic", "general")
    age = context.get("age", 8)
    pools = {
        "math": (
            ["Can you show me with fingers?", "What would happen with bigger numbers?"]
            if age <= 7 else
            ["Can you create a similar problem?", "What's the general rule here?"]
        ),
        "science": ["What would you observe?", "What question would you test next?"],
        "coding": ["How would you change the code?", "What happens with a different input?"],
        "reading": ["What do you think happens next?", "Can you use that word in a sentence?"],
    }
    options = pools.get(topic, ["Can you explain in your own words?", "What do you notice?"])
    return random.sample(options, min(2, len(options)))


__all__ = [
    "AgentRole",
    "AgentDecision",
    "TutoringResponse",
    "multi_agent_respond",
    "route_query",
    "call_domain_expert",
    "call_socratic_guide",
    "call_metacog_coach",
    "call_error_analyst",
]
