---
name: model-benchmark
description: Benchmark candidate language models and embedding models for PNSI tasks (triage, emotions, stance, claim extraction, verification, Derja understanding, retrieval) on the project's labelled test sets, and write a comparison report. Use when choosing or changing a model, a prompt, or the model routing config.
---

# Model benchmark

Model choices are made from measurements on our own Tunisian data, not from reputation.

## Candidates

- Hosted free tiers: Gemini Flash models (Google AI Studio), Groq's large free models. Read current model IDs and limits from the provider consoles.
- Local on Ollama (fits a 6 GB GPU): a 4B-class general model (for example `qwen3:4b`); optionally an 8B model on CPU and GPU split, which is slow.
- Local candidates to note for the pilot server: Jais 2 family, ESPRIT-Derja-Qwen3-8B (Derja-tuned, conversational, not tuned for facts), larger Qwen models.
- Embeddings: BGE-M3 (default) versus a dialect-aware Arabic embedding model such as Swan, if it can run locally.

## Data

- `eval/claims_v1.jsonl` for verification (see `evidence-grounding` skill)
- `eval/triage_v1.jsonl` for route, taxonomy, emotions and stance: real redacted posts collected by PNSI, labelled by Mozart or a reviewer, never invented. Balance Derja Arabic script, Arabizi, French and mixed.
- Keep a frozen test split; never tune prompts on it.

## Procedure

1. Run each candidate with the same prompt version and the same inputs. Record model ID, provider, date, prompt version.
2. Metrics: accuracy and macro-F1 per task; for verification also insufficient rate, judge agreement and citation failures; per language and script; latency and quota cost per 100 items.
3. Inspect failures by hand, especially negation, questions and reported speech in Derja and Arabizi.
4. Write `eval/reports/benchmark-<date>.md` with a table, the failures that matter, and a recommendation for the routing config with reasons.
5. Update the routing config only after Mozart agrees, and log the change in `docs/decisions.md`.
