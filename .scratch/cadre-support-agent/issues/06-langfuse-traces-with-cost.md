# 06: Every Turn is a Trace with cost in Langfuse

**What to build:** A Cadre engineer opens Langfuse and sees each conversation as a Session of Traces, one per Turn, with the model, tokens and cached tokens, the cost OpenRouter reported, latency, nested spans for each provider call and tool execution, the KB Sections cited, and tags for escalated / lead captured / hand-over offered plus the redaction manifest — with Contact Details and the Refuse Set masked on trace inputs and outputs. The Trace id travels back to the browser in the done event so Feedback can attach to it later. Tracing degrades to a no-op when keys are absent (tests and CI never talk to Langfuse). The deploy binds the Langfuse keys from Secret Manager. Phase P1.

**Blocked by:** 03 (Real Grounded Answers on the public URL), 05 (The Refuse Set never reaches the model or storage)

**Status:** ready-for-agent

- [ ] With tracing configured against a fake sink, a Turn produces one Trace with the expected name, session id, tags, cost, and a span per provider call and per tool; covered at seam S1 with the stub provider and an injected fake tracer.
- [ ] Trace input and output pass through the `full` Redaction Profile; a message with an email shows the token, not the address; covered at S1 with the fake sink.
- [ ] Without Langfuse keys the app starts and serves Turns normally with tracing disabled; covered at S1.
- [ ] The done event carries the Trace id; covered at S1.
- [ ] On the deployed app, a real conversation appears in Langfuse with a non-zero cost and the tags; a screenshot is attached to the PR.
