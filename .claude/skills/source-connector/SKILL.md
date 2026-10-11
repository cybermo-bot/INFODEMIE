---
name: source-connector
description: How to add or modify a data source connector in PNSI (news, YouTube, Telegram, Facebook routes, Apify, GDELT, imports). Use when writing collection code, scheduling collection, or touching the source registry.
---

# Writing a source connector

Read `docs/sources-plan.md` for the source's route and basis, and decision D4 in `docs/decisions.md` before touching any social platform.

## Interface

Each connector is a class in `apps/api/pnsi/connectors/` implementing:

- `id`, `display_name`, `route` (`official`, `assisted`, `public_contested`, `internal`), `basis` (one sentence: which API or feed, which terms)
- `validate_config(settings) -> ConfigStatus` returns `ok`, `not_configured` (missing key) or `invalid`
- `healthcheck() -> Health`
- `fetch_batch(cursor, since, limit) -> Batch` with `items`, `next_cursor`, `watermark`, `rate_limit_info`, `partial_errors`
- `normalize(raw) -> ContentItemIn`
- `apply_deletions()` where the source reports deletions

## Rules

1. Missing key: status `not_configured`, no data, no crash. Failure: status `failed` with a readable error. Never substitute sample or cached data silently.
2. Redact before storage: handles, individual names when detectable, phone numbers, emails, profile URLs of individuals. Organisation pages keep their name and URL. Test it.
3. Idempotency on (source, platform item id or content hash). Edits become revisions, not new items.
4. Respect documented quotas and `Retry-After`; exponential backoff with jitter; per-source daily budget in config. For YouTube, account for unit costs (search 100, most reads 1).
5. No evasion: no captcha solving, no rotating proxies or fingerprints to get around blocks, no unattended logged-in automation of social accounts.
6. Store `route`, `source_id`, `run_id`, `fetched_at` (UTC), `published_at` (UTC, null if unknown) on every item.
7. Relevance: apply the health filter before storing full text of high-volume sources.
8. Record each run in `collection_runs` with counts (fetched, stored, duplicates, filtered, errors).
9. Log without secrets and without personal identifiers.

## Tests for every connector

- Parses a recorded fixture of a real response (store fixtures with personal data removed).
- `not_configured` when the key is absent.
- No duplicate on a second identical run.
- No handle, phone or email survives normalisation.
