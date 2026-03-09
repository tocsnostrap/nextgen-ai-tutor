"""
Redis configuration - optional, gracefully disabled if not available
"""

import logging
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_redis_available = False
redis_client = None
redis_pool = None


class NoOpRedisManager:
    """No-op Redis manager when Redis is not available"""

    async def initialize(self):
        logger.info("Redis not configured - using in-memory fallback")

    async def close(self):
        pass

    async def set_session(self, session_id: str, data: Dict[str, Any], ttl: int = 3600):
        return True

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return None

    async def delete_session(self, session_id: str):
        return True

    async def update_session_ttl(self, session_id: str, ttl: int = 3600):
        return True

    async def publish(self, channel: str, message: Dict[str, Any]):
        return True

    async def subscribe(self, channel: str):
        return None

    async def set_cache(self, key: str, value: Any, ttl: int = 300):
        return True

    async def get_cache(self, key: str) -> Optional[Any]:
        return None

    async def delete_cache(self, key: str):
        return True

    async def clear_pattern(self, pattern: str):
        return 0

    async def check_rate_limit(self, key: str, limit: int, period: int) -> Dict[str, Any]:
        return {"allowed": True, "remaining": limit, "reset": datetime.now()}

    async def track_active_session(self, user_id: str, session_id: str):
        return True

    async def get_active_sessions(self, user_id: str) -> List[str]:
        return []

    async def remove_active_session(self, user_id: str, session_id: str):
        return True

    async def add_websocket_connection(self, connection_id: str, user_id: str):
        return True

    async def remove_websocket_connection(self, connection_id: str):
        return True

    async def get_user_websocket_connections(self, user_id: str) -> List[str]:
        return []

    async def ping(self):
        raise ConnectionError("Redis not configured")


redis_manager = NoOpRedisManager()


async def get_redis():
    """Get Redis client for FastAPI dependency injection"""
    return redis_manager


async def init_redis():
    """Initialize Redis connection"""
    from .config import settings
    if settings.REDIS_URL:
        try:
            import redis.asyncio as redis
            global redis_client, redis_pool, redis_manager
            pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_POOL_SIZE,
                decode_responses=True
            )
            client = redis.Redis(connection_pool=pool)
            await client.ping()
            redis_client = client
            redis_pool = pool
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.warning(f"Redis not available, using no-op fallback: {e}")
    else:
        logger.info("Redis URL not configured - using no-op fallback")


__all__ = [
    "NoOpRedisManager",
    "redis_manager",
    "get_redis",
    "init_redis",
]
