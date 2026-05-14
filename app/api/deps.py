# app/api/deps.py
import hashlib
import hmac
import time

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings
from app.state import app_state
from app.services.rag_engine import RAGEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)


# ---- timing-safe key verification ----

def _verify_key(key: str) -> bool:
    """Constant-time comparison to prevent timing attacks.

    The env var stores a SHA-256 hash of the real key (not the key itself).
    The client sends the plain key in the Bearer header.
    """
    settings = get_settings()
    if not settings.api_key:
        return False
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return hmac.compare_digest(key_hash, settings.api_key)


# ---- brute-force protection ----

_failed_attempts: dict[str, list[float]] = {}
_MAX_FAILED = 5           # lock after this many failed attempts
_FAIL_WINDOW = 300        # 5-minute window
_LOCK_DURATION = 600      # 10-minute lockout


def _is_locked(client_ip: str, now: float) -> bool:
    attempts = [t for t in _failed_attempts.get(client_ip, []) if t > now - _FAIL_WINDOW]
    _failed_attempts[client_ip] = attempts
    if len(attempts) >= _MAX_FAILED:
        oldest = min(attempts)
        remaining = int(_LOCK_DURATION - (now - oldest))
        if remaining > 0:
            return True
        _failed_attempts.pop(client_ip, None)
    return False


def _record_failure(client_ip: str, now: float) -> None:
    attempts = _failed_attempts.get(client_ip, [])
    attempts.append(now)
    _failed_attempts[client_ip] = attempts


async def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> HTTPAuthorizationCredentials:
    """Bearer token auth with timing-safe comparison and brute-force lockout."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    if _is_locked(client_ip, now):
        raise HTTPException(
            status_code=429,
            detail="Too many failed auth attempts. Account locked for 10 minutes.",
            headers={"Retry-After": "600"},
        )

    if not credentials:
        _record_failure(client_ip, now)
        raise HTTPException(status_code=401, detail="Missing API key. Use Authorization: Bearer <key>")

    if not _verify_key(credentials.credentials):
        _record_failure(client_ip, now)
        raise HTTPException(status_code=401, detail="Invalid API key")

    return credentials


# ---- IP rate limiter (for /ask endpoint) ----

_rate_window: dict[str, list[float]] = {}
_RATE_LIMIT_CLEAN_INTERVAL = 120
_last_clean = time.time()


def _clean_expired(now: float, window: float) -> None:
    global _last_clean
    if now - _last_clean < _RATE_LIMIT_CLEAN_INTERVAL:
        return
    _last_clean = now
    cutoff = now - window
    stale = [k for k, ts in _rate_window.items() if all(t < cutoff for t in ts)]
    for k in stale:
        del _rate_window[k]


async def rate_limit(request: Request, max_requests: int = 30, window: float = 60.0) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    cutoff = now - window

    _clean_expired(now, window)

    timestamps = _rate_window.get(client_ip, [])
    timestamps = [t for t in timestamps if t > cutoff]
    _rate_window[client_ip] = timestamps

    if len(timestamps) >= max_requests:
        retry_after = int(window - (now - timestamps[0]))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )

    timestamps.append(now)


# ---- helpers ----

async def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_rag_engine() -> RAGEngine:
    engine = app_state.get("rag")
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not initialized")
    return engine
