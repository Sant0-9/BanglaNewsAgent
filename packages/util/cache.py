import time
import hashlib
from typing import Any, Dict, Optional, Tuple

TTL_SECONDS_DEFAULT = 900  # 15 minutes

# Simple in-memory cache: key -> (value, expires_at)
_CACHE: Dict[str, Tuple[Any, float]] = {}


def _now() -> float:
    return time.time()


def _is_expired(expires_at: float) -> bool:
    return _now() > expires_at


def _make_key(key: str) -> str:
    """Create a unique cache key using hash to avoid key collisions"""
    # Use MD5 hash to create consistent short keys while preserving uniqueness
    return hashlib.md5(key.encode('utf-8')).hexdigest()


def create_query_cache_key(query: str, lang: str, window_hours: int, timestamp_minutes: Optional[int] = None) -> str:
    """Create a more sophisticated cache key that preserves query uniqueness
    
    Args:
        query: The original query string
        lang: Language preference
        window_hours: Time window for search
        timestamp_minutes: Optional timestamp in minutes for time-based uniqueness
    """
    # Normalize query while preserving uniqueness
    normalized_query = query.strip().lower()
    
    # Add timestamp component to prevent over-caching for evolving news
    if timestamp_minutes is None:
        # Use 30-minute windows to balance caching and freshness
        timestamp_minutes = int(time.time() / 60 / 30)
    
    # Create comprehensive key that maintains uniqueness
    key_components = [
        "ask",
        "v2",  # Increment version to invalidate old cache
        normalized_query,
        lang,
        str(window_hours),
        str(timestamp_minutes)
    ]
    
    return ":".join(key_components)


def get(key: str) -> Optional[Any]:
    k = _make_key(key)
    item = _CACHE.get(k)
    if not item:
        return None
    value, exp = item
    if _is_expired(exp):
        _CACHE.pop(k, None)
        return None
    return value


def set(key: str, value: Any, ttl_seconds: int = TTL_SECONDS_DEFAULT) -> None:
    k = _make_key(key)
    _CACHE[k] = (value, _now() + float(ttl_seconds))
