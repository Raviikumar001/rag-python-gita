# app/core/searcher.py
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.utils.logger import get_logger

logger = get_logger(__name__)


class SearchResult:
    """Represents a single search result with content, score, and metadata."""

    __slots__ = ("content", "score", "metadata", "id")

    def __init__(self, content: str, score: float, metadata: dict, id: str):
        self.content = content
        self.score = score
        self.metadata = metadata
        self.id = id

    def __repr__(self) -> str:
        return f"SearchResult(id={self.id}, score={self.score:.3f})"


class QdrantSearcher:
    """High-performance vector search with metadata filtering and optional reranking."""

    def __init__(
        self,
        path: str = "data/qdrant_storage",
        collection_name: str = "gita",
        vector_size: int = 3072,
    ):
        self.client = QdrantClient(path=path)
        self.collection_name = collection_name
        self.vector_size = vector_size
        self._ensure_collection()
        self._reranker = None
        logger.info(
            f"Initialized QdrantSearcher collection={collection_name} path={path}"
        )

    def _ensure_collection(self) -> None:
        collections = self.client.get_collections().collections
        names = [c.name for c in collections]
        if self.collection_name not in names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size, distance=Distance.COSINE
                ),
            )
            logger.info(f"Created Qdrant collection: {self.collection_name}")

    def add_points(
        self, ids: List[str], vectors: List[List[float]], payloads: List[dict]
    ) -> None:
        """Upsert points into the collection.
        
        Qdrant requires integer or UUID IDs. We hash string IDs to integers
        and preserve the original ID in the payload metadata.
        """
        import hashlib

        points = []
        for id_str, vec, payload in zip(ids, vectors, payloads):
            # Hash string ID to a positive integer for Qdrant
            id_int = int(hashlib.md5(id_str.encode("utf-8")).hexdigest(), 16) % (2**63)
            # Preserve original string ID in payload
            if "metadata" not in payload:
                payload["metadata"] = {}
            payload["metadata"]["original_id"] = id_str
            points.append(PointStruct(id=id_int, vector=vec, payload=payload))

        self.client.upsert(collection_name=self.collection_name, points=points)
        logger.info(f"Upserted {len(points)} points into {self.collection_name}")

    def search(
        self,
        vector: List[float],
        k: int = 10,
        chapter_filter: Optional[int] = None,
        speaker_filter: Optional[str] = None,
        score_threshold: Optional[float] = None,
    ) -> List[SearchResult]:
        """Search vectors with optional metadata filters."""
        conditions = []
        if chapter_filter is not None:
            conditions.append(
                FieldCondition(
                    key="metadata.chapter_number", match=MatchValue(value=chapter_filter)
                )
            )
        if speaker_filter:
            conditions.append(
                FieldCondition(
                    key="metadata.speaker", match=MatchValue(value=speaker_filter)
                )
            )

        query_filter = Filter(must=conditions) if conditions else None

        # qdrant-client local mode in 1.18+ exposes query_points instead of search
        if hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                query_filter=query_filter,
                limit=k,
                score_threshold=score_threshold,
                with_payload=True,
            )
            points = response.points if hasattr(response, "points") else []
        else:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=k,
                query_filter=query_filter,
                score_threshold=score_threshold,
                with_payload=True,
            )
            points = results

        search_results = []
        for r in points:
            search_results.append(
                SearchResult(
                    content=r.payload.get("content", "") if r.payload else "",
                    score=r.score,
                    metadata=r.payload.get("metadata", {}) if r.payload else {},
                    id=str(r.id),
                )
            )
        return search_results

    def init_reranker(self, model_name: str) -> None:
        """Lazy-load a cross-encoder reranker model."""
        from sentence_transformers import CrossEncoder

        logger.info(f"Loading reranker model: {model_name}")
        self._reranker = CrossEncoder(model_name)
        logger.info("Reranker loaded successfully")

    def _ensure_reranker(self) -> None:
        """Auto-initialize reranker on first use if configured."""
        if self._reranker is None:
            from app.config import get_settings
            settings = get_settings()
            if settings.enable_reranker:
                try:
                    self.init_reranker(settings.reranker_model)
                except Exception as exc:
                    logger.warning(f"Failed to auto-load reranker: {exc}")

    def rerank(
        self, query: str, results: List[SearchResult], top_k: int = 5
    ) -> List[SearchResult]:
        """Rerank results using a cross-encoder for higher accuracy."""
        if len(results) <= 1:
            return results[:top_k]

        self._ensure_reranker()

        if not self._reranker:
            return results[:top_k]

        pairs = [[query, r.content] for r in results]
        scores = self._reranker.predict(pairs)

        for r, score in zip(results, scores):
            r.score = float(score)

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def count(self) -> int:
        return self.client.count(collection_name=self.collection_name).count

    def delete_collection(self) -> None:
        self.client.delete_collection(collection_name=self.collection_name)
        logger.info(f"Deleted collection: {self.collection_name}")
