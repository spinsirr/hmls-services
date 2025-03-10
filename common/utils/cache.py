import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from .config import get_settings
import json
from typing import Any, Optional

settings = get_settings()

# Redis connection pool with optimized settings
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    decode_responses=True,
    health_check_interval=30,
    socket_timeout=10,
    socket_connect_timeout=5,
    socket_keepalive=True,
    retry_on_timeout=True,
    retry_on_error=[redis.ConnectionError, redis.TimeoutError],
)

# Redis client with optimized settings
redis_client = redis.Redis(
    connection_pool=redis_pool,
    socket_keepalive=True,
    retry_on_timeout=True,
    health_check_interval=30
)

async def init_redis():
    """Initialize Redis connection and rate limiter"""
    await FastAPILimiter.init(redis_client)

async def get_cached_data(key: str, default: Any = None) -> Any:
    """Get data from Redis cache with error handling"""
    try:
        value = await redis_client.get(key)
        if value is None:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"Redis error in get_cached_data: {e}")
        return default

async def set_cached_data(key: str, value: Any, expire: int = None):
    """Set data in Redis cache with error handling"""
    try:
        if expire is None:
            expire = settings.CACHE_EXPIRE_SECONDS
            
        if isinstance(value, (dict, list, tuple)):
            value = json.dumps(value)
            
        await redis_client.set(key, value, ex=expire)
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"Redis error in set_cached_data: {e}")

async def clear_cached_data(key: str):
    """Clear data from Redis cache with error handling"""
    try:
        await redis_client.delete(key)
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"Redis error in clear_cached_data: {e}")

async def close_redis():
    """Close Redis connection"""
    await redis_client.close() 