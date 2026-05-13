# tests/test_app.py
"""Integration tests for the FastAPI app with mocked external services.

Mocks are applied at module level BEFORE importing app.main to ensure
lifespan uses the patched classes.
"""

import pytest
from unittest.mock import AsyncMock

# =============================================================================
# Set up mocks BEFORE importing app.main
# =============================================================================

mock_gemini = AsyncMock()
mock_gemini.embed_query.return_value = [0.01] * 3072
mock_gemini.embed_content.return_value = [0.01] * 3072
mock_gemini.get_answer.return_value = "This is a mock answer about the Gita."
mock_gemini.close = AsyncMock()


async def _mock_stream(*args, **kwargs):
    yield "This "
    yield "is "
    yield "a "
    yield "mock "
    yield "answer."


mock_gemini.stream_answer = _mock_stream
mock_gemini.stream_content = _mock_stream

# Patch GeminiService constructor
import app.services.gemini

app.services.gemini.GeminiService = lambda **kwargs: mock_gemini


class MockSearcher:
    """Mock QdrantSearcher that pretends to have indexed data."""

    def __init__(self, **kwargs):
        pass

    def count(self):
        return 100

    def search(self, **kwargs):
        from app.core.searcher import SearchResult

        return [
            SearchResult(
                content="Mock verse about dharma.",
                score=0.95,
                metadata={"chapter_number": 2, "speaker": "Krishna"},
                id="ch2_v1",
            )
        ]

    def add_points(self, *args):
        pass

    def init_reranker(self, *args):
        pass

    _reranker = None


import app.core.searcher

app.core.searcher.QdrantSearcher = MockSearcher

# Now safe to import app.main - it will use our patched classes
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "2.0.0"
    assert data["vectors_count"] == 100


def test_ask_question(client):
    response = client.post(
        "/api/v1/ask",
        json={"question": "What is dharma?"},
        headers={"Authorization": "Bearer dev-key-change-in-production"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["answer"] == "This is a mock answer about the Gita."
    assert data["model_used"] == "gemini-3-flash-preview"
    assert data["query_time_ms"] > 0


def test_ask_without_auth(client):
    response = client.post(
        "/api/v1/ask",
        json={"question": "What is dharma?"},
    )
    assert response.status_code == 401


def test_search_endpoint(client):
    response = client.post(
        "/api/v1/search",
        json={"query": "karma yoga", "k": 3},
        headers={"Authorization": "Bearer dev-key-change-in-production"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert data["total"] == 1
    assert data["results"][0]["content"] == "Mock verse about dharma."


def test_ask_with_chapter_filter(client):
    response = client.post(
        "/api/v1/ask",
        json={"question": "What is dharma?", "chapter_filter": 2},
        headers={"Authorization": "Bearer dev-key-change-in-production"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data


def test_invalid_api_key(client):
    response = client.post(
        "/api/v1/ask",
        json={"question": "test"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert response.status_code == 401


def test_openapi_docs(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
