"""
Redis configuration for session management and real-time updates
"""

import logging
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool

from .config import settings

logger = logging.getLogger(__name__)

# Global Redis connection pool
redis_pool: Optional[ConnectionPool] = None
redis_client: Optional[Redis] = None

class RedisManager:
    """Manager for Redis operations"""
    
    def __init__(self):
        self.client = None
    
    async def initialize(self):
        """Initialize Redis connection"""
        global redis_pool, redis_client
        
        try:
            redis_pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_POOL_SIZE,
                decode_responses=True
            )
            redis_client = Redis(connection_pool=redis_pool)
            
            # Test connection
            await redis_client.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connection"""
        if redis_client:
            await redis_client.close()
        if redis_pool:
            await redis_pool.disconnect()
        logger.info("Redis connection closed")
    
    # Session Management
    async def set_session(self, session_id: str, data: Dict[str, Any], ttl: int = 3600):
        """Store session data in Redis"""
        try:
            data_json = json.dumps(data)
            await redis_client.setex(
                f"session:{session_id}",
                ttl,
                data_json
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set session {session_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data from Redis"""
        try:
            data_json = await redis_client.get(f"session:{session_id}")
            if data_json:
                return json.loads(data_json)
            return None
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def delete_session(self, session_id: str):
        """Delete session data from Redis"""
        try:
            await redis_client.delete(f"session:{session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def update_session_ttl(self, session_id: str, ttl: int = 3600):
        """Update session TTL"""
        try:
            return await redis_client.expire(f"session:{session_id}", ttl)
        except Exception as e:
            logger.error(f"Failed to update session TTL {session_id}: {e}")
            return False
    
    # Real-time Updates (Pub/Sub)
    async def publish(self, channel: str, message: Dict[str, Any]):
        """Publish message to Redis channel"""
        try:
            message_json = json.dumps(message)
            await redis_client.publish(channel, message_json)
            return True
        except Exception as e:
            logger.error(f"Failed to publish to channel {channel}: {e}")
            return False
    
    async def subscribe(self, channel: str):
        """Subscribe to Redis channel"""
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub
    
    # Cache Operations
    async def set_cache(self, key: str, value: Any, ttl: int = settings.CACHE_TTL):
        """Set cache value"""
        try:
            value_json = json.dumps(value)
            await redis_client.setex(key, ttl, value_json)
            return True
        except Exception as e:
            logger.error(f"Failed to set cache {key}: {e}")
            return False
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """Get cache value"""
        try:
            value_json = await redis_client.get(key)
            if value_json:
                return json.loads(value_json)
            return None
        except Exception as e:
            logger.error(f"Failed to get cache {key}: {e}")
            return None
    
    async def delete_cache(self, key: str):
        """Delete cache value"""
        try:
            await redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str):
        """Clear keys matching pattern"""
        try:
            keys = await redis_client.keys(pattern)
            if keys:
                await redis_client.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.error(f"Failed to clear pattern {pattern}: {e}")
            return 0
    
    # Rate Limiting
    async def check_rate_limit(self, key: str, limit: int, period: int) -> Dict[str, Any]:
        """Check rate limit for a key"""
        try:
            current = await redis_client.get(key)
            if current is None:
                # First request
                await redis_client.setex(key, period, 1)
                return {
                    "allowed": True,
                    "remaining": limit - 1,
                    "reset": datetime.now() + timedelta(seconds=period)
                }
            
            current_count = int(current)
            if current_count >= limit:
                # Rate limit exceeded
                ttl = await redis_client.ttl(key)
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset": datetime.now() + timedelta(seconds=ttl)
                }
            
            # Increment counter
            await redis_client.incr(key)
            return {
                "allowed": True,
                "remaining": limit - current_count - 1,
                "reset": datetime.now() + timedelta(seconds=await redis_client.ttl(key))
            }
            
        except Exception as e:
            logger.error(f"Failed to check rate limit {key}: {e}")
            return {
                "allowed": True,  # Fail open for safety
                "remaining": limit,
                "reset": datetime.now()
            }
    
    # Session Tracking
    async def track_active_session(self, user_id: str, session_id: str):
        """Track active session for user"""
        try:
            key = f"user:{user_id}:active_sessions"
            await redis_client.sadd(key, session_id)
            await redis_client.expire(key, 86400)  # 24 hours
            return True
        except Exception as e:
            logger.error(f"Failed to track active session {session_id}: {e}")
            return False
    
    async def get_active_sessions(self, user_id: str) -> List[str]:
        """Get active sessions for user"""
        try:
            key = f"user:{user_id}:active_sessions"
            sessions = await redis_client.smembers(key)
            return list(sessions)
        except Exception as e:
            logger.error(f"Failed to get active sessions for user {user_id}: {e}")
            return []
    
    async def remove_active_session(self, user_id: str, session_id: str):
        """Remove active session for user"""
        try:
            key = f"user:{user_id}:active_sessions"
            await redis_client.srem(key, session_id)
            return True
        except Exception as e:
            logger.error(f"Failed to remove active session {session_id}: {e}")
            return False
    
    # WebSocket Connection Tracking
    async def add_websocket_connection(self, connection_id: str, user_id: str):
        """Track WebSocket connection"""
        try:
            # Store connection -> user mapping
            await redis_client.setex(
                f"ws:connection:{connection_id}",
                3600,
                user_id
            )
            
            # Add to user's connections set
            await redis_client.sadd(
                f"user:{user_id}:ws_connections",
                connection_id
            )
            await redis_client.expire(f"user:{user_id}:ws_connections", 3600)
            
            return True
        except Exception as e:
            logger.error(f"Failed to add WebSocket connection {connection_id}: {e}")
            return False
    
    async def remove_websocket_connection(self, connection_id: str):
        """Remove WebSocket connection"""
        try:
            # Get user_id from connection
            user_id = await redis_client.get(f"ws:connection:{connection_id}")
            
            # Remove connection mapping
            await redis_client.delete(f"ws:connection:{connection_id}")
            
            # Remove from user's connections set
            if user_id:
                await redis_client.srem(f"user:{user_id}:ws_connections", connection_id)
            
            return True
        except Exception as e:
            logger.error(f"Failed to remove WebSocket connection {connection_id}: {e}")
            return False
    
    async def get_user_websocket_connections(self, user_id: str) -> List[str]:
        """Get all WebSocket connections for user"""
        try:
            connections = await redis_client.smembers(f"user:{user_id}:ws_connections")
            return list(connections)
        except Exception as e:
            logger.error(f"Failed to get WebSocket connections for user {user_id}: {e}")
            return []

# Global Redis manager instance
redis_manager = RedisManager()

# FastAPI dependency
async def get_redis() -> Redis:
    """Get Redis client for FastAPI dependency injection"""
    if redis_client is None:
        await redis_manager.initialize()
    return redis_client

async def init_redis():
    """Initialize Redis connection"""
    await redis_manager.initialize()

# Context manager for Redis operations
@asynccontextmanager
async def redis_context():
    """Context manager for Redis operations"""
    try:
        yield redis_manager
    finally:
        pass

# Export
__all__ = [
    "RedisManager",
    "redis_manager",
    "get_redis",
    "init_redis",
    "redis_context",
]