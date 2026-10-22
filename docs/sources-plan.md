# Sources plan

Goal (decision D3): as many sources as possible, each through a route we can defend, each labelled with its route in the data and in the interface.

Routes:

- `official`: documented API or feed offered by the publisher or platform
- `assisted`: a person browses normally, a tool records what is on screen at their click
- `public_contested`: public content collected outside an official API (legal position disputed by the platform)
- `internal`: submitted by the institution's own people (field relays, media cell, tipline)

Everything below must be verified when implemented: endpoints, quotas and terms change. Record the check date in the source registry.

---

## 1. Connector specifications

### Tunisian online media · `official`

- Method: RSS feeds and XML sitemaps where offered; article text extracted with trafilatura (already used in V3); public article comments only where the site exposes them in the page.
- Schedule: every 30 minutes for news sites.
- Relevance: health filter (keywords plus classifier) before storage of full text.
- Candidate sites to verify one by one (homepage given; find the feed or sitemap, test yield, record in the registry). Do not assume a feed exists until fetched.
  - Radios: Mosaïque FM (mosaiquefm.net), Shems FM (shemsfm.net), Jawhara FM (jawharafm.net), Diwan FM (diwanfm.net), Express FM (radioexpressfm.com), IFM (ifm.tn)
  - Agencies and dailies: TAP (tap.info.tn), La Presse (lapresse.tn), Assabah News (assabahnews.tn), Al Chourouk (alchourouk.com)
  - News portals: Business News (businessnews.com.tn), Kapitalis (kapitalis.com), Webdo (webdo.tn), Tuniscope (tuniscope.com), Tunisie Numérique (tunisienumerique.com), Leaders (leaders.com.tn), Réalités (realites.com.tn), Espace Manager (espacemanager.com), African Manager (africanmanager.com), Managers (managers.tn), Gnet (gnet.tn), L'Économiste Maghrébin (leconomistemaghrebin.com), Babnet (babnet.net), Akher Khabar Online (akherkhabaronline.com), Hakaek Online (hakaekonline.com), Assarih (assarih.com)
  - Investigative and fact-checking: Nawaat (nawaat.org), Inkyfada (inkyfada.com)
  - Institutions (monitored for official statements, not as evidence by default): ONMNE (onmne.tn), Ministry of Health portal (santetunisie.rns.tn), DPM (dpm.tn)

### Google News RSS · `official` (kept from V3)

- Topic queries in French and Arabic with `gl=TN`, `hl=fr` and `hl=ar`. Reuse the V3 query builder (`legacy/v3/src/discovery.py`).
- Store the publisher and the original article URL; fetch the article text through the media connector logic.

### GDELT DOC 2.0 API · `official`

- Free, no key. Article list mode with query terms, Tunisian source country filter and source language filter (French, Arabic). Check the current parameter names in the GDELT documentation before coding.
- Returns article metadata and URLs; text extraction through the media connector.

### DuckDuckGo news · `public_contested` (kept from V3)

- `ddgs` Python package (successor of `duckduckgo-search`). Discovery helper only, low frequency, results deduplicated against other news sources.

### YouTube Data API v3 · `official`

- Default quota 10,000 units per day. `search.list` costs 100 units, `videos.list` and `commentThreads.list` cost 1 unit each. Budget searches carefully: favour polling known channels (Tunisian media, health channels) through their uploads playlist, then comment threads.
- Store video title, description, channel (organisation-level), published date, view and comment counts, comments (redacted).

### Facebook

| Route | Implementation | Status |
| --- | --- | --- |
| A · Graph API on managed Pages (`official`) | Page access token for Pages administered by the ministry, ONMNE or a regional directorate; read posts and all comments | Ready to activate when a token is provided (deferred request to ONMNE) |
| B · Page Public Content Access (`official`) | Meta App Review for reading public content of Pages we do not manage | Apply after the Meta app exists; takes weeks |
| C · Monitoring accounts + PNSI Capture (`assisted`) | Real, identifiable accounts operated by analysts; the extension records the post and loaded comments on click, redacted in the browser | Build in stage 3 |
| D · Logged-out watch-list (`public_contested`) | Apify actors for public Pages (posts and comments) and public groups (posts only, decision D18) within the free credit, or our own logged-out collector; polite rate, small curated list in `docs/sources/facebook-watchlist.yaml` | Built (D17, D18) |
| E · Unattended logged-in bots | Not built (decision D4) | No |

### Instagram

- C · PNSI Capture on instagram.com (`assisted`)
- D · Apify actors for public profiles and hashtags (`public_contested`)
- Later · Graph API hashtag search with an Instagram business account (limit of 30 unique hashtags per rolling 7 days, requires App Review)

### TikTok

- C · PNSI Capture on tiktok.com (`assisted`)
- Official oEmbed endpoint to enrich captured video URLs with title and author (organisation accounts only kept by name)
- D · Apify actors for hashtags and selected accounts (`public_contested`)
- Not available: TikTok Research API (excludes commercial and operational users)
- Later: audio transcription of permitted videos (LinTO Tunisian ASR vs Whisper)

### Telegram

- Public channels (`official`): Telethon client with a dedicated account (api_id and api_hash from my.telegram.org). Fallback: the public web preview `https://t.me/s/<channel>` for open channels.
- Tipline (`internal`): a PNSI bot (BotFather token). Relays, health workers and citizens forward rumours they receive, including WhatsApp forwards copied in. The bot answers with a short acknowledgement and never gives medical advice.

### Bluesky · `official` (kept from V3)

- Public AppView search endpoint. Low volume in Tunisia; keep for completeness.

### Reddit · `official`, pending approval (kept from V3)

- Apply for Data API access under Reddit's Responsible Builder Policy. Connector built but disabled until approved. Target communities: r/Tunisia and related.

### Health event feeds · `official` (replaces ProMED)

- WHO Disease Outbreak News, WHO EMRO news, Africa CDC and ECDC publications. Used for the Signaux sanitaires context, not as social conversation.

### Existing fact-checks · `official`

- Google Fact Check Tools API, `claims:search`, with a Google API key. Used by the verification engine to reuse published fact-checks (Nawaat, AFP, Misbar and others publishing ClaimReview).

### Search interest · `public_contested`

- Google Trends for health terms in Tunisia (unofficial client). Daily, aggregated; an early signal of worry, never shown as conversation volume.

### Internal intake · `internal`

- Remontée terrain form (mobile, offline), media cell manual capture, CSV import with validation preview.

### X · later

- Pay-per-use API. Reach in Tunisia is small (about 356K ad reach, DataReportal late 2025). Not in the demo.

---

## 2. Proposed watch-list (to verify in stage 3)

Categories first; each page is checked by hand (exists, public, active, Tunisian, relevant) before it enters the database. Names below are starting points to search for, not verified URLs.

1. National media with large audiences: Mosaïque FM, Shems FM, Jawhara FM, Diwan FM, Express FM, IFM, Nessma, Attessia, El Hiwar Ettounsi, Watania, Business News, Tunisie Numérique.
2. Health institutions (their comment sections show public reaction): Ministère de la Santé, ONMNE, regional health directorates, Institut Pasteur de Tunis, INSP, DPM, CNAM.
3. Health professionals: Conseil national de l'Ordre des médecins, Ordre des pharmaciens, medical societies (paediatrics, infectious diseases), well-known doctors who publish health advice publicly as professionals.
4. Community and parenting pages with public posts about health.
5. Pages promoting traditional or alternative remedies (where false cures circulate), found by searching Derja and Arabic terms in section 3.

TikTok and Instagram: the same categories plus hashtags from section 3.

---

## 3. Seed query terms (draft, must be reviewed by a native Derja speaker)

Organised by demo theme. Arabizi spellings vary; the query builder expands variants (for example 3/a, 7/h, 9/q) without altering stored text.

- Vaccination: vaccin, vaccination, ROR, rougeole; تلقيح، لقاح، الحصبة؛ Arabizi: tal9i7, le9a7, 7asba
- Medicines and shortages: médicament, pénurie, rupture, insuline; دواء، فقدان الأدوية، الأنسولين؛ Arabizi: dwe, mafamech dwe
- Alternative remedies: remède naturel, guérit; طب عربي، أعشاب، دواء طبيعي؛ Arabizi: tib 3arbi
- Infectious disease: épidémie, grippe, fièvre, éruption; وباء، أنفلونزا، سخانة، حبوب؛ Arabizi: s5ana, grippe
- Heat and environment: canicule, chaleur, eau potable; موجة حر، الماء الصالح للشرب

Every query has an ID and version; changes are logged so a volume jump caused by a new keyword is not read as a surge.
