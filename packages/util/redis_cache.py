import os
import json
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, Tuple
import redis.asyncio as redis
from redis.asyncio import Redis

# Redis connection configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Cache key prefixes
CACHE_PREFIX = "khoboragent"
QUERY_CACHE_PREFIX = f"{CACHE_PREFIX}:query"
NEGATIVE_CACHE_PREFIX = f"{CACHE_PREFIX}:negative"
HEALTH_CACHE_PREFIX = f"{CACHE_PREFIX}:health"

class RedisCache:
    """Redis-based caching system with story-aware keys and dynamic TTLs"""
    
    def __init__(self):
        self._redis: Optional[Redis] = None
    
    async def _get_redis(self) -> Redis:
        """Get or create Redis connection"""
        if self._redis is None:
            self._redis = redis.from_url(
                REDIS_URL, 
                db=REDIS_DB,
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                retry_on_timeout=True
            )
        return self._redis
    
    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent caching"""
        # Convert to lowercase, strip whitespace
        normalized = query.lower().strip()
        
        # Remove multiple spaces
        normalized = ' '.join(normalized.split())
        
        # Remove common punctuation that doesn't affect meaning
        for char in '.,!?;:':
            normalized = normalized.replace(char, ' ')
        
        # Final cleanup
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _create_cache_key(
        self, 
        mode: str,
        query: str, 
        window_hours: Optional[int] = None,
        region: Optional[str] = None,
        story_id: Optional[str] = None,
        lang: str = "bn"
    ) -> str:
        """
        Create story-aware cache key.
        
        Args:
            mode: Type of request (news, weather, markets, etc.)
            query: Normalized query string
            window_hours: Time window for news queries
            region: Regional filter (e.g., "BD")
            story_id: Story cluster identifier
            lang: Language preference
        """
        normalized_query = self._normalize_query(query)
        
        # Create key components
        key_parts = [
            QUERY_CACHE_PREFIX,
            mode,
            lang,
        ]
        
        # Add query hash for consistent length
        query_hash = hashlib.md5(normalized_query.encode()).hexdigest()[:12]
        key_parts.append(query_hash)
        
        # Add optional components
        if window_hours is not None:
            key_parts.append(f"w{window_hours}")
        
        if region:
            key_parts.append(f"r{region}")
        
        if story_id:
            story_hash = hashlib.md5(story_id.encode()).hexdigest()[:8]
            key_parts.append(f"s{story_hash}")
        
        return ":".join(key_parts)
    
    def _get_ttl_for_mode(self, mode: str, is_breaking: bool = False) -> int:
        """
        Get TTL (in seconds) based on content type and urgency.
        
        Args:
            mode: Content mode (news, weather, markets, etc.)
            is_breaking: Whether content is breaking news
            
        Returns:
            TTL in seconds
        """
        if mode == "news":
            if is_breaking:
                return 120  # 2 minutes for breaking news
            else:
                return 300  # 5 minutes for generic news
        elif mode == "weather":
            return 180  # 3 minutes for weather
        elif mode == "markets":
            return 60   # 1 minute for markets (fast-changing)
        elif mode in ["sports", "lookup"]:
            return 600  # 10 minutes for sports/lookup
        else:
            return 300  # 5 minutes default
    
    async def get(
        self, 
        mode: str,
        query: str,
        window_hours: Optional[int] = None,
        region: Optional[str] = None, 
        story_id: Optional[str] = None,
        lang: str = "bn"
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response for query.
        
        Returns:
            Cached data dict or None if not found/expired
        """
        cache_key = self._create_cache_key(mode, query, window_hours, region, story_id, lang)
        
        try:
            redis_client = await self._get_redis()
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                
                # Add cache metadata
                data["cache_hit"] = True
                data["cache_key"] = cache_key
                
                return data
            
        except Exception as e:
            print(f"[CACHE] Error getting cache for key {cache_key}: {e}")
        
        return None
    
    async def set(
        self,
        mode: str,
        query: str, 
        data: Dict[str, Any],
        window_hours: Optional[int] = None,
        region: Optional[str] = None,
        story_id: Optional[str] = None,
        lang: str = "bn",
        is_breaking: bool = False
    ) -> bool:
        """
        Cache response data with appropriate TTL.
        
        Args:
            mode: Content mode
            query: Query string
            data: Data to cache
            window_hours: Time window
            region: Regional filter
            story_id: Story cluster ID
            lang: Language
            is_breaking: Whether this is breaking news
            
        Returns:
            True if cached successfully, False otherwise
        """
        cache_key = self._create_cache_key(mode, query, window_hours, region, story_id, lang)
        ttl = self._get_ttl_for_mode(mode, is_breaking)
        
        try:
            # Add cache metadata to data
            cache_data = data.copy()
            cache_data.update({
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "cache_ttl": ttl,
                "cache_key": cache_key
            })
            
            redis_client = await self._get_redis()
            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cache_data, ensure_ascii=False)
            )
            
            return True
            
        except Exception as e:
            print(f"[CACHE] Error setting cache for key {cache_key}: {e}")
            return False
    
    async def set_negative(
        self,
        mode: str,
        query: str,
        reason: str = "empty_results",
        ttl: int = 120  # 2 minutes default
    ) -> bool:
        """
        Cache negative result (empty/error) to avoid repeated processing.
        
        Args:
            mode: Content mode
            query: Query that returned empty results
            reason: Why the query was empty
            ttl: TTL in seconds (default 2 minutes)
        """
        normalized_query = self._normalize_query(query)
        query_hash = hashlib.md5(normalized_query.encode()).hexdigest()[:12]
        cache_key = f"{NEGATIVE_CACHE_PREFIX}:{mode}:{query_hash}"
        
        negative_data = {
            "reason": reason,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "original_query": query
        }
        
        try:
            redis_client = await self._get_redis()
            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(negative_data)
            )
            return True
        except Exception as e:
            print(f"[CACHE] Error setting negative cache: {e}")
            return False
    
    async def get_negative(
        self,
        mode: str, 
        query: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if query is in negative cache.
        
        Returns:
            Negative cache data or None
        """
        normalized_query = self._normalize_query(query)
        query_hash = hashlib.md5(normalized_query.encode()).hexdigest()[:12]
        cache_key = f"{NEGATIVE_CACHE_PREFIX}:{mode}:{query_hash}"
        
        try:
            redis_client = await self._get_redis()
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
                
        except Exception as e:
            print(f"[CACHE] Error getting negative cache: {e}")
        
        return None
    
    async def invalidate_story(self, story_id: str) -> int:
        """
        Invalidate all cache entries for a specific story.
        
        Args:
            story_id: Story cluster ID to invalidate
            
        Returns:
            Number of keys deleted
        """
        story_hash = hashlib.md5(story_id.encode()).hexdigest()[:8]
        pattern = f"{QUERY_CACHE_PREFIX}:*:s{story_hash}"
        
        try:
            redis_client = await self._get_redis()
            keys = await redis_client.keys(pattern)
            
            if keys:
                deleted = await redis_client.delete(*keys)
                print(f"[CACHE] Invalidated {deleted} cache entries for story {story_id}")
                return deleted
        except Exception as e:
            print(f"[CACHE] Error invalidating story cache: {e}")
        
        return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and health info"""
        try:
            redis_client = await self._get_redis()
            info = await redis_client.info()
            
            # Get key counts by prefix
            query_keys = len(await redis_client.keys(f"{QUERY_CACHE_PREFIX}:*"))
            negative_keys = len(await redis_client.keys(f"{NEGATIVE_CACHE_PREFIX}:*"))
            
            return {
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0"),
                "total_keys": info.get("db0", {}).get("keys", 0),
                "query_cache_keys": query_keys,
                "negative_cache_keys": negative_keys,
                "uptime_seconds": info.get("uptime_in_seconds", 0),
                "cache_hit_ratio": info.get("keyspace_hits", 0) / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def clear_expired(self) -> int:
        """Clear expired keys manually (Redis does this automatically but this forces it)"""
        try:
            redis_client = await self._get_redis()
            # This is mostly for monitoring - Redis handles expiration automatically
            info = await redis_client.info()
            return info.get("expired_keys", 0)
        except Exception as e:
            print(f"[CACHE] Error getting expiration info: {e}")
            return 0


# Global cache instance
_cache_instance: Optional[RedisCache] = None


async def get_cache() -> RedisCache:
    """Get global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance


async def close_cache():
    """Close global cache instance"""
    global _cache_instance
    if _cache_instance:
        await _cache_instance.close()
        _cache_instance = None


# Convenience functions for backward compatibility
async def get_cached_response(
    mode: str,
    query: str,
    window_hours: Optional[int] = None,
    region: Optional[str] = None,
    story_id: Optional[str] = None,
    lang: str = "bn"
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Get cached response.
    
    Returns:
        Tuple of (cached_data, is_cache_hit)
    """
    cache = await get_cache()
    result = await cache.get(mode, query, window_hours, region, story_id, lang)
    return result, result is not None


async def cache_response(
    mode: str,
    query: str,
    data: Dict[str, Any],
    window_hours: Optional[int] = None,
    region: Optional[str] = None, 
    story_id: Optional[str] = None,
    lang: str = "bn",
    is_breaking: bool = False
) -> bool:
    """Cache response data"""
    cache = await get_cache()
    return await cache.set(mode, query, data, window_hours, region, story_id, lang, is_breaking)


async def cache_negative_result(
    mode: str,
    query: str, 
    reason: str = "empty_results"
) -> bool:
    """Cache negative result"""
    cache = await get_cache()
    return await cache.set_negative(mode, query, reason)


async def check_negative_cache(mode: str, query: str) -> Optional[Dict[str, Any]]:
    """Check negative cache"""
    cache = await get_cache()
    return await cache.get_negative(mode, query)