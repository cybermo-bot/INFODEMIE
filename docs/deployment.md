# Development operations

Personal local installation: `start-local.ps1` uses API 8001, compiled web 3001 and `data/pnsi-local.db`, enforces loopback binding and takes a verified online backup before every restart. `PNSI-local.cmd` on the Desktop launches it. See `local-use.md`. The launcher checks occupied ports and API readiness before starting the worker/web. Public production deployment is still blocked.

Local processes: API port 8000, web port 3000, one durable polling worker. `start.ps1` starts backend processes hidden and keeps the web server in the terminal. Ctrl+C stops the backend processes started by that invocation. If an old process occupies a port, stop that named process before starting another copy.

PostgreSQL development configuration is available in `infra/compose.yml`; set POSTGRES_PASSWORD in the environment, then run `docker compose -f infra/compose.yml up --build` from the project root. Docker/PostgreSQL were not tested in this session. This compose file is an isolated demo stack, not an approved production deployment. The workers are not horizontally scalable yet.

Health checks: `/health/live` for process health and `/health/ready` for database reachability. `/api/v1/jobs` exposes real queued/running/succeeded/failed records. Source health shows last success; absence of a key or permission never creates replacement data.

For a local SQLite backup, use Python’s SQLite backup API or stop API and worker before copying `pnsi.db` into an encrypted, access-controlled backup destination. `scripts/check-backup.py` creates a separate online backup under ignored artifacts, verifies integrity and checks record counts/actions/follow-up/version rows without replacing the live database. This local restore-file check passed. Restoration must use a separate isolated instance; compare reviewed versions and approval/action consistency before replacing anything. Never restore production data into the demo. This is not an institutional PostgreSQL recovery drill.

Production blockers: approved Tunisian host, TLS/reverse proxy, identity, network/egress policy, private storage, relational migrations, queue leases, encryption, retention policies, monitoring, operating owners, restore testing and rollback. Do not change APP_ENV to production to bypass this work: startup is intentionally blocked.
