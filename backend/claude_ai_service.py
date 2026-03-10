"""
Claude AI Service - Advanced tutoring using Anthropic Claude API

Replaces OpenAI-based ai_service.py with Claude claude-opus-4-6.

Key innovations over current state of art:
- Adaptive thinking for complex problems (math proofs, science explanations)
- Streaming responses for real-time UX with no timeout risk
- Structured JSON outputs for reliable quiz/problem generation
- Prompt caching for student profiles (up to 90% cost reduction on repeat context)
- Causal error analysis (WHY students make mistakes, not just WHAT they got wrong)
- Dynamic problem generation tailored to ZPD (Zone of Proximal Development)
- Metacognitive coaching (teaching HOW to learn, not just WHAT)
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, AsyncIterator

import anthropic

logger = logging.getLogger(__name__)

_async_client: Optional[anthropic.AsyncAnthropic] = None


def _get_async_client() -> anthropic.AsyncAnthropic:
    global _async_client
    if _async_client is None:
        _async_client = anthropic.AsyncAnthropic()  # uses ANTHROPIC_API_KEY env var
    return _async_client


def _build_nova_system_prompt(context: Dict[str, Any], student_profile: str = "") -> str:
    """Build an advanced, emotionally-intelligent system prompt for Nova."""
    age = context.get("age", 8)
    subject = context.get("topic", "general")
    difficulty = context.get("difficulty", "intermediate")
    emotion = context.get("emotion", "neutral")
    strategy = context.get("teaching_strategy", "explain")
    bkt_mastery = context.get("bkt_mastery", {})
    learning_style = context.get("learning_style", "balanced")

    if age <= 5:
        communication = (
            "COMMUNICATION (Age 3-5): Max 3rd-grade vocabulary. 5-8 word sentences. "
            "Concrete tangible examples (toys, food, animals). Celebrate every attempt. "
            "Use repetition, rhythm, emojis. Max 2-3 short paragraphs."
        )
        grade_context = "preschool/kindergarten"
    elif age <= 8:
        communication = (
            "COMMUNICATION (Age 6-8): Warm, friendly tone. Real-world relatable examples. "
            "Numbered step-by-step breakdowns. Use visual language ('imagine...', 'picture this...'). "
            "Celebrate genuine progress. Max 4 paragraphs."
        )
        grade_context = "early elementary (grades 1-3)"
    else:
        communication = (
            "COMMUNICATION (Age 9-12): Intellectually engaging, respectful. "
            "Challenge assumptions with thought-provoking questions. Connect concepts to bigger ideas. "
            "Precise vocabulary but define new terms. Foster metacognitive awareness. Max 6 paragraphs."
        )
        grade_context = "upper elementary (grades 4-6)"

    emotion_layer = {
        "frustrated": (
            "⚠️ STUDENT IS FRUSTRATED. Lead with validation. Break into smallest possible steps. "
            "Celebrate any micro-progress. Do NOT add complexity."
        ),
        "confused": (
            "⚠️ STUDENT IS CONFUSED. Use a completely DIFFERENT approach than before. "
            "Concrete examples first, abstraction last."
        ),
        "bored": (
            "⚠️ STUDENT IS BORED. Make it immediately surprising or challenging. "
            "Skip what they already know."
        ),
        "anxious": (
            "⚠️ STUDENT IS ANXIOUS. Remove all pressure. Normalize struggle. "
            "Frame mistakes as data, not failure."
        ),
        "excited": "🎯 STUDENT IS EXCITED. Match their energy! Channel it into deeper exploration.",
        "confident": (
            "🎯 STUDENT IS CONFIDENT. Push to edge of comfort zone with a harder challenge."
        ),
    }.get(emotion, "Student appears ready to learn.")

    strategy_layer = {
        "socratic": (
            "PEDAGOGY: PURE SOCRATIC METHOD. Never give the answer directly. "
            "Ask precisely targeted questions guiding the student to discover the answer. "
            "Each question reveals one layer of understanding."
        ),
        "example": (
            "PEDAGOGY: CONCRETE EXAMPLES FIRST. 2-3 vivid relatable examples before any abstraction. "
            "Make examples progressively more complex."
        ),
        "analogy": (
            "PEDAGOGY: ANALOGICAL REASONING. Build a precise analogy bridge between what the "
            "student already knows and the new concept."
        ),
        "metacognitive": (
            "PEDAGOGY: METACOGNITIVE COACHING. Focus on HOW the student is thinking. "
            "Ask them to explain reasoning, identify confusion, plan next steps."
        ),
        "error_analysis": (
            "PEDAGOGY: ERROR-BASED LEARNING. Student made a mistake. Find the exact misconception. "
            "Design a micro-lesson targeting ONLY that misconception."
        ),
        "scaffolded": (
            "PEDAGOGY: SCAFFOLDED LEARNING. Start at student's current level. "
            "Add ONE layer of complexity at a time. Remove scaffolds as mastery increases."
        ),
    }.get(strategy, "Adapt your approach to best serve this student's current needs.")

    knowledge_context = ""
    if bkt_mastery:
        strong = [k for k, v in bkt_mastery.items() if v > 0.7]
        weak = [k for k, v in bkt_mastery.items() if v < 0.4]
        if strong:
            knowledge_context += f"\nStudent STRENGTHS (leverage): {', '.join(strong[:3])}"
        if weak:
            knowledge_context += f"\nStudent GAPS (don't assume known): {', '.join(weak[:3])}"

    profile_section = (
        f"\n\n## STUDENT PROFILE (from past sessions):\n{student_profile}"
        if student_profile else ""
    )

    return f"""You are **Nova**, the world's most advanced AI tutor for children. You combine the warmth of a beloved teacher, the expertise of a PhD, the creativity of a game designer, and the empathy of a counselor.

## STUDENT CONTEXT
- Age: {age} | Level: {grade_context} | Subject: {subject}
- Difficulty: {difficulty} | Learning style: {learning_style}
{knowledge_context}

## COMMUNICATION
{communication}

## EMOTIONAL STATE
{emotion_layer}

## TEACHING APPROACH
{strategy_layer}

## CORE PRINCIPLES
1. **Every child is capable** — never hint something is "too hard for you"
2. **Mistakes are data** — analyze errors diagnostically, never judgmentally
3. **Zone of Proximal Development** — pitch just slightly above current mastery
4. **Metacognitive scaffolding** — help students understand their own thinking
5. **Intrinsic motivation** — connect learning to genuine interests and goals
6. **Scientific accuracy** — never simplify to the point of inaccuracy
7. **Specificity** — "Great job figuring out 3×4=12!" beats "Good work!"

## RESPONSE FORMAT
- **Bold** key terms and important concepts
- Numbered lists for step-by-step processes
- End with ONE compelling follow-up question or mini-challenge (not multiple)
- Quality over quantity — be as concise as the topic allows
{profile_section}"""


async def generate_tutor_response(
    message: str,
    context: Dict[str, Any],
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Generate a tutoring response using Claude claude-opus-4-6.

    Uses adaptive thinking for complex problems, streaming for reliability,
    and prompt caching for student profiles.
    """
    try:
        client = _get_async_client()
        student_profile = context.get("student_memory", "")
        system_prompt = _build_nova_system_prompt(context, student_profile)

        messages = []
        if conversation_history:
            for msg in conversation_history[-12:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })
        messages.append({"role": "user", "content": message})

        needs_deep_thinking = _requires_deep_thinking(message, context)

        stream_kwargs: Dict[str, Any] = {
            "model": "claude-opus-4-6",
            "max_tokens": 2048,
            "system": [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},  # cache the system prompt
                }
            ],
            "messages": messages,
        }
        if needs_deep_thinking:
            stream_kwargs["thinking"] = {"type": "adaptive"}

        async with client.messages.stream(**stream_kwargs) as stream:
            final_message = await stream.get_final_message()

        response_text = ""
        for block in final_message.content:
            if block.type == "text":
                response_text = block.text
                break

        return {
            "response": response_text,
            "teaching_strategy": context.get("teaching_strategy", "explain"),
            "follow_up_questions": _generate_contextual_follow_ups(message, context),
            "concepts_covered": _extract_concepts_advanced(
                message, context.get("topic", "general")
            ),
            "difficulty_adjustment": _assess_difficulty(message, context),
            "session_id": context.get("session_id", "default"),
            "ai_powered": True,
            "model": "claude-opus-4-6",
            "used_thinking": needs_deep_thinking,
        }

    except anthropic.APIConnectionError as e:
        logger.error("Claude API connection error: %s", e)
        return None
    except anthropic.RateLimitError as e:
        logger.error("Claude API rate limit: %s", e)
        return None
    except anthropic.APIStatusError as e:
        logger.error("Claude API error %d: %s", e.status_code, e.message)
        return None
    except Exception as e:
        logger.error("Unexpected error in generate_tutor_response: %s", e)
        return None


async def stream_tutor_response(
    message: str,
    context: Dict[str, Any],
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> AsyncIterator[str]:
    """
    Stream a tutoring response token by token for real-time display.
    Yields text chunks as they arrive from Claude.
    """
    client = _get_async_client()
    student_profile = context.get("student_memory", "")
    system_prompt = _build_nova_system_prompt(context, student_profile)

    messages = []
    if conversation_history:
        for msg in conversation_history[-12:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })
    messages.append({"role": "user", "content": message})

    needs_deep_thinking = _requires_deep_thinking(message, context)

    stream_kwargs: Dict[str, Any] = {
        "model": "claude-opus-4-6",
        "max_tokens": 2048,
        "system": [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": messages,
    }
    if needs_deep_thinking:
        stream_kwargs["thinking"] = {"type": "adaptive"}

    try:
        async with client.messages.stream(**stream_kwargs) as stream:
            async for text in stream.text_stream:
                yield text
    except Exception as e:
        logger.error("Streaming error: %s", e)
        yield "I'm having a connection issue. Let me help you directly: "


async def generate_quiz_claude(
    topic: str,
    difficulty: str = "intermediate",
    num_questions: int = 3,
    age: int = 8,
    student_weaknesses: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Generate a personalized quiz with structured outputs.
    Targets student-specific weaknesses when provided.
    Wrong answers are pedagogically crafted (common misconceptions, not random).
    """
    try:
        client = _get_async_client()

        level_map = {(0, 5): "preschool/K", (6, 8): "grades 1-3", (9, 20): "grades 4-6"}
        level = next((v for (lo, hi), v in level_map.items() if lo <= age <= hi), "elementary")

        weakness_ctx = (
            f"\nFOCUS AREAS (student struggles with): {', '.join(student_weaknesses)}"
            if student_weaknesses else ""
        )

        prompt = f"""Create a {num_questions}-question multiple choice quiz about **{topic}** for a {age}-year-old ({level}) at **{difficulty}** difficulty.
{weakness_ctx}

Requirements:
- Test SPECIFIC concepts, not general knowledge
- Wrong answers must be PLAUSIBLE (common misconceptions, not obviously wrong)
- Explanations should teach, not just state the correct answer
- Mix recall, application, and reasoning questions
- Questions should build conceptually on each other"""

        response = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2000,
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "topic": {"type": "string"},
                            "questions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "question": {"type": "string"},
                                        "options": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "correct_answer": {"type": "integer"},
                                        "explanation": {"type": "string"},
                                        "concept_tested": {"type": "string"},
                                        "difficulty_level": {"type": "string"},
                                    },
                                    "required": [
                                        "question",
                                        "options",
                                        "correct_answer",
                                        "explanation",
                                        "concept_tested",
                                        "difficulty_level",
                                    ],
                                    "additionalProperties": False,
                                },
                            },
                            "estimated_minutes": {"type": "integer"},
                            "learning_objectives": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": [
                            "title",
                            "topic",
                            "questions",
                            "estimated_minutes",
                            "learning_objectives",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            messages=[{"role": "user", "content": prompt}],
        )

        quiz_data = json.loads(response.content[0].text)
        quiz_data.update(
            {"ai_generated": True, "model": "claude-opus-4-6", "difficulty": difficulty}
        )
        return quiz_data

    except Exception as e:
        logger.error("Quiz generation failed: %s", e)
        return None


async def analyze_student_error(
    student_answer: str,
    correct_answer: str,
    question: str,
    topic: str,
    age: int = 8,
) -> Dict[str, Any]:
    """
    Deep causal analysis of a student error using Claude's adaptive thinking.

    Returns root cause, misconception type, targeted micro-lesson remediation.
    This goes far beyond "wrong answer" — it understands WHY and HOW to fix it.
    """
    try:
        client = _get_async_client()

        prompt = f"""A student (age {age}) made an error. Perform a deep diagnostic analysis.

**Question:** {question}
**Student's Answer:** {student_answer}
**Correct Answer:** {correct_answer}
**Topic:** {topic}

Analyze:
1. ROOT CAUSE of the error (not just "they got it wrong")
2. Specific MISCONCEPTION revealed
3. PREREQUISITE KNOWLEDGE that may be missing
4. TARGETED MICRO-LESSON (3-5 min) to fix exactly this misconception
5. CONFIRMATION QUESTION to verify the fix worked"""

        response = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1500,
            thinking={"type": "adaptive"},
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "root_cause": {"type": "string"},
                            "misconception_type": {"type": "string"},
                            "misconception_description": {"type": "string"},
                            "missing_prerequisites": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "targeted_remediation": {"type": "string"},
                            "remediation_example": {"type": "string"},
                            "confirmation_question": {"type": "string"},
                            "severity": {"type": "string"},
                        },
                        "required": [
                            "root_cause",
                            "misconception_type",
                            "misconception_description",
                            "targeted_remediation",
                            "confirmation_question",
                            "severity",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            messages=[{"role": "user", "content": prompt}],
        )

        # Get the last text block (adaptive thinking puts thinking blocks first)
        text_block = next(
            (b for b in reversed(response.content) if b.type == "text"), None
        )
        if not text_block:
            raise ValueError("No text block in response")

        analysis = json.loads(text_block.text)
        analysis["analyzed_by"] = "claude-opus-4-6"
        return analysis

    except Exception as e:
        logger.error("Error analysis failed: %s", e)
        return {
            "root_cause": "Unable to analyze at this time",
            "misconception_type": "unknown",
            "misconception_description": "",
            "missing_prerequisites": [],
            "targeted_remediation": f"Let's review {topic} from the beginning",
            "remediation_example": "",
            "confirmation_question": "Can you try a similar problem?",
            "severity": "unknown",
        }


async def generate_personalized_problem(
    topic: str,
    skill_level: float,
    student_interests: List[str],
    age: int = 8,
    recent_errors: Optional[List[str]] = None,
    problem_type: str = "practice",
) -> Dict[str, Any]:
    """
    Generate a problem dynamically tailored to the exact student.

    ZPD targeting: problem pitched at just the right challenge level.
    Interest-based context: uses student's own interests for engagement.
    Error-targeted: addresses recent mistake patterns.
    """
    try:
        client = _get_async_client()

        zpd_offset = {"warmup": -0.1, "practice": 0.05, "challenge": 0.15}
        target = max(0.0, min(1.0, skill_level + zpd_offset.get(problem_type, 0.05)))
        diff_desc = (
            "easy" if target < 0.3 else
            "medium" if target < 0.6 else
            "hard" if target < 0.8 else "expert"
        )

        interests_str = ", ".join(student_interests[:3]) if student_interests else "general topics"
        error_ctx = (
            f"\nRecent mistakes to target: {', '.join(recent_errors[:2])}"
            if recent_errors else ""
        )

        prompt = f"""Create ONE perfect practice problem for a {age}-year-old student.

Topic: **{topic}**
Student mastery: {skill_level:.0%} → target difficulty: {diff_desc}
Student interests: {interests_str}
Problem type: {problem_type}{error_ctx}

Design a problem that:
1. Is set in a context the student will find genuinely interesting (use their interests!)
2. Tests exactly the right level of understanding for their ZPD
3. Has a clear, unambiguous answer
4. Includes 3 graduated hints if student gets stuck
5. Connects to a real-world application"""

        response = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1000,
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "problem_text": {"type": "string"},
                            "context_story": {"type": "string"},
                            "answer": {"type": "string"},
                            "solution_steps": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "hints": {"type": "array", "items": {"type": "string"}},
                            "real_world_connection": {"type": "string"},
                            "follow_up_problem": {"type": "string"},
                        },
                        "required": [
                            "problem_text",
                            "answer",
                            "hints",
                            "solution_steps",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            messages=[{"role": "user", "content": prompt}],
        )

        problem = json.loads(response.content[0].text)
        problem.update(
            {
                "topic": topic,
                "difficulty_level": diff_desc,
                "problem_type": problem_type,
                "ai_generated": True,
                "model": "claude-opus-4-6",
            }
        )
        return problem

    except Exception as e:
        logger.error("Problem generation failed: %s", e)
        return {
            "problem_text": f"Practice problem for {topic}",
            "answer": "Ask Nova for help",
            "hints": ["Take your time", "Break it into steps", "Ask Nova for help"],
            "solution_steps": [],
            "topic": topic,
            "difficulty_level": "medium",
            "ai_generated": False,
        }


async def generate_metacognitive_coaching(
    student_message: str,
    context: Dict[str, Any],
    learning_patterns: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate metacognitive coaching — teaching HOW to learn.

    Detects: fixed/growth mindset patterns, confidence miscalibration,
    poor study strategies, productive vs unproductive struggle.
    """
    try:
        client = _get_async_client()

        age = context.get("age", 8)
        topic = context.get("topic", "general")
        emotion = context.get("emotion", "neutral")

        patterns_ctx = ""
        if learning_patterns:
            hint_rate = learning_patterns.get("hint_seeking_rate", 0)
            give_up = learning_patterns.get("give_up_rate", 0)
            conf_cal = learning_patterns.get("confidence_calibration", 0.5)
            patterns_ctx = (
                f"\nLearning patterns:\n"
                f"- Hint-seeking rate: {hint_rate:.0%}\n"
                f"- Give-up rate: {give_up:.0%}\n"
                f"- Confidence calibration: {conf_cal:.0%} (0=under, 1=over)"
            )

        prompt = f"""Analyze this student's message and provide metacognitive coaching.

Student (age {age}): "{student_message}"
Subject: {topic} | Emotional state: {emotion}{patterns_ctx}

Identify:
1. What THINKING STRATEGY are they using (or missing)?
2. What MINDSET patterns are present? (fixed/growth, confidence calibration)
3. What LEARNING STRATEGY would help most right now?
4. What question makes them reflect on their own thinking?

Provide: A supportive coaching response (NOT preachy) + one powerful metacognitive question."""

        response = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=800,
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "mindset_detected": {"type": "string"},
                            "strategy_gap": {"type": "string"},
                            "coaching_response": {"type": "string"},
                            "metacognitive_question": {"type": "string"},
                            "recommended_strategy": {"type": "string"},
                            "strategy_tip": {"type": "string"},
                        },
                        "required": [
                            "coaching_response",
                            "metacognitive_question",
                            "recommended_strategy",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            messages=[{"role": "user", "content": prompt}],
        )

        coaching = json.loads(response.content[0].text)
        coaching["ai_powered"] = True
        return coaching

    except Exception as e:
        logger.error("Metacognitive coaching failed: %s", e)
        return {
            "coaching_response": "Let's think about how you're approaching this.",
            "metacognitive_question": "What strategy did you try first? What happened?",
            "recommended_strategy": "break_down_problem",
            "ai_powered": False,
        }


async def generate_learning_trajectory(
    student_id: str,
    skill_states: Dict[str, float],
    session_history: List[Dict[str, Any]],
    age: int = 8,
    target_skills: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate a personalized learning trajectory forecast.

    Predicts: mastery timelines, upcoming struggle points, optimal next topics.
    Produces: weekly learning plan with confidence intervals.
    """
    try:
        client = _get_async_client()

        # Summarize session data for the prompt
        recent_accuracy = _calculate_recent_accuracy(session_history)
        mastery_summary = {
            k: f"{v:.0%}" for k, v in sorted(
                skill_states.items(), key=lambda x: x[1]
            )[:10]
        }

        targets_ctx = (
            f"\nTarget skills to master: {', '.join(target_skills)}" if target_skills else ""
        )

        prompt = f"""Analyze this student's learning data and generate a trajectory forecast.

Student age: {age}
Recent accuracy: {recent_accuracy:.0%}
Current skill mastery levels: {json.dumps(mastery_summary, indent=2)}
Sessions completed: {len(session_history)}{targets_ctx}

Generate:
1. A 4-week learning plan with specific weekly goals
2. Skills at risk of regression (not practiced recently)
3. Skills ready to level up (mastery > 75%)
4. Predicted mastery timeline for 3 key skills
5. Parent/teacher alert if any concerning patterns detected
6. Optimal daily practice duration recommendation"""

        response = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2000,
            thinking={"type": "adaptive"},
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "four_week_plan": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "week": {"type": "integer"},
                                        "focus_skills": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "weekly_goal": {"type": "string"},
                                        "recommended_sessions": {"type": "integer"},
                                    },
                                    "required": [
                                        "week",
                                        "focus_skills",
                                        "weekly_goal",
                                        "recommended_sessions",
                                    ],
                                    "additionalProperties": False,
                                },
                            },
                            "skills_at_risk": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "skills_ready_to_level_up": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "mastery_predictions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "skill": {"type": "string"},
                                        "current_mastery": {"type": "string"},
                                        "predicted_mastery_2weeks": {"type": "string"},
                                        "predicted_mastery_4weeks": {"type": "string"},
                                    },
                                    "required": [
                                        "skill",
                                        "current_mastery",
                                        "predicted_mastery_2weeks",
                                        "predicted_mastery_4weeks",
                                    ],
                                    "additionalProperties": False,
                                },
                            },
                            "parent_alert": {"type": "string"},
                            "daily_practice_minutes": {"type": "integer"},
                            "overall_assessment": {"type": "string"},
                        },
                        "required": [
                            "four_week_plan",
                            "skills_at_risk",
                            "skills_ready_to_level_up",
                            "mastery_predictions",
                            "daily_practice_minutes",
                            "overall_assessment",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            messages=[{"role": "user", "content": prompt}],
        )

        text_block = next(
            (b for b in reversed(response.content) if b.type == "text"), None
        )
        trajectory = json.loads(text_block.text)
        trajectory["generated_by"] = "claude-opus-4-6"
        trajectory["student_id"] = student_id
        return trajectory

    except Exception as e:
        logger.error("Trajectory generation failed: %s", e)
        return {
            "four_week_plan": [],
            "skills_at_risk": [],
            "skills_ready_to_level_up": [],
            "mastery_predictions": [],
            "daily_practice_minutes": 20,
            "overall_assessment": "Learning data is being collected.",
            "student_id": student_id,
        }


async def generate_whiteboard_instructions(
    concept: str,
    subject: str = "math",
    age: int = 8,
) -> Optional[Dict[str, Any]]:
    """Generate step-by-step visual whiteboard instructions using Claude."""
    try:
        client = _get_async_client()

        prompt = f"""Create step-by-step visual whiteboard instructions to explain "{concept}" in {subject} for a {age}-year-old.

Requirements:
- Start with the simplest visual representation
- Build complexity step by step
- Use colors strategically (warm for key concepts, cool for context)
- Include visual analogies where helpful
- Max 8 steps

Return JSON:
{{
  "title": "Concept title",
  "steps": [
    {{
      "instruction": "What tutor says while drawing",
      "type": "text|shape|equation|arrow|highlight",
      "content": "Text/equation to display",
      "x": 100, "y": 100,
      "color": "#hex"
    }}
  ]
}}"""

        response = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(content)

    except Exception as e:
        logger.error("Whiteboard generation failed: %s", e)
        return None


# ── Utility helpers ──────────────────────────────────────────────────────────


def _requires_deep_thinking(message: str, context: Dict[str, Any]) -> bool:
    """Determine whether adaptive thinking should be enabled."""
    msg_lower = message.lower()
    age = context.get("age", 8)
    subject = context.get("topic", "").lower()

    deep_keywords = [
        "prove", "why does", "explain why", "how does", "derive",
        "solve", "calculate", "proof", "theorem", "what if",
        "compare", "analyze", "algebra", "geometry", "fraction",
        "photosynthesis", "ecosystem", "hypothesis", "experiment",
        "algorithm", "debug", "recursion", "function", "equation",
    ]
    if age >= 9 and any(w in msg_lower for w in deep_keywords):
        return True
    if subject in ("math", "science", "coding") and age >= 8:
        if any(w in msg_lower for w in ["why", "how", "explain", "solve", "prove"]):
            return True
    return False


def _assess_difficulty(message: str, context: Dict[str, Any]) -> str:
    msg_lower = message.lower()
    emotion = context.get("emotion", "neutral")

    if emotion in ("frustrated", "confused", "anxious") or any(
        w in msg_lower for w in ["too hard", "don't get", "confused", "lost", "stuck"]
    ):
        return "decrease"
    if emotion in ("bored", "confident") or any(
        w in msg_lower for w in ["too easy", "boring", "already know", "challenge"]
    ):
        return "increase"
    return "maintain"


def _generate_contextual_follow_ups(message: str, context: Dict[str, Any]) -> List[str]:
    import random

    topic = context.get("topic", "general")
    age = context.get("age", 8)
    strategy = context.get("teaching_strategy", "explain")

    if strategy == "socratic":
        return [
            "What do you think would happen if we changed one thing?",
            "How does this connect to something you already know?",
        ]

    pools = {
        "math": {
            "young": ["Can you draw a picture?", "Show me with your fingers!", "What comes next?"],
            "middle": ["Can you make up a similar problem?", "Where do you see this in real life?"],
            "older": ["What's the general rule?", "Can you prove this another way?"],
        },
        "science": {
            "young": ["What do you observe?", "What would happen if...?"],
            "middle": ["What question would you test next?", "Can you think of another example?"],
            "older": ["What's the underlying mechanism?", "What evidence would disprove this?"],
        },
        "coding": {
            "young": ["Can you follow the steps yourself?", "What does the computer do first?"],
            "middle": ["How would you change the code?", "What happens if the number is 0?"],
            "older": ["Can you make it more efficient?", "What's the time complexity?"],
        },
    }

    pool = pools.get(topic, {})
    bucket = "young" if age <= 6 else "middle" if age <= 9 else "older"
    options = pool.get(bucket, ["Can you explain in your own words?", "What pattern do you notice?"])
    return random.sample(options, min(2, len(options)))


def _extract_concepts_advanced(message: str, topic: str) -> List[str]:
    msg_lower = message.lower()
    concept_map = {
        "math": {
            "addition": ["add", "plus", "sum", "total"],
            "subtraction": ["subtract", "minus", "difference"],
            "multiplication": ["multiply", "times", "product"],
            "division": ["divide", "quotient", "per", "split"],
            "fractions": ["fraction", "half", "quarter", "numerator", "denominator"],
            "decimals": ["decimal", "point", "hundredths", "tenths"],
            "algebra": ["variable", "equation", "solve for", "unknown"],
            "geometry": ["triangle", "circle", "angle", "area", "perimeter", "volume"],
            "statistics": ["mean", "average", "median", "mode", "probability"],
            "patterns": ["pattern", "sequence", "next", "rule"],
        },
        "science": {
            "cells": ["cell", "membrane", "nucleus", "organism"],
            "plants": ["plant", "photosynthesis", "chlorophyll", "seed", "root"],
            "animals": ["mammal", "habitat", "adaptation", "predator", "prey"],
            "physics": ["force", "gravity", "motion", "energy", "speed", "friction"],
            "chemistry": ["atom", "molecule", "element", "reaction", "compound"],
            "earth science": ["weather", "climate", "volcano", "rock", "mineral"],
            "astronomy": ["planet", "star", "orbit", "solar system", "galaxy"],
        },
        "coding": {
            "variables": ["variable", "store", "value", "assign"],
            "loops": ["loop", "repeat", "iterate", "for", "while"],
            "conditionals": ["if", "else", "condition", "boolean"],
            "functions": ["function", "def", "return", "call", "parameter"],
            "algorithms": ["algorithm", "sort", "search", "recursive"],
            "debugging": ["bug", "error", "debug", "fix", "test"],
        },
    }

    found = []
    for concept, keywords in concept_map.get(topic, {}).items():
        if any(kw in msg_lower for kw in keywords):
            found.append(concept)
    return found if found else [topic]


def _calculate_recent_accuracy(session_history: List[Dict[str, Any]]) -> float:
    if not session_history:
        return 0.5
    recent = session_history[-20:]
    correct = sum(1 for s in recent if s.get("correct", False))
    return correct / len(recent)


__all__ = [
    "generate_tutor_response",
    "stream_tutor_response",
    "generate_quiz_claude",
    "analyze_student_error",
    "generate_personalized_problem",
    "generate_metacognitive_coaching",
    "generate_learning_trajectory",
    "generate_whiteboard_instructions",
]
