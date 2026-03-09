import os
import logging
from typing import Dict, Any, Optional, List

from openai import OpenAI

logger = logging.getLogger(__name__)

_client = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
        api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
        if base_url and api_key:
            _client = OpenAI(base_url=base_url, api_key=api_key)
        else:
            _client = OpenAI()
    return _client


def _build_system_prompt(context: Dict[str, Any]) -> str:
    age = context.get("age", 8)
    subject = context.get("topic", "general")
    difficulty = context.get("difficulty", "intermediate")
    emotion = context.get("emotion", "neutral")
    strategy = context.get("teaching_strategy", "explain")

    if age <= 5:
        tone = "Use very simple words, short sentences, lots of encouragement, and fun comparisons. Use emojis freely."
        grade_desc = "preschool to kindergarten"
    elif age <= 8:
        tone = "Use clear, friendly language. Explain with relatable examples from everyday life. Be encouraging and patient."
        grade_desc = "early elementary (grades 1-3)"
    else:
        tone = "Use grade-appropriate vocabulary. Challenge thinking with follow-up questions. Encourage deeper reasoning."
        grade_desc = "upper elementary (grades 4-6)"

    emotion_guidance = ""
    if emotion == "confused":
        emotion_guidance = "The student seems confused. Break things down into smaller steps. Be extra patient and reassuring."
    elif emotion == "frustrated":
        emotion_guidance = "The student seems frustrated. Be very encouraging. Simplify and celebrate small wins."
    elif emotion == "bored":
        emotion_guidance = "The student seems bored. Make it fun! Use surprising facts, challenges, or games."
    elif emotion == "excited":
        emotion_guidance = "The student is excited! Match their energy and channel it into deeper learning."

    strategy_guidance = ""
    if strategy == "socratic":
        strategy_guidance = "Use the Socratic method: guide with questions rather than giving answers directly."
    elif strategy == "example":
        strategy_guidance = "Teach primarily through concrete examples and demonstrations."
    elif strategy == "analogy":
        strategy_guidance = "Use creative analogies and comparisons to explain concepts."
    elif strategy == "quiz":
        strategy_guidance = "Turn the lesson into an interactive quiz with immediate feedback."

    student_memory = context.get("student_memory", "")
    memory_section = f"\n\nStudent Profile (from past interactions):\n{student_memory}" if student_memory else ""

    return f"""You are Nova, a friendly and brilliant AI tutor for children. You are teaching a {age}-year-old student at the {grade_desc} level.

Subject: {subject}
Difficulty: {difficulty}
{emotion_guidance}
{strategy_guidance}
{memory_section}

Guidelines:
- {tone}
- Keep responses concise (2-4 paragraphs max)
- Use markdown formatting: **bold** for key terms, bullet points for lists
- End with a thought-provoking question or a fun challenge when appropriate
- Never be condescending. Treat the student as a capable learner
- If the student asks something outside the subject, gently redirect but answer briefly
- Use real-world examples relevant to a child's life
- Celebrate correct answers and gently correct mistakes with encouragement
- When possible, connect new topics to subjects and topics the student already enjoys
- If the student is struggling, reference their strengths to build confidence"""


async def generate_tutor_response(
    message: str,
    context: Dict[str, Any],
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    try:
        client = _get_client()
        system_prompt = _build_system_prompt(context)

        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            for msg in conversation_history[-10:]:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        messages.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=messages,
            max_completion_tokens=800,
        )

        ai_response = response.choices[0].message.content

        follow_ups = _generate_follow_ups(context.get("topic", "general"))

        return {
            "response": ai_response,
            "teaching_strategy": context.get("teaching_strategy", "explain"),
            "follow_up_questions": follow_ups,
            "concepts_covered": _extract_concepts(message, context.get("topic", "general")),
            "difficulty_adjustment": "maintain",
            "session_id": context.get("session_id", "default"),
            "ai_powered": True,
        }
    except Exception as e:
        logger.error("OpenAI API call failed: %s", e)
        return None


async def generate_quiz_ai(
    topic: str,
    difficulty: str = "intermediate",
    num_questions: int = 3,
    age: int = 8,
) -> Optional[Dict[str, Any]]:
    try:
        client = _get_client()

        prompt = f"""Create a {num_questions}-question quiz about {topic} for a {age}-year-old student at {difficulty} difficulty.

Return the quiz in this exact JSON format:
{{
  "title": "Quiz title",
  "questions": [
    {{
      "question": "The question text",
      "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
      "correct_answer": 0,
      "explanation": "Brief explanation of the correct answer"
    }}
  ]
}}

Make questions age-appropriate, educational, and engaging. Only return valid JSON."""

        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "You are an educational quiz generator. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=1000,
        )

        import json
        content = response.choices[0].message.content
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        quiz_data = json.loads(content)
        quiz_data["topic"] = topic
        quiz_data["difficulty"] = difficulty
        quiz_data["ai_generated"] = True
        return quiz_data
    except Exception as e:
        logger.error("Quiz generation failed: %s", e)
        return None


async def generate_whiteboard_instructions(
    concept: str,
    subject: str = "math",
    age: int = 8,
) -> Optional[Dict[str, Any]]:
    try:
        client = _get_client()

        prompt = f"""Create step-by-step visual whiteboard instructions to explain "{concept}" in {subject} for a {age}-year-old.

Return JSON with drawing steps:
{{
  "title": "Concept title",
  "steps": [
    {{
      "instruction": "What to draw/write",
      "type": "text|shape|equation|arrow",
      "content": "The text or equation to display",
      "x": 100, "y": 100,
      "color": "#4ecdc4"
    }}
  ]
}}

Keep it simple and visual. Max 8 steps. Only return valid JSON."""

        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "You are a visual education designer. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=800,
        )

        import json
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        return json.loads(content)
    except Exception as e:
        logger.error("Whiteboard generation failed: %s", e)
        return None


def _generate_follow_ups(topic: str) -> List[str]:
    defaults = {
        "math": ["Can you solve a similar problem?", "What if the numbers were bigger?", "Where do you see this in real life?"],
        "science": ["Why do you think that happens?", "Can you think of another example?", "What would you test next?"],
        "reading": ["What do you think happens next?", "How does the character feel?", "Can you use that word in a sentence?"],
        "coding": ["How would you change the code?", "What happens if we add a loop?", "Can you spot the bug?"],
    }
    return defaults.get(topic, ["What else would you like to learn?", "Can you explain it in your own words?", "Ready for a challenge?"])


def _extract_concepts(message: str, topic: str) -> List[str]:
    concept_keywords = {
        "math": {"addition": ["add", "plus", "sum"], "subtraction": ["subtract", "minus", "take away"],
                 "multiplication": ["multiply", "times", "product"], "division": ["divide", "split", "share"],
                 "fractions": ["fraction", "half", "quarter", "numerator", "denominator"],
                 "geometry": ["shape", "triangle", "circle", "square", "angle"],
                 "algebra": ["variable", "equation", "solve for", "unknown"]},
        "science": {"plants": ["plant", "flower", "seed", "grow", "photosynthesis"],
                    "animals": ["animal", "habitat", "species", "mammal"],
                    "weather": ["weather", "rain", "cloud", "temperature", "storm"],
                    "matter": ["solid", "liquid", "gas", "matter", "atom"]},
        "reading": {"comprehension": ["understand", "meaning", "main idea"],
                    "vocabulary": ["word", "definition", "synonym"],
                    "phonics": ["sound", "letter", "syllable"]},
        "coding": {"variables": ["variable", "store", "value", "assign"],
                   "loops": ["loop", "repeat", "for", "while"],
                   "functions": ["function", "def", "call", "return"]},
    }

    msg_lower = message.lower()
    found = []
    for concept, keywords in concept_keywords.get(topic, {}).items():
        if any(kw in msg_lower for kw in keywords):
            found.append(concept)

    return found if found else [topic]


async def generate_lesson_content(
    title: str,
    description: str,
    subject: str,
    objectives: list,
    age: int = 8,
    activity_type: str = "lesson",
) -> Dict[str, Any]:
    try:
        client = _get_client()

        if age <= 5:
            level = "preschool/kindergarten"
            style = "Very simple language, lots of fun examples, emojis, and encouragement. Short paragraphs (2-3 sentences each)."
        elif age <= 8:
            level = "grades 1-3"
            style = "Clear friendly language, relatable real-world examples, step-by-step explanations. Medium paragraphs."
        else:
            level = "grades 4-6"
            style = "Grade-appropriate vocabulary, deeper reasoning, connections between concepts. Can handle longer explanations."

        obj_text = "\n".join(f"- {o}" for o in (objectives or []))

        prompt = f"""Create a structured lesson for a {age}-year-old ({level}) about:

Topic: {title}
Description: {description}
Subject: {subject}
Activity Type: {activity_type}

Learning Objectives:
{obj_text if obj_text else '- Learn about ' + title}

Return a JSON object with this exact structure:
{{
  "intro": "A brief, engaging 2-3 sentence introduction that hooks the student",
  "sections": [
    {{
      "heading": "Section title",
      "content": "2-4 paragraphs of lesson content with **bold** key terms",
      "example": "A concrete example or demonstration (optional, can be null)",
      "tip": "A helpful tip or fun fact (optional, can be null)"
    }}
  ],
  "key_vocabulary": [
    {{"term": "word", "definition": "simple definition"}}
  ],
  "check_understanding": [
    {{
      "question": "A question to check understanding",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct": 0,
      "explanation": "Why this is correct"
    }}
  ],
  "summary": "2-3 sentence summary of what was learned",
  "challenge": "An optional fun challenge or activity to extend learning"
}}

Style: {style}
Create 2-4 sections. Make 2-3 check questions. Keep vocabulary to 3-5 terms.
Only return valid JSON."""

        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "You are an expert curriculum designer creating engaging, age-appropriate lesson content. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=2000,
        )

        import json
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        lesson = json.loads(content)
        lesson["ai_generated"] = True
        lesson["title"] = title
        lesson["subject"] = subject
        return lesson
    except Exception as e:
        logger.error("Lesson generation failed: %s", e)
        return _fallback_lesson(title, description, subject, objectives, age)


def _fallback_lesson(title, description, subject, objectives, age):
    if age <= 5:
        intro = f"Hi there! Today we're going to learn about **{title}**! This is going to be so much fun!"
        summary = f"You did it! You learned all about **{title}**. Give yourself a big high five!"
        challenge = "Can you draw a picture about what you learned today?"
        tip = "Remember, learning is like playing - the more you explore, the more you discover!"
    elif age <= 8:
        intro = f"Welcome to today's lesson on **{title}**! {description or ''} Get ready to explore and discover something awesome!"
        summary = f"Awesome work! You've been learning about **{title}**. Keep practicing and you'll master it in no time!"
        challenge = "Try teaching what you learned to a friend or family member. When you can explain it, you really understand it!"
        tip = "If something feels tricky, that's your brain growing! Take a break and try again."
    else:
        intro = f"Today's focus: **{title}**. {description or ''} Let's build a deeper understanding of this important topic."
        summary = f"Well done on completing this lesson about **{title}**. Review the key concepts and think about how they connect to what you already know."
        challenge = "Write a brief summary in your own words, or try to come up with your own example problem."
        tip = "Strong learners look for connections between new ideas and things they already know."

    sections = [
        {
            "heading": f"Introduction to {title}",
            "content": description or f"In this lesson, we will explore {title} in depth.",
            "example": None,
            "tip": tip,
        }
    ]
    if objectives and len(objectives) > 0:
        obj_content = "By the end of this lesson, you should be able to:\n" + "\n".join(f"- {o}" for o in objectives)
        sections.append({
            "heading": "Learning Goals",
            "content": obj_content,
            "example": None,
            "tip": None,
        })
        sections.append({
            "heading": "Let's Get Started",
            "content": f"Let's begin with the first goal: **{objectives[0]}**. Work through the material carefully, and don't hesitate to ask Nova for help if you need it!",
            "example": None,
            "tip": None,
        })

    check = []
    if objectives:
        check.append({
            "question": f"Which of these is a learning goal for this lesson?",
            "options": [f"A) {objectives[0]}", "B) Learn to fly", "C) Build a rocket", "D) Cook dinner"],
            "correct": 0,
            "explanation": f"That's right! One of our main goals is: {objectives[0]}",
        })
    check.append({
        "question": f"What is the main topic of this lesson?",
        "options": [f"A) {title}", "B) Something else entirely", "C) We haven't started yet", "D) I'm not sure"],
        "correct": 0,
        "explanation": f"Correct! This lesson is all about {title}.",
    })

    return {
        "title": title,
        "subject": subject,
        "ai_generated": False,
        "intro": intro,
        "sections": sections,
        "key_vocabulary": [],
        "check_understanding": check,
        "summary": summary,
        "challenge": challenge,
    }
