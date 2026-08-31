# 06: Every Turn is a Trace with cost in Langfuse

**What to build:** A Cadre engineer opens Langfuse and sees each conversation as a Session of Traces, one per Turn, with the model, tokens and cached tokens, the cost OpenRouter reported, latency, nested spans for each provider call and tool execution, the KB Sections cited, and tags for escalated / lead captured / hand-over offered plus the redaction manifest — with Contact Details and the Refuse Set masked on trace inputs and outputs. The Trace id travels back to the browser in the done event so Feedback can attach to it later. Tracing degrades to a no-op when keys are absent (tests and CI never talk to Langfuse). The deploy binds the Langfuse keys from Secret Manager. Phase P1.

**Blocked by:** 03 (Real Grounded Answers on the public URL), 05 (The Refuse Set never reaches the model or storage)

**Status:** done

- [x] With tracing configured against a fake sink, a Turn produces one Trace with the expected name, session id, tags, cost, and a span per provider call and per tool; covered at seam S1 with the stub provider and an injected fake tracer.
- [x] Trace input and output pass through the `full` Redaction Profile; a message with an email shows the token, not the address; covered at S1 with the fake sink.
- [x] Without Langfuse keys the app starts and serves Turns normally with tracing disabled; covered at S1.
- [x] The done event carries the Trace id; covered at S1.
- [x] On the deployed app, a real conversation appears in Langfuse with a non-zero cost and the tags; a screenshot is attached to the PR.

## Comments

- Delivered in [PR #19](https://github.com/gsbecerrag/cadre-ai-challenge/pull/19). Reviewer: Approved; two Important hardenings (export starvation under Cloud Run CPU throttling; an orphaned span on a `finish` failure) and minors fixed in round 1; scoped re-review: all addressed, no new breakage.
- Ruling: a `Tracer` seam with `NoopTracer` / `LangfuseTracer` / a recording fake; a `TraceBoundary` at the composition root redacts inputs and outputs with `full` and swallows tracer failures, so the Turn loop holds no `try` around tracing and tool spans carry no arguments.
- Ruling: `flush_interval=1 s`, `flush_at=32`, a lifespan shutdown flush; `finish` runs inside the response lifetime; a failed or abandoned Turn still leaves a Trace (`provider_error` / `client_disconnected`), and the store still writes only completed Turns.
- Found on the way and fixed: the `full` profile's obfuscated-email regex was a request-path DoS (54 s on 4,000 characters → 2.7 ms); importing the Langfuse SDK reconfigured the `httpx` logger with a plain-text handler.
- Parked: the module-level `app = create_app()` can build a live tracer at import when keys are exported (serves nothing); `set_trace_io` is deprecated in the SDK; the Langfuse dataset-run upload for the eval suite (ticket 13's `EvalSink` stub) lands with ticket 12.
- Deployed-app Trace (first and last Turn of a conversation) is recorded by the controller after the merge.
- Deployed-app check recorded: [docs/transcripts/2026-08-31-deployed-checks-06-10.md](../../../docs/transcripts/2026-08-31-deployed-checks-06-10.md) — revision `56aa909` on the public URL.
