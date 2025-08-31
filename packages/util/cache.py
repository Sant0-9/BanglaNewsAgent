import time
import hashlib
import asyncio
from typing import Any, Dict, Optional, Tuple
from packages.util.redis_cache import get_cache, RedisCache

TTL_SECONDS_DEFAULT = 300  # 5 minutes (reduced from 15 for more dynamic caching)

# Fallback in-memory cache if Redis is unavailable
_FALLBACK_CACHE: Dict[str, Tuple[Any, float]] = {}


def _now() -> float:
    return time.time()


def _is_expired(expires_at: float) -> bool:
    return _now() > expires_at


def _make_key(key: str) -> str:
    """Create a unique cache key using hash to avoid key collisions"""
    # Use MD5 hash to create consistent short keys while preserving uniqueness
    return hashlib.md5(key.encode('utf-8')).hexdigest()


def create_query_cache_key(
    query: str, 
    lang: str, 
    window_hours: int, 
    region: Optional[str] = None,
    story_id: Optional[str] = None
) -> str:
    """
    Create cache key for Redis-based caching.
    
    Args:
        query: The original query string
        lang: Language preference  
        window_hours: Time window for search
        region: Regional filter
        story_id: Story cluster ID
    """
    # This function now delegates to Redis cache key creation
    # but maintains backward compatibility for existing code
    return f"news:{query}:{lang}:{window_hours}:{region or ''}:{story_id or ''}"


# Async Redis-based functions
async def get_async(
    mode: str,
    query: str, 
    lang: str = "bn",
    window_hours: Optional[int] = None,
    region: Optional[str] = None,
    story_id: Optional[str] = None
) -> Tuple[Optional[Any], bool]:
    """
    Async get from Redis cache with fallback.
    
    Returns:
        Tuple of (cached_value, is_cache_hit)
    """
    try:
        cache = await get_cache()
        result = await cache.get(mode, query, window_hours, region, story_id, lang)
        return result, result is not None
    except Exception as e:
        print(f"[CACHE] Redis error, falling back to memory cache: {e}")
        # Fallback to memory cache
        cache_key = create_query_cache_key(query, lang, window_hours or 168, region, story_id)
        return get(cache_key), False


async def set_async(
    mode: str,
    query: str,
    value: Any,
    lang: str = "bn", 
    window_hours: Optional[int] = None,
    region: Optional[str] = None,
    story_id: Optional[str] = None,
    is_breaking: bool = False
) -> bool:
    """Async set to Redis cache with fallback"""
    try:
        cache = await get_cache()
        return await cache.set(mode, query, value, window_hours, region, story_id, lang, is_breaking)
    except Exception as e:
        print(f"[CACHE] Redis error, falling back to memory cache: {e}")
        # Fallback to memory cache
        cache_key = create_query_cache_key(query, lang, window_hours or 168, region, story_id)
        set(cache_key, value)
        return True


# Backward compatibility - synchronous functions with fallback
def get(key: str) -> Optional[Any]:
    """Synchronous get from fallback memory cache"""
    k = _make_key(key)
    item = _FALLBACK_CACHE.get(k)
    if not item:
        return None
    value, exp = item
    if _is_expired(exp):
        _FALLBACK_CACHE.pop(k, None)
        return None
    return value


def set(key: str, value: Any, ttl_seconds: int = TTL_SECONDS_DEFAULT) -> None:
    """Synchronous set to fallback memory cache"""
    k = _make_key(key)
    _FALLBACK_CACHE[k] = (value, _now() + float(ttl_seconds))


# Convenience functions for negative caching
async def cache_negative_result(mode: str, query: str, reason: str = "empty_results") -> bool:
    """Cache a negative result"""
    try:
        cache = await get_cache()
        return await cache.set_negative(mode, query, reason)
    except Exception as e:
        print(f"[CACHE] Error caching negative result: {e}")
        return False


async def check_negative_cache(mode: str, query: str) -> Optional[Dict[str, Any]]:
    """Check for negative cache entry"""
    try:
        cache = await get_cache()
        return await cache.get_negative(mode, query)
    except Exception as e:
        print(f"[CACHE] Error checking negative cache: {e}")
        return None
