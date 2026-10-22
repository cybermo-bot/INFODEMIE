# PNSI developer commands. Run `make help` for the list.
# Node 22 is expected (see .nvmrc); run `nvm use` first if your shell defaults to another version.

SHELL := /bin/bash
API := apps/api
WEB := apps/web
COMPOSE := docker compose -f infra/docker-compose.yml
UV := uv --directory $(API)

.DEFAULT_GOAL := help
.PHONY: help install services services-down dev api worker web test test-api test-api-db test-web e2e \
        lint fmt migrate migration-check seed watchlist collect eval api-client

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

install:  ## Install Python and Node dependencies
	$(UV) sync
	pnpm install

services:  ## Start Postgres, Redis and Mailpit (Docker) and wait until healthy
	$(COMPOSE) up -d --wait

services-down:  ## Stop the Docker services (data volumes are kept)
	$(COMPOSE) down

dev:  ## Start services, then API, worker and web together (Ctrl-C stops all)
	./scripts/dev.sh

api:  ## Run the API only (port 8000, reload)
	$(UV) run uvicorn pnsi.main:app --reload --host 127.0.0.1 --port 8000

worker:  ## Run the Celery worker with beat
	$(UV) run celery -A pnsi.worker:celery_app worker --beat --loglevel=INFO

web:  ## Run the web app only (port 3000)
	pnpm --filter @pnsi/web dev

test: test-api test-web  ## Run backend and frontend tests (DB tests skip if Postgres is down)

test-api:  ## Backend tests (unit, plus integration when Postgres is reachable)
	$(UV) run pytest

test-api-db:  ## Backend integration tests only; fails if Postgres is unreachable
	PNSI_REQUIRE_DB=1 $(UV) run pytest -m db

test-web:  ## Frontend unit tests
	pnpm --filter @pnsi/web test

e2e:  ## Browser tests (needs `make dev` running and Playwright browsers installed)
	pnpm --filter @pnsi/web e2e

lint:  ## Lint and type-check backend and frontend
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	pnpm --filter @pnsi/web lint
	pnpm --filter @pnsi/web typecheck
	pnpm --filter @pnsi/api-client typecheck

fmt:  ## Format backend code
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

migrate:  ## Apply database migrations
	$(UV) run alembic upgrade head

migration-check:  ## Check that the models and migrations agree (needs Postgres)
	$(UV) run alembic check

seed:  ## Seed ONMNE and one user per role; passwords go to data/seed-credentials.txt
	$(UV) run python -m pnsi.cli.seed

watchlist:  ## Add missing Facebook Pages and groups from docs/sources/facebook-watchlist.yaml
	$(UV) run python -m pnsi.cli.watchlist load

collect:  ## Collect every Facebook source now, uses Apify credit (ONLY=text to pick sources)
	$(UV) run python -m pnsi.cli.watchlist collect $(if $(ONLY),--only "$(ONLY)")

eval:  ## Run the verification test set (Stage 4)
	@echo "make eval is not implemented yet: it arrives with the verification engine in Stage 4." >&2; exit 2

api-client:  ## Export the OpenAPI schema and regenerate the TypeScript client
	$(UV) run python -m pnsi.cli.export_openapi > packages/api-client/openapi.json
	pnpm --filter @pnsi/api-client generate
