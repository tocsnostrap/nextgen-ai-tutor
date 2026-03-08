            rationale_parts.append("Challenging to promote growth")
        
        # Engagement rationale
        if content.engagement_potential > 0.7:
            rationale_parts.append("High engagement potential")
        elif state.engagement_level < 0.5:
            rationale_parts.append("Selected for engagement boost")
        
        # Learning style rationale
        style_match = self._calculate_style_match(content, state)
        if style_match > 0.8:
            rationale_parts.append(f"Matches {state.learning_style} learning style")
        
        # Time rationale
        if content.estimated_time <= 5 and (state.fatigue_level > 0.6 or state.session_duration > 20):
            rationale_parts.append("Short duration suitable for current fatigue level")
        
        # Add adaptation reasons
        for adaptation in adaptations:
            if "reason" in adaptation:
                rationale_parts.append(adaptation["reason"])
        
        if not rationale_parts:
            rationale_parts.append("Balanced content selection based on multiple factors")
        
        return ". ".join(rationale_parts) + "."
    
    def generate_intervention(self, student_state: StudentState, 
                            problem_context: Dict = None) -> Dict:
        """
        Generate intervention based on student state and context
        
        Returns:
            Intervention specification
        """
        interventions = []
        
        # Check for immediate needs
        if student_state.frustration > self.frustration_threshold:
            interventions.append({
                "type": InterventionType.ENCOURAGEMENT.value,
                "priority": "high",
                "message": self._generate_encouragement(student_state),
                "action": "provide_immediate_support"
            })
        
        if student_state.recent_accuracy < 0.3:
            interventions.append({
                "type": InterventionType.HINT.value,
                "priority": "high",
                "content": self._generate_hint(problem_context),
                "action": "scaffold_problem"
            })
        
        if student_state.engagement_level < self.engagement_threshold:
            interventions.append({
                "type": InterventionType.CHALLENGE.value,
                "priority": "medium",
                "message": "Let's try a different approach to make this more interesting!",
                "action": "increase_engagement"
            })
        
        if student_state.fatigue_level > 0.7:
            interventions.append({
                "type": InterventionType.BREAK.value,
                "priority": "medium",
                "duration": 3,  # minutes
                "message": "Great work! Let's take a short break to refresh."
            })
        
        # Sort by priority
        interventions.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["priority"]])
        
        # Select top intervention
        if interventions:
            selected = interventions[0]
            
            # Add metadata
            selected["generated_at"] = datetime.now().isoformat()
            selected["student_state_snapshot"] = self._state_to_dict(student_state)
            
            return selected
        
        # No intervention needed
        return {
            "type": "none",
            "priority": "low",
            "message": "Continuing with current approach",
            "reason": "Student in optimal learning state"
        }
    
    def _generate_encouragement(self, state: StudentState) -> str:
        """Generate personalized encouragement message"""
        encouragement_templates = [
            "You're making progress! Remember that learning takes time.",
            "I can see you're working hard. That's how mastery is built!",
            "Every expert was once a beginner. You're on the right path.",
            "Challenges help us grow. You're building resilience right now.",
            "I believe in your ability to figure this out. Let's try one more time."
        ]
        
        # Select based on frustration level
        if state.frustration > 0.8:
            return "I can see this is challenging. Let's take a step back and approach it differently."
        elif state.confidence < 0.3:
            return "You know more than you think! Let's build on what you already understand."
        else:
            import random
            return random.choice(encouragement_templates)
    
    def _generate_hint(self, problem_context: Dict = None) -> str:
        """Generate context-aware hint"""
        if not problem_context:
            return "Try breaking the problem down into smaller steps."
        
        # In a real implementation, would generate hints based on problem type
        hint_strategies = [
            "What's the first step you would take?",
            "Can you identify what information you already have?",
            "Try working backwards from the solution.",
            "Is there a similar problem you've solved before?",
            "What would happen if you tried a different approach?"
        ]
        
        import random
        return random.choice(hint_strategies)
    
    def adjust_teaching_strategy(self, student_state: StudentState, 
                               current_strategy: TeachingStrategy) -> TeachingStrategy:
        """Adjust teaching strategy based on student state"""
        
        # Map states to preferred strategies
        strategy_preferences = []
        
        if student_state.mastery_level == "novice":
            strategy_preferences.extend([
                (TeachingStrategy.DIRECT_INSTRUCTION, 0.9),
                (TeachingStrategy.SCAFFOLDED_LEARNING, 0.8)
            ])
        
        if student_state.engagement_level < 0.5:
            strategy_preferences.extend([
                (TeachingStrategy.GAMIFIED, 0.8),
                (TeachingStrategy.CONVERSATIONAL, 0.7)
            ])
        
        if student_state.confidence > 0.7:
            strategy_preferences.extend([
                (TeachingStrategy.DISCOVERY_BASED, 0.8),
                (TeachingStrategy.PROBLEM_SOLVING, 0.9)
            ])
        
        if student_state.learning_style == "kinesthetic":
            strategy_preferences.append((TeachingStrategy.GAMIFIED, 0.9))
        
        if student_state.flow_state > 0.7:
            # Don't change strategy if in flow state
            return current_strategy
        
        # Calculate scores for each strategy
        strategy_scores = {}
        for strategy, base_score in strategy_preferences:
            if strategy not in strategy_scores:
                strategy_scores[strategy] = 0.0
            strategy_scores[strategy] += base_score
        
        # Add current strategy with inertia
        if current_strategy in strategy_scores:
            strategy_scores[current_strategy] += 0.3  # Inertia bonus
        else:
            strategy_scores[current_strategy] = 0.3
        
        # Select best strategy
        if strategy_scores:
            best_strategy = max(strategy_scores.items(), key=lambda x: x[1])[0]
            
            # Only change if significantly better
            current_score = strategy_scores.get(current_strategy, 0.0)
            best_score = strategy_scores[best_strategy]
            
            if best_score > current_score + 0.2:  # Threshold for change
                return best_strategy
        
        return current_strategy
    
    def calculate_optimal_pace(self, student_state: StudentState) -> Dict:
        """Calculate optimal learning pace"""
        
        pace_factors = {
            "content_density": 0.5,  # How dense the content should be
            "practice_frequency": 0.5,  # How often to practice
            "review_interval": 24,  # Hours between reviews
            "session_length": 20,  # Minutes per session
            "breaks_needed": 2  # Number of breaks per hour
        }
        
        # Adjust based on student state
        if student_state.optimal_pace == "fast":
            pace_factors["content_density"] = 0.7
            pace_factors["practice_frequency"] = 0.7
            pace_factors["session_length"] = 25
        
        elif student_state.optimal_pace == "slow":
            pace_factors["content_density"] = 0.3
            pace_factors["practice_frequency"] = 0.3
            pace_factors["session_length"] = 15
            pace_factors["breaks_needed"] = 3
        
        # Adjust for fatigue
        if student_state.fatigue_level > 0.6:
            pace_factors["content_density"] *= 0.7
            pace_factors["session_length"] *= 0.8
            pace_factors["breaks_needed"] += 1
        
        # Adjust for engagement
        if student_state.engagement_level > 0.8:
            pace_factors["content_density"] *= 1.2
            pace_factors["session_length"] = min(30, pace_factors["session_length"] * 1.2)
        
        # Adjust for time of day
        if student_state.time_of_day == "evening":
            pace_factors["content_density"] *= 0.8
            pace_factors["session_length"] *= 0.8
        
        return pace_factors
    
    def _state_to_dict(self, state: StudentState) -> Dict:
        """Convert StudentState to dictionary"""
        return {
            "p_knowledge": state.p_knowledge,
            "mastery_level": state.mastery_level,
            "recent_accuracy": state.recent_accuracy,
            "response_time_avg": state.response_time_avg,
            "consistency_score": state.consistency_score,
            "engagement_level": state.engagement_level,
            "motivation_level": state.motivation_level,
            "fatigue_level": state.fatigue_level,
            "confidence": state.confidence,
            "frustration": state.frustration,
            "flow_state": state.flow_state,
            "learning_momentum": state.learning_momentum,
            "optimal_pace": state.optimal_pace,
            "learning_style": state.learning_style,
            "session_duration": state.session_duration,
            "time_of_day": state.time_of_day,
            "days_since_last_practice": state.days_since_last_practice
        }
    
    def get_adaptation_history(self, limit: int = 10) -> List[Dict]:
        """Get recent adaptation history"""
        return self.adaptation_history[-limit:]
    
    def get_adaptation_analytics(self) -> Dict:
        """Get analytics on adaptation effectiveness"""
        if not self.adaptation_history:
            return {"message": "No adaptation history available"}
        
        # Calculate adaptation frequencies
        adaptation_types = {}
        content_selections = {}
        
        for record in self.adaptation_history:
            # Count adaptation types
            for adaptation in record.get("adaptations", []):
                adapt_type = adaptation.get("type", "unknown")
                adaptation_types[adapt_type] = adaptation_types.get(adapt_type, 0) + 1
            
            # Count content selections
            content_id = record.get("selected_content", "unknown")
            content_selections[content_id] = content_selections.get(content_id, 0) + 1
        
        # Calculate effectiveness (simplified - would use outcome data in production)
        total_adaptations = sum(adaptation_types.values())
        adaptation_distribution = {
            k: v / total_adaptations 
            for k, v in adaptation_types.items()
        }
        
        return {
            "total_adaptations": total_adaptations,
            "adaptation_distribution": adaptation_distribution,
            "most_frequent_adaptations": sorted(
                adaptation_types.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5],
            "most_selected_content": sorted(
                content_selections.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5],
            "adaptation_rate": len(self.adaptation_history) / max(1, len(self.adaptation_history) / 10)
        }


# Example usage
if __name__ == "__main__":
    # Create adaptation engine
    engine = AdaptationEngine()
    
    # Add sample content
    sample_content = [
        ContentItem(
            content_id="math_exp_001",
            skill_id="addition",
            difficulty=0.4,
            content_type="explanation",
            modality="text",
            estimated_time=5,
            prerequisites=[],
            learning_objectives=["Understand basic addition"],
            adaptability_score=0.8,
            engagement_potential=0.6,
            cognitive_load=0.4
        ),
        ContentItem(
            content_id="math_game_001",
            skill_id="addition",
            difficulty=0.5,
            content_type="game",
            modality="interactive",
            estimated_time=8,
            prerequisites=["math_exp_001"],
            learning_objectives=["Practice addition in fun context"],
            adaptability_score=0.9,
            engagement_potential=0.9,
            cognitive_load=0.6
        ),
        ContentItem(
            content_id="math_quiz_001",
            skill_id="addition",
            difficulty=0.6,
            content_type="quiz",
            modality="interactive",
            estimated_time=10,
            prerequisites=["math_exp_001", "math_game_001"],
            learning_objectives=["Assess addition mastery"],
            adaptability_score=0.7,
            engagement_potential=0.7,
            cognitive_load=0.7
        )
    ]
    
    for content in sample_content:
        engine.add_content(content)
    
    # Create sample student state
    student_state = StudentState(
        p_knowledge=0.6,
        mastery_level="intermediate",
        recent_accuracy=0.7,
        response_time_avg=8.5,
        consistency_score=0.6,
        engagement_level=0.5,
        motivation_level=0.6,
        fatigue_level=0.3,
        confidence=0.4,
        frustration=0.2,
        flow_state=0.5,
        learning_momentum=0.1,
        optimal_pace="moderate",
        learning_style="visual",
        session_duration=15,
        time_of_day="afternoon",
        days_since_last_practice=1
    )
    
    print("=== Content Selection ===")
    selected_content, metadata = engine.select_content(student_state, target_skill="addition")
    
    print(f"Selected: {selected_content.content_id}")
    print(f"Type: {selected_content.content_type}")
    print(f"Difficulty: {selected_content.difficulty}")
    print(f"Estimated time: {selected_content.estimated_time} minutes")
    print(f"Selection score: {metadata['selection_score']:.3f}")
    print(f"Rationale: {metadata['rationale']}")
    
    print("\n=== Adaptations ===")
    for adaptation in metadata['adaptations']:
        print(f"- {adaptation['type']}: {adaptation.get('reason', 'No reason provided')}")
    
    print("\n=== Intervention Check ===")
    intervention = engine.generate_intervention(student_state)
    print(f"Intervention needed: {intervention['type'] != 'none'}")
    if intervention['type'] != 'none':
        print(f"Type: {intervention['type']}")
        print(f"Priority: {intervention['priority']}")
        print(f"Message: {intervention['message']}")
    
    print("\n=== Teaching Strategy ===")
    current_strategy = TeachingStrategy.DIRECT_INSTRUCTION
    new_strategy = engine.adjust_teaching_strategy(student_state, current_strategy)
    print(f"Current: {current_strategy.value}")
    print(f"Recommended: {new_strategy.value}")
    print(f"Change: {'Yes' if current_strategy != new_strategy else 'No'}")
    
    print("\n=== Optimal Pace ===")
    pace = engine.calculate_optimal_pace(student_state)
    print(f"Session length: {pace['session_length']} minutes")
    print(f"Content density: {pace['content_density']:.2f}")
    print(f"Breaks needed: {pace['breaks_needed']} per hour")
    
    print("\n=== Adaptation Analytics ===")
    analytics = engine.get_adaptation_analytics()
    print(f"Total adaptations: {analytics['total_adaptations']}")
    print("Most frequent adaptations:")
    for adapt_type, count in analytics.get('most_frequent_adaptations', []):
        print(f"  {adapt_type}: {count}")