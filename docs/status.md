# Status

Last updated: 2026-10-11, end of the Stage 1 session (before Docker, Ollama and keys).

## Stage 1 · Foundation: what is done

| Build plan task | State | Where |
| --- | --- | --- |
| 1. Monorepo skeleton, Makefile | Done | `Makefile`, `scripts/dev.sh`, `pnpm-workspace.yaml`, `.nvmrc` |
| 2. docker-compose (Postgres 16 + pgvector, Redis, Mailpit, health checks) | Written, never started | `infra/docker-compose.yml`, `infra/postgres/init.sql` |
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

None of this replaces the run on your Docker stack below: the compose file, the init script, Redis and the Celery worker have not run yet.

## What is left to run once Docker is up

Run from the repository root, in this order. Expected results in brackets.

```bash
nvm use                      # Node 22 (nvm default is already set to 22)
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # paste as SECRET_KEY in .env
make install                 # [no changes: dependencies are already installed]
make services                # [postgres, redis, mailpit healthy]
make migrate                 # [Running upgrade -> 0001]
make migration-check         # [No new upgrade operations detected]
make seed                    # [9 accounts; passwords in data/seed-credentials.txt]
make test-api-db             # [24 passed]
make test                    # [81 + 24 backend passed, 16 web passed]
make lint                    # [clean]
make dev                     # API :8000, worker, web :3000
```

Then, with `make dev` running, in a second terminal:

```bash
curl -s localhost:8000/api/v1/health      # [{"status":"ok","database":"ok","redis":"ok"}]
make e2e                                  # [15 passed]
```

And by hand: open http://localhost:3000, log in with an account from `data/seed-credentials.txt`, check the menu, switch to العربية, check the layout mirrors. Mailpit's inbox is at http://localhost:8025 (nothing sends mail yet).

Things to watch:

- `infra/postgres/init.sql` runs only when the Postgres volume is first created. If you started an earlier Postgres with the same volume, run `make services-down` and `docker volume rm pnsi_pgdata` first (this deletes local data).
- The Celery worker has never been started. `make dev` starts it with beat; it has one `pnsi.ping` task and no schedule yet.
- Ollama is not used in Stage 1. For Stage 2 and 4, check `curl http://localhost:11434/api/tags` lists `bge-m3` and the chat model.
- Playwright's Chromium is already downloaded in `~/.cache/ms-playwright` and ran without extra system packages.

## Stage 1 acceptance checks

| Check | State |
| --- | --- |
| `make dev` starts everything; `make test` and `make lint` pass | `make test` and `make lint` pass now; `make dev` needs Docker |
| Each seeded role logs in and sees only its allowed menu; a forbidden API call returns 403 (tested) | Passed on the throwaway Postgres (API and browser); to confirm on Docker |
| Switching to Arabic mirrors the whole layout; Latin text inside stays LTR | Passed in Chromium; to confirm on Docker |
| An audit event is written on login and on any create or update (tested) | Passed on the throwaway Postgres; to confirm on Docker |

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
