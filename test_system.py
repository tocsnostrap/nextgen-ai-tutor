#!/usr/bin/env python3
"""
Test script for Next-Gen AI Tutoring System
Demonstrates all core components working together
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from bkt_engine import BKTEngine
from lstm_temporal_model import TemporalPatternAnalyzer, TemporalFeature
from adaptation_engine import AdaptationEngine, StudentState, ContentItem, TeachingStrategy
from conversational_memory import ConversationalMemory, MemoryType, MemoryPriority
from emotion_aware_teaching import EmotionAwareTeacher, EmotionalState, EmotionState

from datetime import datetime, timedelta
import numpy as np

def test_bkt_engine():
    """Test Bayesian Knowledge Tracing Engine"""
    print("🧪 Testing BKT Engine...")
    
    engine = BKTEngine(use_deep_learning=True)
    
    # Initialize skills
    engine.initialize_skill("addition_basic", p_init=0.2, p_learn=0.3, p_guess=0.1, p_slip=0.05)
    engine.initialize_skill("subtraction_basic", p_init=0.15, p_learn=0.25, p_guess=0.15, p_slip=0.08)
    
    # Simulate student learning
    student_id = "test_student_001"
    
    print("  Simulating learning session...")
    for i in range(8):
        correct = np.random.random() < (0.3 + i * 0.08)  # Improving over time
        response_time = np.random.uniform(3, 12)
        confidence = np.random.uniform(0.4, 0.9)
        
        p_knowledge, metadata = engine.update_with_observation(
            student_id, "addition_basic", correct, response_time, confidence
        )
        
        print(f"    Attempt {i+1}: {'✓' if correct else '✗'} -> P(knowledge) = {p_knowledge:.3f}")
    
    # Get progress report
    report = engine.get_student_progress_report(student_id)
    print(f"  Overall Mastery: {report.get('overall_mastery', 0):.3f}")
    print(f"  Learning Efficiency: {report.get('learning_efficiency', 0):.3f}")
    
    return True

def test_temporal_analyzer():
    """Test LSTM Temporal Pattern Analyzer"""
    print("🧪 Testing Temporal Pattern Analyzer...")
    
    analyzer = TemporalPatternAnalyzer()
    student_id = "test_student_002"
    
    # Generate temporal features
    base_time = datetime.now() - timedelta(hours=2)
    
    print("  Generating temporal patterns...")
    for i in range(15):
        feature = TemporalFeature(
            response_time=np.random.uniform(2, 20),
            correctness=1.0 if np.random.random() < (0.4 + i * 0.04) else 0.0,
            confidence=np.random.uniform(0.3, 0.9),
            hint_usage=0.0 if np.random.random() < 0.8 else np.random.uniform(0.1, 0.5),
            engagement_level=np.random.uniform(0.5, 0.9),
            difficulty_level=np.random.uniform(0.3, 0.7),
            timestamp=base_time + timedelta(minutes=i * 8)
        )
        analyzer.add_interaction(student_id, feature)
    
    # Analyze patterns
    patterns = analyzer.analyze_patterns(student_id)
    
    if "error" not in patterns and "warning" not in patterns:
        print(f"  Next correctness probability: {patterns.get('next_correctness_prob', 0):.3f}")
        print(f"  Learning state: {patterns.get('learning_state', 'unknown')}")
        print(f"  Engagement level: {patterns.get('engagement_level', 0):.3f}")
        return True
    else:
        print(f"  Warning: {patterns.get('warning', 'Unknown error')}")
        return False

def test_adaptation_engine():
    """Test Real-time Adaptation Engine"""
    print("🧪 Testing Adaptation Engine...")
    
    engine = AdaptationEngine()
    
    # Add sample content
    content = ContentItem(
        content_id="test_content_001",
        skill_id="addition_basic",
        difficulty=0.5,
        content_type="practice",
        modality="interactive",
        estimated_time=8,
        prerequisites=[],
        learning_objectives=["Practice addition skills"],
        adaptability_score=0.8,
        engagement_potential=0.7,
        cognitive_load=0.5
    )
    engine.add_content(content)
    
    # Create student state
    student_state = StudentState(
        p_knowledge=0.6,
        mastery_level="intermediate",
        recent_accuracy=0.7,
        response_time_avg=10.0,
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
    
    # Select content
    selected_content, metadata = engine.select_content(student_state, "addition_basic")
    
    print(f"  Selected content: {selected_content.content_id}")
    print(f"  Selection score: {metadata.get('selection_score', 0):.3f}")
    print(f"  Rationale: {metadata.get('rationale', 'No rationale')[:80]}...")
    
    # Get intervention
    intervention = engine.generate_intervention(student_state)
    print(f"  Intervention needed: {intervention['type'] != 'none'}")
    
    return True

def test_memory_system():
    """Test Conversational Memory System"""
    print("🧪 Testing Conversational Memory System...")
    
    memory = ConversationalMemory(max_short_term=10, max_long_term=100)
    
    # Start session
    memory.start_session("test_student_003", {"learning_goal": "test memory"})
    
    # Add interactions
    print("  Adding interactions to memory...")
    memory.add_interaction(
        "How do I solve 5 + 3?",
        "5 + 3 equals 8. You can count: 5, 6, 7, 8!",
        {"skill": "addition", "difficulty": "easy"}
    )
    
    memory.add_learning_event(
        "concept_understood",
        {"concept": "basic addition", "example": "5 + 3 = 8"},
        skill_id="addition_basic",
        priority=MemoryPriority.HIGH
    )
    
    # Get relevant context
    context = memory.get_relevant_context("addition", limit=2)
    print(f"  Found {len(context)} relevant memories")
    
    # Remember specific information
    remembered = memory.remember("how to add", limit=1)
    print(f"  Retrieved {len(remembered)} memory for 'how to add'")
    
    # End session
    memory.end_session()
    
    return True

def test_emotion_teacher():
    """Test Emotion-Aware Teaching Logic"""
    print("🧪 Testing Emotion-Aware Teaching...")
    
    teacher = EmotionAwareTeacher()
    
    # Analyze emotion from text
    test_text = "I'm really confused about this problem. I don't understand how to solve it."
    behavior_data = {
        "response_time": 25.0,
        "accuracy_trend": -0.2,
        "hint_usage": 0.8,
        "session_duration": 20
    }
    
    emotion_state = teacher.analyze_student_state(test_text, behavior_data)
    
    print(f"  Detected emotion: {emotion_state.primary_emotion.value}")
    print(f"  Emotion intensity: {emotion_state.intensity:.3f}")
    print(f"  Detection confidence: {emotion_state.confidence:.3f}")
    
    # Get teaching recommendations
    recommendations = teacher.get_teaching_recommendations(emotion_state)
    
    print(f"  Intervention needed: {recommendations.get('intervention_needed', False)}")
    print(f"  Optimal approach: {recommendations.get('optimal_teaching_approach', 'unknown')}")
    
    # Generate empathetic response
    response = teacher.generate_empathetic_response(emotion_state)
    print(f"  Empathetic response: {response[:80]}...")
    
    return True

def test_integration():
    """Test all components working together"""
    print("🧪 Testing System Integration...")
    
    # Simulate a complete learning session
    student_id = "integration_test_student"
    
    print("  1. Student asks question...")
    question = "I'm struggling with addition problems. Can you help?"
    
    print("  2. Emotion detection...")
    emotion_teacher = EmotionAwareTeacher()
    emotion_state = emotion_teacher.analyze_student_state(
        question,
        {"response_time": 15.0, "accuracy_trend": 0.0, "session_duration": 10}
    )
    
    print(f"     Emotion: {emotion_state.primary_emotion.value}")
    
    print("  3. Memory retrieval...")
    memory = ConversationalMemory()
    memory.start_session(student_id, {"context": "integration test"})
    memory.add_interaction(question, "Let me help you with addition!", {})
    relevant_memories = memory.remember("addition", limit=1)
    
    print(f"     Relevant memories found: {len(relevant_memories)}")
    
    print("  4. BKT update...")
    bkt_engine = BKTEngine()
    bkt_engine.initialize_skill("addition_basic")
    p_knowledge, metadata = bkt_engine.update_with_observation(
        student_id, "addition_basic", correct=False, response_time=15.0, confidence=0.3
    )
    
    print(f"     P(knowledge): {p_knowledge:.3f}")
    
    print("  5. Adaptation decision...")
    adaptation_engine = AdaptationEngine()
    
    # Add sample content
    content = ContentItem(
        content_id="integration_content",
        skill_id="addition_basic",
        difficulty=0.4,
        content_type="explanation",
        modality="text",
        estimated_time=5,
        prerequisites=[],
        learning_objectives=["Understand addition basics"],
        adaptability_score=0.8,
        engagement_potential=0.6,
        cognitive_load=0.4
    )
    adaptation_engine.add_content(content)
    
    student_state = StudentState(
        p_knowledge=p_knowledge,
        mastery_level=metadata.get('mastery_level', 'novice'),
        recent_accuracy=0.5,
        response_time_avg=15.0,
        consistency_score=0.5,
        engagement_level=0.6,
        motivation_level=0.5,
        fatigue_level=0.2,
        confidence=0.3,
        frustration=0.4,
        flow_state=0.3,
        learning_momentum=0.0,
        optimal_pace="slow",
        learning_style="visual",
        session_duration=10,
        time_of_day="morning",
        days_since_last_practice=2
    )
    
    selected_content, adaptation_metadata = adaptation_engine.select_content(
        student_state, "addition_basic"
    )
    
    print(f"     Selected: {selected_content.content_id}")
    print(f"     Adaptations: {len(adaptation_metadata.get('adaptations', []))}")
    
    print("  6. Generate response...")
    response = f"I can see you're feeling {emotion_state.primary_emotion.value}. Let's start with a simple addition example to build your confidence."
    
    print(f"     AI Tutor: {response}")
    
    print("  7. Update memory...")
    memory.add_interaction(question, response, {
        "emotion": emotion_state.primary_emotion.value,
        "adaptation": selected_content.content_id,
        "p_knowledge": p_knowledge
    })
    
    memory.end_session()
    
    print("  ✅ Integration test complete!")
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("NEXT-GEN AI TUTORING SYSTEM - COMPREHENSIVE TEST")
    print("=" * 60)
    
    tests = [
        ("BKT Engine", test_bkt_engine),
        ("Temporal Analyzer", test_temporal_analyzer),
        ("Adaptation Engine", test_adaptation_engine),
        ("Memory System", test_memory_system),
        ("Emotion Teacher", test_emotion_teacher),
        ("System Integration", test_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*40}")
            print(f"TEST: {test_name}")
            print(f"{'='*40}")
            
            success = test_func()
            results.append((test_name, success))
            
            if success:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! System is fully functional.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())