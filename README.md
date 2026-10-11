# PNSI

Plateforme Nationale de Social Listening Sanitaire et de Gestion de l'Infodémie, built for ONMNE and the Tunisian Ministry of Health.

PNSI collects public health conversation from Tunisian media and social platforms, reads each signal twice (as an information risk and as a possible health event), checks claims against real evidence, drafts responses for human approval, records the actions taken and measures what changed afterwards.

## Status

Stage 1 (foundation) is built; see `docs/status.md` for what runs and what waits on Docker.

## Where to start

| You want to | Read |
| --- | --- |
| Set up your machine | `docs/setup-windows.md` |
| Understand the product | `docs/blueprint.html` (open in a browser) |
| Know what is decided | `docs/decisions.md` |
| Know what to build next | `docs/build-plan.md` |
| Work with Claude Code | `CLAUDE.md` and `.claude/skills/` |
| Read the client's requirements | `docs/client/` |
| Read the full engineering spec | `docs/spec/` |

## Repository layout

```
apps/            api (FastAPI), web (Next.js), capture extension (Stage 3)
packages/        generated API client
infra/           docker compose
corpus/          evidence registry
eval/            test sets and evaluation reports
docs/            all project documentation
legacy/v3/       previous prototype, reference only
.claude/skills/  project skills for Claude Code
```

## Commands

```
make help            # list every command
make install         # uv sync (apps/api) and pnpm install
make services        # start Postgres 16 + pgvector, Redis, Mailpit (Docker) and wait until healthy
make services-down   # stop them (data volumes kept)
make dev             # services, migrations, then API :8000, Celery worker, web :3000 (Ctrl-C stops)
make api | worker | web   # run one process alone
make migrate         # alembic upgrade head
make migration-check # alembic check: models and migrations agree (needs Postgres)
make seed            # ONMNE + one account per role; passwords in data/seed-credentials.txt
make test            # backend tests (DB tests skip if Postgres is down) and web unit tests
make test-api-db     # backend integration tests only; fail if Postgres is down
make e2e             # Playwright browser tests (needs make dev and make seed)
make lint            # ruff, ruff format --check, eslint, tsc
make fmt             # format backend code
make api-client      # export OpenAPI and regenerate packages/api-client types
make eval            # verification test set (Stage 4; exits with a message until then)
```

Node 22 is required (`.nvmrc`); run `nvm use` if your shell starts another version. Playwright needs its browser once: `pnpm --filter @pnsi/web exec playwright install chromium`.
