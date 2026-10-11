# PNSI: Plateforme Nationale de Social Listening Sanitaire et de Gestion de l'Infodémie

National health social-listening and infodemic management platform for Tunisia's Ministry of Health and ONMNE (Observatoire National des Maladies Nouvelles et Émergentes). It will be demonstrated to the Minister of Health. It must work for real, end to end, and every number and verdict must be traceable to its source.

Owner and sole developer: Mozart (Mohamed Fatnassi). Research collaborator: Nour Haouari.

## Read before any non-trivial task

1. `docs/decisions.md`: decisions already taken. They override everything else, including Nour's specification.
2. `docs/build-plan.md`: the stage you are working on, its tasks and its acceptance checks.
3. `docs/blueprint.html`: product concept, screens, source strategy, verification engine (open in a browser or read the HTML).
4. `docs/spec/PNSI_spec.txt`: Nour's full engineering specification (text of the PDF in the same folder). Use it for data contracts, API shape, workflow invariants and tests, unless `docs/decisions.md` says otherwise.
5. `docs/client/`: the ministry's concept note and deck, in Markdown. These are the requirements.
6. `docs/design-brief.md` before any interface work. The blueprint mockups show features and content only; their visual style is rejected (decision D12).
7. Topic docs when relevant: `docs/architecture.md`, `docs/sources-plan.md`, `docs/verification-engine.md`, `docs/v3-audit.md`, `docs/privacy/dpia-outline.md`.

## Non-negotiable rules

These hold in code, tests, seed data, docs, UI copy and commit messages.

1. **No fabricated data.** Never invent statistics, case counts, quotes, citations, document titles, URLs, API responses or evidence. If data is missing, the UI shows it as missing. Scenario or seed data lives in a separate, clearly flagged dataset (`is_scenario = true`) and the UI labels it "Scénario de démonstration".
2. **Evidence comes only from real documents.** A passage can support a verdict only if it comes from a stored document version with a real source URL and an approved registry entry. The files in `legacy/v3/local_whitelist_UNVERIFIED/` were AI-written and must never be indexed as evidence.
3. **Every verdict cites passages.** Citation IDs must resolve to stored passages. A model output with an unresolvable or unsupported citation is rejected and rerun, never shown.
4. **Privacy by design.** Redact names, handles, phone numbers, emails and profile links of individuals before anything is stored or sent to a hosted model. Organisation pages keep their name. No individual profiles, no inference of a person's health status. A test must prove that no handle is stored.
5. **Only redacted public text goes to hosted models.** Hosted free tiers (Gemini, Groq) may use inputs to improve their products. Never send anything else to them.
6. **Every item records its collection route** (`official`, `assisted`, `public_contested`, `internal`) and the run it came from. The Sources screen shows the route.
7. **No evasion.** Respect rate limits and robots rules of official APIs. No captcha solving, no fingerprint spoofing, no proxy rotation to evade blocks, no unattended logged-in bot accounts (see decision D4).
8. **Humans approve, humans publish.** No automatic public posting. Approval binds an exact version of a response variant; any edit invalidates it. Enforced in the backend, not only the UI.
9. **Failures are visible.** A connector or model that fails shows "en échec" or "non configuré". It never falls back to fake or cached data silently.
10. **No secrets in the repo.** Keys live in `.env` (gitignored). Never print secrets in logs.
11. **Writing style.** No em dashes anywhere (code comments, docs, UI copy, messages to Mozart). Plain, human wording. UI copy in formal French by default, with Arabic and English translations.

## Product language

- Interface locales: `fr` (default), `ar` (right-to-left), `en`. Arabic must mirror the layout. Latin-script Arabizi stays left-to-right inside Arabic pages.
- Content languages: Tunisian Derja in Arabic script, Derja in Arabizi (Latin letters with digits such as 3, 7, 9), Modern Standard Arabic, French, English, often mixed in one post. Always keep the original text unchanged and show translations beside it. See the `derja-handling` skill.
- Timestamps are stored in UTC and displayed in Africa/Tunis.

## Stack (decided, see docs/architecture.md)

- Backend: Python 3.12, FastAPI, SQLAlchemy 2 + Alembic, Pydantic v2, Celery + Redis, PostgreSQL 16 with pgvector. Dependencies with `uv`. Tests with `pytest`. Lint with `ruff`.
- Models: one model gateway (LiteLLM) routing per task to Gemini free tier, Groq free tier or local Ollama. Embeddings BGE-M3 on Ollama. Reranker local ONNX cross-encoder. Setting `AI_MODE=local` must make the whole system run without hosted models.
- Frontend: Next.js (App Router) + TypeScript strict + Tailwind + shadcn/ui, `next-intl`, TanStack Query, typed client generated from the FastAPI OpenAPI schema. Package manager `pnpm`. Visual design comes from the direction chosen in Stage 1b and documented in `docs/DESIGN.md`; use the `frontend-design` and taste skills for all interface work.
- Capture extension: Chrome Manifest V3, TypeScript.
- Reports: HTML templates rendered to PDF with WeasyPrint (Arabic shaping must be checked).
- Dev environment: WSL2 Ubuntu on Windows, Docker Compose for Postgres and Redis, Ollama running on Windows and reached at `http://localhost:11434` (WSL mirrored networking).

## Repository layout

```
apps/api/            FastAPI app, domain services, Celery tasks, connectors, AI pipeline
apps/web/            Next.js interface
apps/capture/        PNSI Capture browser extension
packages/api-client/ generated TypeScript client
infra/               docker-compose, init scripts
corpus/              evidence registry (YAML) and document metadata; raw downloads are gitignored
eval/                test sets, evaluation scripts, reports
docs/                decisions, plans, specs, client documents
legacy/v3/           the previous Streamlit prototype, for reference only; do not import from it
```

## How to work in this repo

- Work stage by stage from `docs/build-plan.md`. Start each stage in plan mode, list the tasks, then implement in small vertical slices.
- After every slice: run the tests and the linters, fix failures, then commit with a clear message. Do not leave the repo broken between commits.
- Write tests for the workflow invariants (Nour's spec section 35) as direct API calls, not only through the UI.
- When you take a decision that is not in `docs/decisions.md` and that Mozart would care about (scope, data source, legal basis, model choice, anything user-visible), add it there with date, reason and alternatives, and tell Mozart in your summary.
- Stop and ask Mozart when: a step needs an account, key, payment or a person outside the repo; a source's legal basis is unclear; a requirement in the client documents conflicts with a decision; or a verdict on a real health claim would be shown without reviewed evidence.
- Keep `README.md` commands accurate: when you add a command, document it.
- Use the project skills in `.claude/skills/` when their description matches the task.

## Commands

See `README.md` for the full list (`make help` prints it).

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

## Glossary

- Signal: any collected item. Route: one of five outputs of triage (signal sanitaire, allégation à risque, question / vide informationnel, critique / expérience de service, hors sujet).
- Dossier (case): a claim being handled through evidence, assessment, response, action and follow-up.
- Verdicts: Contredit, Trompeur, Confirmé, Contesté, Preuves insuffisantes, Pas une allégation.
- Température infodémique: experimental composite index (volume, intensité émotionnelle, vitesse, engagement).
- EBS: event-based surveillance, run by ONMNE. EPITEC: ONMNE weekly epidemiological meeting. EIOS: WHO open-source intelligence platform. PHEOC: public health emergency operations centre. RCCE-IM: risk communication, community engagement and infodemic management. INPDP: Tunisian data protection authority. DSSB: directorate of basic health care (vaccination). DPM: directorate of pharmacy and medicines.
