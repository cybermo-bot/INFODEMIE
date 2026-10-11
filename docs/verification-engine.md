# Verification engine

Decision D8: verdicts must be accurate and decisive. V3 returned "uncertain" on almost everything. Causes found in the V3 code and runs:

1. The evidence base was 10 short AI-written notes plus 10 web pages, 165 chunks in total.
2. A 7B local model (Qwen2.5 7B) did both judging and drafting.
3. One query per claim, built from the triage summary, top 6 chunks by cosine similarity only, no keyword search, no reranking, no cross-lingual expansion.
4. No claim decomposition: a post with three assertions was judged as one blob.
5. The quality gate retried once with the same query, which returned the same chunks.

The engine below fixes each cause.

## Pipeline

### 1. Decompose

Input: a redacted item (or a case's representative mentions).
Output (typed JSON): list of atomic claims, each with
- `text_original` (span in the original language), `text_neutral_fr` (neutral French restatement), `text_search_en` (English retrieval form), `text_search_ar` (MSA retrieval form)
- `stance`: assert, question, report (quoting someone else), sarcasm, unclear
- `polarity` and negation preserved; `quantity`, `population`, `time` when present
- `checkable`: true or false (opinions, criticism and pure questions are not checkable claims)

Questions and reports are kept: they feed the question clusters and the case, but they are not judged as the author's assertion.

### 2. Reuse

Before any new search:
- Match the neutral claim against claims already in reviewed cases (embedding similarity plus a model check that the two claims are equivalent, not merely on the same topic: "can cause" is not "always causes").
- Query the Google Fact Check Tools API with the French, English and Arabic retrieval forms. A published fact-check is shown as context with its publisher, date and rating. It is not evidence by itself; the engine still retrieves corpus passages, but the fact-check's own cited sources are good candidates to add to the corpus.

### 3. Retrieve

Hybrid search over approved passages only:
- PostgreSQL full text search (French and simple configurations; Arabic normalised for alef, ya, ta marbuta and diacritics in a derived column)
- pgvector similarity on BGE-M3 embeddings (multilingual, so a Derja or Arabic claim finds French or English passages)
- Run for each retrieval form (FR, EN, AR); merge with reciprocal rank fusion
- Rerank the top 50 with a local multilingual cross-encoder; keep the top 8 to 12
- Ask explicitly for contradicting evidence too: a second query built from the negated claim

### 4. Backstop

If fewer than 2 relevant passages survive reranking:
- Search PubMed (NCBI E-utilities) and Europe PMC for systematic reviews and guidelines on the claim
- Results are shown as "Découverte, non approuvée" with title, journal, year and link. They do not produce a verdict on their own. One click proposes the document to the corpus registry for review.

### 5. Judge twice

Two different models assess independently (default: Gemini and Groq's strongest free model), each given only the claim and the retrieved passages with their IDs. Each returns:

```json
{
  "verdict": "contredit | trompeur | confirme | conteste | preuves_insuffisantes | pas_une_allegation",
  "rationale": "short, in French",
  "supporting_passage_ids": [],
  "contradicting_passage_ids": [],
  "context_missing": "what the claim leaves out, if trompeur",
  "missing_evidence": "what document would settle it, if preuves_insuffisantes"
}
```

- Both agree: proposed verdict, badge "2 modèles concordants".
- They disagree: verdict "À arbitrer", both rationales shown to the reviewer.
- Proposed verdicts are machine proposals until a reviewer confirms them.

### 6. Check citations

For every sentence of the rationale that cites a passage:
- The passage ID must exist and belong to an approved document version.
- A natural language inference check (model call with a strict yes or no schema) confirms the passage supports that sentence.
- Any failure: discard that judge's output and rerun once with the failure noted; if it fails again, mark "Vérification à reprendre" for the analyst.

### 7. Close the gap

When the outcome is "preuves_insuffisantes", the engine stores `missing_evidence` and proposes candidate documents (from the backstop search and from fact-check sources). When a new document is approved in the corpus, cases waiting on that topic are re-verified automatically.

## Verdict rules

- A correction draft can only be created from a reviewed "contredit" or "trompeur" verdict.
- "Preuves insuffisantes" and "contesté" produce an information or uncertainty-aware message at most, never a correction.
- Health signals (route 1) are never judged true or false by the engine; they go to surveillance.

## Evaluation

- `eval/claims_v1.jsonl`: about 150 claims, each with `claim`, `language`, `script`, `expected_verdict`, `evidence_urls` (real, public, citable), `source_of_claim` (WHO myth page, published fact-check, documented Tunisian rumour), `in_corpus_scope` (true or false).
- Built only from real sources. Never invent a claim and its answer; if a claim is a paraphrase, record the original it paraphrases.
- Include Derja (Arabic script), Arabizi, French, English and mixed-language versions of the same claims, plus questions and reported speech to test stance handling.
- `make eval` reports: accuracy on in-scope claims, insufficient rate on in-scope claims, judge agreement rate, citation failure rate, results per language and script, and the list of failures with rationale.
- Proposed targets (to confirm after the first run): at least 90% correct on in-scope claims, insufficient below 10% on in-scope claims.
