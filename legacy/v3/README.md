# OMS Tunisia infodemic demo - web and social upgrade

This version keeps the original **agentic whitelist-grounded pipeline** and adds a second layer for **real web/social discovery**.

## What changed from the first version

The first version already did two live things:
- it fetched RSS/news items,
- it crawled official whitelist pages from the web before embedding them.

What it **did not** do yet was a dedicated **topic discovery crawl** from the open web and public social content.

This upgraded version adds that.

## What this upgraded MVP now proves

1. **Discovery crawl** from the open web and public social content.
   - Topic-based news discovery using a news search RSS endpoint + article scraping.
   - Public social discovery using Bluesky's public search API.
2. **Two separate RAG layers**:
   - **Whitelist RAG** = trusted official health sources for factual grounding.
   - **Discovery RAG** = recent crawled web/social items for context and spread monitoring.
3. **Stateful agent workflow**:
   - normalize -> triage -> retrieve whitelist evidence -> retrieve context evidence -> investigate -> quality gate -> draft -> human review
4. **Scalable design**:
   - connectors are separated from the pipeline,
   - discovery items are stored in JSONL,
   - indexes are separated by purpose,
   - later you can swap JSONL+npy for Qdrant/pgvector/Elasticsearch without changing the workflow logic.

## Stack

- Ollama
- Qwen2.5 Instruct
- BGE-M3 embeddings
- LangGraph
- Streamlit
- feedparser
- trafilatura
- requests

## Quick start

### 1) Install Ollama and pull models

```bash
ollama pull qwen2.5:7b-instruct
ollama pull bge-m3:567m-fp16
```

If your laptop is weak:

```bash
ollama pull qwen2.5:1.5b-instruct
```

Then change `.env` accordingly.

### 2) Create a Python environment

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

### 3) Optional but recommended: add Tunisia official documents

Drop official files into `local_whitelist/`:
- Ministry of Health communiques
- vaccination schedules
- WHO Tunisia notes
- official PDF guidance

### 4) Build the whitelist index once

```bash
python run_pipeline.py --claim "test" --rebuild-index
```

Ignore the output; the goal is only to build the official evidence index.

### 5) Launch the UI

```bash
streamlit run app.py
```

## Demo tabs

### 1. Manual claim
Use this for the safest first demo.

### 2. Monitor feeds
Uses predefined RSS/news feeds from `data/monitor_feeds.json`.

### 3. Web + social discovery
This is the new proof-of-feasibility tab.
It will:
- run a topical crawl,
- collect news results,
- collect public Bluesky posts,
- store them locally,
- rebuild a **discovery RAG index**,
- let you analyze one discovered item with the same pipeline.

Suggested query examples:
- `measles vaccine Tunisia`
- `rougeole vaccin Tunisie`
- `حمى طفح جلدي تونس`
- `cholera rumor North Africa`

### 4. Paste URL
Paste any public news/blog/public page URL and analyze it.

### 5. Upload CSV
Use your team's already collected items.

## CLI options

### Analyze a manual claim

```bash
python run_pipeline.py --claim "The MMR vaccine causes autism." --language fr
```

### Run discovery and analyze the first discovered item

```bash
python run_pipeline.py --discover-query "measles vaccine Tunisia" --max-items 6 --language fr
```

Disable one source if needed:

```bash
python run_pipeline.py --discover-query "rougeole Tunisie" --no-bluesky
python run_pipeline.py --discover-query "rougeole Tunisie" --no-news
```

## What the two RAG layers do

### Whitelist RAG
Used for:
- factual checking,
- support/contradiction judgments,
- final public-health messaging.

### Discovery RAG
Used for:
- recent phrasing,
- spread context,
- what people/news posts are currently saying,
- strengthening analyst situational awareness.

Important rule:
**Only the whitelist RAG should be treated as factual ground truth.**
Discovery RAG is context, not truth.

## Tonight's best demo path

1. Rebuild whitelist index.
2. Run one manual rumor example.
3. Go to **Web + social discovery**.
4. Search `rougeole vaccin Tunisie`.
5. Show the collected news + Bluesky items.
6. Analyze one discovered item.
7. Point out that the agent uses:
   - one RAG for official truth,
   - one RAG for current web/social context,
   - one stateful graph for decision flow.

## What this is still not pretending to be

This is still an MVP, not a production SOC stack.
It is **not yet**:
- Facebook/X/TikTok direct ingestion,
- authenticated platform APIs,
- firehose-scale streaming,
- GraphRAG,
- RBAC,
- One Health platform integration,
- evaluation dashboards.

## Next scalable steps after the demo

1. Replace JSONL/numpy storage with Qdrant or pgvector.
2. Add a queue and scheduled crawlers.
3. Add more public connectors.
4. Add analyst labels and feedback loops.
5. Add RAG evaluation later.

## Key files

- `app.py` - Streamlit UI
- `run_pipeline.py` - CLI
- `src/pipeline.py` - LangGraph workflow
- `src/discovery.py` - web/social connectors + discovery RAG
- `src/whitelist.py` - official source ingestion + whitelist RAG
- `src/retrieval.py` - official retrieval
- `data/monitor_feeds.json` - feed monitoring list
- `data/whitelist_urls.json` - official source list
