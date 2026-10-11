---
name: derja-handling
description: Rules for processing, storing, searching, translating and displaying Tunisian Derja (Arabic script and Arabizi), Modern Standard Arabic, French and mixed-language text in PNSI. Use whenever code touches text normalisation, language detection, search expansion, translation, RTL display, or generates Arabic or Derja content.
---

# Handling Tunisian Derja, Arabizi and mixed text

Tunisian social media mixes Derja written in Arabic script, Derja written in Latin letters with digits (Arabizi, also called Tunizi), Modern Standard Arabic (MSA), French and some English, often inside one sentence. Getting this wrong in front of the minister is a visible failure. Follow these rules.

## Storage

1. Store the original text exactly as received (after redaction of personal identifiers only). Never overwrite it with a normalised, transliterated or translated version.
2. Every derived form (normalised Arabic, Arabizi-to-Arabic transliteration, translation) is a separate field or table row with the method and model version that produced it.
3. Store language per span, not per item: a list of `{start, end, lang, script}` where `lang` is one of `aeb` (Tunisian Arabic), `ar` (MSA), `fr`, `en`, `it`, `und`, and `script` is `arab` or `latn`. Unknown is allowed.

## Detection

- Reuse the markers from `legacy/v3/src/arabic_nlp.py` (Latin markers such as `mta3`, `besh`, `barcha`, `yasser`; Arabic markers such as كيفاش، ياسر، برشة، باش) as features, combined with a classifier or model call.
- Arabizi signals: Latin words containing digits used as letters (3, 5, 7, 9, sometimes 2, 8), and Derja function words in Latin letters.
- Do not infer that a writer lives in Tunisia from dialect alone.

## Normalisation (for search only)

- Arabic search column: remove tatweel and diacritics, unify alef forms (أ إ آ → ا), ya and alef maqsura (ى → ي), ta marbuta (ة → ه) in a derived column used for matching. Keep the display text untouched.
- Arabizi: digit mappings are contextual (3 = ع, 7 = ح, 9 = ق, 5 = خ, 2 = ء, 8 = غ in common Tunisian use, but not always). Generate several candidate Arabic-script forms for query expansion; never apply one destructive replacement.
- Keep negation words, emojis, numbers and units: they change meaning ("ما يعملش" negates; "ma3andich" means "I don't have").

## Search

- Expand a query into French, MSA, Derja Arabic script and Arabizi variants, and search all of them.
- Rely on BGE-M3 embeddings for cross-lingual matching, and keyword search for exact terms (product names, place names).

## Translation and display

- Show the original first, translation beside or below it, labelled "Traduction automatique" until a person has reviewed it.
- Arabic and Arabic-script Derja are displayed right-to-left; Arabizi stays left-to-right even inside an Arabic page. Wrap mixed or embedded runs with `dir="auto"` or `<bdi>` so IDs, numbers and Latin words do not scramble.
- Fonts: IBM Plex Sans Arabic for Arabic, IBM Plex Sans for Latin.

## Generating Derja or Arabic content

- Drafts in Derja are always labelled "Brouillon IA, revue linguistique requise" until a native reviewer approves them.
- Keep medical terms precise. When unsure of the Derja term for a medical concept, use the MSA term and add the French term in parentheses, then flag it for review.
- Never put Derja in the interface strings (menus, buttons) unless a native speaker has reviewed them; the interface uses French, MSA and English.

## Tests to keep

- Round trip: original text is identical after ingestion, redaction aside.
- Mixed sentence with Arabic, Arabizi and French renders in the correct order in an RTL page.
- A Derja negation is preserved through claim extraction ("ما يسببش" must not become "causes").
