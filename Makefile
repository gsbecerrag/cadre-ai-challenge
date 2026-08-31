SHELL := /bin/bash

SERVICE := cadre-support-agent
PROJECT := cadre-ai-challenge
REGION  := us-central1

# The deployed build reports its git sha from /healthz.
VERSION := $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)

# The dotenv is a development convenience only: uv loads it when it exists, and it never
# exists in CI or in the container, so tests and Cloud Run cannot pick up a stray .env.
ENV_FILE := $(if $(wildcard .env),--env-file .env,)

.PHONY: help install dev check test build-web deploy

help:
	@echo "install    install Python (uv) and web (pnpm) dependencies"
	@echo "dev        run the API with reload and the Vite dev server"
	@echo "check      lint, typecheck and unit-test everything (what CI runs)"
	@echo "test       unit tests only (pytest + vitest)"
	@echo "build-web  build the SPA into web/dist so the API can serve it"
	@echo "deploy     build the container and deploy it to Cloud Run"

install:
	uv sync
	cd web && pnpm install --frozen-lockfile

dev:
	@trap 'kill 0' EXIT INT TERM; \
	uv run $(ENV_FILE) uvicorn api.main:app --reload --host 127.0.0.1 --port 8080 & \
	(cd web && pnpm dev) & \
	wait

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	uv run pytest
	cd web && pnpm lint
	cd web && pnpm typecheck
	cd web && pnpm test

test:
	uv run pytest
	cd web && pnpm test

build-web:
	cd web && pnpm build

deploy:
	gcloud run deploy $(SERVICE) \
	  --source . \
	  --project $(PROJECT) \
	  --region $(REGION) \
	  --port 8080 \
	  --allow-unauthenticated \
	  --set-env-vars ENV=production,APP_VERSION=$(VERSION)
	@url=$$(gcloud run services describe $(SERVICE) --project $(PROJECT) --region $(REGION) \
	    --format='value(status.url)'); \
	  echo "Service URL: $$url"; \
	  curl -sS "$$url/healthz"; echo
