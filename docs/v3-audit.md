# V3 audit: what to reuse

The V3 prototype is in `legacy/v3/` for reference. Do not import from it; port the useful logic into `apps/api` with tests.

## Files

| File | Lines | Verdict | Notes for porting |
| --- | --- | --- | --- |
| `src/pipeline.py` | 432 | Rebuild | LangGraph graph: normalise → triage → retrieve whitelist → retrieve context → investigate → quality gate → draft. Prompts are a starting point. Replace with the verification engine (`docs/verification-engine.md`). |
| `src/arabic_nlp.py` | 390 | Port | Language detection (MSA, French, English, Arabizi, Tunisian dialect markers), Arabizi health lexicon (50+ words), manipulation technique patterns (fear, false authority, false urgency, miracle cure, conspiracy). Keep as features and query expansion; never overwrite the original text. |
| `src/inoculation.py` | 281 | Port | 4-step structure (warning, technique, correction, call to action) and channel formats (X 280 chars, Facebook, SMS 160 chars, communiqué). Becomes response templates behind approvals. |
| `src/discovery.py` | 530 | Port pattern | Six collectors (Google News, Bluesky, Reddit, DuckDuckGo, ProMED, Telegram via RSSHub). Re-implement each behind the new connector interface; ProMED RSS is dead since June 2023; Reddit needs approval; Telegram goes direct. |
| `src/collector.py` | 158 | Port | RSS parsing, article text extraction with trafilatura, CSV import. |
| `src/whitelist.py`, `src/retrieval.py` | 200 | Rebuild | Becomes the evidence library with registry, versions and hybrid search. |
| `src/one_health.py` | 286 | Defer | ProMED and WAHIS parsing; One Health is deferred (D11). |
| `src/schemas.py`, `config.py`, `storage.py`, `llm.py`, `utils.py` | 400 | Reference | Replaced by the new models, settings and model gateway. |
| `app.py` | 1,107 | Drop | Streamlit UI; useful only to remember the V3 demo flow. |
| `data/monitor_feeds.json`, `data/whitelist_urls.json`, `data/demo_claims.json` | | Reference | The WHO and CDC URLs in `whitelist_urls.json` are real and can seed the corpus registry after review. |
| `local_whitelist_UNVERIFIED/` | 10 files | Never index | AI-written notes labelled as official sources, with unverified figures. Topic checklist for the deep research phase only (D7). |

Not copied into this repo on purpose: `data/discovery_items.jsonl` and `index/` (contain account handles of real people), `runs/` (outputs built on the unverified notes), `.env`, `.venv`, and the `OMS_Demo` folder (an older version of the same code).

## Bugs and gaps found

1. Counter-messages drafted when the verdict is "uncertain" (route_after_quality sends every `rumor_infodemie` to draft_counter).
2. Account handles stored in discovery items (for example Reddit `author`).
3. No relevance filter on discovery: Tunisia-focused queries stored unrelated US content.
4. No persistence of cases, users, roles, approvals, actions or follow-ups.
5. Verdicts based on 165 chunks of mostly unverified text.
