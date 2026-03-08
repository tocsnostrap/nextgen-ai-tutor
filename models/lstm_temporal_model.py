        # Analyze time-of-day patterns
        morning_perf = []
        afternoon_perf = []
        evening_perf = []
        
        for feat in sequence:
            hour = feat.timestamp.hour
            if 6 <= hour < 12:
                morning_perf.append(feat.correctness)
            elif 12 <= hour < 18:
                afternoon_perf.append(feat.correctness)
            else:
                evening_perf.append(feat.correctness)
        
        # Calculate average performance for each period
        periods = {
            "morning": np.mean(morning_perf) if morning_perf else 0.0,
            "afternoon": np.mean(afternoon_perf) if afternoon_perf else 0.0,
            "evening": np.mean(evening_perf) if evening_perf else 0.0
        }
        
        # Find best period
        best_period = max(periods.items(), key=lambda x: x[1])
        
        # Analyze day-of-week patterns
        weekday_perf = {i: [] for i in range(7)}  # 0=Monday, 6=Sunday
        
        for feat in sequence:
            weekday = feat.timestamp.weekday()
            weekday_perf[weekday].append(feat.correctness)
        
        # Calculate average for each weekday
        weekday_avg = {
            day: np.mean(perf) if perf else 0.0
            for day, perf in weekday_perf.items()
        }
        
        # Find best weekday
        best_weekday = max(weekday_avg.items(), key=lambda x: x[1])
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        return {
            "best_time_of_day": best_period[0],
            "best_time_performance": float(best_period[1]),
            "best_weekday": weekday_names[best_weekday[0]],
            "best_weekday_performance": float(best_weekday[1]),
            "recommended_schedule": f"Practice during {best_period[0]} on {weekday_names[best_weekday[0]]}s"
        }
    
    def _estimate_decay_rate(self, sequence: List[TemporalFeature]) -> float:
        """Estimate knowledge decay rate based on temporal patterns"""
        if len(sequence) < 15:
            return 0.1  # Default decay rate
        
        # Look for patterns of forgetting after breaks
        # This is a simplified estimation
        # In production, would use more sophisticated time-series analysis
        
        # Calculate autocorrelation at different lags
        correctness_series = [feat.correctness for feat in sequence]
        
        if len(correctness_series) > 5:
            # Simple decay estimation based on performance after gaps
            decay_estimates = []
            
            for i in range(1, len(sequence)):
                time_gap = (sequence[i].timestamp - sequence[i-1].timestamp).total_seconds() / 3600  # hours
                
                if time_gap > 12:  # Significant gap
                    performance_change = correctness_series[i] - correctness_series[i-1]
                    if performance_change < 0:  # Performance declined
                        decay_rate = -performance_change / time_gap
                        decay_estimates.append(decay_rate)
            
            if decay_estimates:
                avg_decay = np.mean(decay_estimates)
                return min(0.5, max(0.0, float(avg_decay)))
        
        return 0.1  # Default decay rate
    
    def get_student_insights(self, student_id: str) -> Dict:
        """Get comprehensive insights for a student"""
        patterns = self.analyze_patterns(student_id)
        
        if "error" in patterns or "warning" in patterns:
            return patterns
        
        # Generate insights based on patterns
        insights = {
            "learning_style": self._infer_learning_style(patterns),
            "optimal_pace": self._recommend_pace(patterns),
            "strengths": self._identify_strengths(patterns),
            "areas_for_improvement": self._identify_improvement_areas(patterns),
            "personalized_recommendations": self._generate_recommendations(patterns),
            "predicted_outcome": self._predict_outcome(patterns)
        }
        
        return {
            "patterns": patterns,
            "insights": insights
        }
    
    def _infer_learning_style(self, patterns: Dict) -> str:
        """Infer learning style from temporal patterns"""
        consistency = patterns.get('consistency_pattern', 'unknown')
        learning_curve = patterns.get('learning_curve', 0.0)
        engagement = patterns.get('engagement_level', 0.5)
        
        if consistency == "highly_consistent" and learning_curve > 0.1:
            return "steady_learner"
        elif consistency == "highly_variable" and engagement > 0.7:
            return "exploratory_learner"
        elif learning_curve > 0.2:
            return "quick_learner"
        elif engagement < 0.4:
            return "needs_motivation"
        else:
            return "balanced_learner"
    
    def _recommend_pace(self, patterns: Dict) -> str:
        """Recommend learning pace based on patterns"""
        momentum = patterns.get('learning_momentum', 0.0)
        fatigue = patterns.get('fatigue_pattern', False)
        consistency = patterns.get('consistency_pattern', 'unknown')
        
        if momentum > 0.3 and not fatigue:
            return "accelerated"
        elif momentum < -0.2 or fatigue:
            return "slower"
        elif consistency == "highly_consistent":
            return "steady"
        else:
            return "adaptive"
    
    def _identify_strengths(self, patterns: Dict) -> List[str]:
        """Identify student strengths"""
        strengths = []
        
        if patterns.get('consistency_pattern') in ["consistent", "highly_consistent"]:
            strengths.append("consistent_performance")
        
        if patterns.get('learning_curve', 0.0) > 0.15:
            strengths.append("quick_learning")
        
        if patterns.get('engagement_level', 0.5) > 0.7:
            strengths.append("high_engagement")
        
        if patterns.get('retention_probability', 0.5) > 0.7:
            strengths.append("good_retention")
        
        if not patterns.get('fatigue_pattern', False):
            strengths.append("good_endurance")
        
        return strengths
    
    def _identify_improvement_areas(self, patterns: Dict) -> List[str]:
        """Identify areas for improvement"""
        areas = []
        
        if patterns.get('consistency_pattern') in ["variable", "highly_variable"]:
            areas.append("consistency")
        
        if patterns.get('learning_curve', 0.0) < 0.0:
            areas.append("learning_rate")
        
        if patterns.get('engagement_level', 0.5) < 0.4:
            areas.append("engagement")
        
        if patterns.get('fatigue_pattern', False):
            areas.append("endurance")
        
        if patterns.get('next_correctness_prob', 0.5) < 0.4:
            areas.append("current_understanding")
        
        return areas
    
    def _generate_recommendations(self, patterns: Dict) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        # Based on learning state
        learning_state = patterns.get('learning_state', 'learning')
        if learning_state == "struggling":
            recommendations.append("Focus on foundational concepts before advancing")
            recommendations.append("Use more visual aids and examples")
        
        # Based on engagement
        engagement = patterns.get('engagement_level', 0.5)
        if engagement < 0.4:
            recommendations.append("Incorporate more interactive elements")
            recommendations.append("Take more frequent short breaks")
        
        # Based on consistency
        consistency = patterns.get('consistency_pattern', 'unknown')
        if consistency in ["variable", "highly_variable"]:
            recommendations.append("Practice similar problems to build consistency")
            recommendations.append("Review previous concepts regularly")
        
        # Based on fatigue
        if patterns.get('fatigue_pattern', False):
            recommendations.append("Shorter, more frequent practice sessions")
            recommendations.append("Practice during optimal times (see schedule)")
        
        # Based on momentum
        momentum = patterns.get('learning_momentum', 0.0)
        if momentum > 0.2:
            recommendations.append("You're on a good streak - consider challenging yourself")
        elif momentum < -0.2:
            recommendations.append("Take a step back and review fundamentals")
        
        return recommendations
    
    def _predict_outcome(self, patterns: Dict) -> Dict:
        """Predict learning outcome based on current patterns"""
        correctness_prob = patterns.get('next_correctness_prob', 0.5)
        learning_curve = patterns.get('learning_curve', 0.0)
        engagement = patterns.get('engagement_level', 0.5)
        retention = patterns.get('retention_probability', 0.5)
        
        # Calculate success probability
        success_prob = (correctness_prob * 0.3 + 
                       max(0.0, learning_curve) * 2.0 * 0.3 + 
                       engagement * 0.2 + 
                       retention * 0.2)
        
        success_prob = min(1.0, max(0.0, success_prob))
        
        # Time to mastery estimation (simplified)
        if learning_curve > 0.0:
            time_to_mastery = 10.0 / (learning_curve * 10.0)  # sessions
        else:
            time_to_mastery = 20.0  # default
        
        return {
            "success_probability": float(success_prob),
            "time_to_mastery_sessions": float(time_to_mastery),
            "predicted_mastery_level": self._predict_mastery_level(success_prob),
            "confidence_in_prediction": patterns.get('confidence', 0.5)
        }
    
    def _predict_mastery_level(self, success_prob: float) -> str:
        """Predict final mastery level"""
        if success_prob > 0.8:
            return "advanced_mastery"
        elif success_prob > 0.6:
            return "proficient"
        elif success_prob > 0.4:
            return "competent"
        else:
            return "basic_understanding"


# Example usage
if __name__ == "__main__":
    # Create analyzer
    analyzer = TemporalPatternAnalyzer()
    
    # Generate sample data
    import random
    from datetime import datetime, timedelta
    
    student_id = "student_456"
    base_time = datetime.now() - timedelta(hours=10)
    
    print("=== Generating Sample Data ===")
    
    for i in range(20):
        # Create temporal feature
        feature = TemporalFeature(
            response_time=random.uniform(3, 15),
            correctness=1.0 if random.random() < (0.4 + i * 0.03) else 0.0,
            confidence=random.uniform(0.3, 0.9),
            hint_usage=0.0 if random.random() < 0.8 else random.uniform(0.1, 0.5),
            engagement_level=random.uniform(0.5, 0.9),
            difficulty_level=random.uniform(0.3, 0.7),
            timestamp=base_time + timedelta(minutes=i * 30)
        )
        
        analyzer.add_interaction(student_id, feature)
        
        print(f"  Added interaction {i+1}: "
              f"Correct={feature.correctness:.1f}, "
              f"Time={feature.response_time:.1f}s, "
              f"Confidence={feature.confidence:.2f}")
    
    print("\n=== Analyzing Temporal Patterns ===")
    patterns = analyzer.analyze_patterns(student_id)
    
    print(f"Next correctness probability: {patterns.get('next_correctness_prob', 0.0):.3f}")
    print(f"Learning state: {patterns.get('learning_state', 'unknown')}")
    print(f"Optimal difficulty: {patterns.get('optimal_difficulty', 0.0):.3f}")
    print(f"Engagement level: {patterns.get('engagement_level', 0.0):.3f}")
    print(f"Learning momentum: {patterns.get('learning_momentum', 0.0):.3f}")
    print(f"Intervention needed: {patterns.get('intervention_needed', False)}")
    print(f"Recommended action: {patterns.get('recommended_action', 'none')}")
    
    print("\n=== Student Insights ===")
    insights = analyzer.get_student_insights(student_id)
    
    if "insights" in insights:
        print(f"Learning style: {insights['insights'].get('learning_style', 'unknown')}")
        print(f"Optimal pace: {insights['insights'].get('optimal_pace', 'unknown')}")
        print(f"Strengths: {', '.join(insights['insights'].get('strengths', []))}")
        print(f"Areas for improvement: {', '.join(insights['insights'].get('areas_for_improvement', []))}")
        
        print("\nPersonalized recommendations:")
        for rec in insights['insights'].get('personalized_recommendations', []):
            print(f"  • {rec}")
        
        outcome = insights['insights'].get('predicted_outcome', {})
        print(f"\nPredicted outcome:")
        print(f"  Success probability: {outcome.get('success_probability', 0.0):.1%}")
        print(f"  Time to mastery: {outcome.get('time_to_mastery_sessions', 0.0):.1f} sessions")
        print(f"  Predicted mastery: {outcome.get('predicted_mastery_level', 'unknown')}")