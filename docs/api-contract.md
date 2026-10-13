# API contract

All workspace resources are under `/api/v1`; authentication is required. Object lookup and collection filtering are institution-scoped. Health endpoints are public but expose no workspace counts. Development bearer sessions are issued by `/auth/login` and revoked by `/auth/logout`.

Collection reads accept `q`, `topic`, `language`, `state`, `case_id`, `cursor` and `limit` (1–100). The development cursor is an offset. Responses contain `items`, `total` and `next_cursor`; shareable UI filter state is in the URL. A production indexed cursor implementation remains required for scale.

Mutable workflow records carry `version`. Mutations require `expected_version`; conflicting changes return 409. Errors have a safe message, code and request ID; schema errors follow FastAPI validation responses. Material changes include actor, institution, UTC timestamp and before/after data in audit. Secrets are omitted.

Core operations:

| Operation | Gate |
| --- | --- |
| POST /imports | Analyst, permission declaration, redaction preview; commit requires Idempotency-Key |
| POST /content/{id}/case | Analyst; source item and resulting case stay scoped |
| POST /claims/{id}/verify | Analyst/reviewer; 202 durable job |
| POST /assessments/{id}/review | Scientific reviewer, current expected_version, approved citations |
| POST /responses | Communication editor, confirmed current assessment |
| PUT /responses/{id} | Editor; new immutable version, clears approval/checkpoints |
| POST /responses/{id}/approve | Separate request/scientific/language/institutional stages |
| POST /actions/record | Exact approved version; Idempotency-Key; publication timestamp must be past |
| POST /documents/{id}/review | Scientific reviewer; withdrawal invalidates affected assessment/response |
| GET /reports/{id}/export | Approved snapshot; PDF/JSON/CSV; scoped and audited |
| GET /versions/{kind}/{id} | Scoped immutable version history, except audited privacy redaction |
| POST /annotations/{id}/resolve | Independent scientific reviewer |
| POST /evaluation/freeze | All reference annotations resolved; frozen checksum |
| POST /evaluations/{id}/measure | Entire frozen dataset matched; actual metrics from submitted predictions |
| POST /sources/{id}/enable | Administrator; exact permitted public HTTPS RSS URL |
| POST /sources/{id}/collect | Operator or administrator; enabled RSS only; reuses queued/running job |
| POST /connectors/public | Local administrator; curated licensed public ECDC RSS sources; source and queue deduplication |

`GET /overview` now includes live connection state, the actual worker heartbeat, total persisted content, distinct collected RSS publications, successful source count, original publication dates/URLs, attribution/licenses, recent collection runs and queued/running/failed job counts. Period charts use publication time where known; absent dates are disclosed and use collection time. RSS items shared between multiple feeds are stored once with all observed source IDs. The local dashboard polls this authenticated endpoint every 15 seconds. Enabled catalog feeds are polled by the single worker every 30 minutes with bounded exponential failure backoff; disabled sources are never scheduled.

`/system/capabilities` reports what is actually configured. Local Ollama inference is optional and schema/citation-validated; model quality is unmeasured until evaluated. No remote inference adapter is enabled. The OpenAPI contract is generated at `/openapi.json`; production frontend code generation and fully normalized storage remain release work.

## Local social item tracking

`GET /tracking/status` returns institution-scoped selected targets, actual credential presence (not a connection guarantee), recent transient observations and per-platform errors. Administrator `POST /tracking/targets` accepts an original URL, a documented purpose and `terms_accepted=true`; canonical URLs deduplicate, with 20 targets maximum. Administrator `DELETE /tracking/targets/{id}` removes the active target and its URL/purpose history; offline backups need separate handling. Administrator/operator/analyst `POST /tracking/refresh` calls the official APIs, once per minute maximum per institution. YouTube/X need owner-configured credentials; Bluesky and Mastodon require allowed public API access. Metrics remain in process memory for 15 minutes, with timestamps, unknown values and individual unavailable states. No API data is included in persistent content, scientific claims, reports or backups. Other platform adapters and keyword discovery are not implemented. See `social-tracking.md`.

## Local social item tracking

`GET /tracking/status` returns institution-scoped selected targets, actual credential presence (not a connection guarantee), recent transient observations and per-platform errors. Administrator `POST /tracking/targets` accepts an original URL, a documented purpose and `terms_accepted=true`; canonical URLs deduplicate, with 20 targets maximum. Administrator `DELETE /tracking/targets/{id}` removes the active target and its URL/purpose history; offline backups need separate handling. Administrator/operator/analyst `POST /tracking/refresh` calls the official APIs, once per minute maximum per institution. YouTube/X need owner-configured credentials; Bluesky and Mastodon require allowed public API access. Metrics remain in process memory for 15 minutes, with timestamps, unknown values and individual unavailable states. No API data is included in persistent content, scientific claims, reports or backups. Other platform adapters and keyword discovery are not implemented. See `social-tracking.md`.

`PUT /tracking/automatic` (local administrator) controls persistent enabled state and the target interval. `POST /tracking/watches` creates one of at most four scoped keyword/hashtag watches with purpose and source-terms declaration. `DELETE /tracking/watches/{id}` removes the active query and its history. `GET /tracking/status` includes the automatic runner heartbeat, per-watch schedule/error/credential-wait state and transient discoveries. The background API thread runs without an open browser, with restart recovery, bounded source-specific search requests, daily installation ceilings and Retry-After-aware exponential failure backoff. YouTube/X credentials are read dynamically; waiting watches wake when configured. Mastodon supports a specified public HTTPS server and up to six comma-separated public hashtags. Filters use source language metadata when available, not an evaluated detector. No discovered social text or engagement counters are written to the database.
