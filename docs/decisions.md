# Decision log

Decisions that shape the product. Newest at the bottom. Each entry: date, decision, reason, consequence, alternatives considered. When a decision here conflicts with Nour's specification (`docs/spec/`) or the blueprint, this file wins.

---

## D1 · Demo standard (2026-10-11)

**Decision.** The minister sees a real, working, end-to-end product. Limitations are stated openly, but most of the scope must run for real.

**Consequence.** Every screen shown is backed by persisted data and working actions. Scenario data is used only where live data cannot exist yet (for example a 30-day follow-up on an action taken last week), stored with `is_scenario = true`, and labelled "Scénario de démonstration" on screen.

**Alternatives.** Clickable mockup (rejected: does not prove feasibility).

## D2 · Builder (2026-10-11)

**Decision.** Mozart builds alone, assisted by Claude Code. Nour contributes research.

**Consequence.** The repo is written for agent-assisted work: `CLAUDE.md`, staged build plan with acceptance checks, project skills, decision log.

## D3 · Maximum source coverage (2026-10-11)

**Decision.** Use as many sources as possible. Keep all six V3 sources (Google News, Bluesky, Reddit, DuckDuckGo, ProMED, Telegram) and add every other workable source. Open Facebook, TikTok and Instagram as far as legitimately possible.

**Consequence.** See `docs/sources-plan.md`. ProMED is replaced by WHO outbreak feeds because ProMED switched off its RSS on 2 June 2023. Reddit needs API approval. Every item records its collection route.

## D4 · Facebook, Instagram, TikTok access (2026-10-11)

**Decision.** The client suggested dedicated accounts used for monitoring, with the pages chosen by us. We implement this as **analyst-operated monitoring accounts with the PNSI Capture extension** (a person browses normally, one click records the post and its loaded comments, redacted). In addition: Graph API on Pages the ministry manages (when a token is provided), Meta App Review for Page Public Content Access (to apply for), logged-out collection of a curated public watch-list (Apify free credit or our own logged-out collector), TikTok oEmbed for captured videos, Instagram hashtag search via Graph API later.

**Not built.** Unattended bot accounts that log in and scrape.

**Reason.** In Meta v. BrandTotal (N.D. Cal., 2022) a court found that automated collection from logged-in Facebook accounts breached Meta's terms and violated US anti-hacking law. Such accounts are also blocked quickly, which could happen on demo day. In Meta v. Bright Data (N.D. Cal., January 2024) the court held that logged-out scraping of public data did not breach Meta's terms; Meta's terms still claim otherwise, so that route is labelled "public, contested" and kept small and polite. Monitoring accounts must belong to real, identifiable people (fake personas break Meta's rules and get removed).

**Alternatives.** Full automation (left to ONMNE with legal advice later; the connector interface allows adding it). Paid data provider (next step, D6).

## D5 · AI models (2026-10-11)

**Decision.** Hosted models for quality, at zero cost for now: Gemini API free tier and Groq free tier, behind one model gateway, with a local Ollama fallback. Embeddings, redaction and reranking run locally.

**Reason.** Mozart's laptop (RTX 3050 6 GB, 16 GB RAM) runs only 4B to 8B models, which was a main cause of V3's weak verdicts. Gemini's free tier is available in Tunisia. Groq's free tier gives about 1,000 requests a day on 70B-class models.

**Constraint.** Gemini's unpaid terms say inputs may be used to improve Google products and read by human reviewers, and ask users not to submit sensitive or personal information. Therefore only redacted public text is sent to hosted models. The pilot must move to paid no-training tiers or local hosting.

**Consequence.** `AI_MODE=hybrid|local`. Per-task budgets and automatic fallback to local when a quota is exhausted.

## D6 · Spending (2026-10-11)

**Decision.** Free services only for now. Paid options are documented as next steps for the ministry to fund: paid model tiers, social data provider or Apify paid plan, commercial social listening licence, X API, GPU server hosted in Tunisia.

## D7 · Evidence whitelist (2026-10-11)

**Decision.** Keep the whitelist concept, but rebuild it from real documents (WHO, Tunisian government and other authoritative public health bodies) through a dedicated deep research phase. The 10 AI-written files from V3 are moved to `legacy/v3/local_whitelist_UNVERIFIED/` and used only as a checklist of topics to research. They are never indexed as evidence.

**Consequence.** Evidence registry in `corpus/` with issuer, URL, version, date, language, approval state. Corpus v1 covers the demo themes; the deep research phase expands it.

## D8 · Verification accuracy (2026-10-11)

**Decision.** Rebuild the verification pipeline to be accurate and decisive. V3's near-constant "uncertain" is not acceptable.

**Consequence.** Verification engine in `docs/verification-engine.md`: claim decomposition, reuse of reviewed cases and published fact-checks, hybrid cross-lingual retrieval with reranking, scientific backstop search, two independent model judges, citation checks, measured on a test set. "Preuves insuffisantes" remains a possible outcome but must be rare within corpus scope and must name the missing evidence. Proposed targets: at least 90% correct verdicts and under 10% insufficient on in-scope test claims.

## D9 · Interface and storage (2026-10-11)

**Decision.** No Streamlit. Next.js web app, FastAPI backend, PostgreSQL with pgvector replaces JSON and .npy files.

## D10 · Data protection (2026-10-11)

**Decision.** Prepare the INPDP step in phase 1, not at the end: data protection impact assessment and INPDP declaration drafted during the build (`docs/privacy/`).

**Context.** Organic Law 2004-63 is in force. Draft law PLO 095/2025 (in committee at the ARP as of research date) would require a DPO for public bodies and impact assessments for automated decisions.

## D11 · Deferred (2026-10-11)

**Decision.** Not built for the demo: One Health module, requests to ONMNE, EIOS and PHEOC data exchange, speech and OCR. They stay in the pilot plan.

## D12 · Interface design from scratch (2026-10-11)

**Decision.** The team rejected the visual design of V3 and of the blueprint mockups. The features and the information on each screen stay; the visual design is rebuilt from scratch: professional, simple to the eye, carefully crafted.

**Consequence.** `docs/design-brief.md`. A design direction step (Stage 1b) explores three directions as real pages with the `frontend-design` plugin and the taste skills (`Leonxlnx/taste-skill`), the team picks one, and it is codified in design tokens and `docs/DESIGN.md` before the other screens are built. The blueprint mockups are a content reference only.
