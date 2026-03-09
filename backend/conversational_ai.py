import random
import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConversationalAI:
    def __init__(self):
        self.session_histories: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.max_history = 20
        self._teaching_responses = self._build_teaching_responses()
        self._quiz_bank = self._build_quiz_bank()

    def generate_response(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        session_id = context.get("session_id", "default")
        raw_topic = context.get("topic", "general")
        difficulty = context.get("difficulty", "intermediate")
        emotion = context.get("emotion", "neutral")
        age_group = self._get_age_group(context.get("age", 8))

        subject = self._detect_subject(message, raw_topic)
        specific_topic = self._extract_specific_topic(message, subject)
        topic = specific_topic if specific_topic != subject else subject

        teaching_strategy = self._select_strategy(message, context, emotion)

        self._add_to_history(session_id, "user", message)

        history = self.session_histories.get(session_id, [])

        response_text = self._build_response(message, topic, subject, difficulty, emotion, age_group, teaching_strategy, history)
        follow_up_questions = self._generate_follow_ups(topic, difficulty, age_group, teaching_strategy)
        concepts_covered = self._extract_concepts(message, subject)
        difficulty_adjustment = self._assess_difficulty_adjustment(message, emotion, history)

        self._add_to_history(session_id, "assistant", response_text)

        return {
            "response": response_text,
            "teaching_strategy": teaching_strategy,
            "follow_up_questions": follow_up_questions,
            "concepts_covered": concepts_covered,
            "difficulty_adjustment": difficulty_adjustment,
            "emotion_detected": emotion,
            "session_id": session_id,
        }

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        return list(self.session_histories.get(session_id, []))

    def generate_quiz(self, topic: str, difficulty: str = "intermediate",
                      num_questions: int = 3, age: int = 8) -> Dict[str, Any]:
        age_group = self._get_age_group(age)
        questions = self._get_quiz_questions(topic, difficulty, num_questions, age_group)
        return {
            "topic": topic,
            "difficulty": difficulty,
            "num_questions": len(questions),
            "questions": questions,
            "time_limit_seconds": len(questions) * 60,
        }

    def _get_age_group(self, age: int) -> str:
        if age <= 5:
            return "3-5"
        elif age <= 8:
            return "6-8"
        return "9-12"

    def _detect_subject(self, message: str, fallback: str) -> str:
        msg_lower = message.lower()
        subject_keywords = {
            "math": ["math", "number", "add", "subtract", "multiply", "divide", "fraction", "decimal",
                     "algebra", "geometry", "equation", "calculate", "count", "sum", "plus", "minus",
                     "times", "percent", "ratio", "area", "perimeter", "volume", "graph"],
            "science": ["science", "plant", "animal", "weather", "energy", "force", "motion", "matter",
                       "cell", "ecosystem", "electricity", "magnet", "solar", "water cycle", "atom",
                       "molecule", "gravity", "experiment", "hypothesis", "chemical", "biology"],
            "reading": ["reading", "read", "book", "story", "character", "plot", "vocabulary", "word",
                       "phonics", "comprehension", "author", "poem", "sentence", "paragraph", "fiction",
                       "nonfiction", "writing", "spell", "grammar", "text"],
            "coding": ["coding", "code", "program", "variable", "loop", "function", "if statement",
                      "algorithm", "debug", "python", "javascript", "html", "computer", "software",
                      "class", "array", "list", "boolean", "string", "integer"],
        }
        for subject, keywords in subject_keywords.items():
            if any(kw in msg_lower for kw in keywords):
                return subject
        if fallback in ("math", "science", "reading", "coding"):
            return fallback
        return "math"

    def _extract_specific_topic(self, message: str, subject: str) -> str:
        msg_lower = message.lower()
        topic_map = {
            "math": {
                "fractions": ["fraction", "numerator", "denominator", "half", "quarter", "third", "1/"],
                "addition": ["add", "plus", "sum", "adding"],
                "subtraction": ["subtract", "minus", "take away", "difference"],
                "multiplication": ["multiply", "times", "product", "multiplication"],
                "division": ["divide", "division", "quotient", "remainder"],
                "decimals": ["decimal", "point", "tenths", "hundredths"],
                "geometry": ["shape", "triangle", "circle", "square", "rectangle", "angle", "geometry"],
                "algebra": ["algebra", "variable", "equation", "solve for", "unknown"],
                "measurement": ["measure", "length", "weight", "height", "centimeter", "meter", "inch"],
                "patterns": ["pattern", "sequence", "next number"],
                "place value": ["place value", "ones", "tens", "hundreds", "thousands"],
                "counting": ["count", "counting", "how many"],
            },
            "science": {
                "plants": ["plant", "flower", "leaf", "root", "seed", "photosynthesis", "grow"],
                "animals": ["animal", "mammal", "reptile", "bird", "fish", "insect", "habitat"],
                "weather": ["weather", "rain", "snow", "cloud", "temperature", "climate", "storm"],
                "energy": ["energy", "heat", "light", "sound", "kinetic", "potential"],
                "forces and motion": ["force", "motion", "push", "pull", "gravity", "speed", "friction"],
                "matter": ["matter", "solid", "liquid", "gas", "atom", "molecule", "element"],
                "ecosystems": ["ecosystem", "food chain", "food web", "predator", "prey", "habitat"],
                "solar system": ["planet", "sun", "moon", "star", "solar system", "orbit", "space"],
                "water cycle": ["water cycle", "evaporation", "condensation", "precipitation"],
            },
            "reading": {
                "comprehension": ["comprehension", "understand", "meaning", "main idea"],
                "vocabulary": ["vocabulary", "word", "definition", "synonym", "antonym"],
                "characters": ["character", "protagonist", "antagonist", "hero"],
                "plot": ["plot", "beginning", "middle", "end", "conflict", "resolution"],
                "inference": ["inference", "infer", "conclude", "imply", "clue"],
                "figurative language": ["metaphor", "simile", "personification", "figurative"],
            },
            "coding": {
                "variables": ["variable", "store", "assign", "value"],
                "loops": ["loop", "repeat", "for", "while", "iteration"],
                "functions": ["function", "def", "return", "call", "parameter"],
                "conditionals": ["if", "else", "condition", "true", "false", "boolean"],
                "algorithms": ["algorithm", "step", "instruction", "sequence", "logic"],
            },
        }
        for concept, keywords in topic_map.get(subject, {}).items():
            if any(kw in msg_lower for kw in keywords):
                return concept
        return subject

    def _select_strategy(self, message: str, context: Dict, emotion: str) -> str:
        msg_lower = message.lower()

        if any(w in msg_lower for w in ["why", "how come", "explain", "what does", "what is"]):
            return "explain"
        if any(w in msg_lower for w in ["example", "show me", "like what"]):
            return "example"
        if any(w in msg_lower for w in ["quiz", "test", "question me"]):
            return "quiz"
        if emotion in ("frustrated", "anxious", "sad"):
            return "encourage"
        if any(w in msg_lower for w in ["confused", "don't understand", "hard", "difficult"]):
            return "analogy"

        strategies = ["explain", "example", "analogy", "quiz", "encourage"]
        if context.get("socratic_mode"):
            return "socratic"
        return random.choice(strategies)

    def _build_response(self, message: str, topic: str, subject: str, difficulty: str,
                        emotion: str, age_group: str, strategy: str,
                        history: List[Dict]) -> str:
        msg_lower = message.lower()

        emotional_prefix = self._get_emotional_prefix(emotion, age_group)

        context_reference = ""
        if len(history) >= 2:
            last_assistant = None
            for h in reversed(history):
                if h["role"] == "assistant":
                    last_assistant = h["content"]
                    break
            if last_assistant:
                context_reference = " Building on what we just discussed — "

        if strategy == "socratic":
            body = self._socratic_response(message, topic, difficulty, age_group)
        elif strategy == "explain":
            body = self._explain_response(message, topic, subject, difficulty, age_group)
        elif strategy == "example":
            body = self._example_response(message, topic, difficulty, age_group)
        elif strategy == "analogy":
            body = self._analogy_response(message, topic, difficulty, age_group)
        elif strategy == "quiz":
            body = self._quiz_response(message, topic, difficulty, age_group)
        elif strategy == "encourage":
            body = self._encourage_response(message, topic, difficulty, age_group)
        else:
            body = self._explain_response(message, topic, subject, difficulty, age_group)

        response = f"{emotional_prefix}{context_reference}{body}"
        return self._adapt_language(response, age_group)

    def _get_emotional_prefix(self, emotion: str, age_group: str) -> str:
        prefixes = {
            "frustrated": {
                "3-5": "Hey, it's totally okay to feel stuck! Let's figure this out together. ",
                "6-8": "I know this can feel tricky, but you're doing great by trying! ",
                "9-12": "I understand this is challenging. Let's break it down step by step. ",
            },
            "confused": {
                "3-5": "That's a really good question! Let me help you understand. ",
                "6-8": "No worries — let me explain this in a different way! ",
                "9-12": "Great question — let me clarify this for you. ",
            },
            "excited": {
                "3-5": "Yay, I love your excitement! 🌟 ",
                "6-8": "Awesome energy! Let's keep going! 🚀 ",
                "9-12": "Great enthusiasm! Let's channel that into learning! ",
            },
            "bored": {
                "3-5": "Let's make this super fun! ",
                "6-8": "How about we try something more interesting? ",
                "9-12": "Let's kick it up a notch and try something more challenging! ",
            },
            "anxious": {
                "3-5": "Don't worry, we'll go nice and slow. You're safe here! ",
                "6-8": "Take a deep breath — there's no pressure at all. ",
                "9-12": "Remember, making mistakes is how we learn. No stress here. ",
            },
        }
        group = prefixes.get(emotion, {})
        return group.get(age_group, "")

    def _socratic_response(self, message: str, topic: str, difficulty: str, age_group: str) -> str:
        responses = {
            "3-5": [
                f"Hmm, that's interesting! What do you think happens when we {topic}? Can you try to guess?",
                f"Great thinking! What if I told you it's like putting things together? What do you think {topic} means?",
            ],
            "6-8": [
                f"You're on the right track! Let me ask you this — if you had to teach a friend about {topic}, what would you say first?",
                f"Interesting thought! What do you already know about {topic}? Let's start there and build from it.",
                f"Before I answer, let me ask you: why do you think {topic} works that way? What's your best guess?",
            ],
            "9-12": [
                f"That's a great starting point. Let me challenge you — can you think of a real-world example where {topic} applies? That might help us uncover the answer together.",
                f"Instead of giving you the answer directly, let's reason through it. What are the key components of {topic}? If we understand those, the bigger picture will come together.",
                f"Excellent question. Here's something to consider: how does {topic} connect to what you already know? Sometimes making those connections reveals the answer.",
            ],
        }
        return random.choice(responses.get(age_group, responses["6-8"]))

    def _explain_response(self, message: str, topic: str, subject: str, difficulty: str, age_group: str) -> str:
        responses = {
            "math": {
                "3-5": f"Let me explain **{topic}** in a fun way! Think of numbers like friends at a party. When we work with {topic}, we're figuring out how numbers play together. It's like counting your toys and figuring out new things about them!",
                "6-8": f"Great question about **{topic}**! Here's how it works: {topic} is an important math skill that helps us solve all kinds of problems. Imagine you're building with blocks — each block represents a number, and {topic} helps us figure out how to arrange them to get our answer. Let me walk you through it step by step.",
                "9-12": f"Let's dive into **{topic}**. The fundamental concept here is understanding how numbers relate to each other. When we study {topic}, we're applying mathematical principles that build on everything you've learned so far. Here's the key insight: every complex problem can be broken down into simpler steps. Let me show you the logical progression.",
            },
            "science": {
                "3-5": f"Let's learn about **{topic}**! You know how everything around us is so amazing? Well, {topic} helps us understand why things work the way they do. It's like being a detective — we look for clues in nature!",
                "6-8": f"So **{topic}** is really cool! Scientists study this to understand how our world works. Think of it like this: the universe has rules, and {topic} is one of those rules. When we understand it, we can predict what will happen next. Let me explain the main idea.",
                "9-12": f"Let's explore **{topic}** in depth. This concept is central to understanding how natural systems function. The scientific explanation involves several connected ideas. First, we need to understand the underlying principles, then we can see how they apply in real-world scenarios. Here's the detailed breakdown.",
            },
            "reading": {
                "3-5": f"Reading is like going on an adventure! When we practice **{topic}**, we're learning special tricks to understand stories better. It's like having a superpower for reading books!",
                "6-8": f"Understanding **{topic}** will make you a much stronger reader! Here's what it means: when you read, your brain is doing a lot of work — and {topic} is one of the tools your brain uses. Let me show you how to use this tool really well.",
                "9-12": f"Let's talk about **{topic}** as a reading strategy. Skilled readers use this technique automatically, but understanding it explicitly will help you read more critically. The key is to actively engage with the text rather than passively reading words. Here's how it works in practice.",
            },
            "coding": {
                "3-5": f"Coding is like giving instructions to a robot friend! When we learn about **{topic}**, we're teaching the computer exactly what to do, step by step. It's like writing a recipe!",
                "6-8": f"Let's learn about **{topic}** in coding! Imagine you're writing a set of directions for someone who follows instructions perfectly — that's what coding is. {topic.capitalize()} is one of the important tools programmers use. Let me break it down for you.",
                "9-12": f"Let's dive into **{topic}**. In programming, this concept is fundamental to writing effective code. Understanding {topic} will help you write programs that are more efficient and easier to understand. Here's the concept explained with a practical perspective.",
            },
        }

        subject_responses = responses.get(subject, responses.get("math"))
        if isinstance(subject_responses, dict):
            return subject_responses.get(age_group, subject_responses.get("6-8", f"Let me explain **{topic}** to you in detail. This is an important concept that connects to many things you'll learn."))
        return f"Let me explain **{topic}** to you. This is a really important concept! Here's how it works and why it matters."

    def _example_response(self, message: str, topic: str, difficulty: str, age_group: str) -> str:
        examples = {
            "3-5": f"Let me show you with a fun example! 🎨 Imagine you have 3 red apples and 2 green apples. If we count them all together — 1, 2, 3, 4, 5 — we have 5 apples total! That's how {topic} works. You try one now!",
            "6-8": f"Here's a great example to help you understand {topic}:\n\n**Example:** Imagine you're at a store. You buy 3 notebooks that cost $2 each. To find the total, you can think of it as adding $2 three times: $2 + $2 + $2 = $6. Or you can multiply: 3 × $2 = $6.\n\nSee how {topic} helps us solve real problems? Now let me give you a similar problem to try!",
            "9-12": f"Let me walk you through a detailed example of {topic}:\n\n**Problem:** Suppose we need to solve a problem involving {topic}.\n\n**Step 1:** First, identify what we know and what we need to find.\n**Step 2:** Apply the concept of {topic} to set up our solution.\n**Step 3:** Work through the calculations systematically.\n**Step 4:** Check our answer to make sure it makes sense.\n\nThis systematic approach works for many similar problems. Want to try one on your own?",
        }
        return examples.get(age_group, examples["6-8"])

    def _analogy_response(self, message: str, topic: str, difficulty: str, age_group: str) -> str:
        analogies = {
            "3-5": f"Think of {topic} like building a tower with blocks! 🧱 Each block you add makes the tower taller, just like each step in {topic} gets you closer to the answer. And if a block falls, you just pick it up and try again. That's what learning is all about!",
            "6-8": f"Here's a cool way to think about {topic} — it's like learning to ride a bike! 🚲 At first, it seems wobbly and hard, but each time you practice, you get a little better. The training wheels are like hints — they help you at first, but eventually you won't need them. {topic.capitalize()} works the same way: practice makes it easier and easier!",
            "9-12": f"Think of {topic} like a map. 🗺️ When you first look at a map of a new city, everything seems confusing. But once you identify landmarks and understand how streets connect, you can navigate anywhere. Similarly, {topic} might seem complex at first, but once you understand the foundational 'landmarks' — the key principles — everything else falls into place. Let me point out those key landmarks for you.",
        }
        return analogies.get(age_group, analogies["6-8"])

    def _quiz_response(self, message: str, topic: str, difficulty: str, age_group: str) -> str:
        quizzes = {
            "3-5": f"Let's play a learning game! 🎮\n\n**Question:** If you have 2 cookies and I give you 3 more cookies, how many cookies do you have now?\n\nTake your time to think about it! You can count on your fingers if that helps. 🍪",
            "6-8": f"Time for a quick challenge! 💡\n\n**Question about {topic}:**\nThink carefully and see if you can figure this out. Remember, it's okay to take your time.\n\nHere's a hint if you need it: try breaking the problem into smaller parts. What's the first thing you would do?\n\nGive it your best shot!",
            "9-12": f"Let's test your understanding of {topic} with a challenge! 🧠\n\n**Challenge Question:**\nApply what you've learned about {topic} to solve this problem. Think about the key principles we discussed.\n\nRemember:\n- Start by identifying what you know\n- Think about which concept applies here\n- Show your reasoning, not just the answer\n\nI'll give you feedback on your approach!",
        }
        return quizzes.get(age_group, quizzes["6-8"])

    def _encourage_response(self, message: str, topic: str, difficulty: str, age_group: str) -> str:
        encouragements = {
            "3-5": f"You are doing SO amazing! 🌟 I can tell you're really trying hard, and that makes me so happy! Did you know that every time you try, your brain gets a little bit stronger? It's true! You're like a superhero who gets more powerful with every practice. Let's keep going — I believe in you! 💪",
            "6-8": f"I want you to know something important: struggling with {topic} doesn't mean you're bad at it. It means you're learning! 🌱 Every expert was once a beginner. The fact that you're here, trying and asking questions — that's what real learning looks like. You've already shown great thinking today. Let's tackle this together, one step at a time. You've got this!",
            "9-12": f"I can see you're working through a challenge with {topic}, and I really respect that. Here's what I've noticed: the students who ultimately master difficult concepts are the ones who don't give up when it gets tough. You're showing that kind of persistence right now. Let's try approaching this from a different angle — sometimes a new perspective is all it takes to make things click. What part specifically is giving you trouble?",
        }
        return encouragements.get(age_group, encouragements["6-8"])

    def _generate_follow_ups(self, topic: str, difficulty: str, age_group: str, strategy: str) -> List[str]:
        follow_ups = {
            "3-5": [
                "Can you show me with your fingers?",
                "What's your favorite part about this?",
                "Do you want to try another one?",
            ],
            "6-8": [
                f"Can you think of another example of {topic}?",
                "What part was the hardest for you?",
                "Would you like me to explain it a different way?",
                "Ready for a harder challenge?",
            ],
            "9-12": [
                f"How does {topic} connect to what you've learned before?",
                "Can you explain this concept in your own words?",
                "What would happen if we changed one of the conditions?",
                "Can you think of a real-world application for this?",
                "What's the next logical step to explore?",
            ],
        }
        options = follow_ups.get(age_group, follow_ups["6-8"])
        return random.sample(options, min(3, len(options)))

    def _extract_concepts(self, message: str, topic: str) -> List[str]:
        msg_lower = message.lower()
        concept_keywords = {
            "math": ["addition", "subtraction", "multiplication", "division", "fractions", "decimals",
                     "geometry", "algebra", "counting", "numbers", "patterns", "measurement", "area",
                     "perimeter", "volume", "equations", "place value"],
            "science": ["plants", "animals", "weather", "energy", "force", "motion", "matter",
                       "cells", "ecosystem", "habitat", "electricity", "magnets", "solar system",
                       "water cycle", "rocks", "minerals"],
            "reading": ["comprehension", "vocabulary", "phonics", "fluency", "main idea",
                       "characters", "setting", "plot", "inference", "summary", "theme",
                       "figurative language", "genre"],
            "coding": ["variables", "loops", "functions", "conditionals", "arrays", "lists",
                      "debugging", "algorithms", "sequences", "events", "operators", "classes"],
        }
        found = []
        keywords = concept_keywords.get(topic, [])
        for kw in keywords:
            if kw in msg_lower:
                found.append(kw)
        if not found:
            found = [topic]
        return found

    def _assess_difficulty_adjustment(self, message: str, emotion: str, history: List[Dict]) -> str:
        if emotion in ("frustrated", "confused", "anxious"):
            return "decrease"
        if emotion in ("bored", "confident"):
            return "increase"

        msg_lower = message.lower()
        if any(w in msg_lower for w in ["too hard", "don't get it", "help", "confused", "struggling"]):
            return "decrease"
        if any(w in msg_lower for w in ["too easy", "boring", "already know", "challenge me"]):
            return "increase"

        return "maintain"

    def _adapt_language(self, text: str, age_group: str) -> str:
        if age_group == "3-5":
            replacements = {
                "fundamental": "basic",
                "systematically": "step by step",
                "perspective": "way of looking at it",
                "component": "part",
                "concept": "idea",
                "principle": "rule",
                "calculate": "figure out",
                "efficient": "fast",
                "approximately": "about",
            }
            for old, new in replacements.items():
                text = text.replace(old, new)
        return text

    def _add_to_history(self, session_id: str, role: str, content: str):
        self.session_histories[session_id].append({
            "role": role,
            "content": content,
        })
        if len(self.session_histories[session_id]) > self.max_history:
            self.session_histories[session_id] = self.session_histories[session_id][-self.max_history:]

    def _build_teaching_responses(self) -> Dict:
        return {}

    def _build_quiz_bank(self) -> Dict:
        return {
            "math": {
                "easy": [
                    {"question": "What is 3 + 4?", "options": ["6", "7", "8", "5"], "correct": 1, "explanation": "3 + 4 = 7. You can count up from 3: 4, 5, 6, 7!"},
                    {"question": "What is 10 - 3?", "options": ["6", "7", "8", "5"], "correct": 1, "explanation": "10 - 3 = 7. Start at 10 and count back 3: 9, 8, 7!"},
                    {"question": "Which number comes after 15?", "options": ["14", "15", "16", "17"], "correct": 2, "explanation": "After 15 comes 16!"},
                ],
                "medium": [
                    {"question": "What is 24 + 38?", "options": ["52", "62", "72", "42"], "correct": 1, "explanation": "24 + 38 = 62. Add the ones (4+8=12, carry the 1) then the tens (2+3+1=6)."},
                    {"question": "What is 6 × 7?", "options": ["36", "42", "48", "35"], "correct": 1, "explanation": "6 × 7 = 42. Think of it as 6 groups of 7."},
                    {"question": "What is 1/2 + 1/4?", "options": ["2/6", "1/6", "3/4", "2/4"], "correct": 2, "explanation": "1/2 = 2/4, so 2/4 + 1/4 = 3/4."},
                ],
                "hard": [
                    {"question": "What is 15% of 200?", "options": ["15", "20", "25", "30"], "correct": 3, "explanation": "15% × 200 = 0.15 × 200 = 30."},
                    {"question": "Solve for x: 3x + 7 = 22", "options": ["3", "4", "5", "6"], "correct": 2, "explanation": "3x + 7 = 22 → 3x = 15 → x = 5."},
                ],
            },
            "science": {
                "easy": [
                    {"question": "Which of these is a living thing?", "options": ["Rock", "Tree", "Water", "Cloud"], "correct": 1, "explanation": "A tree is a living thing because it grows, needs food and water, and reproduces."},
                    {"question": "What do plants need to grow?", "options": ["Darkness and cold", "Sunlight and water", "Only soil", "Only air"], "correct": 1, "explanation": "Plants need sunlight, water, air, and soil to grow."},
                ],
                "medium": [
                    {"question": "What are the three states of matter?", "options": ["Hot, warm, cold", "Solid, liquid, gas", "Big, medium, small", "Earth, water, air"], "correct": 1, "explanation": "The three states of matter are solid, liquid, and gas."},
                    {"question": "In a food chain, what is a producer?", "options": ["An animal that eats plants", "A plant that makes its own food", "An animal that eats other animals", "A fungus"], "correct": 1, "explanation": "Producers are organisms (like plants) that make their own food through photosynthesis."},
                ],
                "hard": [
                    {"question": "What happens during evaporation?", "options": ["Liquid turns to solid", "Gas turns to liquid", "Liquid turns to gas", "Solid turns to liquid"], "correct": 2, "explanation": "Evaporation is when a liquid turns into a gas, usually by heating."},
                ],
            },
            "reading": {
                "easy": [
                    {"question": "What is the main character in a story?", "options": ["The setting", "The most important person", "The title", "The ending"], "correct": 1, "explanation": "The main character is the most important person or figure in the story."},
                ],
                "medium": [
                    {"question": "What is an inference?", "options": ["A direct quote from text", "A guess based on clues in the text", "The title of a book", "A type of punctuation"], "correct": 1, "explanation": "An inference is a conclusion you draw based on evidence and reasoning from the text."},
                ],
                "hard": [
                    {"question": "What is the difference between theme and main idea?", "options": ["They are the same thing", "Theme is the lesson; main idea is what the text is about", "Theme is only in fiction", "Main idea is only in poetry"], "correct": 1, "explanation": "The main idea is what the text is mainly about, while the theme is the underlying message or lesson."},
                ],
            },
            "coding": {
                "easy": [
                    {"question": "What is a sequence in coding?", "options": ["Random commands", "Steps in a specific order", "A type of bug", "A coding language"], "correct": 1, "explanation": "A sequence is a set of instructions that are followed in a specific order."},
                ],
                "medium": [
                    {"question": "What does a loop do?", "options": ["Stops the program", "Repeats a set of instructions", "Deletes code", "Saves a file"], "correct": 1, "explanation": "A loop repeats a set of instructions multiple times."},
                ],
                "hard": [
                    {"question": "What is recursion?", "options": ["A loop that runs forever", "A function that calls itself", "A type of variable", "An error in code"], "correct": 1, "explanation": "Recursion is when a function calls itself to solve a problem by breaking it into smaller subproblems."},
                ],
            },
        }

    def _get_quiz_questions(self, topic: str, difficulty: str, num: int, age_group: str) -> List[Dict]:
        diff_map = {"beginner": "easy", "intermediate": "medium", "advanced": "hard", "expert": "hard"}
        diff_key = diff_map.get(difficulty, "medium")

        topic_questions = self._quiz_bank.get(topic, self._quiz_bank.get("math", {}))
        questions = topic_questions.get(diff_key, [])

        if not questions:
            for level in ["easy", "medium", "hard"]:
                questions = topic_questions.get(level, [])
                if questions:
                    break

        if not questions:
            questions = [
                {"question": f"What is an important concept in {topic}?", "options": ["Concept A", "Concept B", "Concept C", "Concept D"], "correct": 0, "explanation": f"This is a key concept in {topic}."},
            ]

        selected = random.sample(questions, min(num, len(questions)))
        return [
            {
                "id": f"q_{i+1}",
                "question": q["question"],
                "type": "multiple_choice",
                "options": q["options"],
                "correct_answer": q["correct"],
                "explanation": q["explanation"],
            }
            for i, q in enumerate(selected)
        ]


conversational_ai = ConversationalAI()

__all__ = ["ConversationalAI", "conversational_ai"]
