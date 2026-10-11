---
name: evidence-grounding
description: Rules for building the PNSI evidence corpus and for producing verdicts and responses grounded in it. Use when adding documents to the evidence registry, writing retrieval or verification code, writing prompts that judge health claims, building the evaluation test set, or drafting public responses.
---

# Evidence grounding

The platform will be shown to the Minister of Health. A wrong confident verdict, or a citation that does not say what we claim, is the worst possible failure. These rules apply everywhere.

## The corpus

1. Only real documents, fetched from their real URL or supplied by the institution, enter the corpus. Store: issuer, title, canonical URL, language, publication date, effective or review date if stated, retrieval date, checksum, licence or reuse note, topic, approval state.
2. Priority order of issuers for the demo themes:
   - Tunisian official sources (Ministry of Health, ONMNE, DSSB, DPM, INSP, Institut Pasteur de Tunis) when the documents are publicly available or supplied
   - WHO (fact sheets, Q&A pages, position papers, guidelines, EMRO pages), including Arabic and French versions where they exist
   - Other recognised public health agencies (for example ECDC, CDC, UNICEF, Africa CDC) for topics where WHO is silent
   - Systematic reviews and guidelines found through PubMed or Europe PMC, after review
3. News articles and social posts are monitored content, never evidence.
4. The AI-written files in `legacy/v3/local_whitelist_UNVERIFIED/` are a topic checklist only. Never index them, never quote them, never copy a figure from them without finding it in a real document.
5. When a document is in several languages, store each language version as its own document version linked to the same work.
6. Record what you could not access (paywall, broken link, no text). Never paraphrase a document you have not actually read.

## Verdicts

- A verdict is valid only if every cited passage ID exists in the corpus and supports the sentence that cites it.
- Use the verdict scale in `docs/verification-engine.md`. "Rumeur" describes circulation, not falsehood. Criticism of institutions is not misinformation.
- Do not infer intent ("désinformation") from text alone; use "information fausse ou trompeuse" unless intent is documented.
- Model outputs are proposals until a reviewer confirms them. Store which models produced them and with which prompt version.

## Responses

- Start from the reviewed verdict and the approved passages only.
- Structure: accurate information first in simple words, acknowledge the concern, what the evidence says and its limits, a practical next step, references with the checked date.
- Avoid repeating the false claim in headlines. No personal medical advice. No invented official attribution: never write "le Ministère affirme" unless an approved ministry document says it.
- A "preuves insuffisantes" or "contesté" verdict can only produce an information message that says what is known and unknown, never a correction.

## Test set (`eval/`)

- Every test claim comes from a real, citable source: a WHO myth-busting page, a published fact-check (Nawaat, AFP Factuel or AFP Arabic, Misbar, others), or a documented rumour. Record that source.
- Every expected verdict cites the real document that justifies it.
- Never invent a claim and its answer to pad the set.
