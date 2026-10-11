# Build plan (Track A: minister-ready build)

Stages, not weeks. Each stage ends with a product that works and can be shown. Do them in order; inside a stage, build vertical slices (database to API to screen to test) rather than layers.

For each stage: start in plan mode, restate the tasks below as a checklist, implement, then verify every acceptance check before moving on. Record any scope change in `docs/decisions.md`.

Nour's specification (`docs/spec/PNSI_spec.txt`) gives detailed contracts. Section references below ("spec §14") point to it.

---

## Stage 0 · Setup (Mozart, outside Claude Code)

See `docs/setup-windows.md`. Done when:

- [ ] 40 GB or more free on the disk
- [ ] WSL2 Ubuntu, Docker, Ollama (with `bge-m3` and one 4B-class chat model), Node 22, pnpm, uv, git, gh installed
- [ ] Claude Code installed in WSL and logged in; plugins installed
- [ ] Free keys created and stored in `.env`: Gemini, Groq, Google API key with YouTube Data API v3 and Fact Check Tools API enabled, Telegram api_id/api_hash, Telegram bot token, Apify token
- [ ] Applications started (they take time): Reddit Data API access, Meta developer account and app
- [ ] Private GitHub repository created from this starter, first commit pushed

## Stage 1 · Foundation

Tasks:

1. Monorepo skeleton per `CLAUDE.md`. `Makefile` with `dev`, `test`, `lint`, `migrate`, `seed`, `eval`.
2. `infra/docker-compose.yml`: PostgreSQL 16 with pgvector, Redis, Mailpit (dev email). Health checks.
3. `apps/api`: FastAPI app, settings from env with validation at startup (missing optional keys mark connectors "non configuré", never crash), structured logging with secret redaction, `/api/v1/health`.
4. Data model and Alembic migrations (spec §14 and §35): institutions, users, memberships and roles, sources, collection_runs, content_items (+ revisions), claims, mentions, cases, narratives, evidence_sources, documents, document_versions, passages, assessments, evidence_links, responses, response_variants, approvals, actions, follow_ups, alerts, reports, audit_events, jobs. Every mutable table has `created_at`, `updated_at`, `version`. Every content item has `route`, `source_id`, `run_id`, `is_scenario`.
5. Auth: local accounts for development (argon2 hashes), sessions or JWT in httpOnly cookies, CSRF protection. Roles from `docs/blueprint.html` §8. Object-level authorisation in a central service.
6. Audit log: append-only `audit_events` written by domain services for every material change.
7. `apps/web`: Next.js app with `next-intl` (`fr`, `ar`, `en`), `dir="rtl"` for Arabic, language switcher persisted per user, login page, and a neutral temporary layout. No visual styling decisions yet: they come from Stage 1b.
8. OpenAPI to TypeScript client generation in `packages/api-client`.
9. Seed: one institution (ONMNE), one user per role.

Acceptance:

- [ ] `make dev` starts everything; `make test` and `make lint` pass
- [ ] Each seeded role logs in and sees only its allowed menu items; a forbidden API call returns 403 (tested)
- [ ] Switching to Arabic mirrors the whole layout; Latin text inside stays LTR
- [ ] An audit event is written on login and on any create or update (tested)

## Stage 1b · Design direction

Follow `docs/design-brief.md`.

Tasks:

1. Install and load the design skills: `frontend-design` plugin; taste skills from `Leonxlnx/taste-skill` (`design-taste-frontend`, `minimalist-ui`).
2. Write realistic content for two screens (Vue Cabinet and Dossier) from blueprint §9, labelled as scenario content.
3. Build three clearly different visual directions as real pages under `/design/a`, `/design/b`, `/design/c`, each in French and Arabic.
4. Present them to Mozart with a short rationale each, and wait for the choice.
5. Codify the chosen direction: tokens, themed shadcn components, chart styling, `docs/DESIGN.md`. Delete the unused directions.

Acceptance:

- [ ] Mozart has chosen a direction and the choice is in `docs/decisions.md`
- [ ] `docs/DESIGN.md` exists and the app shell uses its tokens
- [ ] The two screens pass a contrast check and look right in Arabic

## Stage 2 · Open sources

Tasks:

1. Connector interface (spec §7): `validate_config`, `healthcheck`, `fetch_batch(cursor, since, limit)`, `normalize(item)`, `apply_deletions`. Each connector declares its `route` and `basis`.
2. Source registry screen (`/sources`): each source with route, basis, schedule, last success, last error, item counts, enable/disable.
3. Ingestion pipeline: redaction (handles, names when detectable, phones, emails, profile URLs of individuals), language and script detection per span (reuse `legacy/v3/src/arabic_nlp.py` logic), near-duplicate detection, health relevance filter, storage.
4. Connectors, in this order (details in `docs/sources-plan.md`):
   - Tunisian media RSS and sitemaps (start with the verified subset of the candidate list)
   - Google News RSS (FR and AR, Tunisia)
   - GDELT DOC 2.0 API
   - YouTube Data API (search, videos, comment threads) with quota tracking
   - Telegram public channels (Telethon) and t.me/s preview fallback
   - Telegram tipline bot (forwarded messages enter the inbox with route `internal`)
   - Bluesky public search
   - DuckDuckGo news (`ddgs`), route `public_contested`
   - WHO Disease Outbreak News and WHO EMRO news feeds
   - CSV import with validation preview; manual capture form (paste text or URL)
   - Reddit official API connector (disabled until approval)
5. Celery beat schedule per source; manual "run now" button.
6. Signals inbox (`/signaux`): original text, detected language and script, translation (on demand, cached), source, route badge, date, duplicate group, filters.

Acceptance:

- [ ] A scheduled run collects from at least 8 sources; the Sources screen shows each with status
- [ ] A connector with a missing key shows "non configuré"; a failing one shows "en échec" with the error; neither produces data
- [ ] Test: no stored item contains a handle, a phone number, an email or an individual profile URL
- [ ] Re-running the same collection does not duplicate items (idempotency test)

## Stage 3 · Social platforms

Tasks:

1. PNSI Capture extension (`apps/capture`), Chrome MV3:
   - Works on facebook.com, instagram.com, tiktok.com, and any page (generic text capture)
   - On click: reads the post text, visible metadata (page name for organisation pages, date, reaction and comment counts if shown) and the comments currently loaded in the page
   - Redacts individual names and handles in the browser before sending
   - Sends to `/api/v1/imports/capture` with the analyst's session token; route `assisted`
   - Never scrolls, clicks or navigates on its own
2. Logged-out watch-list collector, route `public_contested`:
   - Apify connector (free credit) for Facebook public pages, TikTok hashtags and accounts, Instagram public profiles; budget guard that stops at the free credit
   - Watch-list stored in the database and editable in the Sources screen
3. Facebook Graph API connector for managed Pages: posts and comments, ready to activate when a Page token is provided
4. TikTok oEmbed enrichment for captured TikTok URLs
5. Proposed watch-list (`docs/sources-plan.md`), verified page by page with Mozart

Acceptance:

- [ ] One click on a Facebook post with comments creates a redacted item with its comments in the inbox
- [ ] The Apify connector stops before exceeding the configured budget (tested with a mock)
- [ ] Items show their route in the inbox and on the Sources screen

## Stage 4 · Intelligence and evidence

Tasks:

1. Model gateway (LiteLLM): providers Gemini, Groq, Ollama; per-task model routing in config; JSON schema outputs validated with Pydantic; bounded retries; per-day budgets; automatic fallback to local; `AI_MODE=local` switch; prompt templates versioned in `apps/api/pnsi/ai/prompts/`.
2. Analysis pipeline per item: five-route triage, WHO-style taxonomy (multi-label), risk types from the concept note, emotions (6 labels, multi-label), stance (assert, question, report, sarcasm), claim extraction (atomic claims).
3. Narrative clustering: embeddings plus clustering per theme and time window; growth metrics; analyst confirm, merge, split.
4. Evidence library: registry in `corpus/registry.yaml` (issuer, URL, title, language, dates, topic, approval state), fetcher, text extraction with page and section offsets, chunking, embeddings, PostgreSQL full text index. Corpus v1 from real WHO and Tunisian official documents for the demo themes (see `evidence-grounding` skill). Document viewer that opens the exact passage.
5. Verification engine (`docs/verification-engine.md`).
6. Test set in `eval/claims_v1.jsonl` built only from real, citable sources (WHO myth pages, published fact-checks), with expected verdicts and source URLs; `make eval` prints accuracy, insufficient rate, per-language breakdown and failures.
7. Model benchmark (`model-benchmark` skill) for triage and Derja understanding.

Acceptance:

- [ ] `make eval` runs and writes `eval/reports/<date>.md`
- [ ] Every verdict in the UI shows its passages and the two judges' outcomes
- [ ] With `AI_MODE=local` the pipeline still completes (slower, possibly lower quality, clearly marked)
- [ ] No AI-written V3 file is in the index (test)

## Stage 5 · Case workflow

Tasks: cases (create from inbox, merge, split, assign), case workspace with tabs (blueprint §9 screen C), assessments with reviewer decision, response studio with variants FR, AR, Derja (Arabic script), Arabizi and channel templates (inoculation structure from `legacy/v3/src/inoculation.py`), approval chain (scientific, language, institutional) bound to exact versions, action journal, follow-up scheduling at 48 h, 7 days, 30 days. Invariants from spec §35 as API tests.

Acceptance:

- [ ] The worked example (spec §37) runs end to end through the UI
- [ ] Editing an approved variant invalidates its approval (API test)
- [ ] A "Preuves insuffisantes" verdict cannot produce a corrective draft (API test)
- [ ] Follow-ups are created exactly once per recorded action (idempotency test)

## Stage 6 · Decision layer

Tasks: indicators (temperature with visible components and completeness, trust, intentions, information gaps), alert rules and email notifications, Salle de veille, Vue Cabinet, governorate tile cartogram (explicit locations only, unknown share shown), Remontée terrain mobile form (offline-capable), Note au Ministre PDF and weekly report PDF (FR and AR), Signaux sanitaires queue with export.

Acceptance:

- [ ] Every KPI drills down to the items behind it
- [ ] A source outage marks affected indicators as partial instead of showing a drop
- [ ] PDF reports render Arabic correctly

## Stage 7 · Demo hardening

Tasks: scenario dataset for what cannot be live (flagged), offline switch rehearsal, native Arabic and Derja review of every visible string, accessibility pass (keyboard, contrast, RTL), `demo-readiness` skill run, two timed rehearsals of the 7-minute script (blueprint §14), readiness report (`docs/readiness.md`: what works, what waits on access, what needs evaluation), DPIA and INPDP declaration drafts, wording fixes for the ministry deck.

Acceptance:

- [ ] `demo-readiness` checklist passes with no blocker
- [ ] Rehearsal completes in under 8 minutes without errors, twice
