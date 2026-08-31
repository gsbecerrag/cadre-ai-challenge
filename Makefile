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

# What the deployed service reads at runtime. The cookie-signing key is generated here if it
# does not exist yet — never printed, never in the repository, never in the image — and the
# runtime service account is granted read access to every bound secret on every run, because
# a grant that only happens the day a secret is created is a grant nobody can see is missing.
# Both steps are idempotent.
deploy-secrets:
	@sa="$$(gcloud projects describe $(PROJECT) --format='value(projectNumber)')-compute@developer.gserviceaccount.com"; \
	gcloud secrets describe $(COOKIE_SECRET) --project $(PROJECT) >/dev/null 2>&1 || { \
	  echo "Creating $(COOKIE_SECRET) in Secret Manager"; \
	  openssl rand -hex 32 \
	    | gcloud secrets create $(COOKIE_SECRET) --project $(PROJECT) \
	        --replication-policy=automatic --data-file=- >/dev/null; \
	}; \
	for secret in $(OPENROUTER_SECRET) $(COOKIE_SECRET); do \
	  echo "Granting $$sa read access to $$secret"; \
	  gcloud secrets add-iam-policy-binding "$$secret" --project $(PROJECT) \
	    --member="serviceAccount:$$sa" \
	    --role=roles/secretmanager.secretAccessor >/dev/null; \
	done

# --update-env-vars and --update-secrets, not their --set- forms: a variable or a secret
# binding another ticket added to the service survives this deploy instead of being replaced.
# Secret values are bound from Secret Manager and never passed on the command line.
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
	  --update-secrets OPENROUTER_API_KEY=$(OPENROUTER_SECRET):latest,SESSION_COOKIE_SECRET=$(COOKIE_SECRET):latest
	@url=$$(gcloud run services describe $(SERVICE) --project $(PROJECT) --region $(REGION) \
	    --format='value(status.url)'); \
	  echo "Service URL: $$url"; \
	  curl -sS "$$url/api/healthz"; echo
