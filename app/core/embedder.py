# app/core/embedder.py
import asyncio
import hashlib
from typing import List

from app.services.gemini import GeminiService
from app.services.cache import CacheService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentEmbedder:
    """Async document embedder with intelligent caching and batched processing.

    Respects Gemini API rate limits by:
    - Adding delays between embedding batches during indexing
    - Limiting concurrent requests
    - Caching embeddings to avoid redundant API calls
    """

    def __init__(
        self,
        gemini: GeminiService,
        cache: CacheService,
        max_concurrency: int = 3,
        batch_delay: float = 1.0,
    ):
        self.gemini = gemini
        self.cache = cache
        self.max_concurrency = max_concurrency
        self.batch_delay = batch_delay
        logger.info(f"Initialized DocumentEmbedder model={gemini.embedding_model} concurrency={max_concurrency}")

    def _cache_key(self, text: str) -> str:
        return f"emb:{hashlib.md5(text.encode('utf-8')).hexdigest()}"

    async def embed(self, text: str) -> List[float]:
        """Embed a single text with cache lookup."""
        cache_key = self._cache_key(text)
        cached = await self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Embedding cache hit for key={cache_key}")
            return cached

        embedding = await self.gemini.embed_query(text)
        await self.cache.set(cache_key, embedding, ttl=86400)
        return embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts with parallel processing, caching, and rate limiting.

        Adds delays between batches to respect Gemini API rate limits.
        """
        results: List[List[float] | None] = [None] * len(texts)
        to_fetch: List[tuple[int, str]] = []

        # Phase 1: Check cache for all texts
        for i, text in enumerate(texts):
            cache_key = self._cache_key(text)
            cached = await self.cache.get(cache_key)
            if cached is not None:
                results[i] = cached
            else:
                to_fetch.append((i, text))

        logger.info(f"Embedding batch: {len(texts)} total, {len(to_fetch)} cache misses")

        # Phase 2: Fetch missing embeddings with concurrency limit and batch delays
        if to_fetch:
            sem = asyncio.Semaphore(self.max_concurrency)
            batch_count = 0

            async def fetch(index: int, text: str) -> tuple[int, List[float]]:
                async with sem:
                    embedding = await self.gemini.embed_content(text)
                    cache_key = self._cache_key(text)
                    await self.cache.set(cache_key, embedding, ttl=86400)
                    return index, embedding

            # Process in small batches with delays to avoid rate limits
            batch_size = self.max_concurrency
            for i in range(0, len(to_fetch), batch_size):
                batch = to_fetch[i:i + batch_size]
                if i > 0 and self.batch_delay > 0:
                    logger.info(f"Rate limit delay: sleeping {self.batch_delay}s before next batch")
                    await asyncio.sleep(self.batch_delay)

                fetched = await asyncio.gather(
                    *[fetch(idx, text) for idx, text in batch], return_exceptions=True
                )

                for item in fetched:
                    if isinstance(item, Exception):
                        logger.error(f"Embedding failed: {item}")
                        raise item
                    index, embedding = item
                    results[index] = embedding

                batch_count += 1
                logger.info(f"Completed embedding batch {batch_count}/{(len(to_fetch) + batch_size - 1) // batch_size}")

        return results
