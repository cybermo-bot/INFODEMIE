# Evidence corpus

`registry.yaml` lists every evidence document: issuer, URL, language, dates, topics, approval state. Raw downloads go to `corpus/raw/` (gitignored). Procedure: `.claude/skills/corpus-builder/SKILL.md`. Rules: `.claude/skills/evidence-grounding/SKILL.md`.

Only documents with `approval: approved` can support a verdict.
