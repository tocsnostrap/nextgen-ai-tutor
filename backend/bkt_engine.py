        total_p_knowledge = 0.0
        total_consistency = 0.0
        total_efficiency = 0.0
        
        for skill_id, state in skill_states.items():
            skill_report = {
                "skill_id": skill_id,
                "p_knowledge": state.p_knowledge,
                "mastery_level": self._get_mastery_level(state.p_knowledge),
                "opportunities": state.opportunities,
                "accuracy": state.correct_count / max(1, state.total_count),
                "consistency": state.consistency_score,
                "confidence": state.confidence,
                "learning_momentum": state.learning_momentum,
                "transfer_potential": state.transfer_potential,
                "needs_review": self._needs_review(state, self.skill_parameters[skill_id]),
                "last_updated": state.last_updated.isoformat()
            }
            report["skills"].append(skill_report)
            
            total_p_knowledge += state.p_knowledge
            total_consistency += state.consistency_score
            
            # Calculate learning efficiency (knowledge gained per opportunity)
            if state.opportunities > 0:
                efficiency = state.p_knowledge / state.opportunities
                total_efficiency += efficiency
        
        if skill_states:
            report["overall_mastery"] = total_p_knowledge / len(skill_states)
            report["consistency"] = total_consistency / len(skill_states)
            report["learning_efficiency"] = total_efficiency / len(skill_states)
        
        return report
    
    def save_state(self, filepath: str):
        """Save engine state to file"""
        state = {
            "skill_parameters": {k: v.to_dict() for k, v in self.skill_parameters.items()},
            "student_states": {
                student_id: {
                    skill_id: state.to_dict() 
                    for skill_id, state in skill_states.items()
                }
                for student_id, skill_states in self.student_states.items()
            },
            "use_deep_learning": self.use_deep_learning
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2, default=str)
        
        logger.info(f"Engine state saved to {filepath}")
    
    def load_state(self, filepath: str):
        """Load engine state from file"""
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        self.use_deep_learning = state.get("use_deep_learning", True)
        
        # Load skill parameters
        self.skill_parameters = {}
        for skill_id, params_dict in state.get("skill_parameters", {}).items():
            self.skill_parameters[skill_id] = SkillParameters.from_dict(params_dict)
        
        # Load student states
        self.student_states = {}
        for student_id, skill_states_dict in state.get("student_states", {}).items():
            self.student_states[student_id] = {}
            for skill_id, state_dict in skill_states_dict.items():
                self.student_states[student_id][skill_id] = StudentSkillState.from_dict(state_dict)
        
        logger.info(f"Engine state loaded from {filepath}")
    
    def export_for_visualization(self, student_id: str) -> Dict:
        """Export data for visualization frontend"""
        if student_id not in self.student_states:
            return {"error": "Student not found"}
        
        skill_states = self.student_states[student_id]
        
        # Prepare time series data for each skill
        visualization_data = {
            "student_id": student_id,
            "skills": [],
            "timeline": []
        }
        
        for skill_id, state in skill_states.items():
            skill_data = {
                "skill_id": skill_id,
                "current_p_knowledge": state.p_knowledge,
                "mastery_level": self._get_mastery_level(state.p_knowledge),
                "progress_data": [
                    {"opportunity": i, "p_knowledge": state.p_knowledge * (i / max(1, state.opportunities))}
                    for i in range(1, state.opportunities + 1)
                ],
                "accuracy": state.correct_count / max(1, state.total_count),
                "consistency": state.consistency_score
            }
            visualization_data["skills"].append(skill_data)
        
        return visualization_data


# Example usage and testing
if __name__ == "__main__":
    # Create BKT engine
    engine = BKTEngine(use_deep_learning=True)
    
    # Initialize some skills
    engine.initialize_skill("addition_basic", p_init=0.2, p_learn=0.3, p_guess=0.1, p_slip=0.05)
    engine.initialize_skill("subtraction_basic", p_init=0.15, p_learn=0.25, p_guess=0.15, p_slip=0.08)
    engine.initialize_skill("multiplication_basic", p_init=0.1, p_learn=0.2, p_guess=0.2, p_slip=0.1)
    
    # Simulate student interactions
    student_id = "student_123"
    
    print("=== Initial State ===")
    print(engine.get_student_progress_report(student_id))
    
    print("\n=== Simulating Learning Session ===")
    
    # Practice addition
    print("\nPracticing addition:")
    for i in range(10):
        # Simulate responses (getting better over time)
        correct = np.random.random() < (0.3 + i * 0.07)  # Improving accuracy
        response_time = np.random.uniform(3, 15)  # Random response time
        confidence = np.random.uniform(0.4, 0.9)  # Random confidence
        
        p_knowledge, metadata = engine.update_with_observation(
            student_id, "addition_basic", correct, response_time, confidence
        )
        
        print(f"  Attempt {i+1}: {'Correct' if correct else 'Incorrect'}, "
              f"P(knowledge)={p_knowledge:.3f}, "
              f"Mastery={metadata['mastery_level']}")
    
    # Practice subtraction
    print("\nPracticing subtraction:")
    for i in range(8):
        correct = np.random.random() < (0.25 + i * 0.08)
        response_time = np.random.uniform(4, 20)
        confidence = np.random.uniform(0.3, 0.8)
        
        p_knowledge, metadata = engine.update_with_observation(
            student_id, "subtraction_basic", correct, response_time, confidence
        )
        
        print(f"  Attempt {i+1}: {'Correct' if correct else 'Incorrect'}, "
              f"P(knowledge)={p_knowledge:.3f}")
    
    print("\n=== Final Progress Report ===")
    report = engine.get_student_progress_report(student_id)
    print(f"Overall Mastery: {report['overall_mastery']:.3f}")
    print(f"Learning Efficiency: {report['learning_efficiency']:.3f}")
    print(f"Consistency: {report['consistency']:.3f}")
    
    print("\n=== Skill Recommendations ===")
    recommendations = engine.get_skill_recommendations(
        student_id, ["addition_basic", "subtraction_basic", "multiplication_basic"]
    )
    for rec in recommendations:
        print(f"  {rec['skill_id']}: Priority={rec['priority_score']:.3f}, "
              f"Mastery={rec['mastery_level']}, Needs Review={rec['needs_review']}")
    
    # Save state
    engine.save_state("bkt_engine_state.json")
    print("\nEngine state saved to bkt_engine_state.json")