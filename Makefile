SHELL := /bin/bash

SERVICE := cadre-support-agent
# The Triage Agent function is a gen2 Firebase Function, which is a Cloud Run service underneath.
FUNCTION_SERVICE := triage-on-feedback-written
PROJECT := cadre-ai-challenge
REGION  := us-central1

# Secret Manager names the deployed service binds at runtime.
OPENROUTER_SECRET := openrouter-api-key
COOKIE_SECRET     := session-cookie-secret
LANGFUSE_PUBLIC   := langfuse-public-key
LANGFUSE_SECRET   := langfuse-secret-key
DAILY_SECRET      := daily-api-key
# The Access Code a browser gives once before the Assistant answers (ticket 21). Optional: with
# no such secret the chat deploys open, which is what a laptop and CI see.
ACCESS_SECRET     := chat-access-code

# The same three secrets again, under a second set of ids — because the Triage Agent function
# cannot name the ones above. `firebase-functions` takes `secrets=[...]` as Secret Manager
# secret *ids* and binds each one to an environment variable of the same name, so the id has
# to be spelled the way an environment variable is: `OPENROUTER_API_KEY`, not
# `openrouter-api-key`. Rather than rename what Cloud Run already binds, `deploy-secrets`
# keeps a copy under each function-shaped id. Source id first, function id second.
FUNCTION_SECRET_PAIRS := \
  $(OPENROUTER_SECRET):OPENROUTER_API_KEY \
  $(LANGFUSE_PUBLIC):LANGFUSE_PUBLIC_KEY \
  $(LANGFUSE_SECRET):LANGFUSE_SECRET_KEY
FUNCTION_SECRETS := OPENROUTER_API_KEY LANGFUSE_PUBLIC_KEY LANGFUSE_SECRET_KEY

# Where the Langfuse project lives. Not a secret, and the wrong region is an authentication
# error rather than a redirect, so it is pinned here next to the keys it goes with.
LANGFUSE_HOST     := https://us.cloud.langfuse.com

# The Daily.co account the Live Hand-over's rooms are created in (ADR-0007). Not a secret —
# it is half of every room URL a Visitor sees — so it is pinned here beside the key it goes
# with. `LIVE_HANDOVER_ENABLED=true` in the deploy below is what turns video on: with it off,
# or with the key unbound, every accepted Hand-over is a Callback and nothing breaks.
DAILY_DOMAIN      := cadre-demo.daily.co

# The deployed build reports its git sha from /healthz.
VERSION := $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)

# The Strategist Console allowlist the deployed service reads (ADR-0010). It is set here, not
# left to a one-off gcloud command, because a blank allowlist admits nobody: a deploy that
# forgot it would close the Console and look exactly like a broken sign-in. `make rules`
# renders the same value into firestore.rules. The demo account (ticket 20) is on the list so
# a reviewer without a Google account can sign in with email/password and the demo credentials
# from Secret Manager (`console-demo-password`) — it is a real, verified Firebase Auth user,
# not a code path, so no server change was needed to add it. Override for a different list:
#   make deploy ADMIN_ALLOWED_EMAILS="a@gocadre.ai,b@gocadre.ai"
ADMIN_ALLOWED_EMAILS ?= galo.s.becerra@gmail.com,strategist@cadre-demo.example

# The dotenv is a development convenience only: uv loads it when it exists, and it never
# exists in CI or in the container, so tests and Cloud Run cannot pick up a stray .env.
ENV_FILE := $(if $(wildcard .env),--env-file .env,)

.PHONY: help install dev check test build-web deploy deploy-secrets eval eval-stub rules deploy-rules deploy-functions check-openrouter-key rotate-openrouter-key set-chat-access-code unset-chat-access-code

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
	@echo "deploy-functions  copy core/ and knowledge/ into functions/ and deploy the Triage Agent"
	@echo "check-openrouter-key   is the deployed OpenRouter key alive, how much credit is left, when it expires"
	@echo "rotate-openrouter-key  replace the deployed OpenRouter key: both secrets, Cloud Run, the Function (.env only with UPDATE_ENV=1)"
	@echo "set-chat-access-code   set or change the Access Code the deployed chat asks for (hidden prompt)"
	@echo "unset-chat-access-code remove the Access Code gate from the deployed chat"

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

# What the deployed service and the Triage Agent function read at runtime. The cookie-signing
# key is generated here if it does not exist yet — never printed, never in the repository,
# never in the image — the three function-shaped copies are made from their sources when they
# are missing, and the runtime service account is granted read access to every one of them on
# every run, because a grant that only happens the day a secret is created is a grant nobody
# can see is missing. Every step is idempotent.
#
# The copy is a copy, not a link: rotating `openrouter-api-key` does NOT update
# `OPENROUTER_API_KEY`. Add a version to both, or delete the function-shaped one and run this
# again. No secret value is ever echoed — it goes from `versions access` straight into
# `create --data-file=-` down a pipe.
deploy-secrets:
	@sa="$$(gcloud projects describe $(PROJECT) --format='value(projectNumber)')-compute@developer.gserviceaccount.com"; \
	gcloud secrets describe $(COOKIE_SECRET) --project $(PROJECT) >/dev/null 2>&1 || { \
	  echo "Creating $(COOKIE_SECRET) in Secret Manager"; \
	  openssl rand -hex 32 \
	    | gcloud secrets create $(COOKIE_SECRET) --project $(PROJECT) \
	        --replication-policy=automatic --data-file=- >/dev/null; \
	}; \
	for pair in $(FUNCTION_SECRET_PAIRS); do \
	  src="$${pair%%:*}"; dst="$${pair##*:}"; \
	  gcloud secrets describe "$$dst" --project $(PROJECT) >/dev/null 2>&1 && continue; \
	  gcloud secrets describe "$$src" --project $(PROJECT) >/dev/null 2>&1 || { \
	    echo "Cannot create $$dst: its source $$src does not exist yet"; \
	    continue; \
	  }; \
	  echo "Copying $$src to $$dst, the id the Triage Agent function can name"; \
	  gcloud secrets versions access latest --secret="$$src" --project $(PROJECT) \
	    | gcloud secrets create "$$dst" --project $(PROJECT) \
	        --replication-policy=automatic --data-file=- >/dev/null; \
	done; \
	for secret in $(OPENROUTER_SECRET) $(COOKIE_SECRET) $(LANGFUSE_PUBLIC) $(LANGFUSE_SECRET) \
	              $(DAILY_SECRET) $(ACCESS_SECRET) $(FUNCTION_SECRETS); do \
	  gcloud secrets describe "$$secret" --project $(PROJECT) >/dev/null 2>&1 || { \
	    echo "Skipping the grant on $$secret: it does not exist"; \
	    continue; \
	  }; \
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
	access=""; \
	if gcloud secrets describe $(ACCESS_SECRET) --project $(PROJECT) >/dev/null 2>&1; then \
	  access=",CHAT_ACCESS_CODE=$(ACCESS_SECRET):latest"; \
	else \
	  echo "No $(ACCESS_SECRET) secret: the chat deploys with no Access Code (make set-chat-access-code)"; \
	fi; \
	gcloud run deploy $(SERVICE) \
	  --source . \
	  --project $(PROJECT) \
	  --region $(REGION) \
	  --port 8080 \
	  --allow-unauthenticated \
	  --update-env-vars "^|^ENV=production|APP_VERSION=$(VERSION)|MODEL_PROVIDER=openrouter|CONVERSATION_STORE=firestore|GOOGLE_CLOUD_PROJECT=$(PROJECT)|ADMIN_ALLOWED_EMAILS=$(ADMIN_ALLOWED_EMAILS)|OPENROUTER_APP_URL=$${url:-https://cadreai.com}|LANGFUSE_HOST=$(LANGFUSE_HOST)|LIVE_HANDOVER_ENABLED=true|DAILY_DOMAIN=$(DAILY_DOMAIN)" \
	  --update-secrets OPENROUTER_API_KEY=$(OPENROUTER_SECRET):latest,SESSION_COOKIE_SECRET=$(COOKIE_SECRET):latest,LANGFUSE_PUBLIC_KEY=$(LANGFUSE_PUBLIC):latest,LANGFUSE_SECRET_KEY=$(LANGFUSE_SECRET):latest,DAILY_API_KEY=$(DAILY_SECRET):latest$$access
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

# The Triage Agent (ADR-0005): a second deployable, a Firebase Function on writes to the
# `feedback` collection. It shares this repository's `core` package by copying it into the
# functions directory at deploy time — the one drift risk the ADR accepted, and the reason it
# is one make target and not a paragraph in a README. The copy is deliberately dumb: rsync,
# no rendering, no generated file, so what runs in the function is the same source `make
# check` just tested, and the triage prompt's cached prefix is byte-identical to the chat's.
# `--delete` so a module deleted here is deleted there rather than lingering in the bundle.
#
#   make deploy-functions COPY_ONLY=1   # copy the packages in, deploy nothing (emulator)
deploy-functions:
	rsync -a --delete \
	  --exclude '__pycache__' --exclude 'tests' --exclude '*.pyc' \
	  core/ functions/core/
	rsync -a --delete --exclude 'README.md' knowledge/ functions/knowledge/
	@if [ -n "$(COPY_ONLY)" ]; then \
	  echo "COPY_ONLY set: core/ and knowledge/ are in functions/, nothing deployed."; \
	else \
	  firebase deploy --only functions --project $(PROJECT); \
	fi

# The OpenRouter key in Secret Manager is whichever one the operator put there — the platform
# ships on the key Cadre issued, the operator's own key is the spare — and any key can be revoked,
# capped or run dry at any moment, so swapping it must be one command and no code change.
# Rotation is three moves:
#   1. add the new key as a version of BOTH secrets — Cloud Run binds `openrouter-api-key`, the
#      Triage Agent function binds the copy `OPENROUTER_API_KEY` (see FUNCTION_SECRET_PAIRS);
#   2. roll the Cloud Run service — it binds `:latest`, but an instance resolves the version when
#      it starts, so only a new revision (no rebuild, ~30 s) makes every instance read the new one;
#   3. re-bind the function's own Cloud Run service to `:latest` — `firebase deploy` pins the
#      version number that was current at deploy time, so without this step the Triage Agent
#      would keep the dead key until the next `make deploy-functions`.
# The key is read from the terminal with echo off (or from stdin when piped in), verified with
# OpenRouter before anything is written, and never appears on a command line or in the output.
# The developer's .env is a separate budget and is left alone unless UPDATE_ENV=1: `make eval`
# costs ~$0.60 a run and must never draw on the platform's credit by accident.
rotate-openrouter-key:
	@if [ -t 0 ]; then printf 'New OpenRouter key (input hidden): '; read -rs key; echo; else read -r key; fi; \
	[ -n "$$key" ] || { echo "No key given; nothing changed."; exit 2; }; \
	echo "Checking the key with OpenRouter before writing it anywhere"; \
	printf '%s' "$$key" | uv run python scripts/openrouter-key-status.py || { echo "Nothing changed."; exit 1; }; \
	for secret in $(OPENROUTER_SECRET) OPENROUTER_API_KEY; do \
	  version=$$(printf '%s' "$$key" | gcloud secrets versions add "$$secret" --project $(PROJECT) \
	      --data-file=- --format='value(name)'); \
	  echo "$$secret: added version $${version##*/}"; \
	done; \
	echo "Rolling $(SERVICE) so every instance reads the new version"; \
	gcloud run services update $(SERVICE) --project $(PROJECT) --region $(REGION) --quiet \
	  --update-secrets OPENROUTER_API_KEY=$(OPENROUTER_SECRET):latest \
	  --update-env-vars OPENROUTER_KEY_ROTATED_AT=$$(date -u +%Y-%m-%dT%H:%M:%SZ) >/dev/null; \
	echo "Re-binding $(FUNCTION_SERVICE) to the latest version of OPENROUTER_API_KEY"; \
	gcloud run services update $(FUNCTION_SERVICE) --project $(PROJECT) --region $(REGION) --quiet \
	  --update-secrets OPENROUTER_API_KEY=OPENROUTER_API_KEY:latest >/dev/null \
	  || echo "Could not update $(FUNCTION_SERVICE) in place — run: make deploy-functions"; \
	if [ -n "$(UPDATE_ENV)" ] && [ -f .env ]; then \
	  NEW_KEY="$$key" perl -pi -e 's/^OPENROUTER_API_KEY=.*/OPENROUTER_API_KEY=$$ENV{NEW_KEY}/' .env; \
	  echo ".env: OPENROUTER_API_KEY replaced — local runs and make eval now spend this key"; \
	else \
	  echo ".env left alone: local runs and make eval keep the key already there (UPDATE_ENV=1 replaces it)"; \
	fi; \
	url=$$(gcloud run services describe $(SERVICE) --project $(PROJECT) --region $(REGION) --format='value(status.url)'); \
	printf 'Health: '; curl -sS "$$url/api/healthz"; echo; \
	echo "Rotated. Send one message on the live app to confirm the model answers."

# The pre-demo question — "is the key still alive, and how much is left on it?" — asked of the
# very version Cloud Run is bound to. The value goes from Secret Manager into the script
# over a pipe and is never printed.
check-openrouter-key:
	@gcloud secrets versions access latest --secret=$(OPENROUTER_SECRET) --project $(PROJECT) \
	  | uv run python scripts/openrouter-key-status.py

# The Access Code (ticket 21): a public URL in front of a metered model key needs something
# between a stranger's script and the balance. The code is shared with the Cadre team privately
# and lives only in Secret Manager — never in the repository, a log line or a command line: it
# is read with echo off (or piped in), stored, and the service rolled so the new value is live.
# A link with `?code=<the code>` unlocks a browser without typing.
set-chat-access-code:
	@if [ -t 0 ]; then printf 'Access code (input hidden): '; read -rs code; echo; else read -r code; fi; \
	[ -n "$$code" ] || { echo "No code given; nothing changed."; exit 2; }; \
	if gcloud secrets describe $(ACCESS_SECRET) --project $(PROJECT) >/dev/null 2>&1; then \
	  printf '%s' "$$code" | gcloud secrets versions add $(ACCESS_SECRET) --project $(PROJECT) --data-file=- >/dev/null; \
	  echo "$(ACCESS_SECRET): new version added"; \
	else \
	  printf '%s' "$$code" | gcloud secrets create $(ACCESS_SECRET) --project $(PROJECT) \
	      --replication-policy=automatic --data-file=- >/dev/null; \
	  echo "$(ACCESS_SECRET): created"; \
	fi; \
	sa="$$(gcloud projects describe $(PROJECT) --format='value(projectNumber)')-compute@developer.gserviceaccount.com"; \
	gcloud secrets add-iam-policy-binding $(ACCESS_SECRET) --project $(PROJECT) \
	  --member="serviceAccount:$$sa" --role=roles/secretmanager.secretAccessor >/dev/null; \
	echo "Rolling $(SERVICE) so the code is live"; \
	gcloud run services update $(SERVICE) --project $(PROJECT) --region $(REGION) --quiet \
	  --update-secrets CHAT_ACCESS_CODE=$(ACCESS_SECRET):latest \
	  --update-env-vars CHAT_ACCESS_CODE_SET_AT=$$(date -u +%Y-%m-%dT%H:%M:%SZ) >/dev/null; \
	echo "Done. Share the code privately; a link with ?code=<the code> unlocks a browser without typing."

# The gate off again, in one revision: the secret stays in Secret Manager for the next
# `make set-chat-access-code` or `make deploy`, which would bind it once more.
unset-chat-access-code:
	@gcloud run services update $(SERVICE) --project $(PROJECT) --region $(REGION) --quiet \
	  --remove-secrets CHAT_ACCESS_CODE >/dev/null && echo "$(SERVICE): the chat is open again"
