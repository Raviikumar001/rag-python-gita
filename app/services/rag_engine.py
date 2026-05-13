# app/services/rag_engine.py
import hashlib
import time
from typing import AsyncIterator, Optional, List

from app.services.gemini import GeminiService
from app.services.cache import CacheService
from app.core.searcher import QdrantSearcher
from app.core.embedder import DocumentEmbedder
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RAGEngine:
    """Orchestrates the full RAG pipeline: embed -> search -> rerank -> generate -> cache."""

    def __init__(
        self,
        gemini: GeminiService,
        embedder: DocumentEmbedder,
        searcher: QdrantSearcher,
        cache: CacheService,
    ):
        self.gemini = gemini
        self.embedder = embedder
        self.searcher = searcher
        self.cache = cache
        logger.info("RAGEngine initialized")

    def _answer_cache_key(
        self,
        question: str,
        context_limit: int,
        chapter_filter: Optional[int],
        speaker_filter: Optional[str],
    ) -> str:
        key_data = f"{question}:{context_limit}:{chapter_filter}:{speaker_filter}"
        return f"ans:{hashlib.md5(key_data.encode()).hexdigest()}"

    # -- session memory ---------------------------------------------------------

    async def get_memory(self, session_id: str) -> List[dict]:
        key = f"session:{session_id}"
        return await self.cache.get(key) or []

    async def update_memory(
        self, session_id: str, question: str, answer: str
    ) -> None:
        key = f"session:{session_id}"
        history = await self.cache.get(key) or []
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
        history = history[-20:]  # keep last 10 exchanges
        await self.cache.set(key, history, ttl=86400)
        logger.debug(f"Updated memory session={session_id}, turns={len(history) // 2}")

    # -- answer generation ------------------------------------------------------

    async def get_answer(
        self,
        question: str,
        context_limit: int = 5,
        chapter_filter: Optional[int] = None,
        speaker_filter: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        start = time.time()

        # Load chat history for context (if session is active)
        chat_history = await self.get_memory(session_id) if session_id else None

        # Cache only applies when there's no conversation context
        if not session_id:
            cache_key = self._answer_cache_key(
                question, context_limit, chapter_filter, speaker_filter
            )
            cached = await self.cache.get(cache_key)
            if cached is not None:
                logger.info(f"Answer cache hit for '{question[:50]}...'")
                return cached

        # Retrieve relevant Gita verses
        context = await self._retrieve_context(
            question, context_limit, chapter_filter, speaker_filter
        )

        # Generate with conversation history for follow-up context
        answer = await self.gemini.get_answer(question, context, chat_history)

        # Cache standalone answers only (session answers depend on history)
        if not session_id:
            await self.cache.set(cache_key, answer, ttl=3600)

        # Persist this turn
        if session_id:
            await self.update_memory(session_id, question, answer)

        duration = (time.time() - start) * 1000
        logger.info(
            f"Answer generated in {duration:.1f}ms",
            extra={"duration_ms": duration, "endpoint": "/ask"},
        )
        return answer

    async def stream_answer(
        self,
        question: str,
        context_limit: int = 5,
        chapter_filter: Optional[int] = None,
        speaker_filter: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        chat_history = await self.get_memory(session_id) if session_id else None

        context = await self._retrieve_context(
            question, context_limit, chapter_filter, speaker_filter
        )

        async for token in self.gemini.stream_answer(question, context, chat_history):
            yield token

    # -- retrieval --------------------------------------------------------------

    async def _retrieve_context(
        self,
        question: str,
        context_limit: int,
        chapter_filter: Optional[int],
        speaker_filter: Optional[str],
    ) -> List[str]:
        embedding = await self.embedder.embed(question)
        search_k = context_limit * 2 if self.searcher._reranker else context_limit

        results = self.searcher.search(
            vector=embedding,
            k=search_k,
            chapter_filter=chapter_filter,
            speaker_filter=speaker_filter,
        )

        if self.searcher._reranker:
            results = self.searcher.rerank(question, results, top_k=context_limit)
        else:
            results = results[:context_limit]

        return [r.content for r in results]
