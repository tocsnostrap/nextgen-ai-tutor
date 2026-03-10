            if priority in [MemoryPriority.HIGH, MemoryPriority.CRITICAL]:
                self._store_in_long_term(memory_item)
        else:
            self._store_in_long_term(memory_item)
        
        self.stats["memories_created"] += 1
        
        return memory_item
    
    def _store_in_long_term(self, memory_item: MemoryItem):
        """Store memory in long-term storage"""
        # Check capacity
        if len(self.long_term_memory) >= self.max_long_term:
            self._make_space_for_new_memory()
        
        # Store memory
        self.long_term_memory[memory_item.memory_id] = memory_item
        
        # Update index
        if memory_item.student_id not in self.memory_index:
            self.memory_index[memory_item.student_id] = []
        
        if memory_item.memory_id not in self.memory_index[memory_item.student_id]:
            self.memory_index[memory_item.student_id].append(memory_item.memory_id)
    
    def _make_space_for_new_memory(self):
        """Make space in long-term memory by removing low-priority items"""
        # Calculate retention scores for all memories
        retention_scores = []
        for memory_id, memory in self.long_term_memory.items():
            if memory.priority != MemoryPriority.CRITICAL:
                retention = memory.calculate_retention_score()
                retention_scores.append((memory_id, retention))
        
        # Sort by retention score (lowest first)
        retention_scores.sort(key=lambda x: x[1])
        
        # Remove lowest scoring memories until we have space
        memories_to_remove = min(10, len(retention_scores) // 10 + 1)
        
        for i in range(memories_to_remove):
            if i < len(retention_scores):
                memory_id, score = retention_scores[i]
                self.forget(memory_id)
    
    def _search_memories(self, query: str, 
                        memory_type: Optional[MemoryType] = None,
                        limit: int = 3) -> List[Dict]:
        """Search for relevant memories"""
        if not self.current_student_id:
            return []
        
        relevant_memories = []
        student_memory_ids = self.memory_index.get(self.current_student_id, [])
        
        # Simple keyword matching (in production would use embeddings)
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        for memory_id in student_memory_ids:
            if memory_id in self.long_term_memory:
                memory = self.long_term_memory[memory_id]
                
                # Filter by type if specified
                if memory_type and memory.memory_type != memory_type:
                    continue
                
                # Calculate relevance score
                relevance = self._calculate_relevance(memory, query_words)
                
                if relevance > 0.1:  # Threshold
                    relevant_memories.append({
                        "memory_id": memory_id,
                        "type": memory.memory_type.value,
                        "content": memory.content,
                        "relevance": relevance,
                        "retention": memory.calculate_retention_score(),
                        "timestamp": memory.timestamp.isoformat()
                    })
        
        # Sort by relevance
        relevant_memories.sort(key=lambda x: x["relevance"], reverse=True)
        
        return relevant_memories[:limit]
    
    def _calculate_relevance(self, memory: MemoryItem, 
                           query_words: set) -> float:
        """Calculate relevance score between memory and query"""
        relevance = 0.0
        
        # Check content fields
        content_str = str(memory.content).lower()
        memory_words = set(content_str.split())
        
        # Word overlap
        overlap = len(query_words.intersection(memory_words))
        if query_words:
            word_overlap_score = overlap / len(query_words)
            relevance += word_overlap_score * 0.6
        
        # Recency bonus
        hours_old = (datetime.now() - memory.timestamp).total_seconds() / 3600
        recency_bonus = max(0.0, 1.0 - (hours_old / 168))  # Decay over a week
        relevance += recency_bonus * 0.2
        
        # Access frequency bonus
        access_bonus = min(0.2, memory.access_count * 0.05)
        relevance += access_bonus
        
        # Context match bonus
        if memory.context and self.conversation_context:
            context_match = self._calculate_context_match(memory.context)
            relevance += context_match * 0.2
        
        return min(1.0, relevance)
    
    def _calculate_context_match(self, memory_context: Dict) -> float:
        """Calculate how well memory context matches current context"""
        if not memory_context or not self.conversation_context:
            return 0.0
        
        match_score = 0.0
        matching_keys = 0
        
        for key, value in memory_context.items():
            if key in self.conversation_context:
                current_value = self.conversation_context[key]
                if str(value) == str(current_value):
                    matching_keys += 1
        
        if memory_context:
            match_score = matching_keys / len(memory_context)
        
        return match_score
    
    def _extract_and_store_knowledge(self, user_input: str, 
                                    ai_response: str, metadata: Dict):
        """Extract and store knowledge from interaction"""
        # Extract key information based on interaction type
        # This is a simplified version - in production would use NLP
        
        # Check for learning moments
        learning_keywords = ["learned", "understood", "figured out", "now I know", "明白了", "懂了"]
        
        for keyword in learning_keywords:
            if keyword in user_input.lower():
                # Store as learning event
                self.add_learning_event(
                    event_type="concept_understood",
                    event_data={
                        "concept": self._extract_concept(ai_response),
                        "user_statement": user_input,
                        "confidence": 0.7
                    },
                    priority=MemoryPriority.HIGH
                )
                break
        
        # Check for confusion
        confusion_keywords = ["confused", "don't understand", "not sure", "不明白", "不懂"]
        
        for keyword in confusion_keywords:
            if keyword in user_input.lower():
                self.add_learning_event(
                    event_type="confusion_expressed",
                    event_data={
                        "topic": self._extract_topic(ai_response),
                        "user_statement": user_input,
                        "ai_explanation": ai_response[:200]  # Truncate
                    },
                    priority=MemoryPriority.MEDIUM
                )
                break
    
    def _extract_concept(self, text: str) -> str:
        """Extract main concept from text (simplified)"""
        # In production, would use NLP for concept extraction
        words = text.lower().split()[:5]  # First few words often contain concept
        return " ".join(words)
    
    def _extract_topic(self, text: str) -> str:
        """Extract topic from text (simplified)"""
        # Look for keywords indicating topic
        topic_keywords = ["addition", "subtraction", "multiplication", "division", 
                         "fractions", "algebra", "geometry", "reading", "science"]
        
        text_lower = text.lower()
        for keyword in topic_keywords:
            if keyword in text_lower:
                return keyword
        
        return "general"
    
    def _consolidate_memories(self):
        """Consolidate important short-term memories to long-term"""
        for memory in self.short_term_memory:
            if memory.priority in [MemoryPriority.HIGH, MemoryPriority.CRITICAL]:
                # Check if already in long-term
                if memory.memory_id not in self.long_term_memory:
                    self._store_in_long_term(memory)
    
    def _create_session_summary(self) -> Dict:
        """Create summary of the session"""
        interactions = []
        learning_events = []
        
        # Collect session data
        for memory in self.short_term_memory:
            if memory.memory_type == MemoryType.SHORT_TERM:
                interactions.append(memory.content)
            elif memory.memory_type == MemoryType.EPISODIC:
                learning_events.append(memory.content)
        
        summary = {
            "session_id": self.current_session_id,
            "student_id": self.current_student_id,
            "start_time": self.conversation_context.get("session_start"),
            "end_time": datetime.now().isoformat(),
            "total_interactions": len(interactions),
            "learning_events": learning_events,
            "key_topics": self._extract_session_topics(interactions),
            "achievements": self._identify_achievements(learning_events)
        }
        
        return summary
    
    def _extract_session_topics(self, interactions: List[Dict]) -> List[str]:
        """Extract main topics from session interactions"""
        topics = set()
        
        for interaction in interactions:
            text = f"{interaction.get('user_input', '')} {interaction.get('ai_response', '')}"
            topic = self._extract_topic(text)
            if topic != "general":
                topics.add(topic)
        
        return list(topics)
    
    def _identify_achievements(self, learning_events: List[Dict]) -> List[str]:
        """Identify achievements from learning events"""
        achievements = []
        
        for event in learning_events:
            event_type = event.get("event_type", "")
            
            if event_type == "concept_understood":
                concept = event.get("event_data", {}).get("concept", "something")
                achievements.append(f"Understood {concept}")
            elif event_type == "skill_mastered":
                skill = event.get("event_data", {}).get("skill", "a skill")
                achievements.append(f"Mastered {skill}")
            elif event_type == "problem_solved":
                achievements.append("Solved a challenging problem")
        
        return achievements
    
    def _analyze_learning_patterns(self, student_id: str) -> Dict:
        """Analyze learning patterns from student's memories"""
        if student_id not in self.memory_index:
            return {}
        
        patterns = {
            "preferred_topics": defaultdict(int),
            "learning_times": defaultdict(int),
            "interaction_patterns": {
                "questions_per_session": [],
                "confusion_frequency": 0,
                "breakthrough_frequency": 0
            }
        }
        
        memory_ids = self.memory_index[student_id]
        
        for memory_id in memory_ids:
            if memory_id in self.long_term_memory:
                memory = self.long_term_memory[memory_id]
                
                # Analyze topics
                if memory.skill_id:
                    patterns["preferred_topics"][memory.skill_id] += 1
                
                # Analyze learning times
                hour = memory.timestamp.hour
                time_of_day = "morning" if 6 <= hour < 12 else \
                             "afternoon" if 12 <= hour < 18 else "evening"
                patterns["learning_times"][time_of_day] += 1
                
                # Analyze interaction patterns
                if memory.memory_type == MemoryType.EPISODIC:
                    event_type = memory.content.get("event_type", "")
                    if "confusion" in event_type:
                        patterns["interaction_patterns"]["confusion_frequency"] += 1
                    elif "understood" in event_type or "mastered" in event_type:
                        patterns["interaction_patterns"]["breakthrough_frequency"] += 1
        
        # Convert defaultdict to dict
        patterns["preferred_topics"] = dict(patterns["preferred_topics"])
        patterns["learning_times"] = dict(patterns["learning_times"])
        
        # Calculate averages
        total_sessions = len(set(
            m.content.get("session_id") 
            for mid in memory_ids 
            if mid in self.long_term_memory 
            for m in [self.long_term_memory[mid]]
            if m.memory_type == MemoryType.SHORT_TERM
        ))
        
        if total_sessions > 0:
            total_interactions = sum(
                1 for mid in memory_ids
                if mid in self.long_term_memory
                and self.long_term_memory[mid].memory_type == MemoryType.SHORT_TERM
            )
            patterns["interaction_patterns"]["questions_per_session"] = \
                total_interactions / total_sessions
        
        return patterns
    
    def _identify_knowledge_gaps(self, student_id: str) -> List[Dict]:
        """Identify knowledge gaps from student's learning patterns"""
        # Simplified implementation
        # In production, would analyze skill dependencies and mastery levels
        
        gaps = []
        
        # Example gaps based on common patterns
        patterns = self._analyze_learning_patterns(student_id)
        
        # High confusion frequency might indicate gaps
        if patterns.get("interaction_patterns", {}).get("confusion_frequency", 0) > 5:
            gaps.append({
                "type": "foundational_gap",
                "description": "Frequent confusion suggests gaps in foundational knowledge",
                "confidence": 0.7
            })
        
        # Low breakthrough frequency might indicate engagement issues
        breakthroughs = patterns.get("interaction_patterns", {}).get("breakthrough_frequency", 0)
        confusions = patterns.get("interaction_patterns", {}).get("confusion_frequency", 0)
        
        if breakthroughs > 0 and confusions > breakthroughs * 3:
            gaps.append({
                "type": "conceptual_gap",
                "description": "More confusion than breakthroughs suggests conceptual misunderstandings",
                "confidence": 0.6
            })
        
        return gaps
    
    def _get_recent_progress(self, student_id: str) -> Dict:
        """Get recent learning progress"""
        if student_id not in self.memory_index:
            return {}
        
        # Get recent learning events
        recent_events = []
        memory_ids = self.memory_index[student_id]
        
        for memory_id in memory_ids[-20:]:  # Last 20 memories
            if memory_id in self.long_term_memory:
                memory = self.long_term_memory[memory_id]
                if memory.memory_type == MemoryType.EPISODIC:
                    recent_events.append(memory.content)
        
        progress = {
            "recent_achievements": [],
            "skills_practiced": set(),
            "confidence_trend": "stable"  # Would calculate from events
        }
        
        for event in recent_events[-5:]:  # Last 5 events
            event_type = event.get("event_type", "")
            if "understood" in event_type or "mastered" in event_type:
                progress["recent_achievements"].append(event_type)
            
            skill = event.get("event_data", {}).get("skill_id")
            if skill:
                progress["skills_practiced"].add(skill)
        
        progress["skills_practiced"] = list(progress["skills_practiced"])
        
        return progress
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_part = hashlib.md5(timestamp.encode()).hexdigest()[:6]
        return f"session_{timestamp}_{random_part}"
    
    def _generate_memory_id(self, content: Dict) -> str:
        """Generate unique memory ID from content"""
        content_str = json.dumps(content, sort_keys=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_obj = hashlib.md5(content_str.encode())
        return f"memory_{timestamp}_{hash_obj.hexdigest()[:8]}"
    
    def _load_student_memories(self, student_id: str):
        """Load student's memories into short-term context"""
        # In this implementation, we just update stats
        # In production, might pre-load relevant memories
        logger.info(f"Loaded memories for student {student_id}")


# Example usage
if __name__ == "__main__":
    # Create memory system
    memory = ConversationalMemory()
    
    # Start session
    memory.start_session("student_789", {
        "learning_goal": "master basic addition",
        "age": 8,
        "previous_experience": "beginner"
    })
    
    print("=== Adding Interactions ===")
    
    # Add some interactions
    memory.add_interaction(
        "How do I add 5 + 3?",
        "5 + 3 equals 8. You can think of it as counting: 5, 6, 7, 8!",
        {"skill": "addition", "difficulty": "easy"}
    )
    
    memory.add_interaction(
        "What about 7 + 4?",
        "7 + 4 equals 11. You can break it down: 7 + 3 = 10, then +1 = 11.",
        {"skill": "addition", "difficulty": "medium", "strategy": "breaking_down"}
    )
    
    # Add learning events
    memory.add_learning_event(
        "concept_understood",
        {"concept": "addition", "example": "5 + 3 = 8", "confidence": 0.8},
        skill_id="addition_basic",
        priority=MemoryPriority.HIGH
    )
    
    # Add conceptual knowledge
    memory.add_conceptual_knowledge(
        concept="addition",
        explanation="Addition is combining two or more numbers to find their total.",
        examples=["2 + 3 = 5", "7 + 1 = 8"],
        relationships=["subtraction", "counting"]
    )
    
    print("=== Getting Relevant Context ===")
    context = memory.get_relevant_context("addition problems", limit=3)
    print(f"Found {len(context)} relevant memories")
    
    for i, mem in enumerate(context):
        print(f"{i+1}. Type: {mem['type']}, Relevance: {mem['relevance']:.2f}")
    
    print("\n=== Remembering Specific Information ===")
    remembered = memory.remember("how to add numbers", limit=2)
    
    for i, mem in enumerate(remembered):
        print(f"{i+1}. {mem