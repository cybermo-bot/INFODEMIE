---
name: corpus-builder
description: Research, verify and register real authoritative documents (WHO, Tunisian Ministry of Health, ONMNE, other public health agencies) into the PNSI evidence corpus for a given health theme. Use for the deep research phase that rebuilds the evidence whitelist, or whenever a verdict comes back "preuves insuffisantes" and a document must be found.
---

# Building the evidence corpus

Decision D7: the whitelist is rebuilt from real documents through deep research. Follow the `evidence-grounding` skill for what counts as evidence. This skill is the procedure.

## For one theme (for example "vaccination ROR", "pénuries de médicaments", "remèdes traditionnels")

1. **List the questions.** Write the 10 to 30 concrete claims or questions people raise on this theme (use collected posts, the topic checklist in `legacy/v3/local_whitelist_UNVERIFIED/` as hints only, and published fact-checks).
2. **Search authoritative sources** for each, in French, Arabic and English:
   - Tunisian: Ministry of Health portal, ONMNE, DSSB, DPM, INSP, Institut Pasteur de Tunis
   - WHO global and WHO EMRO pages (fact sheets, Q&A, position papers, guidelines), including official Arabic and French versions
   - Other agencies where WHO is silent (ECDC, CDC, UNICEF, Africa CDC)
   - Systematic reviews (PubMed, Europe PMC, Cochrane abstracts) for scientific questions
3. **Open and read every document** you register. Confirm it loads, who issued it, its date, and that the relevant passage actually says what you need. If you cannot read it, do not register it; note it as "inaccessible".
4. **Register** each document in `corpus/registry.yaml`:

```yaml
- id: who-measles-factsheet-fr
  issuer: OMS
  title: "<exact title as published>"
  url: "<canonical URL>"
  language: fr
  published: "<date as shown, or null>"
  reviewed_or_updated: "<date as shown, or null>"
  retrieved: "<today, ISO date>"
  topics: [vaccination, rougeole]
  doc_type: fact_sheet   # fact_sheet | qa | guideline | position_paper | circular | report | systematic_review
  reuse_note: "<licence or terms note>"
  approval: pending      # pending | approved | suspended
  answers: ["<question ids from step 1>"]
```

5. **Fetch and index** with the corpus ingestion command; spot-check extracted text against the original for 3 passages per document.
6. **Coverage table.** For the theme, list each question and the documents that answer it. Questions without an answer are listed as gaps, not filled with guesses.
7. **Report** to Mozart: documents added, gaps, documents found but inaccessible.

## Never

- Never register a URL you have not opened.
- Never type a title, date or figure from memory; copy it from the page.
- Never treat a news article, blog, forum or AI-generated text as evidence.
