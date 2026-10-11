---
name: demo-readiness
description: Pre-presentation audit of PNSI before showing it to ONMNE, the ministry or the minister. Use when Mozart asks whether the build is ready to show, before a rehearsal, or before any external demo.
disable-model-invocation: true
---

# Demo readiness check

Run every check, then write `docs/readiness.md` with three lists: blockers, warnings, and what works. A single blocker means not ready.

## Truthfulness (blockers)

- [ ] No evidence passage comes from `legacy/v3/local_whitelist_UNVERIFIED/` or any AI-written file (query the passages table by source)
- [ ] Every verdict shown in the demo path cites passages that resolve to approved documents with real URLs; open each URL and confirm it loads
- [ ] Every scenario record has `is_scenario = true` and the UI shows "Scénario de démonstration" wherever it appears
- [ ] No number on Vue Cabinet, Salle de veille or reports is hard-coded; trace each KPI to its query
- [ ] The Sources screen shows the real status of every connector; failing or unconfigured ones are visible as such
- [ ] No claim in the interface, the deck or the speaker notes that the build does not actually do

## Privacy (blockers)

- [ ] Search the database for handles (`@`), phone patterns, emails and individual profile URLs: zero hits
- [ ] Exports and PDFs contain no personal identifiers
- [ ] Only redacted text was sent to hosted models (check the gateway's redaction flag enforcement test)

## Workflow invariants (blockers)

- [ ] Run the invariant API tests: stale approval rejected, edit invalidates approval, insufficient verdict cannot create a correction, follow-ups created once, cross-institution access denied

## Robustness (warnings)

- [ ] Offline switch tested: network off, local model takes over, recorded collection replays
- [ ] Free-tier quotas: enough remaining for the demo day; analysis pre-computed
- [ ] Laptop: disk space above 10 GB free, charger, display output tested, browser zoom and fonts checked on the projector resolution

## Language and accessibility (warnings)

- [ ] Every Arabic and Derja string on the demo path reviewed by a native speaker
- [ ] RTL layout checked on every demo screen; mixed Arabizi and numbers render in order
- [ ] Keyboard navigation and visible focus on the demo path; contrast of risk colours

## Rehearsal

- [ ] The 7-minute script (blueprint §14) run twice end to end under 8 minutes without errors
- [ ] A one-sentence answer ready for: data sources and their legality, privacy, cost, hosting, what is not done yet
