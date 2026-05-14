# Gita AI RAG API — Client Integration Guide

Base URL: `http://localhost:8080`
API Version: `v1` (prefix: `/api/v1`)
Auth: Bearer token in `Authorization` header
Content-Type: `application/json`

---

## Quick Reference

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| `POST` | `/api/v1/ask` | Bearer | Ask a question (supports streaming + multi-turn chat) |
| `POST` | `/api/v1/search` | Bearer | Direct verse search (no LLM, fast) |
| `GET` | `/health` | None | Basic health check |
| `GET` | `/api/v1/health` | None | Detailed health + vector count |

---

## 1. Ask a Question (`POST /api/v1/ask`)

The main endpoint. Supports streaming (SSE), multi-turn chat via `session_id`, and chapter/speaker filtering.

### Request Body

```json
{
  "question": "string (1-2000 chars, required)",
  "context_limit": 5,           // int, 1-20, default 5. Number of Gita verses to retrieve
  "stream": false,              // bool, default false. Set true for SSE streaming
  "chapter_filter": null,       // int or null, 1-18. Filter verses to one chapter
  "speaker_filter": null,       // string or null. Valid: "Krishna", "Arjuna", "Sanjaya", "Dhritirashtra"
  "session_id": null            // string or null. Pass for multi-turn chat, omit/auto-generate for new
}
```

### Response (non-streaming)

```json
{
  "answer": "Dharma in the Bhagavad Gita refers to...",
  "citations": [],
  "model_used": "gemini-3-flash-preview",
  "context_chunks_used": 5,
  "query_time_ms": 14668.69,
  "session_id": "bf6c96da-f2e9-4a38-9c0f-245bac2e5f7e"
}
```

`session_id` is always returned — save it for follow-up questions.

### Errors

| Status | Meaning |
|--------|---------|
| `400` | Invalid input (question too long, invalid chapter, etc.) |
| `401` | Missing or wrong API key |
| `429` | Rate limited — 30 requests/minute/IP. Check `Retry-After` header |
| `503` | Service starting up (first boot takes a few minutes) |
| `500` | Server error (check logs) |

---

## 2. Streaming (`stream: true`)

Returns Server-Sent Events (SSE). Each event is a JSON object on a `data:` line.

### Event Types

**Token event** — one `token` per chunk:
```
data: {"token":"Karma"}
data: {"token":" yoga"}
data: {"token":" is"}
```

**Done event** — signals end of stream:
```
data: {"done":true,"session_id":"bf6c96da...","query_time_ms":5200}
```

### Usage

```bash
curl -N -X POST http://localhost:8080/api/v1/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -d '{"question": "What is karma yoga?", "stream": true}'
```

The `-N` flag disables curl's output buffering so tokens appear in real-time.

### JavaScript/TypeScript Client Example

```typescript
async function* streamAsk(
  question: string,
  sessionId?: string,
  chapter?: number
): AsyncGenerator<{ token?: string; done?: boolean; session_id?: string; query_time_ms?: number }> {
  const response = await fetch('http://localhost:8080/api/v1/ask', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer dev-key-change-in-production',
    },
    body: JSON.stringify({
      question,
      stream: true,
      session_id: sessionId,
      chapter_filter: chapter,
    }),
  });

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        yield JSON.parse(line.slice(6));
      }
    }
  }
}

// Usage
const gen = streamAsk('What is dharma?');
let sessionId: string | undefined;
for await (const event of gen) {
  if (event.token) {
    process.stdout.write(event.token); // print token in real-time
  }
  if (event.done) {
    sessionId = event.session_id; // save for follow-ups
    console.log(`\nDone in ${event.query_time_ms}ms`);
  }
}
```

### Python Client Example

```python
import httpx
import json

async def stream_ask(question: str, session_id: str | None = None):
    """Stream tokens from the Gita API."""
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:8080/api/v1/ask",
            json={
                "question": question,
                "stream": True,
                "session_id": session_id,
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer dev-key-change-in-production",
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    if event.get("token"):
                        print(event["token"], end="", flush=True)
                    if event.get("done"):
                        print(f"\n[Done in {event['query_time_ms']:.0f}ms, session={event['session_id']}]")
                        return event["session_id"]

# Usage
import asyncio
session_id = asyncio.run(stream_ask("What is dharma?"))
session_id = asyncio.run(stream_ask("How does Krishna explain that?", session_id))
```

---

## 3. Multi-Turn Chat Flow

```
┌─────────┐                    ┌──────────┐
│ Client  │                    │   API    │
└────┬────┘                    └────┬─────┘
     │  POST /ask                   │
     │  {"question":"What is dharma?"} │
     │─────────────────────────────>│
     │                              │ auto-generates session_id
     │  {"answer":"...",            │ stores Q&A in memory
     │   "session_id":"abc123"}     │
     │<─────────────────────────────│
     │                              │
     │  POST /ask                   │
     │  {"question":"How does Krishna explain that?", │
     │   "session_id":"abc123"}     │
     │─────────────────────────────>│
     │                              │ loads history for "abc123"
     │                              │ prompt includes:
     │                              │ "Previous: User asked about dharma..."
     │                              │ understands "that" = dharma
     │  {"answer":"...",            │
     │   "session_id":"abc123"}     │
     │<─────────────────────────────│
```

**Rules:**
- First message: omit `session_id` → API generates one, returns it
- Follow-up messages: include the `session_id` from the previous response
- Maximum 10 exchanges (20 messages) stored, last 3 sent to LLM per request
- Sessions expire after 24 hours of inactivity
- Each `session_id` is isolated — two clients never see each other's context

### Curl Example

```bash
# Step 1: Start a new conversation
RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -d '{"question": "What is dharma?"}')

# Extract session_id
SESSION_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
echo "Session: $SESSION_ID"

# Step 2: Follow-up
curl -X POST http://localhost:8080/api/v1/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -d "{\"question\": \"How does Krishna explain that?\", \"session_id\": \"$SESSION_ID\"}"
```

---

## 4. Direct Search (`POST /api/v1/search`)

Retrieve relevant verses without LLM generation. Fast (~50ms).

### Request

```json
{
  "query": "string (1-2000 chars, required)",
  "k": 5,                  // int, 1-20, default 5. Number of results
  "chapter_filter": null,  // int or null, 1-18
  "speaker_filter": null   // string or null. "Krishna", "Arjuna", etc.
}
```

### Response

```json
{
  "results": [
    {
      "content": "Krishna said: ...",
      "score": 0.95,
      "metadata": {
        "chapter_number": 2,
        "speaker": "Krishna",
        "original_id": "ch2_v47"
      },
      "id": "123456789"
    }
  ],
  "total": 1,
  "query_time_ms": 45.3
}
```

`score` is cosine similarity (0-1). Higher = more relevant.

### Example

```bash
# Search for verses about karma yoga in chapter 3
curl -X POST http://localhost:8080/api/v1/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -d '{"query": "karma yoga action without attachment", "k": 5, "chapter_filter": 3}'
```

---

## 5. Health Check

```bash
# Basic
curl http://localhost:8080/health
# → {"status":"healthy","timestamp":"...","version":"2.0.0"}

# Detailed
curl http://localhost:8080/api/v1/health
# → {"status":"healthy","timestamp":"...","version":"2.0.0",
#    "vectors_count":700,"qdrant_ready":true,"gemini_ready":true,"cache_ready":true}
```

---

## 6. Error Codes

| Code | When | Response Body | Headers |
|------|------|---------------|---------|
| `400` | Invalid input (Pydantic validation fails) | `{"detail":[{"loc":["body","question"],"msg":"..."}]}` | — |
| `401` | Missing/wrong API key | `{"detail":"Invalid or missing API key"}` | — |
| `429` | Rate limited (>30 req/min per IP) | `{"detail":"Rate limit exceeded. Try again in 45s."}` | `Retry-After: 45` |
| `500` | Server error (Gemini API failed, etc.) | No body | — |
| `503` | App starting up | `{"detail":"RAG engine not initialized"}` | — |

---

## 7. Config Reference (for hosting/deploying)

All configurable via environment variables. See `.env.example` for defaults.

| Variable | Default | Notes |
|----------|---------|-------|
| `GEMINI_API_KEY` | *required* | Google AI Studio API key |
| `API_KEY` | `dev-key-change-in-production` | Bearer token clients must send |
| `PORT` | `8080` | Server port |
| `GEMINI_MODEL` | `gemini-3-flash-preview` | LLM model for answers |
| `EMBEDDING_MODEL` | `gemini-embedding-2-preview` | Embedding model (3072-dim) |
| `EMBEDDING_VECTOR_SIZE` | `3072` | Must match embedding model |
| `REDIS_URL` | *(empty)* | Set to `redis://host:6379/0` for persistent sessions |
| `ENABLE_RERANKER` | `false` | Set `true` for 20-35% better retrieval (+300MB RAM) |
