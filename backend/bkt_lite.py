import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class BKTLite:
    def __init__(self):
        self.skill_params: Dict[str, Dict[str, float]] = {}
        self.student_states: Dict[str, Dict[str, Dict]] = {}

    def initialize_skill(self, skill_id: str, p_init: float = 0.3, p_learn: float = 0.2, p_guess: float = 0.15, p_slip: float = 0.1):
        self.skill_params[skill_id] = {
            "p_init": p_init,
            "p_learn": p_learn,
            "p_guess": p_guess,
            "p_slip": p_slip,
        }

    def update(self, user_id: str, skill_id: str, correct: bool) -> dict:
        if skill_id not in self.skill_params:
            self.initialize_skill(skill_id)

        if user_id not in self.student_states:
            self.student_states[user_id] = {}

        params = self.skill_params[skill_id]

        if skill_id not in self.student_states[user_id]:
            self.student_states[user_id][skill_id] = {
                "p_knowledge": params["p_init"],
                "total_attempts": 0,
                "correct_attempts": 0,
            }

        state = self.student_states[user_id][skill_id]
        old_p = state["p_knowledge"]

        p_slip = params["p_slip"]
        p_guess = params["p_guess"]
        p_learn = params["p_learn"]

        p_correct_given_know = 1.0 - p_slip
        p_correct_given_not_know = p_guess

        if correct:
            numerator = old_p * p_correct_given_know
            denominator = old_p * p_correct_given_know + (1.0 - old_p) * p_correct_given_not_know
        else:
            numerator = old_p * p_slip
            denominator = old_p * p_slip + (1.0 - old_p) * (1.0 - p_guess)

        if denominator > 0:
            p_posterior = numerator / denominator
        else:
            p_posterior = old_p

        new_p = p_posterior + (1.0 - p_posterior) * p_learn

        state["p_knowledge"] = new_p
        state["total_attempts"] += 1
        if correct:
            state["correct_attempts"] += 1

        if new_p >= 0.9:
            mastery_level = "mastered"
        elif new_p >= 0.7:
            mastery_level = "proficient"
        elif new_p >= 0.4:
            mastery_level = "developing"
        else:
            mastery_level = "novice"

        return {
            "skill": skill_id,
            "previous_mastery": round(old_p, 4),
            "current_mastery": round(new_p, 4),
            "mastery_change": round(new_p - old_p, 4),
            "mastery_level": mastery_level,
            "total_attempts": state["total_attempts"],
            "correct_attempts": state["correct_attempts"],
        }

    def get_mastery(self, user_id: str, skill_id: str) -> float:
        if user_id in self.student_states and skill_id in self.student_states[user_id]:
            return self.student_states[user_id][skill_id]["p_knowledge"]
        if skill_id in self.skill_params:
            return self.skill_params[skill_id]["p_init"]
        return 0.3

    def get_all_mastery(self, user_id: str) -> dict:
        if user_id not in self.student_states:
            return {}
        return {
            skill_id: state["p_knowledge"]
            for skill_id, state in self.student_states[user_id].items()
        }


bkt_lite = BKTLite()

for skill in [
    "addition", "subtraction", "multiplication", "division",
    "fractions", "decimals", "geometry", "algebra",
    "counting", "patterns", "measurement",
    "plants", "animals", "weather", "ecosystems",
    "matter", "energy", "forces",
    "comprehension", "vocabulary", "phonics", "inference",
    "variables", "loops", "functions", "conditionals", "algorithms",
]:
    bkt_lite.initialize_skill(skill)
