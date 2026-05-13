# app/api/deps.py
import time

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings
from app.state import app_state
from app.services.rag_engine import RAGEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)

# ---- in-memory rate limiter (no extra dependencies) ----

_rate_window: dict[str, list[float]] = {}
_RATE_LIMIT_CLEAN_INTERVAL = 120  # seconds between cleanups
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
    """Simple fixed-window rate limiter per client IP."""
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


# ---- auth ----

async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> HTTPAuthorizationCredentials:
    settings = get_settings()
    if not credentials or credentials.credentials != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return credentials


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
