"""Redis cache adapter using async Redis client."""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Async Redis cache adapter.
    
    Provides caching functionality using Redis with async operations.
    Supports JSON serialization for complex Python objects.
    
    Example:
        ```python
        cache = RedisCache(redis_url="redis://localhost:6379/0")
        await cache.connect()
        
        # Set value
        await cache.set("key", {"data": "value"}, expire=3600)
        
        # Get value
        value = await cache.get("key")
        
        await cache.close()
        ```
    """
    
    def __init__(
        self,
        redis_url: str,
        max_connections: int = 50,
        decode_responses: bool = True,
    ) -> None:
        """
        Initialize Redis cache adapter.
        
        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379/0")
            max_connections: Maximum number of connections in the pool
            decode_responses: Whether to decode responses to strings
        """
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.decode_responses = decode_responses
        
        # Connection pool and client (initialized in connect())
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
    
    async def connect(self) -> None:
        """
        Establish connection to Redis.
        
        Creates connection pool and Redis client.
        Should be called before using any cache operations.
        """
        try:
            self._pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                decode_responses=self.decode_responses,
            )
            self._client = Redis(connection_pool=self._pool)
            
            # Test connection
            await self._client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
            
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def close(self) -> None:
        """
        Close Redis connection and cleanup resources.
        
        Should be called when shutting down the application.
        """
        if self._client:
            await self._client.aclose()
            logger.info("Redis connection closed")
        
        if self._pool:
            await self._pool.aclose()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value (deserialized from JSON) or None if not found
        """
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        
        try:
            value = await self._client.get(key)
            if value is None:
                return None
            
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Return raw value if not JSON
                return value
                
        except RedisError as e:
            logger.error(f"Error getting key '{key}' from cache: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized if not a string)
            expire: Expiration time in seconds (None = no expiration)
            
        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        
        try:
            # Serialize to JSON if not a string
            if not isinstance(value, str):
                value = json.dumps(value)
            
            await self._client.set(key, value, ex=expire)
            return True
            
        except (RedisError, TypeError, ValueError) as e:
            logger.error(f"Error setting key '{key}' in cache: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if key didn't exist
        """
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        
        try:
            result = await self._client.delete(key)
            return result > 0
            
        except RedisError as e:
            logger.error(f"Error deleting key '{key}' from cache: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        
        try:
            result = await self._client.exists(key)
            return result > 0
            
        except RedisError as e:
            logger.error(f"Error checking existence of key '{key}': {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for a key.
        
        Args:
            key: Cache key
            seconds: Expiration time in seconds
            
        Returns:
            True if expiration was set, False if key doesn't exist
        """
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        
        try:
            result = await self._client.expire(key, seconds)
            return result
            
        except RedisError as e:
            logger.error(f"Error setting expiration for key '{key}': {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment integer value in cache.
        
        Args:
            key: Cache key
            amount: Amount to increment by (default: 1)
            
        Returns:
            New value after increment, or None on error
        """
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        
        try:
            result = await self._client.incrby(key, amount)
            return result
            
        except RedisError as e:
            logger.error(f"Error incrementing key '{key}': {e}")
            return None
    
    async def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Decrement integer value in cache.
        
        Args:
            key: Cache key
            amount: Amount to decrement by (default: 1)
            
        Returns:
            New value after decrement, or None on error
        """
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        
        try:
            result = await self._client.decrby(key, amount)
            return result
            
        except RedisError as e:
            logger.error(f"Error decrementing key '{key}': {e}")
            return None
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values from cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dictionary mapping keys to values (missing keys are omitted)
        """
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        
        try:
            values = await self._client.mget(keys)
            result = {}
            
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = value
            
            return result
            
        except RedisError as e:
            logger.error(f"Error getting multiple keys from cache: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        if not self._client:
            return False
        
        try:
            await self._client.ping()
            return True
        except RedisError:
            return False

