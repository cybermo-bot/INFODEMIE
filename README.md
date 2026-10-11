# PNSI

Plateforme Nationale de Social Listening Sanitaire et de Gestion de l'Infodémie, built for ONMNE and the Tunisian Ministry of Health.

PNSI collects public health conversation from Tunisian media and social platforms, reads each signal twice (as an information risk and as a possible health event), checks claims against real evidence, drafts responses for human approval, records the actions taken and measures what changed afterwards.

## Status

Starter pack: documentation, decisions, build plan and project skills. Code starts at Stage 1 (`docs/build-plan.md`).

## Where to start

| You want to | Read |
| --- | --- |
| Set up your machine | `docs/setup-windows.md` |
| Understand the product | `docs/blueprint.html` (open in a browser) |
| Know what is decided | `docs/decisions.md` |
| Know what to build next | `docs/build-plan.md` |
| Work with Claude Code | `CLAUDE.md` and `.claude/skills/` |
| Read the client's requirements | `docs/client/` |
| Read the full engineering spec | `docs/spec/` |

## Repository layout

```
apps/            api, web, capture extension (from Stage 1)
packages/        generated API client
infra/           docker compose
corpus/          evidence registry
eval/            test sets and evaluation reports
docs/            all project documentation
legacy/v3/       previous prototype, reference only
.claude/skills/  project skills for Claude Code
```

## Commands

Added in Stage 1. See `CLAUDE.md`.
