# app/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    port: int = Field(default=8080, alias="PORT")
    host: str = Field(default="0.0.0.0", alias="HOST")

    # Security
    api_key: str = Field(default="dev-key-change-in-production", alias="API_KEY")

    # Gemini
    gemini_api_key: str = Field(alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3-flash-preview", alias="GEMINI_MODEL")
    gemini_embedding_model: str = Field(
        default="text-embedding-004", alias="EMBEDDING_MODEL"
    )

    # Cache
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    cache_ttl: int = Field(default=3600, alias="CACHE_TTL")

    # Vector Database
    qdrant_path: str = Field(default="data/qdrant_storage", alias="QDRANT_PATH")
    qdrant_collection: str = Field(default="gita", alias="QDRANT_COLLECTION")

    # HuggingFace
    hf_token: str | None = Field(default=None, alias="HF_TOKEN")

    # Reranker - disabled by default for low-memory deployments
    reranker_model: str = Field(
        default="BAAI/bge-reranker-base", alias="RERANKER_MODEL"
    )
    enable_reranker: bool = Field(default=False, alias="ENABLE_RERANKER")

    # Chunking
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=100, alias="CHUNK_OVERLAP")

    # Search
    search_top_k: int = Field(default=10, alias="SEARCH_TOP_K")
    rerank_top_k: int = Field(default=5, alias="RERANK_TOP_K")
    similarity_threshold: float = Field(default=0.3, alias="SIMILARITY_THRESHOLD")

    # Rate Limiting
    rate_limit_requests: int = Field(default=10, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")

    # Langfuse (optional)
    langfuse_public_key: str | None = Field(default=None, alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str | None = Field(default=None, alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", alias="LANGFUSE_HOST")

    # Generation
    max_tokens: int = Field(default=8192, alias="MAX_TOKENS")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "populate_by_name": True,
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
