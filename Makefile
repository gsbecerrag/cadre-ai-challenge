SHELL := /bin/bash

SERVICE := cadre-support-agent
PROJECT := cadre-ai-challenge
REGION  := us-central1

# Secret Manager names the deployed service binds at runtime.
OPENROUTER_SECRET := openrouter-api-key
COOKIE_SECRET     := session-cookie-secret
LANGFUSE_PUBLIC   := langfuse-public-key
LANGFUSE_SECRET   := langfuse-secret-key

# Where the Langfuse project lives. Not a secret, and the wrong region is an authentication
# error rather than a redirect, so it is pinned here next to the keys it goes with.
LANGFUSE_HOST     := https://us.cloud.langfuse.com

# The deployed build reports its git sha from /healthz.
VERSION := $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)

# The Strategist Console allowlist the deployed service reads (ADR-0010). It is set here, not
# left to a one-off gcloud command, because a blank allowlist admits nobody: a deploy that
# forgot it would close the Console and look exactly like a broken sign-in. `make rules`
# renders the same value into firestore.rules. Override for a different list:
#   make deploy ADMIN_ALLOWED_EMAILS="a@gocadre.ai,b@gocadre.ai"
ADMIN_ALLOWED_EMAILS ?= galo.s.becerra@gmail.com

# The dotenv is a development convenience only: uv loads it when it exists, and it never
# exists in CI or in the container, so tests and Cloud Run cannot pick up a stray .env.
ENV_FILE := $(if $(wildcard .env),--env-file .env,)

.PHONY: help install dev check test build-web deploy deploy-secrets eval eval-stub rules deploy-rules

help:
	@echo "install    install Python (uv) and web (pnpm) dependencies"
	@echo "dev        run the API with reload and the Vite dev server"
	@echo "check      lint, typecheck and unit-test everything (what CI runs)"
	@echo "test       unit tests only (pytest + vitest)"
	@echo "eval       run all 50 Eval Cases against the real provider and judge (needs a key)"
	@echo "eval-stub  run the deterministic Eval Cases against the stub provider (free)"
	@echo "build-web  build the SPA into web/dist so the API can serve it"
	@echo "deploy     build the container and deploy it to Cloud Run"
	@echo "rules      render ADMIN_ALLOWED_EMAILS into firestore.rules"
	@echo "deploy-rules  deploy firestore.rules and the indexes to Firebase"

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

# The whole suite against the real model and the Haiku judge: about $0.50 and a couple of
# minutes at a concurrency of four. It needs OPENROUTER_API_KEY and skips with a message
# saying so when there is none, so a machine without a key can still run every other target.
# A non-zero exit means an Eval Case failed, which is information — see evals/reports/.
eval:
	uv run $(ENV_FILE) python -m evals.runner

# What CI runs after `make check`: the deterministic Eval Cases — every Trap Question and every
# qualification case — driven through the whole application with the stub provider scripted
# from the case. No key, no network, no spend. `python -m evals.runner --stub` is the same
# subset with a printed scorecard instead of pytest's output.
eval-stub:
	uv run pytest evals -m evals --stub

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
	for secret in $(OPENROUTER_SECRET) $(COOKIE_SECRET) $(LANGFUSE_PUBLIC) $(LANGFUSE_SECRET); do \
	  echo "Granting $$sa read access to $$secret"; \
	  gcloud secrets add-iam-policy-binding "$$secret" --project $(PROJECT) \
	    --member="serviceAccount:$$sa" \
	    --role=roles/secretmanager.secretAccessor >/dev/null; \
	done

# --update-env-vars and --update-secrets, not their --set- forms: a variable or a secret
# binding another ticket added to the service survives this deploy instead of being replaced.
# Secret values are bound from Secret Manager and never passed on the command line.
# The `^|^` prefix is gcloud's alternate delimiter: `|` separates the pairs instead of a
# comma, so an ADMIN_ALLOWED_EMAILS holding several comma-separated addresses stays one
# value. It has to be `|` and not `@`, which every address in that list contains.
deploy: deploy-secrets
	@url=$$(gcloud run services describe $(SERVICE) --project $(PROJECT) --region $(REGION) \
	    --format='value(status.url)' 2>/dev/null); \
	gcloud run deploy $(SERVICE) \
	  --source . \
	  --project $(PROJECT) \
	  --region $(REGION) \
	  --port 8080 \
	  --allow-unauthenticated \
	  --update-env-vars "^|^ENV=production|APP_VERSION=$(VERSION)|MODEL_PROVIDER=openrouter|CONVERSATION_STORE=firestore|GOOGLE_CLOUD_PROJECT=$(PROJECT)|ADMIN_ALLOWED_EMAILS=$(ADMIN_ALLOWED_EMAILS)|OPENROUTER_APP_URL=$${url:-https://cadreai.com}|LANGFUSE_HOST=$(LANGFUSE_HOST)" \
	  --update-secrets OPENROUTER_API_KEY=$(OPENROUTER_SECRET):latest,SESSION_COOKIE_SECRET=$(COOKIE_SECRET):latest,LANGFUSE_PUBLIC_KEY=$(LANGFUSE_PUBLIC):latest,LANGFUSE_SECRET_KEY=$(LANGFUSE_SECRET):latest
	@url=$$(gcloud run services describe $(SERVICE) --project $(PROJECT) --region $(REGION) \
	    --format='value(status.url)'); \
	  echo "Service URL: $$url"; \
	  curl -sS "$$url/api/healthz"; echo

# The Console enforces the Strategist allowlist twice — in the API and in Firestore's rules,
# because the browser reads Leads live and a realtime listener never passes through the API
# (ADR-0010). This renders the second one from the same ADMIN_ALLOWED_EMAILS the first reads,
# so the committed rules always say what the deployment says. Commit the result.
rules:
	uv run $(ENV_FILE) scripts/render-firestore-rules.py

# Rules and indexes are deployed separately from the container: they belong to the Firebase
# project, not to the Cloud Run revision. Run `make rules` first if the allowlist changed.
deploy-rules:
	firebase deploy --only firestore:rules,firestore:indexes --project $(PROJECT)
