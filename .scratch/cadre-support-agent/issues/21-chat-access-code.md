# 21: Access Code on the chat — the metered key behind a public URL

**What to build:** The deployed Assistant runs on a metered OpenRouter key with a small balance, on a URL anyone can reach. A Visitor who has not entered the shared Access Code — handed to the Cadre team privately, never in the repository — sees the greeting and a small "enter the access code" field instead of the composer; the right code unlocks that browser for the rest of its Session and the composer appears. The gate is enforced on the server on the two endpoints that spend the key (a Turn and a thumbs-down's Triage), so a script cannot bypass the widget. A link with `?code=…` unlocks silently, so the reviewer who opens the review pack's link never types anything. With no code configured (CI, `make dev`, a reviewer's laptop) there is no gate at all. Scope addition of 31 Aug (Phase P8).

**Blocked by:** 19 (Honesty pass)

**Status:** done

- [x] `POST /api/chat` and `POST /api/feedback` answer 401 `access_code_required` until the Session's browser holds a valid unlock cookie, and are unchanged when no code is configured.
- [x] `POST /api/access {code}` sets a signed, HTTP-only unlock cookie on the right code, refuses a wrong one without saying why, and refuses further attempts after five wrong codes in a Session; `GET /api/access` reports `{required, unlocked}`.
- [x] The widget shows the code field in place of the composer while locked, unlocks on the right code, and honours `?code=` on the page URL.
- [x] The code lives in Secret Manager (`chat-access-code`); `make set-chat-access-code` creates or rotates it with a hidden prompt and rolls the service; `make deploy` binds it only when it exists. The value never appears in the repository, a log line, or a command line.
- [x] README, plan.md, the demo script, CLAUDE.md, CONTEXT.md and the spec record the gate; tests at S1 show RED then GREEN.

## Comments

- 2026-08-31 — done in [PR #32](https://github.com/gsbecerrag/cadre-ai-challenge/pull/32). Built directly by the controller (TDD at S1: 8 tests RED on a missing `api.access`, GREEN after; the full suite, mypy, ruff, eslint, tsc and vitest green) — the subagent seat was skipped because every subagent build that day ran a pnpm install inside the VS Code workspace, which was the crash trigger. The code itself is set by the operator with `make set-chat-access-code`; the gate is off until then.
