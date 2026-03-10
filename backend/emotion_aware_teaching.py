                    "actions": ["ask_diagnostic_questions", "review_prerequisites", "fill_gaps"]
                }
            ],
            EmotionState.BORED: [
                {
                    "strategy": "increase_engagement",
                    "description": "Make learning more interesting",
                    "actions": ["gamify", "add_story", "real_world_context"]
                },
                {
                    "strategy": "adjust_pace",
                    "description": "Speed up or change approach",
                    "actions": ["skip_ahead", "challenge_problems", "student_choice"]
                }
            ],
            EmotionState.ANXIOUS: [
                {
                    "strategy": "reduce_pressure",
                    "description": "Create safe learning environment",
                    "actions": ["no_grading", "unlimited_time", "positive_reinforcement"]
                },
                {
                    "strategy": "build_confidence",
                    "description": "Start with easy successes",
                    "actions": ["easy_warmup", "celebrate_small_wins", "growth_feedback"]
                }
            ],
            EmotionState.EXCITED: [
                {
                    "strategy": "channel_energy",
                    "description": "Use excitement for learning",
                    "actions": ["challenging_projects", "creative_applications", "teach_others"]
                },
                {
                    "strategy": "sustain_motivation",
                    "description": "Maintain excitement over time",
                    "actions": ["progress_tracking", "achievements", "next_challenges"]
                }
            ],
            EmotionState.FLOW: [
                {
                    "strategy": "maintain_flow",
                    "description": "Keep optimal challenge level",
                    "actions": ["gradual_increase", "varied_challenges", "minimal_interruption"]
                }
            ],
            EmotionState.FATIGUED: [
                {
                    "strategy": "reduce_cognitive_load",
                    "description": "Make learning easier",
                    "actions": ["shorter_sessions", "more_breaks", "simpler_content"]
                },
                {
                    "strategy": "energy_management",
                    "description": "Address fatigue directly",
                    "actions": ["suggest_break", "physical_movement", "hydration_reminder"]
                }
            ],
            EmotionState.PROUD: [
                {
                    "strategy": "reinforce_success",
                    "description": "Celebrate and build on success",
                    "actions": ["specific_praise", "connect_to_goals", "set_new_challenges"]
                }
            ]
        }
    
    def _initialize_intervention_templates(self) -> Dict[EmotionState, List[str]]:
        """Initialize intervention message templates"""
        return {
            EmotionState.FRUSTRATED: [
                "I can see this is challenging. Let's take a step back and try a different approach.",
                "It's okay to find this difficult. Many students struggle here. Let's break it down together.",
                "Frustration is a normal part of learning. What part is most confusing? Let's focus there."
            ],
            EmotionState.CONFUSED: [
                "Let me explain this in a different way. The key idea is...",
                "I think I see where the confusion is. Let's clarify this point first.",
                "That's a great question! Many people wonder about that. Here's how it works..."
            ],
            EmotionState.BORED: [
                "I notice this might be too easy for you. Let's try something more challenging!",
                "How about we make this more interesting? Let's add a game element.",
                "You seem ready for something more advanced. Want to try a harder problem?"
            ],
            EmotionState.ANXIOUS: [
                "There's no pressure here. Take your time, and we'll go at your pace.",
                "It's okay to make mistakes. That's how we learn. Let's try without worrying about being perfect.",
                "You're doing great! Remember, learning is a journey, not a race."
            ],
            EmotionState.FATIGUED: [
                "You've been working hard. How about a short break to refresh?",
                "Let's keep this session short and sweet. Quality over quantity!",
                "I can see you're getting tired. Let's do one more and then take a break."
            ],
            EmotionState.PROUD: [
                "Wow, you really understood that! Great work!",
                "I'm impressed with how quickly you figured that out!",
                "You should be proud of yourself. That was excellent thinking!"
            ]
        }
    
    def analyze_student_state(self, text_input: str, behavior_data: Dict, 
                            context: Dict = None) -> EmotionalState:
        """Analyze student's emotional state from multiple sources"""
        # Detect emotions from text
        text_emotions = self.emotion_detector.detect_from_text(text_input, context)
        
        # Detect emotions from behavior
        behavior_emotions = self.emotion_detector.detect_from_behavior(behavior_data)
        
        # Combine detections
        emotional_state = self.emotion_detector.combine_detections(
            text_emotions, behavior_emotions
        )
        
        # Update context
        if context:
            emotional_state.triggers.append(f"context: {context.get('learning_context', 'general')}")
        
        # Add to history
        self.emotion_history.append({
            "timestamp": datetime.now(),
            "state": emotional_state,
            "context": context
        })
        
        # Keep history manageable
        if len(self.emotion_history) > 100:
            self.emotion_history = self.emotion_history[-100:]
        
        return emotional_state
    
    def get_teaching_recommendations(self, emotional_state: EmotionalState, 
                                   learning_context: Dict = None) -> Dict:
        """Get teaching recommendations based on emotional state"""
        primary = emotional_state.primary_emotion
        intensity = emotional_state.intensity
        
        # Get strategies for primary emotion
        strategies = self.teaching_strategies.get(primary, [])
        
        # Adjust based on intensity
        adjusted_strategies = []
        for strategy in strategies:
            adjusted = strategy.copy()
            
            # Higher intensity might require more direct interventions
            if intensity > 0.7 and primary in [EmotionState.FRUSTRATED, EmotionState.ANXIOUS]:
                adjusted["priority"] = "high"
                adjusted["urgency"] = "immediate"
            elif intensity > 0.5:
                adjusted["priority"] = "medium"
                adjusted["urgency"] = "soon"
            else:
                adjusted["priority"] = "low"
                adjusted["urgency"] = "when_convenient"
            
            adjusted_strategies.append(adjusted)
        
        # Check if intervention is needed
        intervention_needed = self._check_intervention_needed(emotional_state)
        intervention = None
        
        if intervention_needed:
            intervention = self._generate_intervention(emotional_state, learning_context)
        
        # Consider secondary emotions
        secondary_recommendations = []
        for emotion, emo_intensity in emotional_state.secondary_emotions:
            if emo_intensity > 0.3:  # Significant secondary emotion
                sec_strategies = self.teaching_strategies.get(emotion, [])
                if sec_strategies:
                    secondary_recommendations.append({
                        "emotion": emotion.value,
                        "intensity": emo_intensity,
                        "strategies": sec_strategies[:1]  # Top strategy only
                    })
        
        recommendations = {
            "primary_emotion": primary.value,
            "intensity": intensity,
            "confidence": emotional_state.confidence,
            "strategies": adjusted_strategies,
            "intervention_needed": intervention_needed,
            "intervention": intervention,
            "secondary_considerations": secondary_recommendations,
            "emotional_trend": self._analyze_emotional_trend(),
            "optimal_teaching_approach": self._determine_optimal_approach(emotional_state, learning_context)
        }
        
        return recommendations
    
    def _check_intervention_needed(self, emotional_state: EmotionalState) -> bool:
        """Check if immediate intervention is needed"""
        primary = emotional_state.primary_emotion
        intensity = emotional_state.intensity
        
        # Check threshold
        threshold = self.intervention_thresholds.get(primary)
        if threshold and intensity > threshold:
            return True
        
        # Check for dangerous combinations
        secondary_intense = any(
            emotion in [EmotionState.FRUSTRATED, EmotionState.ANXIOUS] and intensity > 0.6
            for emotion, intensity in emotional_state.secondary_emotions
        )
        
        if secondary_intense and intensity > 0.5:
            return True
        
        return False
    
    def _generate_intervention(self, emotional_state: EmotionalState, 
                             context: Dict = None) -> Dict:
        """Generate intervention for emotional state"""
        primary = emotional_state.primary_emotion
        intensity = emotional_state.intensity
        
        # Get template
        templates = self.intervention_templates.get(primary, [])
        if templates:
            import random
            message = random.choice(templates)
        else:
            message = "I notice you might be feeling some strong emotions. Let's adjust our approach."
        
        # Determine intervention type
        if primary in [EmotionState.FRUSTRATED, EmotionState.CONFUSED]:
            intervention_type = "cognitive_support"
        elif primary in [EmotionState.ANXIOUS, EmotionState.FATIGUED]:
            intervention_type = "emotional_support"
        elif primary == EmotionState.BORED:
            intervention_type = "engagement_boost"
        else:
            intervention_type = "general_support"
        
        # Add context-specific adjustments
        if context:
            skill = context.get("current_skill", "the material")
            message = message.replace("this", skill)
        
        intervention = {
            "type": intervention_type,
            "message": message,
            "emotion_targeted": primary.value,
            "intensity_level": "high" if intensity > 0.7 else "medium",
            "suggested_actions": self._get_intervention_actions(primary, intensity),
            "follow_up": "Check in after intervention to assess effectiveness"
        }
        
        return intervention
    
    def _get_intervention_actions(self, emotion: EmotionState, 
                                intensity: float) -> List[str]:
        """Get specific actions for intervention"""
        if emotion == EmotionState.FRUSTRATED:
            if intensity > 0.7:
                return ["take_break", "simplify_problem", "provide_step_by_step"]
            else:
                return ["offer_hint", "break_into_parts", "encourage"]
        
        elif emotion == EmotionState.CONFUSED:
            return ["re_explain", "use_visual_aid", "give_example", "check_prerequisites"]
        
        elif emotion == EmotionState.BORED:
            return ["increase_challenge", "add_game_element", "change_topic", "student_choice"]
        
        elif emotion == EmotionState.ANXIOUS:
            return ["reduce_pressure", "positive_reinforcement", "easy_success", "breathing_exercise"]
        
        elif emotion == EmotionState.FATIGUED:
            return ["suggest_break", "shorter_session", "lighter_content", "hydration_reminder"]
        
        return ["acknowledge_emotion", "adjust_approach", "check_in"]
    
    def _analyze_emotional_trend(self) -> Dict:
        """Analyze emotional trends over time"""
        if len(self.emotion_history) < 3:
            return {"trend": "insufficient_data", "confidence": 0.1}
        
        recent_states = self.emotion_history[-5:]  # Last 5 states
        
        # Calculate trend in frustration/negative emotions
        negative_emotions = [EmotionState.FRUSTRATED, EmotionState.ANXIOUS, 
                           EmotionState.BORED, EmotionState.FATIGUED]
        
        negative_count = sum(
            1 for entry in recent_states
            if entry["state"].primary_emotion in negative_emotions
        )
        
        positive_count = len(recent_states) - negative_count
        
        trend = "improving" if positive_count > negative_count else "declining"
        
        # Calculate volatility (changes in emotion)
        emotion_changes = 0
        for i in range(1, len(recent_states)):
            if recent_states[i]["state"].primary_emotion != recent_states[i-1]["state"].primary_emotion:
                emotion_changes += 1
        
        volatility = emotion_changes / len(recent_states)
        
        return {
            "trend": trend,
            "volatility": volatility,
            "recent_negative_ratio": negative_count / len(recent_states),
            "confidence": min(1.0, len(recent_states) / 10)
        }
    
    def _determine_optimal_approach(self, emotional_state: EmotionalState,
                                  learning_context: Dict) -> str:
        """Determine optimal teaching approach based on emotion and context"""
        primary = emotional_state.primary_emotion
        intensity = emotional_state.intensity
        
        # Map emotions to teaching approaches
        approach_map = {
            EmotionState.ENGAGED: "challenge_based",
            EmotionState.CONFIDENT: "accelerated",
            EmotionState.FRUSTRATED: "scaffolded",
            EmotionState.CONFUSED: "explanatory",
            EmotionState.BORED: "interactive",
            EmotionState.ANXIOUS: "supportive",
            EmotionState.EXCITED: "project_based",
            EmotionState.FLOW: "autonomous",
            EmotionState.FATIGUED: "light",
            EmotionState.PROUD: "reinforcement"
        }
        
        base_approach = approach_map.get(primary, "adaptive")
        
        # Adjust based on intensity
        if intensity > 0.7:
            if primary in [EmotionState.FRUSTRATED, EmotionState.ANXIOUS]:
                base_approach = "high_support"
            elif primary in [EmotionState.CONFIDENT, EmotionState.ENGAGED]:
                base_approach = "high_challenge"
        
        # Adjust based on context
        if learning_context:
            difficulty = learning_context.get("difficulty", 0.5)
            if difficulty > 0.7 and primary not in [EmotionState.CONFIDENT, EmotionState.ENGAGED]:
                base_approach = "high_scaffolding"
            elif difficulty < 0.3 and primary not in [EmotionState.BORED, EmotionState.FATIGUED]:
                base_approach = "enrichment"
        
        return base_approach
    
    def generate_empathetic_response(self, emotional_state: EmotionalState,
                                   learning_context: Dict = None) -> str:
        """Generate empathetic response based on emotional state"""
        primary = emotional_state.primary_emotion
        
        # Base empathetic responses
        empathetic_responses = {
            EmotionState.FRUSTRATED: "I can see this is really challenging you. That's okay - tough problems help us grow the most.",
            EmotionState.CONFUSED: "It's completely normal to feel confused here. Many students find this part tricky.",
            EmotionState.BORED: "I get the sense this might not be engaging enough for you. Let's make it more interesting!",
            EmotionState.ANXIOUS: "I understand this might feel stressful. Remember, we're here to learn, not to be perfect.",
            EmotionState.FATIGUED: "You've been working hard. It's important to listen to your body and mind.",
            EmotionState.PROUD: "I can tell you're really proud of what you just accomplished - and you should be!",
            EmotionState.EXCITED: "Your excitement is contagious! This is what learning is all about.",
            EmotionState.ENGAGED: "I love how focused and engaged you are. That's the key to deep learning.",
            EmotionState.CONFIDENT: "Your confidence is showing - and it's well deserved!",
            EmotionState.FLOW: "You're in the zone! This is that perfect balance of challenge and skill."
        }
        
        response = empathetic_responses.get(primary, 
                                          "I'm here to support your learning journey.")
        
        # Add context-specific element
        if learning_context:
            skill = learning_context.get("current_skill")
            if skill:
                response = response.replace("this", f"this {skill}")
        
        return response
    
    def get_emotion_history_summary(self, limit: int = 10) -> Dict:
        """Get summary of emotion history"""
        if not self.emotion_history:
            return {"message": "No emotion history available"}
        
        recent = self.emotion_history[-limit:]
        
        summary = {
            "total_entries": len(self.emotion_history),
            "recent_emotions": [
                {
                    "timestamp": entry["timestamp"].isoformat(),
                    "emotion": entry["state"].primary_emotion.value,
                    "intensity": entry["state"].intensity,
                    "confidence": entry["state"].confidence
                }
                for entry in recent
            ],
            "emotion_distribution": self._calculate_emotion_distribution(),
            "average_intensity": np.mean([e["state"].intensity for e in recent]) if recent else 0,
            "most_common_emotion": self._get_most_common_emotion()
        }
        
        return summary
    
    def _calculate_emotion_distribution(self) -> Dict[str, float]:
        """Calculate distribution of emotions in history"""
        if not self.emotion_history:
            return {}
        
        emotion_counts = {}
        for entry in self.emotion_history:
            emotion = entry["state"].primary_emotion.value
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        total = sum(emotion_counts.values())
        distribution = {
            emotion: count / total
            for emotion, count in emotion_counts.items()
        }
        
        return distribution
    
    def _get_most_common_emotion(self) -> str:
        """Get most common emotion in history"""
        distribution = self._calculate_emotion_distribution()
        if not distribution:
            return "unknown"
        
        return max(distribution.items(), key=lambda x: x[1])[0]


# Example usage
if __name__ == "__main__":
    #