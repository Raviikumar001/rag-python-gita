# api/models.py
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class SearchQuery:
    query: str
    k: int = 5
    threshold: float = 0.3

@dataclass
class QuestionQuery:
    question: str
    context_limit: int = 5

@dataclass
class MetadataModel:
    timestamp: datetime
    user: str = "ravi-hisoka"
    request_id: str = ""
    additional_info: Optional[Dict] = None

@dataclass
class SearchResult:
    content: str
    score: float
    chunk_index: int

@dataclass
class SearchResponse:
    results: List[SearchResult]
    total: int
    query_time: float
    metadata: MetadataModel

@dataclass
class QuestionResponse:
    answer: str
    metadata: MetadataModel

def validate_query(query_data: dict) -> QuestionQuery:
    """Helper function to validate and create QuestionQuery"""
    if not query_data.get('question'):
        raise ValueError("Question is required")
    
    context_limit = query_data.get('context_limit', 5)
    if not 0 < context_limit <= 10:
        raise ValueError("Context limit must be between 1 and 10")
        
    return QuestionQuery(
        question=query_data['question'],
        context_limit=context_limit
    )

