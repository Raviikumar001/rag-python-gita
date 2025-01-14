# api/models.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string")
    k: Optional[int] = Field(default=5, gt=0, le=20, description="Number of results to return")
    threshold: Optional[float] = Field(default=0.3, gt=0, le=1.0, description="Similarity threshold")

class QuestionQuery(BaseModel):
    question: str = Field(..., min_length=1, description="Question about the API")
    context_limit: Optional[int] = Field(default=5, gt=0, le=10, description="Number of context chunks to use")

class MetadataModel(BaseModel):
    timestamp: datetime
    user: str
    request_id: str
    additional_info: Optional[dict] = None

class SearchResult(BaseModel):
    content: str
    score: float
    chunk_index: int

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query_time: float
    metadata: MetadataModel

class QuestionResponse(BaseModel):
    answer: str
    metadata: MetadataModel