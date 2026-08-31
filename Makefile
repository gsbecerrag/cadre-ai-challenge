SHELL := /bin/bash

SERVICE := cadre-support-agent
PROJECT := cadre-ai-challenge
REGION  := us-central1

# Secret Manager names the deployed service binds at runtime.
OPENROUTER_SECRET := openrouter-api-key
COOKIE_SECRET     := session-cookie-secret

# The deployed build reports its git sha from /healthz.
VERSION := $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)

# The dotenv is a development convenience only: uv loads it when it exists, and it never
# exists in CI or in the container, so tests and Cloud Run cannot pick up a stray .env.
ENV_FILE := $(if $(wildcard .env),--env-file .env,)

.PHONY: help install dev check test build-web deploy deploy-secrets

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

# The Session cookie is signed, so the deployed service needs a key that outlives an
# instance. It is generated here on first deploy and never leaves Secret Manager: not in the
# repository, not in the image, not in a log line. Idempotent, so re-running is free.
deploy-secrets:
	@gcloud secrets describe $(COOKIE_SECRET) --project $(PROJECT) >/dev/null 2>&1 || { \
	  echo "Creating $(COOKIE_SECRET) in Secret Manager"; \
	  openssl rand -hex 32 \
	    | gcloud secrets create $(COOKIE_SECRET) --project $(PROJECT) \
	        --replication-policy=automatic --data-file=- >/dev/null; \
	  gcloud secrets add-iam-policy-binding $(COOKIE_SECRET) --project $(PROJECT) \
	    --member="serviceAccount:$$(gcloud projects describe $(PROJECT) \
	        --format='value(projectNumber)')-compute@developer.gserviceaccount.com" \
	    --role=roles/secretmanager.secretAccessor >/dev/null; \
	}

# --update-env-vars, not --set-env-vars: a variable another ticket set on the service stays
# set. Secrets are bound from Secret Manager and never passed as values.
deploy: deploy-secrets
	@url=$$(gcloud run services describe $(SERVICE) --project $(PROJECT) --region $(REGION) \
	    --format='value(status.url)' 2>/dev/null); \
	gcloud run deploy $(SERVICE) \
	  --source . \
	  --project $(PROJECT) \
	  --region $(REGION) \
	  --port 8080 \
	  --allow-unauthenticated \
	  --update-env-vars ENV=production,APP_VERSION=$(VERSION),MODEL_PROVIDER=openrouter,CONVERSATION_STORE=firestore,GOOGLE_CLOUD_PROJECT=$(PROJECT),OPENROUTER_APP_URL=$${url:-https://cadreai.com} \
	  --set-secrets OPENROUTER_API_KEY=$(OPENROUTER_SECRET):latest,SESSION_COOKIE_SECRET=$(COOKIE_SECRET):latest
	@url=$$(gcloud run services describe $(SERVICE) --project $(PROJECT) --region $(REGION) \
	    --format='value(status.url)'); \
	  echo "Service URL: $$url"; \
	  curl -sS "$$url/api/healthz"; echo
