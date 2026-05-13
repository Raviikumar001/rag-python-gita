# app/services/gemini.py
import asyncio
import json
import logging
import os
import time
from typing import AsyncIterator, List

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ---- Prompt template (single source, no duplication) ----

_PROMPT_TEMPLATE = """You are a deeply knowledgeable assistant specializing in the Bhagavad Gita.
Your role is to provide clear, accurate, and spiritually insightful explanations of its teachings, verses, and philosophical concepts.

Guidelines:
1. Directly address the user's question using the provided context.
2. Cite specific verses and chapters when relevant.
3. Explain Sanskrit terms clearly.
4. Connect teachings to broader philosophical and spiritual context.
5. Provide practical interpretations for modern life.
6. Use markdown formatting for readability.

Context from the Bhagavad Gita:
```
{context}
```

Question: {question}

Provide a comprehensive answer, citing specific verses where relevant."""


# ---- Retry logic ----

class RateLimitError(Exception):
    """Raised when Gemini API returns 429 and we should back off."""
    pass


def _should_retry(exception: BaseException) -> bool:
    """Only retry transient errors (429, 5xx, connection). 4xx (except 429) fail immediately."""
    if isinstance(exception, RateLimitError):
        return True
    if isinstance(exception, (httpx.ConnectError, httpx.ReadError)):
        return True
    if isinstance(exception, httpx.HTTPStatusError):
        status = exception.response.status_code
        return status == 429 or 500 <= status < 600
    return False


# ---- Service ----

class GeminiService:
    """Async HTTP client for Google Gemini REST API.

    All model names come from configuration (env vars or Settings).
    No hardcoded fallbacks — the app's config layer is the single source of truth.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    EMBEDDING_MIN_INTERVAL = 0.5
    GENERATION_MIN_INTERVAL = 4.0

    def __init__(
        self,
        api_key: str,
        model: str,
        embedding_model: str,
    ):
        self.api_key = api_key
        self.model = model
        self.embedding_model = embedding_model
        self.client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_connections=20),
        )
        self._lock = asyncio.Lock()
        self._last_request_time = 0.0
        logger.info(
            f"Initialized GeminiService gen_model={model} emb_model={embedding_model}"
        )

    # ---- payload builder ----

    def _build_payload(self, contents: list, response_schema: dict | None = None) -> dict:
        payload: dict = {"contents": contents}
        if response_schema:
            payload["generationConfig"] = {
                "response_mime_type": "application/json",
                "response_schema": response_schema,
            }
        return payload

    # ---- rate limiting ----

    async def _throttle(self, min_interval: float) -> None:
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            self._last_request_time = time.time()

    # ---- response checking ----

    async def _check_response(self, response: httpx.Response) -> None:
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            wait_time = int(retry_after) if retry_after else 10
            logger.warning(f"Gemini rate limited (429). Waiting {wait_time}s before retry.")
            await asyncio.sleep(wait_time)
            raise RateLimitError(f"Rate limited, retry after {wait_time}s")

        if response.status_code == 404:
            body = response.text[:200]
            logger.error(f"Gemini model not found (404): {response.url} — {body}")
            raise httpx.HTTPStatusError(
                f"Model not found. Check GEMINI_MODEL / EMBEDDING_MODEL env vars or API key permissions.",
                request=response.request,
                response=response,
            )

        response.raise_for_status()

    # ---- generation ----

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=_should_retry,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def generate_content(self, prompt: str, response_schema: dict | None = None) -> str:
        await self._throttle(self.GENERATION_MIN_INTERVAL)

        url = f"{self.BASE_URL}/models/{self.model}:generateContent?key={self.api_key}"
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        payload = self._build_payload(contents, response_schema=response_schema)

        response = await self.client.post(url, json=payload)
        await self._check_response(response)
        data = response.json()

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            logger.error(f"Unexpected Gemini response format: {data}")
            raise ValueError("Unexpected response format") from exc

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=_should_retry,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def stream_content(self, prompt: str) -> AsyncIterator[str]:
        await self._throttle(self.GENERATION_MIN_INTERVAL)

        url = (
            f"{self.BASE_URL}/models/{self.model}:streamGenerateContent"
            f"?key={self.api_key}&alt=sse"
        )
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        payload = {"contents": contents}

        async with self.client.stream("POST", url, json=payload) as response:
            await self._check_response(response)

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str in ("", "[DONE]", "[DONE]\r"):
                        break
                    try:
                        data = json.loads(data_str)
                        candidate = data.get("candidates", [{}])[0]
                        parts = candidate.get("content", {}).get("parts", [{}])
                        text = parts[0].get("text", "") if parts else ""
                        if text:
                            yield text
                    except json.JSONDecodeError:
                        continue

    # ---- prompt builders ----

    def _build_qa_prompt(self, question: str, context_chunks: List[str]) -> str:
        context_text = "\n\n---\n\n".join(context_chunks)
        return _PROMPT_TEMPLATE.format(context=context_text, question=question)

    async def get_answer(self, question: str, context_chunks: List[str]) -> str:
        return await self.generate_content(self._build_qa_prompt(question, context_chunks))

    async def stream_answer(self, question: str, context_chunks: List[str]) -> AsyncIterator[str]:
        async for chunk in self.stream_content(self._build_qa_prompt(question, context_chunks)):
            yield chunk

    # ---- embeddings ----

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=_should_retry,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def embed_content(self, text: str) -> List[float]:
        await self._throttle(self.EMBEDDING_MIN_INTERVAL)

        url = f"{self.BASE_URL}/models/{self.embedding_model}:embedContent?key={self.api_key}"
        payload = {
            "content": {"parts": [{"text": text}]},
            "taskType": "RETRIEVAL_DOCUMENT",
        }
        response = await self.client.post(url, json=payload)
        await self._check_response(response)
        data = response.json()
        return data["embedding"]["values"]

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=_should_retry,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def embed_query(self, text: str) -> List[float]:
        await self._throttle(self.EMBEDDING_MIN_INTERVAL)

        url = f"{self.BASE_URL}/models/{self.embedding_model}:embedContent?key={self.api_key}"
        payload = {
            "content": {"parts": [{"text": text}]},
            "taskType": "RETRIEVAL_QUERY",
        }
        response = await self.client.post(url, json=payload)
        await self._check_response(response)
        data = response.json()
        return data["embedding"]["values"]

    async def close(self) -> None:
        await self.client.aclose()
        logger.info("Closed GeminiService HTTP client")
