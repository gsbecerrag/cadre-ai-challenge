# 01: Hello-world Assistant live on Cloud Run

**What to build:** A Visitor opens the public URL and sees a Cadre-branded placeholder chat page; `/healthz` answers. This is the scaffold every later slice builds on: one container that runs the API (Python, FastAPI, uv) and serves the built web app (React, Vite, TypeScript, pnpm, Tailwind with Cadre's tokens) from the same origin; a shared core package for seams and utilities; a Makefile with `dev`, `check` (lint + typecheck + unit tests), `test`, and `deploy` (Cloud Run, `us-central1`, project `cadre-ai-challenge`); structured JSON logging with severity, request id, and session id, level from `LOGLEVEL`; configuration read from environment variables with the documented example file as the schema; a GitHub Actions workflow that runs `make check` on every pull request. Phase P0.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `GET /healthz` returns 200 with a JSON body naming the service and version; covered by an HTTP test at seam S1 (test client against the app).
- [ ] The root URL serves the built web app; the page shows the Cadre wordmark/colours and an empty chat shell with a disabled composer ("coming soon").
- [ ] Configuration loads from environment variables with typed defaults; a missing required variable fails fast at startup with a clear message; covered at seam S2.
- [ ] Every log line is one JSON object with `severity`, `message`, `request_id`, and (when present) `session_id`; `LOGLEVEL=DEBUG` enables debug lines; covered at seam S2 with a captured log record.
- [ ] `make check` runs lint (ruff, eslint), typecheck (mypy or pyright, tsc) and the unit suites and passes; `make dev` runs API and web app locally.
- [ ] `make deploy` builds the container and deploys to Cloud Run; the printed public URL answers `/healthz` and serves the page (verified by curl and a browser check, recorded in the PR).
- [ ] CI workflow runs `make check` on pull requests and is green on this PR.
- [ ] No secret is read at build time; the deploy binds none yet.
