# app/api/deps.py
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings
from app.state import app_state
from app.services.rag_engine import RAGEngine

security = HTTPBearer(auto_error=False)


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
