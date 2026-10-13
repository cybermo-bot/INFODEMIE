# Status

Last updated: 2026-10-13. Stage 1 verified on the Docker stack. Stage 1b not started.

## Stage 1 · Foundation: what is done

| Build plan task | State | Where |
| --- | --- | --- |
| 1. Monorepo skeleton, Makefile | Done | `Makefile`, `scripts/dev.sh`, `pnpm-workspace.yaml`, `.nvmrc` |
| 2. docker-compose (Postgres 16 + pgvector, Redis, Mailpit, health checks) | Done, running (Postgres on host port 5433) | `infra/docker-compose.yml`, `infra/postgres/init.sql` |
| 3. FastAPI app, settings validation, logging with secret redaction, `/api/v1/health` | Done | `apps/api/pnsi/` |
| 4. Data model (30 tables) and Alembic migration | Done | `apps/api/pnsi/models/`, `apps/api/migrations/versions/0001_initial.py` |
| 5. Auth (argon2id, httpOnly session cookies, CSRF), 9 roles, central authorisation | Done | `apps/api/pnsi/auth/`, `apps/api/pnsi/authz/` (decisions D13, D14) |
| 6. Append-only audit log | Done | `apps/api/pnsi/audit/`, DB trigger in migration 0001 |
| 7. Next.js app, next-intl fr/ar/en, RTL, language saved per user, login, neutral layout | Done | `apps/web/` |
| 8. OpenAPI to TypeScript client | Done | `packages/api-client/`, `make api-client` |
| 9. Seed: ONMNE and one user per role | Done | `apps/api/pnsi/cli/seed.py`, `make seed` |

API endpoints so far: `GET /health/live`, `GET /health`, `POST /auth/login`, `POST /auth/logout`, `GET /me`, `PATCH /me`, `GET|POST /users`, `GET /users/{id}`, `GET /audit-events` (all under `/api/v1`).

## How it was verified

- `make lint` and `make test` pass from the repository root: 81 backend unit tests, 16 web unit tests. The 24 backend integration tests skip with a clear message when Postgres is down.
- `pnpm --filter @pnsi/web build` succeeds.
- Migration 0001 renders to SQL offline, and unit tests check it against the models (every table, constraint, index and CHECK).
- **One extra check, outside Docker.** To catch database bugs early, I ran a throwaway PostgreSQL 16.2 with pgvector from the `pgserver` Python package, in a temporary folder outside the repo (not a project dependency; now stopped). Against it:
  - all 24 integration tests passed (each role logs in, menu per role, 403 on a forbidden call, 404 across institutions, CSRF, audit on login, logout, create and update, audit rows cannot be updated or deleted, stale writes give 409);
  - `alembic downgrade base`, `upgrade head` and `alembic check` passed ("No new upgrade operations detected");
  - `make seed` ran twice (idempotent, credentials file mode 600);
  - with the API and `next dev` running, all 15 Playwright tests passed in Chromium, including Arabic mirroring and Latin text staying left-to-right.
  
  This run found one real bug, now fixed: the `follow_ups.window` column is a reserved word in PostgreSQL (renamed `horizon`; a test now rejects reserved column names). It also showed that `pg_trgm` is not needed yet, so migration 0001 no longer creates it (the compose init script still does).

**Run on the Docker stack, 2026-10-13.** `make services`, `make migrate` (upgrade to 0001), `make migration-check` ("No new upgrade operations detected"), `make seed` (9 accounts), `make test-api-db` (24 passed), `make test` (105 backend, 16 web passed), `make lint` (clean), `make dev` (API, Celery worker with beat, web), `GET /api/v1/health` (`{"status":"ok","database":"ok","redis":"ok"}`), a `pnsi.ping` task round trip through Redis (`pong`), and `make e2e` (15 passed).

**Port change.** Ubuntu in WSL has its own PostgreSQL 16 (apt package `postgresql-16`) that starts with WSL and holds `127.0.0.1:5432`. The Docker container could not bind that port, and connections went to the Ubuntu server ("password authentication failed for user pnsi"). The project's Postgres is now published on host port **5433** (`infra/docker-compose.yml`, `.env.example`, settings defaults). If your `.env` was copied before this change, set `DATABASE_URL` and `TEST_DATABASE_URL` to `localhost:5433` (done on this machine). The Ubuntu PostgreSQL is untouched; PNSI does not use it.

Things to watch:

- `infra/postgres/init.sql` runs only when the Postgres volume is first created. To start over: `make services-down` then `docker volume rm pnsi_pgdata` (this deletes local data).
- Celery beat has no schedule yet; it arrives with the Stage 2 connectors.
- Mailpit's inbox is at http://localhost:8025 (nothing sends mail yet).

## Stage 1 acceptance checks

| Check | State |
| --- | --- |
| `make dev` starts everything; `make test` and `make lint` pass | Passed on Docker |
| Each seeded role logs in and sees only its allowed menu; a forbidden API call returns 403 (tested) | Passed on Docker (API and browser) |
| Switching to Arabic mirrors the whole layout; Latin text inside stays LTR | Passed in Chromium on Docker |
| An audit event is written on login and on any create or update (tested) | Passed on Docker |

## Stage 0 items still open on your side (checked 2026-10-13)

Done: WSL mirrored networking (`.wslconfig`), Docker, Node 22, `.env` with `SECRET_KEY`, the design plugin (`frontend-design`).

1. **Ollama on Windows**: done 2026-10-13. Ollama 0.40.3 with `bge-m3` (1024-dim embeddings) and `qwen3:4b-instruct` (D16), both fully on the GPU (RTX 3050 6 GB, driver 617.42), reachable from Ubuntu at `http://localhost:11434`. About 55 tokens/s; a short answer takes under 1 s once the model is loaded. `qwen3:4b` (the Thinking variant) is also pulled; it can be removed with `ollama rm qwen3:4b` unless the Stage 2 benchmark wants it.
2. **Taste skills**: done 2026-10-13. `design-taste-frontend` (v2) and `minimalist-ui` from `Leonxlnx/taste-skill`, installed in `.agents/skills/` with links in `.claude/skills/`, pinned in `skills-lock.json`. Note: v2 targets marketing pages ("not for dashboards or app screens"); Stage 1b uses its references, lint and browser inspector, and relies on `minimalist-ui` and `frontend-design` for the screens.
3. **Keys in `.env`** (all empty), see `docs/setup-windows.md` section 7: `GEMINI_API_KEY`, `GROQ_API_KEY`, `GOOGLE_API_KEY` (YouTube Data API v3 + Fact Check Tools API), `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE`, `TELEGRAM_BOT_TOKEN`, `APIFY_TOKEN`; optional `NCBI_API_KEY`, `NCBI_EMAIL`. Missing keys never block the build: those connectors show "non configuré".
4. **Applications that take weeks**: Reddit Data API access, Meta developer account and app.

## Decisions taken in this session

Recorded in `docs/decisions.md`:

- **D13** Server-side sessions in httpOnly cookies with CSRF double submit, rather than JWT.
- **D14** The nine blueprint roles and the permission matrix, including choices the blueprint leaves open: `administrateur` has no editorial rights; granting `referent_scientifique` or `approbateur` needs a justification and cannot be self-granted; `redacteur` and `approbateur` may record a publication; `partenaire` gets a partner-views screen; other institutions' objects answer 404.
- **D15** Dates shown in Africa/Tunis, 24-hour clock, Western digits in Arabic.

Smaller technical choices, not in the decision log: TypeScript pinned to 5.x (5.9) because Next.js and openapi-typescript use its JavaScript API and the default install picked 7.0; `next dev` is told not to write `apps/web/AGENTS.md` (`agentRules: false`), since agent guidance lives in `CLAUDE.md`; Next.js 16 uses `src/proxy.ts` for locale routing (the former middleware).

## Open points for Mozart

- **Arabic interface strings** (`apps/web/messages/ar.json`) are Modern Standard Arabic written by me and need a native review, as do the Arabic and English role and screen names.
- **Role matrix** (D14): please confirm, in particular who may record a publication and what partners may see.
- **Login throttle** blocks an account for 15 minutes after 5 failures. Someone who knows an address could lock that account during the demo; fine for dev, to revisit before the pilot (per IP and per account, in Redis).
- Not started: Stage 1b (design directions). The layout is deliberately plain.
