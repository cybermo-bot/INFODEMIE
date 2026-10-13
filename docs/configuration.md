# Configuration status

Configuration is server-side environment only. `.env.example` is a safe reference, not an automatically loaded file. Use your shell or approved deployment secret manager. Never put actual provider keys in NEXT_PUBLIC variables, PDF files or Git.

Active today: APP_ENV (demo/test/local), DATABASE_URL, LOCAL_SETUP_CODE for one-time local provisioning, DEMO_PASSWORD for initial demo fixture seeding, API_INTERNAL_URL for web proxy, PDF_FONT_PATH for a licensed Unicode font, AI_PROVIDER/AI_BASE_URL/EXTRACTION_MODEL for an optional local Ollama-compatible service. Default AI_PROVIDER is lexical; no model download, model call or remote inference occurred during this build. The local launcher configures its own separate database and ports; see `local-use.md`.

For local inference, provide an already-installed approved model service; set `AI_PROVIDER=local`, `AI_BASE_URL=http://127.0.0.1:11434`, `EXTRACTION_MODEL=<your locally evaluated model name>` in the API and worker environment, then restart both. Schema validation rejects extra fields or unresolved citations. Failed outputs fail the job visibly rather than substituting data. The model remains unapproved for clinical use until the institution’s benchmark passes.

For RSS, an institution administrator creates a source with an exact public HTTPS feed URL and documented access permission. Enable it through the permission review operation. An operator requests collection and inspects the durable job. No live source was enabled or requested in this session; add only approved sources.

PDF exports use the system Arial font on this Windows development computer. Other hosts must set PDF_FONT_PATH to an approved Unicode TrueType font. No Windows font was copied or redistributed. Arabic exports fail explicitly if a suitable font is absent. Review the linguistic layout before sharing official Arabic reports.

Reserved placeholders, not implemented integrations: OIDC*, S3*, REDIS_URL/Celery production queues, optional social API keys, NCBI discovery, SMTP recipients, embedding/reranking/draft model selectors and external inference. Setting these values alone does not turn the feature on. External AI and automatic publication remain disabled in code. The current compose stack includes only database/API/worker/web.
