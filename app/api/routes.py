# app/api/routes.py
import hashlib
import json
import time
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.models import (
    QuestionQuery,
    AnswerResponse,
    SearchQuery,
    SearchResponse,
    SearchResultItem,
    Citation,
)
from app.api.deps import verify_api_key, get_client_ip, get_rag_engine
from app.services.rag_engine import RAGEngine
from app.config import get_settings

router = APIRouter()


@router.post("/ask", response_model=AnswerResponse)
async def ask_question(
    query: QuestionQuery,
    rag: RAGEngine = Depends(get_rag_engine),
    api_key=Depends(verify_api_key),
    client_ip: str = Depends(get_client_ip),
):
    """Ask a question about the Bhagavad Gita. Supports streaming via SSE."""
    start_time = time.time()
    settings = get_settings()

    if query.stream:
        async def stream_generator() -> AsyncIterator[str]:
            buffer = []
            async for token in rag.stream_answer(
                question=query.question,
                context_limit=query.context_limit,
                chapter_filter=query.chapter_filter,
                speaker_filter=query.speaker_filter,
                session_id=query.session_id,
            ):
                buffer.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"

            # Cache the full answer after streaming completes
            full_answer = "".join(buffer)
            cache_key = f"ans:{hashlib.md5(query.question.encode()).hexdigest()}:{query.context_limit}:{query.chapter_filter}:{query.speaker_filter}"
            await rag.cache.set(cache_key, full_answer, ttl=settings.cache_ttl)

            if query.session_id:
                await rag.update_memory(query.session_id, query.question, full_answer)

            query_time = (time.time() - start_time) * 1000
            yield f"data: {json.dumps({'done': True, 'query_time_ms': query_time})}\n\n"

        return StreamingResponse(
            stream_generator(), media_type="text/event-stream"
        )

    # Non-streaming path
    answer = await rag.get_answer(
        question=query.question,
        context_limit=query.context_limit,
        chapter_filter=query.chapter_filter,
        speaker_filter=query.speaker_filter,
        session_id=query.session_id,
    )

    query_time = (time.time() - start_time) * 1000

    return AnswerResponse(
        answer=answer,
        citations=[],  # TODO: extract structured citations from response
        model_used=settings.gemini_model,
        context_chunks_used=query.context_limit,
        query_time_ms=query_time,
    )


@router.post("/search", response_model=SearchResponse)
async def search_chunks(
    query: SearchQuery,
    rag: RAGEngine = Depends(get_rag_engine),
    api_key=Depends(verify_api_key),
):
    """Direct semantic search endpoint to retrieve relevant chunks."""
    start_time = time.time()

    embedding = await rag.embedder.embed(query.query)
    results = rag.searcher.search(
        vector=embedding,
        k=query.k,
        chapter_filter=query.chapter_filter,
        speaker_filter=query.speaker_filter,
    )

    query_time = (time.time() - start_time) * 1000

    return SearchResponse(
        results=[
            SearchResultItem(
                content=r.content,
                score=r.score,
                metadata=r.metadata,
                id=r.id,
            )
            for r in results
        ],
        total=len(results),
        query_time_ms=query_time,
    )


@router.get("/health")
async def health_check(rag: RAGEngine = Depends(get_rag_engine)):
    """Health check endpoint."""
    from datetime import datetime, timezone

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
        "vectors_count": rag.searcher.count(),
        "qdrant_ready": rag.searcher.count() > 0,
        "gemini_ready": True,
        "cache_ready": True,
    }
