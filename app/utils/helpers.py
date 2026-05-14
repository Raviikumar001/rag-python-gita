# app/utils/helpers.py
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Optional


def create_metadata(additional_data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Create standardized metadata for responses."""
    metadata = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": str(uuid.uuid4()),
        "service_version": "2.0.0",
        "environment": "development",
    }
    if additional_data:
        metadata.update(additional_data)
    return metadata


def sanitize_text(text: str, max_length: int = 500) -> str:
    """Sanitize and truncate text for logging."""
    cleaned = text.replace("\n", " ").replace("\r", " ").strip()
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "..."
    return cleaned


def generate_cache_key(*parts: str) -> str:
    """Generate a deterministic cache key from string parts."""
    combined = ":".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()[:32]
