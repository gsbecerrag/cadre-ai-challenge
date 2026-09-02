# 22: Research Agent and the Lead Brief

**What to build:** A Strategist can run the Research Agent on a Qualified Lead and get a Lead Brief. `POST /api/console/leads/{session_id}/research`, behind the Console allowlist, runs the agent inside the request and streams Server-Sent Events (the contract below), then persists the brief at `lead_briefs/{session_id}` — one brief per Session, a second run overwrites. `GET /api/console/briefs` lists the latest briefs newest first: the Console's polling fallback. The agent is `core/research.py`, the Triage Agent's shape plus tools: it takes its seams as arguments (store, provider, `ResearchSource`, tracer, the rendered Knowledge Base, the model id), uses the Assistant's cached prefix byte for byte with the research instructions in the volatile tail, runs three tools in code — `search_web(query)`, `lookup_company(name)`, `write_brief(...)` — for at most four iterations, and stops when `write_brief` runs; at the cap it assembles a brief from the Research Findings gathered and marks it `complete: false`. `ResearchSource` is a new seam in `core/` with one adapter, `core/adapters/fixture_research.py`: canned Findings for three or four demo companies (Acme Manufacturing among them) keyed case-insensitively by company name or email domain, and a deterministic "no public record found" Finding for any other Lead. Settings: `RESEARCH_SOURCE=fixture` (the only value) and `RESEARCH_MODEL` (blank → the chat model, like `TRIAGE_MODEL`). Each run is its own Trace with cost; the cost is written on the brief. The brief carries one advisory note per Qualification Signal and never writes to the Lead: the Qualification Score is unchanged by research (ADR-0009). Docs in this ticket: CLAUDE.md's architecture paragraph, `.env.example`, `firestore.rules` (`lead_briefs`: Strategist read, no client write), and `docs/architecture.md` kept true if the shape moves. Phase P9. (ADR-0011)

**Blocked by:** None (every earlier ticket is done)

**Event contract** — fixed here so ticket 23 builds against it in parallel. Framing is `core/sse.py`; every payload is one JSON object.

```
event: progress   data: {"step": "searching" | "looking_up" | "writing", "label": "<what the agent is doing, in words a Strategist reads>"}
event: finding    data: {"title": "...", "url": "...", "snippet": "...", "query": "..."}
event: brief      data: <LeadBrief>
event: done       data: {"trace_id": "..." | null, "usage": {"input_tokens": n, "output_tokens": n, "cached_tokens": n, "cost_usd": x}}
event: error      data: {"message": "<safe for a Strategist; never the provider's words>"}
```

`LeadBrief`, on the wire and in `GET /api/console/briefs` (`{"briefs": [LeadBrief, ...]}`):

```
{
  "session_id": "...",
  "company_snapshot": "two or three sentences",
  "person_snapshot": "two or three sentences",
  "talking_points": ["...", "..."],
  "signal_notes": {"industry_fit": "...", "company_size_or_role": "...", "initiative_or_pain": "...", "timeline_or_budget": "...", "explicit_intent": "..."},
  "findings": [{"title": "...", "url": "...", "snippet": "...", "query": "..."}],
  "source": "fixture",
  "model": "anthropic/claude-sonnet-5",
  "cost_usd": 0.0123,
  "complete": true,
  "created_at": "2026-09-02T15:04:05+00:00" | null
}
```

Every key is always present; "nothing to say" is an empty string or an empty list, never a missing key. `signal_notes` always has the five names from `core/qualification.py`.

**Interfaces to add (core):** `ResearchSource` Protocol with `async search(query) -> tuple[Finding, ...]` and `async lookup_company(name) -> tuple[Finding, ...]`; `Finding` frozen dataclass (title, url, snippet, query); `LeadBrief` frozen dataclass next to `Lead` in `core/store.py`; `ConversationStore` gains `save_lead_brief`, `get_lead_brief`, `list_lead_briefs(limit)` in both adapters (`lead_briefs` collection, in-memory dict). The two routes sit on the Console router so the existing route-enumeration refusal test covers them the day they exist; keep `api/console.py` thin by putting the endpoint bodies and the `ConsoleLeadBrief` model in `api/research.py` and mounting them from the router factory — the reviewer checks that `console_endpoints()` still lists both.

**Status:** ready-for-agent

- [ ] S1: researching a Qualified Lead streams `progress` → `finding` → `brief` → `done` in that order (at least one of each), the brief's `source` is `fixture`, its `signal_notes` carry the five signal names, and its `findings` are the fixture's; the brief is then in `GET /api/console/briefs`, and a second run overwrites rather than duplicates.
- [ ] S1: a Session with no Lead is 404; a Lead below the threshold is 409 with a message that says research is for Qualified Leads; both routes refuse a missing, bad or non-allowlisted credential (the route enumeration covers this — confirm it lists them).
- [ ] S1: a provider failure mid-run yields an `error` event with a safe message and persists no brief; the Lead's score and signals are byte-identical after any run.
- [ ] S3: `research_lead` with the in-memory store, the fixture source, the stub provider scripted to call `search_web`, then `lookup_company`, then `write_brief`, and the recording tracer: it yields the events in order, persists the brief, opens one Trace carrying the usage; scripted to never call `write_brief`, it yields and persists a brief with `complete: false` built from the Findings gathered.
- [ ] S2: `write_brief` arguments are validated where the tool runs (a missing or filler field comes back to the model as a tool error result it can correct, never an exception out of the loop); the fixture source answers a known company with its Findings and an unknown one with the "no public record" Finding, keyed case-insensitively by company name or email domain.
- [ ] Personal data: the Lead's Contact Details reach the tools and the prompt raw (they are what is researched — the Refuse Set never reached the store); log lines carry counts and ids only; Traces go through the `full` profile at the existing boundary.
- [ ] `make check` green; `.env.example`, `firestore.rules`, CLAUDE.md and `docs/architecture.md` updated; plan.md's P9 box for ticket 22 ticked in the PR.

## Comments
