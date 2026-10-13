# PNSI — Plateforme Nationale de Surveillance de l'Infodémie
### Sovereign Health Intelligence, Evidence Verification & Response Workspace

[![Status: Functional Local & Demo](https://img.shields.io/badge/Status-Functional_Local_%26_Demo-blue.svg)](docs/readiness.md)
[![Python: 3.12](https://img.shields.io/badge/Python-3.12-brightgreen.svg)](https://www.python.org/)
[![Node.js: 22+](https://img.shields.io/badge/Node.js-22%2B-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js 16](https://img.shields.io/badge/Frontend-Next.js_16_App_Router-black.svg)](https://nextjs.org/)
[![Multi-lingual](https://img.shields.io/badge/Languages-FR_|_EN_|_AR_(RTL)_|_Derja-orange.svg)](apps/web/app/i18n.ts)

---

## 📑 Table of Contents

- [1. Executive Summary & Vision (Non-Technical)](#1-executive-summary--vision-non-technical)
  - [What is PNSI?](#what-is-pnsi)
  - [The Infodemic Challenge](#the-infodemic-challenge)
  - [Core Principles & Ethics](#core-principles--ethics)
  - [User Personas & Role Matrix](#user-personas--role-matrix)
- [2. End-to-End Operational Lifecycle (SOPs)](#2-end-to-end-operational-lifecycle-sops)
  - [Stage 1: Multi-Source Signal Collection & Ingestion](#stage-1-multi-source-signal-collection--ingestion)
  - [Stage 2: Case Formulation & Harm Triage](#stage-2-case-formulation--harm-triage)
  - [Stage 3: Evidence Retrieval & Scientific Assessment](#stage-3-evidence-retrieval--scientific-assessment)
  - [Stage 4: Response Studio & Staged Approvals](#stage-4-response-studio--staged-approvals)
  - [Stage 5: Action Execution & 3-Window Impact Tracking](#stage-5-action-execution--3-window-impact-tracking)
  - [Stage 6: Audited Executive Briefings & Reports](#stage-6-audited-executive-briefings--reports)
- [3. System Architecture & Technical Stack](#3-system-architecture--technical-stack)
  - [Architecture Diagram](#architecture-diagram)
  - [Frontend Architecture (`apps/web`)](#frontend-architecture-appsweb)
  - [Backend API Architecture (`apps/api`)](#backend-api-architecture-appsapi)
  - [Durable Asynchronous Worker (`workers/run.py`)](#durable-asynchronous-worker-workersrunpy)
  - [Background Monitoring Daemon (`apps/api/automatic_tracking.py`)](#background-monitoring-daemon-appsapiautomatic_trackingpy)
  - [Connectors & External Integrations](#connectors--external-integrations)
  - [Database & Storage Engine](#database--storage-engine)
- [4. Operational Environments](#4-operational-environments)
  - [Mode A: Synthetic Demonstration Environment (`demo`)](#mode-a-synthetic-demonstration-environment-demo)
  - [Mode B: Sovereign Local Workspace (`local`)](#mode-b-sovereign-local-workspace-local)
- [5. Functional Modules & Workspace Pages](#5-functional-modules--workspace-pages)
- [6. Security, Compliance & Governance Boundary](#6-security-compliance--governance-boundary)
- [7. Getting Started & Installation](#7-getting-started--installation)
  - [System Requirements](#system-requirements)
  - [Initial Dependency Installation](#initial-dependency-installation)
  - [Launching the Environments](#launching-the-environments)
  - [Local Setup & First Account Creation](#local-setup--first-account-creation)
- [8. Configuration Matrix](#8-configuration-matrix)
  - [Environment Variables (`.env`)](#environment-variables-env)
  - [Social Media Credentials Configuration](#social-media-credentials-configuration)
- [9. Testing, Verification & Quality Assurance](#9-testing-verification--quality-assurance)
- [10. Data Backup, Integrity & Recovery Procedures](#10-data-backup-integrity--recovery-procedures)
- [11. API Specification & Endpoints](#11-api-specification--endpoints)
- [12. Readiness, Audit Status & Production Release Gates](#12-readiness-audit-status--production-release-gates)
- [13. Repository Directory Structure](#13-repository-directory-structure)

---

## 1. Executive Summary & Vision (Non-Technical)

### What is PNSI?
**PNSI** (*Plateforme Nationale de Surveillance de l'Infodémie* / National Infodemic Surveillance Platform) is a specialized, sovereign public health intelligence workspace. Developed in alignment with comprehensive national health surveillance specifications (such as those outlined by Tunisia's **ONMNE** — *Observatoire National des Maladies Nouvelles et Émergentes*, the Ministry of Health, and international public health partners), PNSI equips public health teams to monitor, assess, counteract, and evaluate circulating health rumors, misconceptions, and disinformation.

### The Infodemic Challenge
During disease outbreaks, vaccination campaigns, and public health alerts, an "infodemic" — an overwhelming flood of information including misinformation and fabricated rumors — travels faster than epidemics. When left unchecked, misinformation breeds vaccine hesitancy, promotes toxic self-medication, diminishes trust in health systems, and costs lives.

PNSI addresses this crisis by providing health institutions with an integrated, auditable decision engine:
1. **Listening & Detection**: Ingesting signals from authorized public health feeds, social networks, and manual field reports.
2. **Contextual Grounding**: Matching claims strictly against official, approved scientific evidence corpuses.
3. **Structured Governance**: Enforcing distinct scientific, editorial, and administrative approvals.
4. **Linguistic Adaptation**: Formulating culturally sensitive counter-messaging in French, Modern Standard Arabic, and Tunisian Derja.
5. **Closed-Loop Follow-up**: Measuring real-world impact across 48-hour, 7-day, and 30-day windows.

### Core Principles & Ethics
PNSI is designed with strict ethical, medical, and legal boundaries:

* **Strict Human-in-the-Loop Supervision**: No algorithm, machine learning model, or generative AI produces an unreviewed clinical verdict or publishes statements autonomously. Human experts make all decisions.
* **Evidence-Grounded Veracity**: Factual verdicts (`supported`, `contradicted`, `misleading`, `conflicting_evidence`) require citation of specific, version-controlled passages from approved medical literature. If scientific consensus is absent or out of scope, the system explicitly marks `insufficient_evidence`.
* **Honest Provenance & Transparency**: Data metrics never invent certainty. If a source date is missing, it is reported as unknown. Social media counts reflect collected public signals, never total national population sentiment.
* **Privacy by Design**: Automated first-pass redaction strips emails, phone numbers, and social handles before analyst review. Social engagement counters are transient and kept in memory only; post contents and user profiles are never archived in core database records or backups.
* **Linguistic Sovereignty**: Full native multi-lingual support:
  * **French (`fr`)**: Primary administrative and institutional working language.
  * **English (`en`)**: International liaison and technical monitoring.
  * **Modern Standard Arabic (`ar`)**: Right-to-Left (RTL) mirrored interface and bidirectional report rendering.
  * **Tunisian Derja (`derja` / `derja-latin`)**: Arabic and Latin/Arabizi script representation for authentic community understanding.

### User Personas & Role Matrix
PNSI enforces strict Role-Based Access Control (RBAC) across 7 specialized profiles:

| Role | Title (FR) | Core Responsibilities |
| :--- | :--- | :--- |
| **`analyst`** | Analyste de veille | Ingests data, monitors live signals, formulates cases (`C-xxx`), triages urgency, calculates harm & completeness scores, and requests evidence checks. |
| **`scientific_reviewer`** | Réviseur scientifique | Manages the institutional medical corpus, inspects cited literature passages, confirms or rejects claim assessments with scientific rationales, and resolves annotation disputes. |
| **`communication_editor`** | Rédacteur de communication | Drafts targeted, uncertainty-aware counter-responses tailored to channels and languages; validates linguistic and cultural equivalence. |
| **`institutional_approver`** | Valideur institutionnel | Delivers formal institutional sign-off for responses, authorizes frozen executive reports for export, and signs off on recorded public actions. |
| **`viewer`** | Observateur | Read-only access to dashboards, cases, and published reports. Cannot mutate data or trigger operations. |
| **`administrator`** | Administrateur | Manages organization accounts, provisions staff, configures allowed RSS sources and social tracking parameters. Cannot substitute for scientific authority. |
| **`operator`** | Opérateur système | Supervises background collection queues, tracks worker heartbeats, inspects failed ingestion jobs, and triggers retries. |

---

## 2. End-to-End Operational Lifecycle (SOPs)

PNSI implements a traceable 6-stage lifecycle that transforms raw external signals into validated public health actions:

```mermaid
flowchart LR
    A[1. Ingestion & Redaction] --> B[2. Case Formulation & Triage]
    B --> C[3. Scientific Assessment]
    C --> D[4. Multi-Variant Response Studio]
    D --> E[5. Staged Approval Gate]
    E --> F[6. Action & 3-Window Follow-up]
    
    subgraph Approval Gate
        D -->|Step 1| S1[Scientific Review]
        S1 -->|Step 2| S2[Linguistic Review]
        S2 -->|Step 3| S3[Institutional Sign-off]
        S3 --> E
    end
```

### Stage 1: Multi-Source Signal Collection & Ingestion
* **Public Official Feeds (RSS/Atom)**: Curated public streams (e.g., European Centre for Disease Prevention and Control — ECDC epidemiological updates, communicable disease threats, and news) ingested via the durable background worker with CC BY 4.0 attribution and cross-feed deduplication.
* **Social Publication Tracking**: Targeted monitoring of specific public posts/videos on YouTube, Bluesky, Mastodon, and X via official APIs.
* **Automated Topic Watches**: Background search daemon querying pre-configured multilingual public health keywords (`vaccination`, `measles`, `rougeole`, `لقاح`, `tla9i7`, `s7a`) without requiring open browser sessions.
* **Authorized File & Batch Imports**: Analysts import structured CSV or JSON files (up to 500 records / 2 MB) with provenance declarations. An automated first-pass engine redacts phone numbers, emails, and social handles before analyst commit.

### Stage 2: Case Formulation & Harm Triage
* Raw signals are grouped into formal investigation cases (e.g., `C-001`).
* Analysts assign narrative themes (*Vaccination*, *Prévention*, *Accès aux soins*), language, and initial priority scores (0–100) calculated from:
  $$\text{Priority} = f(\text{Potential Harm}, \text{Observed Engagement}, \text{Completeness}, \text{Exposure Proxy})$$
* Cases with priority $\ge 70$ automatically trigger urgent notification alerts.

### Stage 3: Evidence Retrieval & Scientific Assessment
* Analysts request evidence verification against the registered medical corpus.
* The asynchronous worker executes lexical retrieval across approved documents, identifying relevant passage excerpts with overlap scoring.
* A scientific reviewer opens the case evaluation tab:
  * Inspects original claim context, source edition, and exact passage citations.
  * Formulates a verdict: `supported`, `contradicted`, `misleading`, `conflicting_evidence`, `insufficient_evidence`, or `not_factual`.
  * Logs mandatory scientific rationale and documentation limitations.
  * Any edit to underlying evidence documents immediately flags dependent assessments as stale.

### Stage 4: Response Studio & Staged Approvals
* Once an assessment is confirmed, communication editors draft communication variants across target channels (Press Release, Social Media, FAQ, Radio Brief, Healthcare Provider Memo) and languages (FR, EN, AR, Derja).
* Responses undergo a strict 3-tier approval gate:
  1. **Scientific Approval**: Verifies factual accuracy against the confirmed assessment.
  2. **Linguistic & Cultural Approval**: Verifies translation equivalence and nuance (especially in Derja dialects).
  3. **Institutional Approval**: Final leadership sign-off binding the exact response version, assessment version, and evidence checksum.
* Any subsequent textual edit to a response resets all prior approvals to prevent unauthorized alterations.

### Stage 5: Action Execution & 3-Window Impact Tracking
* Institutional approvers authorize manual dissemination through official external channels (PNSI never auto-publishes to external networks).
* The action is recorded with channel, exact published text version, reference ID, and UTC timestamp.
* The system automatically generates three mandatory follow-up evaluation checkpoints:
  * **Window 1: +48 Hours** (Immediate signal stabilization and emergent reactions).
  * **Window 2: +7 Days** (Medium-term narrative trajectory and volume reduction).
  * **Window 3: +30 Days** (Long-term residual impact and baseline comparison).
* Follow-up assessments enforce causal honesty: observed changes in volume do not prove direct causality.

### Stage 6: Audited Executive Briefings & Reports
* Periodic or ad-hoc reports freeze a complete snapshot of cases, evidence links, actions, and follow-ups.
* Requires institutional review before export.
* Exportable to:
  * **PDF Briefings**: Formatted with ReportLab, complete with Arabic RTL shaping, multi-lingual labels, and evidence matrices.
  * **Spreadsheet CSV**: Hardened with automatic sanitization against formula injection (`=`, `+`, `-`, `@`).
  * **Raw JSON**: Machine-readable audit archive.

---

## 3. System Architecture & Technical Stack

### Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                                  BROWSER CLIENT                                   |
|   Next.js 16 (React 19, TypeScript)  |  i18n (FR, EN, AR RTL, Derja)  |  Vanilla CSS   |
+-----------------------------------------+-----------------------------------------+
                                          | Same-origin proxy (/api/v1)
                                          v
+-----------------------------------------------------------------------------------+
|                                FASTAPI BACKEND API                                |
|  - Bearer Session Auth (SHA-256 digested)  - PBKDF2 Password Hasher (310k iter)   |
|  - Institution Isolation Guard             - Optimistic Concurrency (version)     |
|  - Role-Based Access Control (RBAC)        - First-pass PII Redaction Engine      |
|  - Append-only Audit Trail (`audit_events`) - Immutable Snapshots (`record_versions`)  |
+--------------------+-------------------------------------+------------------------+
                     |                                     |
                     v                                     v
+------------------------------------+    +-----------------------------------------+
|     DURABLE DATABASE QUEUE         |    |        BACKGROUND SOCIAL MONITOR        |
|  - Worker Heartbeat Tracking       |    |  - Scheduled Topic Discovery Daemon     |
|  - Crash Recovery (`recover()`)    |    |  - Transient In-Memory Cache (15m TTL)  |
|  - Lexical Evidence Matcher        |    |  - Daily Search Budget Guard (80/day)   |
|  - SSRF-Hardened RSS Collector     |    |  - Retry-After & Exponential Backoff    |
+--------------------+---------------+    +--------------------+--------------------+
                     |                                         |
                     +--------------------+--------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                             STORAGE & DATA PERSISTENCE                            |
|  - SQLite (Local & Demo: `data/pnsi-local.db` / `pnsi.db`) | PostgreSQL (Deploy)   |
|  - Online Atomic SQLite Backups (`data/backups/`) with integrity & FK verification |
+-----------------------------------------------------------------------------------+
```

### Frontend Architecture (`apps/web`)
* **Framework**: Next.js 16 (App Router) with React 19 and TypeScript.
* **Styling**: Vanilla CSS design tokens (`globals.css`) delivering a responsive, high-contrast, accessible interface with zero heavy utility dependencies.
* **Proxy Layer**: Browser traffic routes through a same-origin `/api/v1` Next.js route proxy (`apps/web/app/api.ts`). External API tokens and backend endpoints never leak to the client.
* **Internationalization**: Complete custom dictionary engine (`apps/web/app/i18n.ts`) supporting `fr`, `en`, `ar` (with native Right-to-Left DOM layout), `derja`, and `derja-latin`.
* **Accessibility**: Full keyboard navigation, modal focus traps, ARIA indicators, and tabular alternatives for all visual SVG charts.

### Backend API Architecture (`apps/api`)
* **Framework**: FastAPI (Python 3.12) with Pydantic v2 validation models.
* **Session Security**: Stateless, opaque bearer sessions stored as SHA-256 hashes in the `sessions` table. Expire after 8 hours; revoked on logout or password change.
* **Password Encryption**: PBKDF2-HMAC-SHA256 with cryptographically random 16-byte unique salts and 310,000 iterations.
* **Multi-Tenancy & Isolation**: Institution scoping enforced across all database queries (`institution == user['institution']`).
* **Optimistic Locking**: Every mutation requires `expected_version`. Concurrent collisions return HTTP 409 Conflict.
* **Audit System**: All state changes record before/after diffs in `audit_events`. Passwords, API tokens, and secrets are automatically scrubbed prior to persistence.

### Durable Asynchronous Worker (`workers/run.py`)
* Dedicated standalone process managing long-running tasks via the `jobs` database table.
* **Lexical Evidence Retrieval**: Tokenizes claims and searches approved corpus passages; computes overlap scores to associate context without hallucinating medical claims.
* **Scheduled RSS Polling**: Ingests enabled feeds every 30 minutes, handling network backoff, XML entity security, and deduplication.
* **Worker Lifecycle**: Emits periodic heartbeats to `worker_status`; recovers interrupted running jobs upon process restart.

### Background Monitoring Daemon (`apps/api/automatic_tracking.py`)
* Standalone daemon thread operating inside the local API process.
* Executes hourly discovery across configured social platforms without needing browser interaction.
* Respects global daily search quotas (80 requests per platform per UTC day) and exponential error backoffs.
* Maintains transient engagement observations in RAM, expiring them after 15 minutes.

### Connectors & External Integrations
* **Public RSS/Atom Connector (`apps/api/connectors.py`)**:
  * Enforces public HTTPS on port 443; rejects private, loopback, or non-global IP destinations (SSRF defense).
  * Blocks HTTP redirects; limits payload sizes to 2 MB; strips XML entities and DTD declarations.
  * Connects real ECDC feeds (News, Epidemiological Updates, Disease Threats) with CC BY 4.0 attribution.
* **Official Social Media APIs (`apps/api/social_tracking.py`)**:
  * **YouTube**: Uses Data API v3 (`videos.list`, `search.list`) with API key from `data/social-credentials.json` or `YOUTUBE_API_KEY`.
  * **Bluesky**: Interacts with the official public AppView API (`getPosts`, `searchPosts`).
  * **Mastodon**: Connects to public status endpoints and hashtag timelines (`/api/v1/timelines/tag/*`) with per-instance bearer token support.
  * **X (Twitter)**: Uses official v2 lookup (`/2/tweets`) and recent search with bearer token from credentials or `X_BEARER_TOKEN`.
* **Local Inference Boundary (`apps/api/ai.py`)**:
  * Optional adapter for localhost Ollama (`AI_PROVIDER=local`, default `lexical`).
  * Enforces strict structured output via Pydantic schemas.
  * Rejects any model citation that does not resolve to an already approved database passage.
* **PDF Report Renderer (`apps/api/reports.py`)**:
  * ReportLab engine with A4 layout and Unicode font registration.
  * Bidirectional reshaping for Arabic and Derja via `arabic_reshaper` and `python-bidi`.

### Database & Storage Engine
* **ORM**: SQLAlchemy with declarative mapping.
* **SQLite Persistence**: Default for local workstation operations (`data/pnsi-local.db`) and demo (`pnsi.db`).
* **PostgreSQL Readiness**: Full compatibility via `DATABASE_URL` (configured in `infra/compose.yml`).
* **Core Tables**:
  * `records`: Versioned JSON payloads indexed by kind and institution.
  * `record_versions`: Immutable historical snapshots of all entity versions.
  * `record_relations`: Foreign-key parent-child links (`case_id`, `claim_id`, `response_id`, etc.).
  * `audit_events`: Append-only audit logs.
  * `sessions`: Expiring opaque token digests.
  * `idempotency`: Operation replay protection keys.
  * `worker_status`: Heartbeat and liveness tracking.

---

## 4. Operational Environments

PNSI operates in two distinct, mutually exclusive local modes:

```
+-----------------------------------------------------------------------------------+
|                                 OPERATING MODES                                   |
+-----------------------------------------+-----------------------------------------+
|      SYNTHETIC DEMONSTRATION MODE       |        SOVEREIGN LOCAL WORKSPACE        |
|           (APP_ENV = demo)              |            (APP_ENV = local)            |
+-----------------------------------------+-----------------------------------------+
| Ports: 3000 (Web), 8000 (API)           | Ports: 3001 (Web), 8001 (API)           |
| Database: pnsi.db                       | Database: data/pnsi-local.db            |
| Pre-populated with synthetic fixtures   | Starts completely empty                 |
| Institutions: demo-onmne, demo-partner  | Setup code required (one-time bootstrap)|
| Generic dev accounts (<role>@demo-...)  | Individual staff account provisioning   |
| Default password: Pnsi-Demo-2026!       | Mandatory temporary password change     |
| Training corpus (Products Z, Q, etc.)   | Real ECDC feeds & owner imports         |
| Public production barred                | Loopback-bound host & origin checks     |
+-----------------------------------------+-----------------------------------------+
```

### Mode A: Synthetic Demonstration Environment (`demo`)
* **Purpose**: Safe training, client demonstrations, and walkthrough simulations without handling sensitive institutional data.
* **Access**: http://127.0.0.1:3000 (API at http://127.0.0.1:8000).
* **Database**: `pnsi.db`.
* **Fixtures**: Two synthetic institutions (`demo-onmne` and `demo-partner`), 7 pre-configured user roles, 6 clinical training cases (C-001 through C-006), and a training document corpus regarding fictional Products Z and Q.
* **Credentials**: `<role>@demo-onmne.local` with password `Pnsi-Demo-2026!`.

### Mode B: Sovereign Local Workspace (`local`)
* **Purpose**: Real local operational workspace with personal staff accounts and authentic data.
* **Access**: http://127.0.0.1:3001 (API at http://127.0.0.1:8001).
* **Database**: `data/pnsi-local.db`. Starts completely empty; refuses to start if synthetic demo accounts exist.
* **One-Time Bootstrap**: Protected by an unpredictable 32-byte cryptographic setup code (`data/local-setup-code.txt`).
* **Security Hardening**:
  * Loopback firewalling: Rejects connections with origins or hostnames other than `127.0.0.1` or `localhost`.
  * Mandatory temporary password change upon initial staff login.
  * Verified online SQLite backup created in `data/backups/` before every process start.

---

## 5. Functional Modules & Workspace Pages

| Navigation Item | Route | Module Capabilities |
| :--- | :--- | :--- |
| **Vue d’ensemble** | `/overview` | Real-time system pulse: collected items, pending reviews, active cases, worker heartbeat, latest ECDC articles, volume graphs (7/30/90 days), and quick feed sync. |
| **Suivi des publications** | `/overview` | Tracking up to 20 individual public posts on YouTube, Bluesky, Mastodon, X; manual API query with 1-min rate limiting. |
| **Veille automatique** | `/overview` | Scheduled background topic discovery across four platforms; status indicators, runner heartbeat, and daily quota meters. |
| **Conversations** | `/conversations` | Stream of all collected items; filtering by source, topic, language, and case assignment; direct case formulation. |
| **Allégations & dossiers** | `/claims` | Comprehensive case directory (`C-xxx`); tabs for Summary, Content, Spread, Evidence, Assessment, Responses, Actions, Follow-up, and Timeline. |
| **Narratifs** | `/narratives` | Thematic clustering of related cases into overarching narratives (*Vaccination*, *Santé maternelle*, etc.). |
| **Alertes** | `/alerts` | Urgent triage inbox for high-priority cases ($\ge 70$), severity flags, assignment, and due dates. |
| **Bibliothèque de preuves** | `/evidence` | Registered scientific documents, source metadata, edition tracking, and approved passage library with checksums. |
| **Studio de réponses** | `/responses` | Drafting multi-channel, multi-lingual counter-narratives; variant management; uncertainty-aware templating. |
| **File de validation** | `/approvals` | Governance staging area for scientific, linguistic, and institutional review checkpoints. |
| **Actions & suivi** | `/actions` | Audit log of published communication actions and monitoring of the 48h, 7d, and 30d follow-up windows. |
| **Observations** | `/impact` | Follow-up evaluation workbench; qualitative and quantitative observations; comparability assessment. |
| **Rapports** | `/reports` | Frozen snapshot report creation; institutional sign-off; multi-lingual PDF, CSV, and JSON downloads. |
| **Sources de veille** | `/sources` | Catalog of configured public RSS feeds and collectors; enablement toggle, polling intervals, error status. |
| **Importer des données** | `/imports` | CSV and JSON batch import wizard; PII redaction preview; provenance and legal authorization declaration. |
| **Annotation** | `/annotation` | Dual-annotator labeling workbench; agreement metrics; scientific reviewer disagreement resolution. |
| **Évaluation des modèles**| `/evaluation` | Frozen dataset benchmarking; precision, recall, confusion matrix calculation without metric fabrication. |
| **Administration** | `/admin` | Staff account creation, temporary password generation, password resets, session revocation. |
| **Opérations** | `/jobs` | Background queue dashboard: inspection of queued, running, succeeded, and failed worker tasks. |
| **Journal d’audit** | `/audit` | Immutable, append-only security log with actor names, timestamps, action types, and before/after diffs. |
| **Mon profil** | `/profile` | User password management, language preferences, and timezone selection (default: `Africa/Tunis`). |

---

## 6. Security, Compliance & Governance Boundary

### Threat Boundary & Hardening Measures
* **Loopback Enforced**: In local mode, requests originating from non-loopback IPs or external hostnames are denied with HTTP 403.
* **SSRF Mitigation**:
  * RSS URLs require public HTTPS on port 443.
  * Destination hostnames are resolved via DNS; private, loopback, multicast, and reserved IPv4/IPv6 ranges are blocked.
  * HTTP redirects are disabled to prevent redirection into internal subnets.
* **XML Entity & DTD Defense**: Feed parsers explicitly reject payloads containing `<!DOCTYPE` or `<!ENTITY` declarations, neutralizing XXE (XML External Entity) attacks.
* **Formula Injection Prevention**: CSV export cells starting with `=`, `+`, `-`, or `@` are automatically escaped with leading single quotes to prevent code execution in spreadsheet software.
* **Transient Data Isolation**: Social media API responses are kept in memory with a 15-minute TTL. Social metrics and post bodies are never stored in the database, audit records, reports, or backups.
* **Audit Cleansing**: Passwords, hashes, bearer tokens, and API credentials are automatically filtered out before audit event creation.

### Privacy Redaction Engine
Ingested text automatically passes through regex-based sanitization:
* Emails: `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` $\rightarrow$ `[email masqué]`
* Phone Numbers: `(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}` $\rightarrow$ `[numéro masqué]`
* Social Handles: `@[\w_]{2,30}` $\rightarrow$ `@[utilisateur]`

Analysts must manually inspect remaining text for contextual or indirect identifiers.

---

## 7. Getting Started & Installation

### System Requirements
* **Operating System**: Windows 10/11, macOS, or Linux.
* **Python**: Version **3.12** (64-bit).
* **Node.js**: Version **22.x** or newer (with npm).
* **PowerShell**: Version 5.1 or PowerShell Core (on Windows).

### Initial Dependency Installation
From PowerShell in the project root:

```powershell
# 1. Create and activate Python virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r apps\api\requirements.lock

# 2. Install frontend dependencies and compile web application
cd apps\web
npm ci
npm run build
cd ..\..
```

### Launching the Environments

#### Option 1: Sovereign Local Workspace (Personal Accounts & Data)
Double-click `C:\Users\nourh\Desktop\PNSI-local.cmd` on your Desktop, or run from PowerShell:

```powershell
.\start-local.ps1
```

* **Web UI**: http://127.0.0.1:3001
* **API Documentation**: http://127.0.0.1:8001/docs
* **Database**: `data/pnsi-local.db`

#### Option 2: Synthetic Demonstration Environment (Training Walkthrough)
From PowerShell:

```powershell
.\start.ps1
```

* **Web UI**: http://127.0.0.1:3000
* **API Documentation**: http://127.0.0.1:8000/docs
* **Database**: `pnsi.db`
* **Credentials**: `<role>@demo-onmne.local` / `Pnsi-Demo-2026!`

### Local Setup & First Account Creation
When launching the local workspace for the first time:
1. Open http://127.0.0.1:3001.
2. The browser displays **Créer ton espace**.
3. Retrieve your unique 64-character setup code from the launcher terminal window or `data/local-setup-code.txt`.
4. Enter your organization name, administrator name, email address, password (at least 12 characters), and the setup code.
5. Once submitted, the setup code is permanently invalidated.
6. Sign in and navigate to **Administration** $\rightarrow$ **Créer un compte** to invite team members with specific roles.

---

## 8. Configuration Matrix

### Environment Variables (`.env`)
Configuration is managed through environment variables (the application deliberately does not silently load uninspected `.env` files in production):

| Variable | Default | Purpose / Description |
| :--- | :--- | :--- |
| `APP_ENV` | `demo` | Environment mode: `demo`, `local`, or `test`. (Production values fail closed without institutional identity setup). |
| `APP_BASE_URL` | `http://127.0.0.1:3000` | Canonical public URL of the web application. |
| `DATABASE_URL` | `sqlite:///./pnsi.db` | SQLAlchemy database connection string (e.g., `postgresql://user:pass@host/pnsi`). |
| `API_INTERNAL_URL`| `http://127.0.0.1:8000` | Backend API address accessed by the Next.js reverse proxy. |
| `DEFAULT_LOCALE` | `fr` | Default language for newly created profiles (`fr`, `en`, `ar`, `derja`). |
| `DEFAULT_TIMEZONE`| `Africa/Tunis` | Default display timezone for all timestamps. |
| `DEMO_PASSWORD` | `Pnsi-Demo-2026!` | Password used only when seeding demo fixtures in `demo` mode. |
| `AI_PROVIDER` | `lexical` | Inference provider: `lexical` (default, no AI) or `local` (Ollama). |
| `AI_BASE_URL` | `http://127.0.0.1:11434`| Local Ollama inference server address. |
| `EXTRACTION_MODEL`| `""` | Name of the local LLM model (e.g., `llama3:8b`). |
| `YOUTUBE_API_KEY` | `""` | Optional Google Cloud API key for YouTube Data API v3. |
| `X_BEARER_TOKEN` | `""` | Optional X (Twitter) Developer v2 Bearer Token. |
| `BLUESKY_BASE_URL`| `https://public.api.bsky.app` | Bluesky AppView public API endpoint. |
| `RAW_RETENTION_HOURS`| `24` | Maximum retention window for unredacted incoming data. |
| `REDACTED_RETENTION_DAYS`| `90` | Retention window for processed, redacted items. |

### Social Media Credentials Configuration
Social media API keys can be supplied via environment variables or stored in `data/social-credentials.json` (ignored by Git):

```json
{
  "youtube_api_key": "YOUR_RESTRICTED_GOOGLE_API_KEY",
  "x_bearer_token": "YOUR_X_BEARER_TOKEN",
  "mastodon_tokens": {
    "mastodon.social": "YOUR_READ_ONLY_ACCESS_TOKEN"
  }
}
```

*The application reads this file dynamically on each request; restarting the server is not required after modifying credentials.*

---

## 9. Testing, Verification & Quality Assurance

### Executing the Test Suite
PNSI includes a comprehensive suite of unit, integration, and security tests covering workflows, RBAC enforcement, SSRF protections, and backup integrity.

```powershell
# Run the complete Python test suite
.\.venv\Scripts\python.exe -m pytest tests -q --basetemp=artifacts/pytest-temp -p no:cacheprovider

# Verify TypeScript type safety
cd apps\web
npm run typecheck

# Verify frontend production build
npm run build
cd ..\..
```

### Automated Verifications Covered
* **Security & Isolation**: Enforces tenant boundary separation; blocks administrators from self-granting scientific privileges; verifies SSRF defense against private IP ranges; confirms password removal from audit trails.
* **Workflow Integrity**: Tests optimistic concurrency (409 Conflict); validates evidence citation requirements; ensures editing a response invalidates existing approvals; validates 3-window follow-up scheduling.
* **RSS Feeds**: Validates date parsing, HTML entity sanitization, cross-feed deduplication, and exponential backoff.
* **Backup & Restore**: Verifies online SQLite backup integrity without locking or modifying the source database.

---

## 10. Data Backup, Integrity & Recovery Procedures

### Creating an Online Backup
PNSI includes an atomic online backup utility that operates while the application is running:

```powershell
# Perform an immediate online backup of the local database
.\backup-local.ps1
```

* Backups are written to `data/backups/pnsi-<TIMESTAMP>.db`.
* The script executes SQLite `PRAGMA integrity_check` and `PRAGMA foreign_key_check` before validating the snapshot.
* Existing backup files are strictly immutable and never overwritten.

### Restoration Procedure
To restore from a backup:
1. Stop all running PNSI services (`start-local.ps1` or `start.ps1`) by pressing `Ctrl+C`.
2. Make a safety copy of the current `data/pnsi-local.db`.
3. Copy the selected verified backup file from `data/backups/` to `data/pnsi-local.db`.
4. Relaunch the application.
5. Verify data consistency via `http://127.0.0.1:3001/overview`.

---

## 11. API Specification & Endpoints

All authenticated endpoints reside under `/api/v1` and require an `Authorization: Bearer <TOKEN>` header:

### Authentication & Account Management
* `POST /api/v1/auth/login` — Authenticate and receive an 8-hour bearer token.
* `POST /api/v1/auth/logout` — Revoke the active session token.
* `GET  /api/v1/me` — Retrieve current user profile and role details.
* `POST /api/v1/auth/setup` — One-time bootstrap of the organization and first administrator.
* `POST /api/v1/accounts` — Administrator endpoint to provision staff accounts with temporary passwords.
* `POST /api/v1/auth/password` — Change personal account password (revokes other sessions).
* `POST /api/v1/accounts/{id}/reset-password` — Administrator password reset.

### Workspace & Intelligence Operations
* `GET  /api/v1/overview` — Dashboard summary: live connection statuses, worker heartbeat, feed counts.
* `GET  /api/v1/{kind}` — Scoped query for entities (`cases`, `content`, `narratives`, `alerts`, `evidence-sources`, `documents`, `assessments`, `responses`, `actions`, `reports`, `sources`, `jobs`, `audit`).
* `POST /api/v1/imports` — Batch import CSV or JSON data with provenance declaration.
* `POST /api/v1/content/{id}/case` — Formulate an official case from an ingested signal.
* `POST /api/v1/claims/{id}/verify` — Enqueue an asynchronous lexical evidence retrieval job.
* `POST /api/v1/assessments/{id}/review` — Scientific reviewer sign-off on a claim assessment.
* `POST /api/v1/responses/{id}/approve` — Multi-stage response review (`scientific`, `language`, `institutional`).
* `POST /api/v1/actions/record` — Record a completed public communication action and schedule follow-ups.
* `GET  /api/v1/reports/{id}/export` — Export an approved report snapshot (`format=pdf|csv|json`).

### Social & Automatic Tracking
* `GET  /api/v1/tracking/status` — Get target states, API credentials status, and transient observations.
* `POST /api/v1/tracking/targets` — Register a specific social URL for engagement tracking.
* `POST /api/v1/tracking/refresh` — Manually query official social APIs for updated counters.
* `PUT  /api/v1/tracking/automatic` — Toggle background topic watch daemon and polling interval.
* `POST /api/v1/tracking/watches` — Configure a multilingual topic search watch.

---

## 12. Readiness, Audit Status & Production Release Gates

> [!IMPORTANT]
> **Production Deployment Status**: This software is configured as a functional local workspace and training demonstration. Public production deployment is intentionally blocked by startup guards until official release gates are satisfied.

### Implemented & Validated Capabilities
- [x] Dedicated Next.js 16 frontend and FastAPI backend with loopback security.
- [x] Complete multi-lingual support (FR, EN, AR with native RTL, Derja).
- [x] 7 discrete RBAC roles with institution-scoped tenant isolation.
- [x] Automated PII redaction engine for imports.
- [x] SSRF-hardened RSS connector with live ECDC public feeds.
- [x] Official social engagement monitoring (YouTube, Bluesky, Mastodon, X).
- [x] Automated background multilingual topic discovery daemon.
- [x] Asynchronous lexical evidence retrieval worker.
- [x] Staged 3-tier approval gate (Scientific $\rightarrow$ Linguistic $\rightarrow$ Institutional).
- [x] 3-window action impact monitoring protocol (48h, 7d, 30d).
- [x] Unicode Arabic PDF report rendering with formula injection defense.
- [x] Atomic online SQLite backups with integrity checks.

### Gates Required for National Production Deployment
1. **Relational Schema Normalization**: Migrate the current JSON record store to a fully normalized relational PostgreSQL schema with managed Alembic migrations.
2. **Enterprise Identity (OIDC & MFA)**: Integrate national institutional single sign-on (OIDC/SAML) and Multi-Factor Authentication.
3. **Distributed Job Infrastructure**: Upgrade the single-process worker to distributed Celery/Redis workers with dead-letter queue handling.
4. **Malware-Scanned Object Storage**: Connect S3-compatible private object storage with automated antivirus/malware scanning for uploaded documents.
5. **Clinical & Linguistic Certification**: Conduct formal clinical validation of evidence hierarchies and full linguistic review of Derja dialect terms by native sociolinguists.
6. **Egress Firewall & DNS Pinning**: Implement strict egress proxy firewalls with DNS pinning to eliminate DNS-rebinding risks during external feed fetches.
7. **Sovereign Hosting & Legal Clearances**: Deploy on certified national infrastructure in compliance with Tunisian data privacy laws and institutional data governance frameworks.

---

## 13. Repository Directory Structure

```
pnsi/
├── README.md                      # Complete project documentation and guide
├── .env.example                   # Master configuration template
├── start.ps1                      # Synthetic demonstration launcher (ports 3000/8000)
├── start-local.ps1                # Sovereign local workspace launcher (ports 3001/8001)
├── backup-local.ps1               # Online verified SQLite backup utility
├── apps/
│   ├── api/                       # FastAPI Backend Application
│   │   ├── main.py                # Core API routes, middleware, and lifecycle
│   │   ├── db.py                  # SQLAlchemy models, sessions, and audit logger
│   │   ├── seed.py                # Seed fixtures for synthetic demo environment
│   │   ├── connectors.py          # SSRF-protected RSS/Atom connector
│   │   ├── social_tracking.py     # Official social API client (YouTube, Bluesky, Mastodon, X)
│   │   ├── automatic_tracking.py  # Background topic discovery daemon
│   │   ├── ai.py                  # Local Ollama inference boundary with citation check
│   │   ├── reports.py             # Scoped PDF generator with Arabic RTL reshaping
│   │   └── requirements.lock      # Pinned Python backend dependencies
│   └── web/                       # Next.js 16 Client Application
│       ├── app/
│       │   ├── workspace.tsx      # Unified client workspace interface
│       │   ├── globals.css        # Vanilla CSS design tokens and theme
│       │   ├── i18n.ts            # Translation dictionaries (FR, EN, AR RTL, Derja)
│       │   ├── api.ts             # Same-origin API reverse proxy
│       │   ├── live-overview.tsx  # Overview dashboard and feed sync widgets
│       │   └── social-tracking.tsx# Social monitoring and topic discovery UI
│       └── package.json           # Frontend dependencies and build scripts
├── workers/
│   └── run.py                     # Durable asynchronous worker process
├── scripts/
│   ├── backup-local.py            # SQLite online backup and integrity checker
│   ├── check-backup.py            # Restore-check validation script
│   ├── connect-public-feeds.py    # Public ECDC feed provisioning utility
│   ├── configure-automatic-watch.py # Multilingual health scope configuration
│   └── verify-local-http.py       # End-to-end local HTTP verification test
├── tests/                         # Comprehensive automated test suite
│   ├── test_workflows.py          # Core workflow, governance, and RBAC tests
│   ├── test_local_accounts.py     # Local installation and credential tests
│   ├── test_live_feeds.py         # RSS connector, date parsing, and SSRF tests
│   ├── test_social_tracking.py    # Official social API adapter tests
│   ├── test_automatic_tracking.py # Automatic topic discovery tests
│   └── test_backup.py             # Online SQLite backup and restoration tests
├── docs/                          # Detailed technical & operational specifications
│   ├── architecture.md            # System architecture and data model
│   ├── api-contract.md            # Detailed API specifications and contracts
│   ├── configuration.md           # Configuration documentation
│   ├── deployment.md              # Operations and deployment guide
│   ├── local-use.md               # User guide for local workstation mode
│   ├── readiness.md               # Audit findings, traceability, and open gates
│   ├── security.md                # Security boundaries and threat defenses
│   ├── social-tracking.md         # Social media monitoring documentation
│   └── user-sops.md               # Standard Operating Procedures for user roles
├── data/                          # Local data directory (git-ignored databases & logs)
│   ├── pnsi-local.db              # Local sovereign database (created on first run)
│   ├── local-setup-code.txt       # Unpredictable bootstrap setup code
│   ├── social-credentials.json    # Private API keys for social monitoring
│   └── backups/                   # Online verified SQLite backups
└── infra/                         # Deployment infrastructure
    ├── compose.yml                # Docker Compose stack definition (PostgreSQL ready)
    ├── api.Dockerfile             # Backend container definition
    └── web.Dockerfile             # Frontend container definition
```

---

*For operational procedures and daily workflows, refer to [docs/user-sops.md](docs/user-sops.md). For technical architecture and data schemas, refer to [docs/architecture.md](docs/architecture.md) and [docs/api-contract.md](docs/api-contract.md).*
