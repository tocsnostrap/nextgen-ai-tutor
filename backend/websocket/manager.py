"""
WebSocket manager for real-time AI tutoring interactions
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any, Optional
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

from ..core.config import settings
from ..core.redis import redis_manager
from ..models.session import SessionManager

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_user_map: Dict[str, str] = {}  # connection_id -> user_id
        self.user_connections_map: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
    
    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        """Accept WebSocket connection and register it"""
        await websocket.accept()
        
        # Generate unique connection ID
        connection_id = str(uuid4())
        
        # Store connection
        self.active_connections[connection_id] = websocket
        self.connection_user_map[connection_id] = user_id
        
        # Update user connections map
        if user_id not in self.user_connections_map:
            self.user_connections_map[user_id] = set()
        self.user_connections_map[user_id].add(connection_id)
        
        # Track in Redis
        await redis_manager.add_websocket_connection(connection_id, user_id)
        
        logger.info(f"WebSocket connected: {connection_id} for user {user_id}")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Disconnect WebSocket connection"""
        if connection_id in self.active_connections:
            # Get user_id before removing
            user_id = self.connection_user_map.get(connection_id)
            
            # Remove from active connections
            websocket = self.active_connections.pop(connection_id, None)
            
            # Remove from connection map
            self.connection_user_map.pop(connection_id, None)
            
            # Remove from user connections map
            if user_id and user_id in self.user_connections_map:
                self.user_connections_map[user_id].discard(connection_id)
                if not self.user_connections_map[user_id]:
                    self.user_connections_map.pop(user_id)
            
            # Remove from Redis
            await redis_manager.remove_websocket_connection(connection_id)
            
            # Close WebSocket if still open
            if websocket and websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close()
                except Exception:
                    pass
            
            logger.info(f"WebSocket disconnected: {connection_id} for user {user_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_json(message)
                return True
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")
                await self.disconnect(connection_id)
                return False
        return False
    
    async def send_user_message(self, message: Dict[str, Any], user_id: str):
        """Send message to all connections of a user"""
        if user_id in self.user_connections_map:
            connections = list(self.user_connections_map[user_id])
            results = await asyncio.gather(
                *[self.send_personal_message(message, conn_id) for conn_id in connections],
                return_exceptions=True
            )
            return any(results)
        return False
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        disconnected = []
        
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {connection_id}: {e}")
                disconnected.append(connection_id)
        
        # Clean up disconnected clients
        for connection_id in disconnected:
            await self.disconnect(connection_id)
    
    async def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
    
    async def get_user_connection_count(self, user_id: str) -> int:
        """Get number of active connections for a user"""
        if user_id in self.user_connections_map:
            return len(self.user_connections_map[user_id])
        return 0

class WebSocketManager:
    """Main WebSocket manager for AI tutoring"""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.session_manager = SessionManager()
    
    async def initialize(self):
        """Initialize WebSocket manager"""
        logger.info("WebSocket manager initialized")
    
    async def cleanup(self):
        """Clean up all WebSocket connections"""
        # Disconnect all connections
        connection_ids = list(self.connection_manager.active_connections.keys())
        for connection_id in connection_ids:
            await self.connection_manager.disconnect(connection_id)
        
        logger.info("WebSocket manager cleaned up")
    
    async def handle_connection(self, websocket: WebSocket, user_id: str, session_id: Optional[str] = None):
        """Handle WebSocket connection lifecycle"""
        connection_id = None
        
        try:
            # Connect WebSocket
            connection_id = await self.connection_manager.connect(websocket, user_id)
            
            # Create or resume session
            if session_id:
                # Resume existing session
                session = await self.session_manager.resume_session(session_id, user_id)
                if not session:
                    await self.send_error(websocket, "Session not found or expired")
                    return
            else:
                # Create new session
                session = await self.session_manager.create_session(user_id)
                session_id = session["session_id"]
            
            # Send session info
            await self.send_message(websocket, {
                "type": "session_started",
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "AI tutoring session started"
            })
            
            # Main message loop
            while True:
                try:
                    # Receive message with timeout
                    data = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=settings.WEBSOCKET_PING_INTERVAL
                    )
                    
                    # Process message
                    await self.process_message(
                        websocket, 
                        connection_id, 
                        user_id, 
                        session_id, 
                        data
                    )
                    
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await self.send_ping(websocket)
                    
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected normally: {connection_id}")
                    break
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self.send_error(websocket, "Error processing message")
                    break
        
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        
        finally:
            # Cleanup
            if connection_id:
                await self.connection_manager.disconnect(connection_id)
            
            if session_id:
                await self.session_manager.end_session(session_id, user_id)
    
    async def process_message(self, websocket: WebSocket, connection_id: str, 
                            user_id: str, session_id: str, data: Dict[str, Any]):
        """Process incoming WebSocket message"""
        message_type = data.get("type")
        
        if message_type == "chat_message":
            await self.handle_chat_message(websocket, user_id, session_id, data)
        
        elif message_type == "question":
            await self.handle_question(websocket, user_id, session_id, data)
        
        elif message_type == "answer":
            await self.handle_answer(websocket, user_id, session_id, data)
        
        elif message_type == "emotion":
            await self.handle_emotion(websocket, user_id, session_id, data)
        
        elif message_type == "ping":
            await self.send_pong(websocket)
        
        elif message_type == "session_control":
            await self.handle_session_control(websocket, user_id, session_id, data)
        
        else:
            await self.send_error(websocket, f"Unknown message type: {message_type}")
    
    async def handle_chat_message(self, websocket: WebSocket, user_id: str, 
                                session_id: str, data: Dict[str, Any]):
        """Handle chat message from user"""
        message = data.get("message", "")
        
        if not message:
            await self.send_error(websocket, "Message cannot be empty")
            return
        
        # Store interaction
        interaction = await self.session_manager.add_interaction(
            session_id=session_id,
            interaction_type="question",
            content=message,
            metadata={"source": "websocket"}
        )
        
        # Get AI response (simulated for now)
        ai_response = await self.get_ai_response(message, user_id, session_id)
        
        # Send response
        await self.send_message(websocket, {
            "type": "ai_response",
            "message": ai_response,
            "interaction_id": interaction.get("id"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Store AI response
        await self.session_manager.update_interaction(
            interaction_id=interaction["id"],
            ai_response=ai_response,
            response_time_ms=500  # Simulated
        )
    
    async def handle_question(self, websocket: WebSocket, user_id: str, 
                            session_id: str, data: Dict[str, Any]):
        """Handle question from user"""
        question = data.get("question", "")
        topic = data.get("topic", "general")
        difficulty = data.get("difficulty", "medium")
        
        # Store question
        interaction = await self.session_manager.add_interaction(
            session_id=session_id,
            interaction_type="question",
            content=question,
            metadata={
                "topic": topic,
                "difficulty": difficulty,
                "source": "websocket"
            }
        )
        
        # Get AI explanation
        explanation = await self.get_ai_explanation(question, topic, difficulty)
        
        # Send explanation
        await self.send_message(websocket, {
            "type": "explanation",
            "explanation": explanation,
            "question": question,
            "interaction_id": interaction.get("id"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def handle_answer(self, websocket: WebSocket, user_id: str, 
                          session_id: str, data: Dict[str, Any]):
        """Handle answer from user"""
        answer = data.get("answer", "")
        question_id = data.get("question_id", "")
        
        # Check answer correctness (simulated)
        is_correct = await self.check_answer_correctness(answer, question_id)
        
        # Update learning progress
        await self.update_learning_progress(user_id, is_correct)
        
        # Send feedback
        await self.send_message(websocket, {
            "type": "answer_feedback",
            "is_correct": is_correct,
            "feedback": self.get_feedback_message(is_correct),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def handle_emotion(self, websocket: WebSocket, user_id: str, 
                           session_id: str, data: Dict[str, Any]):
        """Handle emotion detection data"""
        emotion = data.get("emotion", "")
        confidence = data.get("confidence", 0.0)
        source = data.get("source", "unknown")
        
        # Store emotion detection
        await self.session_manager.add_emotion_detection(
            session_id=session_id,
            emotion=emotion,
            confidence=confidence,
            source=source,
            metadata={"source": "websocket"}
        )
        
        # Adjust AI response based on emotion
        if emotion in ["confused", "frustrated"]:
            await self.send_message(websocket, {
                "type": "emotion_response",
                "message": "I notice you might be confused. Let me explain this differently.",
                "emotion": emotion,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    async def handle_session_control(self, websocket: WebSocket, user_id: str, 
                                   session_id: str, data: Dict[str, Any]):
        """Handle session control messages"""
        action = data.get("action", "")
        
        if action == "pause":
            await self.session_manager.pause_session(session_id, user_id)
            await self.send_message(websocket, {
                "type": "session_paused",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        elif action == "resume":
            await self.session_manager.resume_session(session_id, user_id)
            await self.send_message(websocket, {
                "type": "session_resumed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        elif action == "end":
            await self.session_manager.end_session(session_id, user_id)
            await self.send_message(websocket, {
                "type": "session_ended",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            # Close WebSocket
            await websocket.close()
    
    async def get_ai_response(self, message: str, user_id: str, session_id: str) -> str:
        """Get AI response for chat message (simulated)"""
        # TODO: Integrate with actual AI model
        return f"I understand you're saying: '{message}'. As your AI tutor, I'm here to help you learn. What specific topic would you like to explore today?"
    
    async def get_ai_explanation(self, question: str, topic: str, difficulty: str) -> str:
        """Get AI explanation for question (simulated)"""
        # TODO: Integrate with actual AI model
        return f"Here's an explanation for your question about '{question}' in the topic of '{topic}' at {difficulty} difficulty level. [Detailed explanation would go here]"
    
    async def check_answer_correctness(self, answer: str, question_id: str) -> bool:
        """Check if answer is correct (simulated)"""
        # TODO: Integrate with actual answer checking logic
        return len(answer) > 5  # Simple heuristic for demo
    
    async def update_learning_progress(self, user_id: str, is_correct: bool):
        """Update learning progress based on answer (simulated)"""
        # TODO: Integrate with BKT model
        pass
    
    def get_feedback_message(self, is_correct: bool) -> str:
        """Get feedback message based on correctness"""
        if is_correct:
            return "Great job! That's correct. You're making excellent progress."
        else:
            return "Not quite right, but that's okay! Learning involves making mistakes. Let me explain the concept again."
    
    async def send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message through WebSocket"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    async def send_error(self, websocket: WebSocket, error_message: str):
        """Send error message"""
        await self.send_message(websocket, {
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def send_ping(self, websocket: WebSocket):
        """Send ping to keep connection alive"""
        await self.send_message(websocket, {
            "type": "ping",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def send_pong(self, websocket: WebSocket):
        """Send pong response"""
        await self.send_message(websocket, {
            "type": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def broadcast_session_update(self, session_id: str, update: Dict[str, Any]):
        """Broadcast session update to all connected clients for that session"""
        # TODO: Implement session-specific broadcasting
        pass

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

# Export
__all__ = ["websocket_manager", "WebSocketManager", "ConnectionManager"]