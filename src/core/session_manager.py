"""Session management with in-memory and Redis storage support"""

import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

from ..models.session import Session
from ..models.openai import Message


class SessionStorage(ABC):
    """Abstract base class for session storage backends"""

    @abstractmethod
    async def get(self, session_id: str, user_id: str) -> Optional[Session]:
        """Get session by ID"""
        pass

    @abstractmethod
    async def set(self, session: Session) -> None:
        """Store or update session"""
        pass

    @abstractmethod
    async def delete(self, session_id: str, user_id: str) -> None:
        """Delete session"""
        pass

    @abstractmethod
    async def cleanup_expired(self, ttl: int) -> int:
        """Remove expired sessions, return count of removed sessions"""
        pass


class InMemoryStorage(SessionStorage):
    """In-memory session storage with TTL support"""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._lock = asyncio.Lock()

    def _make_key(self, session_id: str, user_id: str) -> str:
        """Create storage key from session_id and user_id"""
        return f"{user_id}:{session_id}"

    async def get(self, session_id: str, user_id: str) -> Optional[Session]:
        """Get session by ID"""
        async with self._lock:
            key = self._make_key(session_id, user_id)
            return self._sessions.get(key)

    async def set(self, session: Session) -> None:
        """Store or update session"""
        async with self._lock:
            key = self._make_key(session.session_id, session.user_id)
            session.updated_at = datetime.utcnow()
            self._sessions[key] = session

    async def delete(self, session_id: str, user_id: str) -> None:
        """Delete session"""
        async with self._lock:
            key = self._make_key(session_id, user_id)
            if key in self._sessions:
                del self._sessions[key]

    async def cleanup_expired(self, ttl: int) -> int:
        """Remove expired sessions based on TTL"""
        async with self._lock:
            now = datetime.utcnow()
            expired_keys = []
            
            for key, session in self._sessions.items():
                age = (now - session.updated_at).total_seconds()
                if age > ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._sessions[key]
            
            return len(expired_keys)


class RedisStorage(SessionStorage):
    """Redis-based session storage"""

    def __init__(self, redis_url: str, redis_db: int = 0):
        """
        Initialize Redis storage
        
        Args:
            redis_url: Redis connection URL
            redis_db: Redis database number
        """
        self.redis_url = redis_url
        self.redis_db = redis_db
        self._redis = None

    async def _get_redis(self):
        """Get or create Redis connection"""
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = await aioredis.from_url(
                self.redis_url,
                db=self.redis_db,
                decode_responses=True
            )
        return self._redis

    def _make_key(self, session_id: str, user_id: str) -> str:
        """Create Redis key from session_id and user_id"""
        return f"session:{user_id}:{session_id}"

    async def get(self, session_id: str, user_id: str) -> Optional[Session]:
        """Get session from Redis"""
        redis = await self._get_redis()
        key = self._make_key(session_id, user_id)
        
        data = await redis.get(key)
        if data is None:
            return None
        
        session_dict = json.loads(data)
        return Session.from_dict(session_dict)

    async def set(self, session: Session) -> None:
        """Store session in Redis"""
        redis = await self._get_redis()
        key = self._make_key(session.session_id, session.user_id)
        
        session.updated_at = datetime.utcnow()
        data = json.dumps(session.to_dict())
        
        await redis.set(key, data)

    async def delete(self, session_id: str, user_id: str) -> None:
        """Delete session from Redis"""
        redis = await self._get_redis()
        key = self._make_key(session_id, user_id)
        await redis.delete(key)

    async def cleanup_expired(self, ttl: int) -> int:
        """
        Redis handles expiration automatically with TTL
        This method is a no-op for Redis storage
        """
        return 0

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()


class SessionManager:
    """Manage conversation sessions with automatic cleanup"""

    def __init__(self, storage: SessionStorage, session_ttl: int = 3600):
        """
        Initialize session manager
        
        Args:
            storage: Storage backend for sessions
            session_ttl: Session time-to-live in seconds (default: 1 hour)
        """
        self.storage = storage
        self.session_ttl = session_ttl
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup_task(self):
        """Start background task for cleaning up expired sessions"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup_task(self):
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def _cleanup_loop(self):
        """Background loop for cleaning up expired sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                removed = await self.storage.cleanup_expired(self.session_ttl)
                if removed > 0:
                    print(f"Cleaned up {removed} expired sessions")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in cleanup loop: {e}")

    async def get_session(self, session_id: str, user_id: str) -> Session:
        """
        Get existing session or create new one
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            
        Returns:
            Session object
        """
        session = await self.storage.get(session_id, user_id)
        
        if session is None:
            # Create new session
            session = Session(
                session_id=session_id,
                user_id=user_id,
                conversation_history=[],
                memory_zone=[],
                metadata={},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                total_tokens_used=0
            )
            await self.storage.set(session)
        
        return session

    async def update_session(self, session: Session) -> None:
        """
        Update existing session
        
        Args:
            session: Session to update
        """
        await self.storage.set(session)

    async def reset_session(self, session_id: str, user_id: str) -> None:
        """
        Reset session conversation history while preserving memory zone
        
        Args:
            session_id: Session identifier
            user_id: User identifier
        """
        session = await self.get_session(session_id, user_id)
        session.conversation_history = []
        session.updated_at = datetime.utcnow()
        await self.storage.set(session)

    async def add_message(self, session_id: str, user_id: str, message: Message) -> None:
        """
        Add message to session conversation history
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            message: Message to add
        """
        session = await self.get_session(session_id, user_id)
        session.conversation_history.append(message)
        session.updated_at = datetime.utcnow()
        await self.storage.set(session)

    async def get_context(self, session_id: str, user_id: str) -> List[Message]:
        """
        Get conversation context for session
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            List of messages in conversation history
        """
        session = await self.get_session(session_id, user_id)
        return session.conversation_history

    async def delete_session(self, session_id: str, user_id: str) -> None:
        """
        Delete session completely
        
        Args:
            session_id: Session identifier
            user_id: User identifier
        """
        await self.storage.delete(session_id, user_id)


def create_session_manager(storage_type: str, redis_url: Optional[str] = None, 
                          redis_db: int = 0, session_ttl: int = 3600) -> SessionManager:
    """
    Factory function to create SessionManager with appropriate storage backend
    
    Args:
        storage_type: "memory" or "redis"
        redis_url: Redis connection URL (required if storage_type is "redis")
        redis_db: Redis database number
        session_ttl: Session time-to-live in seconds
        
    Returns:
        Configured SessionManager instance
        
    Raises:
        ValueError: If storage_type is invalid or redis_url is missing for redis storage
    """
    if storage_type == "memory":
        storage = InMemoryStorage()
    elif storage_type == "redis":
        if not redis_url:
            raise ValueError("redis_url is required for redis storage")
        storage = RedisStorage(redis_url, redis_db)
    else:
        raise ValueError(f"Invalid storage type: {storage_type}")
    
    return SessionManager(storage, session_ttl)
