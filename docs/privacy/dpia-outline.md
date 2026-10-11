# Data protection impact assessment and INPDP file (outline)

Decision D10: prepare this in phase 1. This is a working outline to be filled during the build and reviewed by ONMNE's legal and data protection contacts. It is not legal advice and does not certify compliance.

## Legal frame to confirm with ONMNE and the INPDP

- Organic Law 2004-63 on the protection of personal data is the law in force. It requires a prior declaration to the INPDP for processing of personal data and stricter conditions (authorisation) for certain categories, including health data. Confirm the exact obligations and forms with the INPDP or a lawyer.
- Draft law PLO 095/2025 (in committee at the ARP at the time of research) would replace it: mandatory DPO for public bodies, impact assessments for high-risk and automated processing, prior authorisation maintained for high-risk processing. Track its status.
- WHO guidance on ethical considerations for social listening in infodemic management is the reference framework for practice.

## 1. Description of the processing

- Controller: ONMNE / Ministry of Health (to confirm). Processor during the demo phase: the project team.
- Purpose: public health monitoring of public online conversation to detect rumours, questions and concerns, support risk communication, and detect early signals of health events.
- Not purposes: identifying, profiling or targeting individuals; inferring anyone's health status; sanctions.

## 2. Data

- Public posts, comments and articles from the sources in `docs/sources-plan.md`, plus messages voluntarily forwarded to the tipline and field reports.
- Personal identifiers removed at collection: names and handles of individuals, phone numbers, emails, profile links. Organisation pages kept.
- Residual risk: health-related speech can reveal information about a person even without a name (for example a quoted symptom with a place). Mitigation: aggregation in reports, short retention of item-level text, access control, no export of item-level text by default.

## 3. Necessity and proportionality

- Minimal fields per source (spec §7); text-first; audiovisual only when needed.
- Retention (proposed, to validate): raw buffers 24 h; redacted items 90 days; aggregates and case records according to institutional policy; deletion propagated to indexes and embeddings.

## 4. Recipients and transfers

- Internal roles only (see blueprint §8), scoped by institution.
- Hosted AI providers during the demo phase receive redacted public text only (decision D5). Their free-tier terms allow use of inputs to improve services. For the pilot: paid no-training tiers under a data processing agreement, or local models hosted in Tunisia. Record this as a transfer to assess.

## 5. Security

- Encryption in transit and at rest, least privilege, audit log of access and exports, MFA for privileged roles, backups with tested restore (spec §24 and §29).

## 6. Rights and transparency

- Public notice describing the monitoring (to draft with ONMNE communication).
- Process to handle deletion requests for items that could still identify someone.
- Tipline: short notice to users explaining what happens to forwarded messages.

## 7. Risks and measures (to complete)

| Risk | Likelihood | Severity | Measure |
| --- | --- | --- | --- |
| Re-identification from quoted text | | | Redaction, aggregation, retention, access control |
| Misuse to target critics of institutions | | | Purpose limitation, no individual profiles, audit, criticism route not treated as misinformation |
| Wrong verdict harming trust | | | Human review, citations, evaluation |
| Data sent to providers outside Tunisia | | | Redaction, paid or local for pilot |

## 8. Next steps

- Share this outline with ONMNE, name the DPO or data protection contact, prepare the INPDP declaration form, schedule a review before the pilot.
