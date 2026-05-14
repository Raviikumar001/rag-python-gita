# app/api/models.py
from pydantic import BaseModel, Field
from typing import Optional, List


class QuestionQuery(BaseModel):
    """Request model for asking a question."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The question to ask about the Bhagavad Gita",
    )
    context_limit: int = Field(
        default=5, ge=1, le=20, description="Number of context chunks to retrieve"
    )
    stream: bool = Field(
        default=False, description="Whether to stream the response as SSE"
    )
    chapter_filter: Optional[int] = Field(
        default=None, ge=1, le=18, description="Filter by chapter number (1-18)"
    )
    speaker_filter: Optional[str] = Field(
        default=None, description="Filter by speaker (Krishna, Arjuna, Sanjaya, Dhritirashtra)"
    )
    session_id: Optional[str] = Field(
        default=None, description="Conversation session ID for multi-turn memory"
    )


class Citation(BaseModel):
    """A citation for a specific verse or passage."""

    chapter: Optional[int] = None
    verse: Optional[int] = None
    speaker: Optional[str] = None
    content: str = ""


class AnswerResponse(BaseModel):
    """Response model for a generated answer."""

    answer: str
    citations: List[Citation] = []
    model_used: str = ""
    context_chunks_used: int = 0
    query_time_ms: float = 0.0
    session_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: str
    version: str
    vectors_count: int
    qdrant_ready: bool
    gemini_ready: bool
    cache_ready: bool


class SearchQuery(BaseModel):
    """Direct search query for retrieving relevant chunks."""

    query: str = Field(..., min_length=1, max_length=2000)
    k: int = Field(default=5, ge=1, le=20)
    chapter_filter: Optional[int] = Field(default=None, ge=1, le=18)
    speaker_filter: Optional[str] = Field(default=None)


class SearchResultItem(BaseModel):
    """Individual search result item."""

    content: str
    score: float
    metadata: dict
    id: str


class SearchResponse(BaseModel):
    """Response for direct search endpoint."""

    results: List[SearchResultItem]
    total: int
    query_time_ms: float
