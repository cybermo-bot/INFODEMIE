# Architecture

Modular monolith with background workers, as recommended in Nour's specification (spec §13), adapted to decisions D5 and D9.

## Components

| Component | Choice | Notes |
| --- | --- | --- |
| API | FastAPI, Python 3.12, Pydantic v2 | All endpoints under `/api/v1`; OpenAPI published; typed errors (spec §15) |
| Domain and persistence | SQLAlchemy 2, Alembic | Domain services enforce invariants (spec §35) inside transactions |
| Database | PostgreSQL 16 + pgvector | Full text search (French, simple, normalised Arabic column) + vectors |
| Queue and scheduler | Celery + Redis, Celery beat | Idempotent tasks, persistent job records |
| Model gateway | LiteLLM | Providers: Gemini, Groq, Ollama. Per-task routing, budgets, fallback |
| Embeddings | BGE-M3 on Ollama | 1024-dim dense vectors |
| Reranker | Local multilingual cross-encoder via ONNX (fastembed or equivalent) | No PyTorch needed |
| Files | Local disk under `data/` (gitignored) | MinIO for the pilot |
| Web | Next.js App Router, TypeScript strict, Tailwind, shadcn/ui, next-intl, TanStack Query | RTL via `dir` on `<html>` and logical CSS properties |
| Charts | A React chart library that supports RTL axes and custom theming | Decide in stage 6 |
| Capture | Chrome MV3 extension, TypeScript | Talks to the API with the analyst's token |
| PDF | WeasyPrint | Verify Arabic shaping and bidi |
| Email | SMTP; Mailpit in development | Configured recipients only |
| Auth | Local accounts in dev (argon2), httpOnly cookie sessions, CSRF | OIDC for the pilot |

## Model routing (initial, to tune with the benchmark)

| Task | Default | Fallback |
| --- | --- | --- |
| Triage, taxonomy, emotions, stance (batched) | Groq, fast large model | Ollama local |
| Claim decomposition | Gemini Flash | Groq |
| Judge A | Gemini Flash | Ollama |
| Judge B | Groq strongest free model | Ollama |
| Citation check (yes/no) | Groq | Ollama |
| Drafting | Gemini Flash | Groq |
| Translation for display | Gemini Flash | Groq |
| Embeddings | Ollama BGE-M3 | none (required) |

Free-tier limits change; read them from the provider consoles and set them in config. Track daily usage per provider and switch to fallback before hitting the limit.

## Data flow

Browser → API → PostgreSQL. API → Celery queue → workers → sources and model gateway. Workers → indexes → API. The browser never holds a provider key.

## Privacy boundary

Redaction runs in the ingestion worker (and in the capture extension) before storage. The model gateway refuses any payload that has not passed redaction (a flag set by the ingestion step) when the provider is hosted.

## Environments

- `dev`: Mozart's laptop, WSL2, Docker Compose, Ollama on Windows.
- `demo`: same machine, `make demo` profile with pre-computed analysis and the offline switch tested.
- `pilot`: server hosted in Tunisia, institutional login, paid tiers or local models, backups and monitoring (spec §29).
