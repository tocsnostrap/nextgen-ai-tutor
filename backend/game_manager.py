import logging
import random
import time
import uuid
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

MATH_QUESTIONS = [
    {"q": "What is 7 + 8?", "options": ["13", "14", "15", "16"], "answer": 2},
    {"q": "What is 12 - 5?", "options": ["6", "7", "8", "9"], "answer": 1},
    {"q": "What is 6 × 4?", "options": ["20", "22", "24", "26"], "answer": 2},
    {"q": "What is 36 ÷ 6?", "options": ["4", "5", "6", "7"], "answer": 2},
    {"q": "What is 15 + 27?", "options": ["40", "42", "44", "52"], "answer": 1},
    {"q": "What is 9 × 7?", "options": ["54", "56", "63", "72"], "answer": 2},
    {"q": "What is 100 - 37?", "options": ["53", "57", "63", "67"], "answer": 2},
    {"q": "What is 48 ÷ 8?", "options": ["4", "5", "6", "7"], "answer": 2},
    {"q": "What is 25 + 38?", "options": ["53", "63", "73", "83"], "answer": 1},
    {"q": "What is 11 × 11?", "options": ["111", "121", "131", "144"], "answer": 1},
]

SCIENCE_QUESTIONS = [
    {"q": "What planet is closest to the Sun?", "options": ["Venus", "Mercury", "Mars", "Earth"], "answer": 1},
    {"q": "What gas do plants breathe in?", "options": ["Oxygen", "Nitrogen", "Carbon Dioxide", "Hydrogen"], "answer": 2},
    {"q": "How many legs does an insect have?", "options": ["4", "6", "8", "10"], "answer": 1},
    {"q": "What is the hardest natural substance?", "options": ["Gold", "Iron", "Diamond", "Platinum"], "answer": 2},
    {"q": "What organ pumps blood through the body?", "options": ["Brain", "Lungs", "Heart", "Liver"], "answer": 2},
    {"q": "What is water made of?", "options": ["H2O", "CO2", "O2", "NaCl"], "answer": 0},
    {"q": "Which animal is the largest on Earth?", "options": ["Elephant", "Giraffe", "Blue Whale", "Shark"], "answer": 2},
    {"q": "What causes rainbows?", "options": ["Wind", "Rain", "Light refraction", "Clouds"], "answer": 2},
]

SPELLING_WORDS = [
    {"word": "BEAUTIFUL", "scrambled": "UAEFTIBLF", "hint": "Something lovely to look at"},
    {"word": "ELEPHANT", "scrambled": "PANETLHE", "hint": "A large animal with a trunk"},
    {"word": "TRIANGLE", "scrambled": "GRAILNET", "hint": "A shape with three sides"},
    {"word": "DINOSAUR", "scrambled": "UAROSIDN", "hint": "An extinct giant reptile"},
    {"word": "BUTTERFLY", "scrambled": "LFTTYBURE", "hint": "An insect with colorful wings"},
    {"word": "MOUNTAIN", "scrambled": "TNUMAINO", "hint": "A very tall landform"},
    {"word": "SKELETON", "scrambled": "LETEKNOS", "hint": "The bones inside your body"},
    {"word": "NOVEMBER", "scrambled": "MOVREENB", "hint": "The 11th month of the year"},
]

CODING_QUESTIONS = [
    {"q": "What does a 'loop' do in coding?", "options": ["Stops the program", "Repeats code", "Deletes data", "Creates a file"], "answer": 1},
    {"q": "What is a 'variable'?", "options": ["A type of loop", "A stored value", "A function name", "An error"], "answer": 1},
    {"q": "What symbol starts a comment in Python?", "options": ["//", "/*", "#", "--"], "answer": 2},
    {"q": "What does 'print()' do in Python?", "options": ["Prints paper", "Shows output", "Saves a file", "Creates a loop"], "answer": 1},
    {"q": "What is a 'function'?", "options": ["A number", "A reusable block of code", "A file type", "A variable"], "answer": 1},
    {"q": "What does 'if' do in code?", "options": ["Loops forever", "Makes a decision", "Prints text", "Stores data"], "answer": 1},
]

GAME_TYPES = {
    "math_race": {"name": "Math Race", "icon": "🔢", "questions": MATH_QUESTIONS, "time_per_round": 15},
    "science_trivia": {"name": "Science Trivia", "icon": "🔬", "questions": SCIENCE_QUESTIONS, "time_per_round": 20},
    "spelling_bee": {"name": "Spelling Bee", "icon": "📝", "questions": SPELLING_WORDS, "time_per_round": 30},
    "code_challenge": {"name": "Code Challenge", "icon": "💻", "questions": CODING_QUESTIONS, "time_per_round": 20},
}

BOT_NAMES = ["RoboScholar", "BrainBot", "QuizWhiz", "SmartPanda", "CodeBuddy"]


class GameSession:
    def __init__(self, game_type: str, creator_id: str, rounds: int = 5):
        self.id = str(uuid.uuid4())[:8]
        self.game_type = game_type
        self.creator_id = creator_id
        self.rounds = min(rounds, 10)
        self.players: Dict[str, Dict] = {}
        self.current_round = 0
        self.state = "waiting"
        self.questions: List[Dict] = []
        self.created_at = time.time()
        self.round_start_time = 0.0
        self.answers_this_round: Dict[str, Any] = {}

        game_info = GAME_TYPES.get(game_type, GAME_TYPES["math_race"])
        pool = list(game_info["questions"])
        random.shuffle(pool)
        self.questions = pool[:self.rounds]
        self.time_per_round = game_info["time_per_round"]

    def add_player(self, player_id: str, name: str, is_bot: bool = False):
        self.players[player_id] = {
            "name": name,
            "score": 0,
            "correct": 0,
            "streak": 0,
            "is_bot": is_bot,
        }

    def start(self):
        self.state = "playing"
        self.current_round = 0
        self.advance_round()

    def advance_round(self):
        self.current_round += 1
        self.answers_this_round = {}
        self.round_start_time = time.time()

        if self.current_round > len(self.questions):
            self.state = "finished"

    def submit_answer(self, player_id: str, answer: int) -> Dict:
        if player_id in self.answers_this_round:
            return {"already_answered": True}

        elapsed = time.time() - self.round_start_time
        question = self.questions[self.current_round - 1]
        correct = answer == question.get("answer", -1)

        speed_bonus = max(0, int((self.time_per_round - elapsed) * 10))
        points = (100 + speed_bonus) if correct else 0

        player = self.players.get(player_id, {})
        if correct:
            player["correct"] = player.get("correct", 0) + 1
            player["streak"] = player.get("streak", 0) + 1
            if player["streak"] >= 3:
                points += 50
        else:
            player["streak"] = 0

        player["score"] = player.get("score", 0) + points
        self.answers_this_round[player_id] = {
            "answer": answer,
            "correct": correct,
            "points": points,
            "time": round(elapsed, 1),
        }

        return {"correct": correct, "points": points, "time": round(elapsed, 1)}

    def get_bot_answers(self) -> List[Dict]:
        results = []
        for pid, player in self.players.items():
            if player["is_bot"] and pid not in self.answers_this_round:
                question = self.questions[self.current_round - 1]
                correct_prob = random.random()
                if correct_prob < 0.7:
                    answer = question.get("answer", 0)
                else:
                    answer = random.randint(0, 3)
                bot_time = random.uniform(2, self.time_per_round - 2)
                time.sleep(0)
                r = self.submit_answer(pid, answer)
                r["player_id"] = pid
                r["player_name"] = player["name"]
                results.append(r)
        return results

    def all_answered(self) -> bool:
        return len(self.answers_this_round) >= len(self.players)

    def get_rankings(self) -> List[Dict]:
        ranked = sorted(
            [{"id": pid, **p} for pid, p in self.players.items()],
            key=lambda x: x["score"],
            reverse=True,
        )
        for i, r in enumerate(ranked):
            r["rank"] = i + 1
        return ranked

    def get_current_question(self) -> Optional[Dict]:
        if self.current_round < 1 or self.current_round > len(self.questions):
            return None
        q = dict(self.questions[self.current_round - 1])
        safe_q = {k: v for k, v in q.items() if k != "answer"}
        safe_q["round"] = self.current_round
        safe_q["total_rounds"] = len(self.questions)
        safe_q["time_limit"] = self.time_per_round
        return safe_q

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "game_type": self.game_type,
            "game_name": GAME_TYPES.get(self.game_type, {}).get("name", self.game_type),
            "game_icon": GAME_TYPES.get(self.game_type, {}).get("icon", "🎮"),
            "state": self.state,
            "current_round": self.current_round,
            "total_rounds": len(self.questions),
            "players": {pid: {"name": p["name"], "score": p["score"], "is_bot": p["is_bot"]} for pid, p in self.players.items()},
            "time_per_round": self.time_per_round,
        }


class GameManager:
    def __init__(self):
        self.games: Dict[str, GameSession] = {}

    def create_game(self, game_type: str, creator_id: str, creator_name: str, rounds: int = 5, add_bots: int = 1) -> GameSession:
        game = GameSession(game_type, creator_id, rounds)
        game.add_player(creator_id, creator_name)

        for i in range(min(add_bots, 3)):
            bot_id = f"bot_{game.id}_{i}"
            bot_name = BOT_NAMES[i % len(BOT_NAMES)]
            game.add_player(bot_id, bot_name, is_bot=True)

        self.games[game.id] = game
        return game

    def get_game(self, game_id: str) -> Optional[GameSession]:
        return self.games.get(game_id)

    def list_games(self) -> List[Dict]:
        now = time.time()
        active = []
        for gid, game in list(self.games.items()):
            if now - game.created_at > 3600:
                del self.games[gid]
                continue
            active.append(game.to_dict())
        return active

    def cleanup_old_games(self):
        now = time.time()
        to_remove = [gid for gid, g in self.games.items() if now - g.created_at > 3600]
        for gid in to_remove:
            del self.games[gid]


game_manager = GameManager()
