# Design brief

Decision D12: the team rejected the visual design of the V3 interface and of the blueprint mockups. The features and the information on each screen stay. The look and feel is designed from scratch.

## What to keep from the blueprint mockups

- The list of screens and what each one is for (blueprint §9): Vue Cabinet, Salle de veille, Signaux, Dossier, Studio de réponse, Actions et impact, Remontée terrain, Sources, Bibliothèque de preuves, Rapports, Administration.
- The information each screen must show: for example, on a case, the neutral claim wording, verdict with who validated it, priority and its completeness, mentions in original language with translation and stance, evidence passages, history.
- The trust signals: route of every item, coverage and source health beside numbers, "Scénario de démonstration" labels, machine proposal versus reviewed decision.

## What to discard

- Every visual choice in the mockups and in V3: the navy sidebar, the pills on everything, cards around every block, monospace uppercase labels, the browser-frame look, the colour scheme and the fonts. None of it is a constraint.

## The target

Professional, calm and simple to the eye, with a high level of craft. It is a government decision tool: analysts use it all day, and the minister glances at it for one minute. It should feel trustworthy and quiet, and every detail should look deliberate.

Principles:

1. **Hierarchy first.** On each screen, one thing matters most and it is obvious within two seconds. Everything else recedes.
2. **Typography carries the design.** A strong type scale, few weights, generous line height. Decoration is rare.
3. **One accent colour.** Status colours (risk, success, warning) are separate from the accent and used sparingly, always with a word or icon, never colour alone.
4. **Space over borders.** Group with spacing and alignment before reaching for boxes and lines.
5. **Two densities.** The Vue Cabinet is sparse and large (readable on a projector from the back of a room). Analyst screens are denser but still calm.
6. **Arabic is a first-class language.** Design the Arabic version of each key screen at the same time as the French one, not by mirroring afterwards. Choose a type pairing where the Arabic and Latin faces were designed to work together.
7. **Honest data display.** Charts start at zero where it matters, show coverage gaps, and never imply precision the data does not have. No decorative maps, no 3D, no fake live tickers.
8. **Motion is functional.** Short transitions for state changes only.

Constraints:

- WCAG 2.2 AA: contrast, keyboard navigation, visible focus, text alternatives for charts.
- Projector legibility for the demo: test at 1280×720 and at 1920×1080, body text never below 14 px on the cabinet view.
- Light theme is the primary theme. Dark theme optional.
- Built with Tailwind and shadcn/ui components, restyled through design tokens, so the look is consistent and easy to change.

## Process (Stage 1b in `docs/build-plan.md`)

1. Install the design skills: the `frontend-design` plugin, and the taste skills from `Leonxlnx/taste-skill` (at least `design-taste-frontend`, and `minimalist-ui` which fits "simple to the eye"). Your claude.ai design plugins (`design-skills`, `design-superpowers`) sync in as well.
2. Build **three clearly different visual directions** as real Next.js pages, each rendering the same two screens (Vue Cabinet and Dossier) with the same realistic content, in French and in Arabic.
3. Mozart and the team choose one direction, or combine parts of them. Record the choice and why in `docs/decisions.md`.
4. Codify the chosen direction: design tokens (colour, type scale, spacing, radius, shadows), themed shadcn components, chart styling, and a `docs/DESIGN.md` describing the system with examples.
5. Build every screen on that system. Run a design critique and an accessibility audit at the end of stages 5 and 6, and fix what they find.

Quality qualities to study (not to copy): the restraint and typography of Linear and Stripe's dashboard, the clarity of the GOV.UK Design System, the honest charts of Our World in Data.
