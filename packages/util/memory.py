import hashlib
import time
from typing import Any, Dict, Optional

TTL_SECONDS = 3600  # 1 hour

# In-memory session store: sid -> {data, expires_at}
_SESSIONS: Dict[str, Dict[str, Any]] = {}
_EXPIRY: Dict[str, float] = {}


def _now() -> float:
    return time.time()


def _purge_expired() -> None:
    now = _now()
    expired_keys = [sid for sid, ts in _EXPIRY.items() if ts <= now]
    for sid in expired_keys:
        _SESSIONS.pop(sid, None)
        _EXPIRY.pop(sid, None)


def derive_session_id(client_ip: Optional[str], user_agent: Optional[str]) -> str:
    """Derive a stable session id from client IP and User-Agent.

    Uses SHA1 over "ip|ua"; safe for non-sensitive session affinity.
    """
    ip = (client_ip or "").strip()
    ua = (user_agent or "").strip()
    raw = f"{ip}|{ua}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def _ensure_session(sid: str) -> Dict[str, Any]:
    _purge_expired()
    if sid not in _SESSIONS:
        _SESSIONS[sid] = {
            "preferred_lang": None,
            "last_query": None,
            "last_evidence": None,
            "updated_at": _now(),
        }
    _EXPIRY[sid] = _now() + TTL_SECONDS
    return _SESSIONS[sid]


def remember_preferred_lang(sid: str, lang: Optional[str]) -> None:
    sess = _ensure_session(sid)
    if lang:
        sess["preferred_lang"] = lang
        sess["updated_at"] = _now()


def remember_last_query(sid: str, query: str) -> None:
    sess = _ensure_session(sid)
    if query:
        sess["last_query"] = query
        sess["updated_at"] = _now()


def remember_last_evidence(sid: str, evidence: Any) -> None:
    sess = _ensure_session(sid)
    sess["last_evidence"] = evidence
    sess["updated_at"] = _now()


def get_session(sid: str) -> Dict[str, Any]:
    """Return session data (creates if missing)."""
    return _ensure_session(sid)
