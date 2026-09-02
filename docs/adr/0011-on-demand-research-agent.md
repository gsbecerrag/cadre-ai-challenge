---
status: accepted
date: 2026-09-02
---

# The Research Agent runs on demand inside the Console request, over a Research Source seam that is fixture-backed today

A Strategist presses "Research this Lead" on a Qualified Lead; the API runs a small tool loop — the Triage Agent's shape plus tools — inside that request, streams what the agent is doing, and writes a Lead Brief keyed by the Session. Public information comes through a new `ResearchSource` seam whose only adapter is a set of canned Research Findings: the model is real, the sources are not, and the brief says so. We chose this over the Firestore-trigger pattern ADR-0005 reserved for lead enrichment because a person is waiting and wants to watch, and over a live search provider because the request was to mock external sourcing first.

## Context

- The ask (2 Sep): a copilot for Cadre's team preparing a first call with a pre-qualified Lead — take what the Lead said, look them up in public sources, and hand the team a brief. External sourcing is to be mocked in this first pass.
- ADR-0005 reserved the Firestore-trigger pattern for a "lead-enrichment agent": automatic, nobody waiting, one Function per agent. That fits triage, where the Visitor who clicked has already moved on. It fits research less well: the Strategist is on the page, the demo *is* the agent visibly working, and a second deployable is real cost on a review-week clock.
- Cloud Run keeps the CPU on for the life of a request, and a run is a handful of model calls with no retrieval: ten to twenty seconds, well inside the service's request timeout. Streaming the steps over SSE is the framing the chat already uses (`core/sse.py`).
- The Triage Agent gets its structured output from `response_format`. The Research Agent needs tools *and* a structured result; on OpenRouter a strict `response_format` in the same request as tool calls is the less-travelled path, and a tool call's arguments are already a schema the loop validates.
- ADR-0009: the Qualification Score is counted in code from what the Visitor said. A brief built from fixtures must not be able to turn a 2-of-5 into a Qualified Lead.
- The Knowledge Base block is ~25K tokens of cached prefix (ADR-0001). Talking points for a Cadre call should name Cadre's services, which live in that block.

## Decision

- **Trigger:** `POST /api/console/leads/{session_id}/research`, behind the Console allowlist (ADR-0010). Only a Qualified Lead may be researched: no Lead is 404, below the threshold is 409. The run happens in the request and streams `progress`, `finding`, `brief`, `done` and `error` as Server-Sent Events. Running again overwrites: one Lead Brief per Session, as there is one Lead per Session.
- **Loop:** `core/research.py` takes its seams as arguments — store, provider, source, tracer, the rendered Knowledge Base, the model id — the same boundary as `core/triage.py`, so the handler runs at seam S3 with fakes and could be called by a Firestore trigger later without change. Three tools run in code: `search_web(query)`, `lookup_company(name)` and `write_brief(...)`. The loop ends when `write_brief` runs, or at four iterations, when a brief is assembled from the Findings gathered so far and marked incomplete. The brief's shape is validated where the tool runs; there is no "the JSON did not parse" branch.
- **Prompt:** the Assistant's cached prefix byte for byte, research instructions in the volatile tail — the Triage Agent's trick (ADR-0005), for the same two reasons: Cadre's services are in the block, and the call lands on a warm cache.
- **Sources:** `ResearchSource` is a seam in `core/` with one adapter, `core/adapters/fixture_research.py`: canned Findings for a few demo companies keyed by company name or email domain, and a deterministic "no public record found" Finding for everyone else, so every run produces a brief. Selected by `RESEARCH_SOURCE=fixture`, the only value. The brief carries `source: "fixture"` and the Console prints "Demo fixtures" on it.
- **Boundary with the score:** the brief carries one advisory note per Qualification Signal and never writes to the Lead. ADR-0009 stands unchanged.
- **Model and cost:** `RESEARCH_MODEL`, defaulting to the chat model; each run is one Trace with its cost, and the cost is written on the brief because it is the number a Strategist will ask about.

## Considered Options

- Firestore trigger on the Lead becoming Qualified (ADR-0005's reserved pattern) — lost for the MVP because nobody is waiting on a trigger and everybody is waiting on this; the demo would have nothing to press; and it is a second Function to deploy and rotate keys into. It remains the Phase 2 evolution: the same handler, a different trigger.
- Generalising the chat Turn loop (`core/turn.py`) — lost because it is welded to Sessions (history, the Turn cap, Visitor redaction, chat events) and a research run has no Session; the refactor would touch the request path that is already working.
- One structured-output call over lookups made in code, no tools — lost because the model would never decide what to look for, which is the behaviour being demonstrated.
- A conversational research panel in the Console — lost as a second chat surface with its own prompt, tools and loop; a button that runs one agent is the smallest thing that shows the loop.
- A live search provider now (Tavily, Firecrawl, a company-data API) — deferred by request; it is one adapter behind the seam.

## Consequences

- Positive: no new deployable; the agent is tested offline end to end (S1 through the endpoint, S3 on the handler); the trigger can change without the agent changing.
- Positive: the brief is a schema the provider fills and the loop validates; a bad answer is a tool error the model corrects, not a crash and not a parse fallback.
- Negative: the run occupies a Cloud Run request for its duration; a Strategist who closes the tab loses the stream, and the brief is written only if the loop finishes — the same rule as a chat Turn.
- Negative: the brief is only as good as the fixtures; an unknown company gets an honest "no public record" and a brief that leans on what the Visitor said. That is the point of the label.
- Negative: two collections keyed by the session id (`leads`, `lead_briefs`) rather than one document — chosen so the Lead document, which `capture_lead` overwrites mid-Turn, never carries something the Assistant did not write.
- Reopen when: a live source lands (the fixture then stays as the test double); Strategists want briefs waiting for them (add the trigger); or a brief's facts should count toward the score (reopen ADR-0009 with the source's reliability in hand).

## Links

- Related: [ADR-0001](0001-kb-in-prompt-no-rag.md), [ADR-0004](0004-raw-tool-loop.md), [ADR-0005](0005-event-driven-triage-agent.md), [ADR-0009](0009-bant-lite-qualification.md), [ADR-0010](0010-firebase-auth-console.md)
- Tickets: `.scratch/cadre-support-agent/issues/22-research-agent-and-lead-brief.md`, `.scratch/cadre-support-agent/issues/23-console-research-this-lead.md`
