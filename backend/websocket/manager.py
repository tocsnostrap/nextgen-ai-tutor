"""
WebSocket manager for real-time AI tutoring interactions
"""

import asyncio
import json
import logging
import random
from typing import Dict, Set, Any, Optional
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

from ..core.config import settings
from ..core.database import _get_session_local
from ..unified_adaptive_engine import record_game_interaction

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_user_map: Dict[str, str] = {}
        self.user_connections_map: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        await websocket.accept()
        connection_id = str(uuid4())
        self.active_connections[connection_id] = websocket
        self.connection_user_map[connection_id] = user_id
        if user_id not in self.user_connections_map:
            self.user_connections_map[user_id] = set()
        self.user_connections_map[user_id].add(connection_id)
        logger.info(f"WebSocket connected: {connection_id} for user {user_id}")
        return connection_id

    async def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            user_id = self.connection_user_map.get(connection_id)
            websocket = self.active_connections.pop(connection_id, None)
            self.connection_user_map.pop(connection_id, None)
            if user_id and user_id in self.user_connections_map:
                self.user_connections_map[user_id].discard(connection_id)
                if not self.user_connections_map[user_id]:
                    self.user_connections_map.pop(user_id)
            if websocket and websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close()
                except Exception:
                    pass
            logger.info(f"WebSocket disconnected: {connection_id}")

    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
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

    async def broadcast(self, message: Dict[str, Any]):
        disconnected = []
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(connection_id)
        for connection_id in disconnected:
            await self.disconnect(connection_id)

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        conn_ids = self.user_connections_map.get(user_id, set())
        for conn_id in list(conn_ids):
            await self.send_message(conn_id, message)

    async def broadcast_to_users(self, user_ids: list, message: Dict[str, Any]):
        for uid in user_ids:
            await self.send_to_user(uid, message)

    async def get_connection_count(self) -> int:
        return len(self.active_connections)


class WebSocketManager:
    def __init__(self):
        self.connection_manager = ConnectionManager()
        from ..models.session import SessionManager
        self.session_manager = SessionManager()

    async def initialize(self):
        logger.info("WebSocket manager initialized")

    async def cleanup(self):
        connection_ids = list(self.connection_manager.active_connections.keys())
        for connection_id in connection_ids:
            await self.connection_manager.disconnect(connection_id)
        logger.info("WebSocket manager cleaned up")

    async def handle_connection(self, websocket: WebSocket, user_id: str, session_id: Optional[str] = None):
        connection_id = None
        try:
            connection_id = await self.connection_manager.connect(websocket, user_id)

            await self.send_message(websocket, {
                "type": "session_started",
                "session_id": session_id or "demo",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "AI tutoring session started"
            })

            while True:
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=settings.WEBSOCKET_PING_INTERVAL
                    )
                    await self.process_message(websocket, connection_id, user_id, session_id or "demo", data)
                except asyncio.TimeoutError:
                    await self.send_ping(websocket)
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    break
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            if connection_id:
                await self.connection_manager.disconnect(connection_id)

    async def process_message(self, websocket: WebSocket, connection_id: str,
                            user_id: str, session_id: str, data: Dict[str, Any]):
        message_type = data.get("type")
        if message_type == "chat_message":
            await self.handle_chat_message(websocket, user_id, session_id, data)
        elif message_type == "ping":
            await self.send_pong(websocket)
        elif message_type in ("create_game", "join_game", "start_game", "game_answer", "list_games", "game_state"):
            await self.handle_game_message(websocket, connection_id, user_id, str(message_type), data)
        else:
            await self.send_message(websocket, {
                "type": "ai_response",
                "message": f"Received your message of type '{message_type}'",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

    async def handle_chat_message(self, websocket: WebSocket, user_id: str,
                                session_id: str, data: Dict[str, Any]):
        message = data.get("message", "")
        if not message:
            await self.send_error(websocket, "Message cannot be empty")
            return
        ai_response = f"I understand you're saying: '{message}'. As your AI tutor, I'm here to help you learn. What specific topic would you like to explore today?"
        await self.send_message(websocket, {
            "type": "ai_response",
            "message": ai_response,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    async def send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    async def send_error(self, websocket: WebSocket, error_message: str):
        await self.send_message(websocket, {
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def _get_game_human_player_ids(self, game):
        return [pid for pid, p in game.players.items() if not p.get("is_bot")]

    def _get_player_xp(self, rankings, user_id):
        for r in rankings:
            if r.get("id") == user_id:
                return max(10, r.get("score", 0) // 10)
        return 10

    async def _broadcast_to_game(self, game, message: Dict[str, Any]):
        player_ids = self._get_game_human_player_ids(game)
        await self.connection_manager.broadcast_to_users(player_ids, message)

    async def handle_game_message(self, websocket: WebSocket, connection_id: str,
                                user_id: str, message_type: str, data: Dict[str, Any]):
        from ..game_manager import game_manager, GAME_TYPES

        if message_type == "list_games":
            games = game_manager.list_games()
            await self.send_message(websocket, {
                "type": "game_list",
                "games": games,
                "game_types": {k: {"name": v["name"], "icon": v["icon"]} for k, v in GAME_TYPES.items()},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        elif message_type == "create_game":
            game_type = data.get("game_type", "math_race")
            player_name = data.get("player_name", "Player")
            rounds = data.get("rounds", 5)
            add_bots = data.get("add_bots", 1)
            game = game_manager.create_game(game_type, user_id, player_name, rounds, add_bots)
            await self.send_message(websocket, {
                "type": "game_created",
                "game": game.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        elif message_type == "join_game":
            game_id = data.get("game_id", "")
            player_name = data.get("player_name", "Player")
            game = game_manager.get_game(game_id)
            if game and game.state == "waiting" and len(game.players) < 4:
                game.add_player(user_id, player_name)
                await self._broadcast_to_game(game, {
                    "type": "game_joined",
                    "game": game.to_dict(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            else:
                await self.send_error(websocket, "Cannot join this game")

        elif message_type == "start_game":
            game_id = data.get("game_id", "")
            game = game_manager.get_game(game_id)
            if game and game.state == "waiting" and game.creator_id == user_id:
                game.start()
                if game.state == "playing":
                    question = game.get_current_question()
                    await self._broadcast_to_game(game, {
                        "type": "game_started",
                        "game": game.to_dict(),
                        "question": question,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    asyncio.create_task(self._run_bot_answers(game))
            else:
                await self.send_error(websocket, "Cannot start this game")

        elif message_type == "game_answer":
            game_id = data.get("game_id", "")
            answer = data.get("answer", 0)
            game = game_manager.get_game(game_id)
            if game and game.state == "playing":
                result = game.submit_answer(user_id, answer)
                await self.send_message(websocket, {
                    "type": "game_answer_result",
                    "result": result,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                bot_results = game.get_bot_answers()

                if game.all_answered():
                    await asyncio.sleep(1.5)
                    rankings = game.get_rankings()
                    game.advance_round()

                    if game.state == "finished":
                        for pid in self._get_game_human_player_ids(game):
                            xp = self._get_player_xp(rankings, pid)
                            await self.connection_manager.send_to_user(pid, {
                                "type": "game_over",
                                "rankings": rankings,
                                "game": game.to_dict(),
                                "xp_earned": xp,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })
                        asyncio.create_task(self._record_game_adaptive(game, rankings))
                    else:
                        question = game.get_current_question()
                        await self._broadcast_to_game(game, {
                            "type": "game_next_round",
                            "game": game.to_dict(),
                            "question": question,
                            "rankings": rankings,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                        asyncio.create_task(self._run_bot_answers(game))
            else:
                await self.send_error(websocket, "Cannot submit answer")

        elif message_type == "game_state":
            game_id = data.get("game_id", "")
            game = game_manager.get_game(game_id)
            if game:
                await self.send_message(websocket, {
                    "type": "game_state_update",
                    "game": game.to_dict(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            else:
                await self.send_error(websocket, "Game not found")

    async def _run_bot_answers(self, game):
        try:
            await asyncio.sleep(random.uniform(2, 4))
            if game.state == "playing" and not game.all_answered():
                game.get_bot_answers()
                if game.all_answered():
                    await asyncio.sleep(1.5)
                    rankings = game.get_rankings()
                    game.advance_round()

                    if game.state == "finished":
                        for pid in self._get_game_human_player_ids(game):
                            xp = self._get_player_xp(rankings, pid)
                            await self.connection_manager.send_to_user(pid, {
                                "type": "game_over",
                                "rankings": rankings,
                                "game": game.to_dict(),
                                "xp_earned": xp,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })
                        asyncio.create_task(self._record_game_adaptive(game, rankings))
                    else:
                        question = game.get_current_question()
                        await self._broadcast_to_game(game, {
                            "type": "game_next_round",
                            "game": game.to_dict(),
                            "question": question,
                            "rankings": rankings,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                        asyncio.create_task(self._run_bot_answers(game))
        except Exception as e:
            logger.error(f"Bot answer error: {e}")

    async def _record_game_adaptive(self, game, rankings):
        try:
            session_factory = _get_session_local()
            async with session_factory() as db:
                for pid in self._get_game_human_player_ids(game):
                    player_ranking = next(
                        (r for r in rankings if r.get("id") == pid), None
                    )
                    if player_ranking:
                        placement = player_ranking.get("rank", rankings.index(player_ranking) + 1)
                        await record_game_interaction(
                            db, pid,
                            game_type=game.game_type,
                            score=player_ranking.get("score", 0),
                            correct_count=player_ranking.get("correct", 0),
                            total_questions=len(game.questions),
                            placement=placement,
                        )
                await db.commit()
        except Exception as e:
            logger.warning("Failed to record adaptive game interaction: %s", e)

    async def send_ping(self, websocket: WebSocket):
        await self.send_message(websocket, {
            "type": "ping",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    async def send_pong(self, websocket: WebSocket):
        await self.send_message(websocket, {
            "type": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


websocket_manager = WebSocketManager()

__all__ = ["websocket_manager", "WebSocketManager", "ConnectionManager"]
