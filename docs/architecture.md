# Architecture

`apps/web` is a Next.js app with a client workspace, accessible controls and reusable case/review forms. Browser requests use a same-origin `/api/v1` proxy; provider credentials never enter the frontend. Internal API location is configured with API_INTERNAL_URL.

`apps/api` contains authentication, scoped record services, governance, review and action workflows. SQLAlchemy supports SQLite for development and PostgreSQL via DATABASE_URL. Four base tables hold versioned records, audit events, sessions and idempotency records. Payloads are JSON text with institution and kind indexed separately. This is a compact development storage model, not the final normalized schema requested for production.

Every material mutation records an actor, old/new values and timestamp. Optimistic updates use `WHERE id AND version` and fail with 409 instead of overwriting another reviewer. Response workflow checks run server-side. SQL transactions bind action records and follow-up creation. Retry keys are institution-bound.

`workers/run.py` processes durable job records independently of API requests. It performs approved-corpus lexical retrieval or a permitted RSS collection. The worker deliberately abstains from an automated medical assessment. Start one worker only; queued jobs persist across restarts. Verification returns 202 and a job ID, with progress at `/api/v1/jobs/{id}`.

Time is stored in ISO UTC and rendered in the user profile timezone (default Africa/Tunis). Counts refer to selected collected content; geography remains unknown unless supplied through an approved future schema. Evidence status and action priority are distinct fields. Missing growth is visible rather than a fabricated zero.

No private groups, influencer profiling, personal health inference, public auto-publishing or external model calls are implemented.
