"""
Rate Limiter and API Cache for External Tools

Provides rate limiting and short-TTL caching for external API calls
to prevent timeouts and improve reliability.
"""
import asyncio
import time
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json

@dataclass
class CacheEntry:
    """Cache entry with TTL support."""
    value: Any
    expires_at: float
    created_at: float

class RateLimiter:
    """Simple rate limiter using sliding window."""
    
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.calls = defaultdict(list)
        
    def can_make_request(self, key: str) -> bool:
        """Check if a request can be made for the given key."""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old calls
        self.calls[key] = [call_time for call_time in self.calls[key] if call_time > minute_ago]
        
        # Check if under limit
        return len(self.calls[key]) < self.calls_per_minute
    
    def record_request(self, key: str) -> None:
        """Record that a request was made."""
        self.calls[key].append(time.time())

class APICache:
    """Simple in-memory cache with TTL."""
    
    def __init__(self):
        self.cache: Dict[str, CacheEntry] = {}
    
    def _make_key(self, namespace: str, **kwargs) -> str:
        """Create cache key from namespace and parameters."""
        key_data = json.dumps(kwargs, sort_keys=True)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{namespace}:{key_hash}"
    
    def get(self, namespace: str, **kwargs) -> Optional[Any]:
        """Get value from cache if not expired."""
        key = self._make_key(namespace, **kwargs)
        entry = self.cache.get(key)
        
        if entry is None:
            return None
            
        if time.time() > entry.expires_at:
            del self.cache[key]
            return None
            
        return entry.value
    
    def set(self, namespace: str, value: Any, ttl_seconds: int = 120, **kwargs) -> None:
        """Set value in cache with TTL."""
        key = self._make_key(namespace, **kwargs)
        now = time.time()
        
        self.cache[key] = CacheEntry(
            value=value,
            expires_at=now + ttl_seconds,
            created_at=now
        )
    
    def clear_expired(self) -> int:
        """Clear expired entries and return count cleared."""
        now = time.time()
        expired_keys = [key for key, entry in self.cache.items() if now > entry.expires_at]
        
        for key in expired_keys:
            del self.cache[key]
            
        return len(expired_keys)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = time.time()
        total_entries = len(self.cache)
        expired_entries = sum(1 for entry in self.cache.values() if now > entry.expires_at)
        
        return {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
            "cache_keys": list(self.cache.keys())
        }

class ExternalAPIManager:
    """Manages rate limiting and caching for external API calls."""
    
    def __init__(self):
        # Different rate limits for different APIs
        self.rate_limiters = {
            "weather": RateLimiter(calls_per_minute=60),    # OpenWeatherMap free tier
            "markets": RateLimiter(calls_per_minute=5),     # Alpha Vantage free tier
            "sports": RateLimiter(calls_per_minute=100),    # More generous for sports
            "news": RateLimiter(calls_per_minute=1000),     # News APIs are usually generous
        }
        
        # Short-TTL cache for different API types
        self.cache_ttls = {
            "weather": 300,     # 5 minutes for weather
            "markets": 60,      # 1 minute for markets (they change quickly)
            "sports": 180,      # 3 minutes for sports
            "news": 120,        # 2 minutes for news
        }
        
        self.cache = APICache()
    
    async def call_with_protection(
        self,
        api_type: str,
        api_function: Callable[..., Awaitable[Dict[str, Any]]],
        cache_key_params: Dict[str, Any],
        retry_count: int = 2,
        retry_delay: float = 1.0,
        **api_kwargs
    ) -> Dict[str, Any]:
        """
        Call an external API with rate limiting, caching, and retry logic.
        
        Args:
            api_type: Type of API (weather, markets, sports, news)
            api_function: Async function to call the API
            cache_key_params: Parameters to use for cache key generation
            retry_count: Number of retries on failure
            retry_delay: Delay between retries in seconds
            **api_kwargs: Arguments to pass to the API function
            
        Returns:
            API response dictionary
        """
        # Check cache first
        cached_result = self.cache.get(api_type, **cache_key_params)
        if cached_result is not None:
            cached_result["_cache_hit"] = True
            cached_result["_cached_at"] = datetime.now().isoformat()
            return cached_result
        
        # Check rate limit
        rate_limiter = self.rate_limiters.get(api_type)
        if rate_limiter and not rate_limiter.can_make_request(api_type):
            # Return cached result even if expired, or error
            expired_result = self.cache.get(api_type, **cache_key_params)  # Try anyway
            if expired_result:
                expired_result["_cache_hit"] = True
                expired_result["_cache_expired"] = True
                expired_result["_rate_limited"] = True
                return expired_result
            
            return {
                "_error": "Rate limit exceeded",
                "_rate_limited": True,
                "_api_type": api_type,
                "_retry_after": 60,  # Suggest retry after 1 minute
            }
        
        # Make API call with retry logic
        last_exception = None
        
        for attempt in range(retry_count + 1):
            try:
                # Record rate limit usage
                if rate_limiter:
                    rate_limiter.record_request(api_type)
                
                # Call the API
                result = await api_function(**api_kwargs)
                
                # Cache successful result
                ttl = self.cache_ttls.get(api_type, 120)
                self.cache.set(api_type, result, ttl_seconds=ttl, **cache_key_params)
                
                # Add metadata
                result["_cache_hit"] = False
                result["_api_type"] = api_type
                result["_attempt"] = attempt + 1
                result["_cached_until"] = (datetime.now() + timedelta(seconds=ttl)).isoformat()
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < retry_count:
                    # Wait before retry
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
        
        # All retries failed - return error with any cached data
        cached_result = self.cache.get(api_type, **cache_key_params)
        if cached_result is not None:
            cached_result["_cache_hit"] = True
            cached_result["_cache_expired"] = True
            cached_result["_fallback_used"] = True
            cached_result["_last_error"] = str(last_exception)
            return cached_result
        
        # No cache available - return error
        return {
            "_error": str(last_exception),
            "_api_type": api_type,
            "_all_retries_failed": True,
            "_retry_count": retry_count
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for rate limiting and caching."""
        rate_limit_stats = {}
        for api_type, limiter in self.rate_limiters.items():
            now = time.time()
            minute_ago = now - 60
            recent_calls = [call for calls in limiter.calls.values() for call in calls if call > minute_ago]
            
            rate_limit_stats[api_type] = {
                "calls_per_minute_limit": limiter.calls_per_minute,
                "recent_calls": len(recent_calls),
                "active_keys": len(limiter.calls)
            }
        
        return {
            "rate_limits": rate_limit_stats,
            "cache": self.cache.stats(),
            "cache_ttls": self.cache_ttls
        }
    
    async def cleanup(self) -> Dict[str, Any]:
        """Clean up expired cache entries."""
        expired_count = self.cache.clear_expired()
        return {
            "expired_entries_cleared": expired_count,
            "timestamp": datetime.now().isoformat()
        }

# Global API manager instance
api_manager = ExternalAPIManager()