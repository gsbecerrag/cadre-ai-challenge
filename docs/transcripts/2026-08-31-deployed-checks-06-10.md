# Deployed-app checks — tickets 06 and 10 (2026-08-31)

Recorded against the public URL <https://cadre-support-agent-495870119371.us-central1.run.app> serving `56aa909` (tickets 01–10 and 13 merged): Claude Sonnet 5 through OpenRouter, Firestore Sessions/Leads/presence, Langfuse tracing with the keys bound from Secret Manager, the Strategist Console with its allowlist, and the Firestore security rules deployed with `make deploy-rules`.

## Ticket 06 — every Turn is a Trace in Langfuse

Two Turns on one Session; each `done` event's `trace_id` was fetched back through the Langfuse API. The second Turn is the last one of the conversation — the case the 1-second flush interval and the shutdown hook exist for.

| Turn | `done.trace_id` | Langfuse |
|---|---|---|
| "What does Cadre AI do?" | `3d3926ac…` | name `turn`, our Session id, `totalCost` 0.058666 = the `done` event's cost, latency 5.9 s, 2 observations (generation + span), metadata: model, tokens, cached tokens, citations, redactions, `request_id` |
| "Which industries do you serve, and how do I book a call?" | `84ac170b…` | same Session id, `totalCost` 0.0124152 = the `done` event's cost, tag `walkthrough_shown`, 4 observations (generation, span, tool) |

Raw check output:

```
### Turn: What does Cadre AI do?
done.trace_id=3d3926ac507234b1a902c4071c3c6bd1 cost_usd=0.058666
### Turn: Which industries do you serve, and how do I book a call?
done.trace_id=84ac170b02a67faa5021fb6665a30d33 cost_usd=0.012415200000000001
### Langfuse trace 3d3926ac507234b1a902c4071c3c6bd1
{'name': 'turn', 'sessionId': 'NDlVhMQRb91CsXnoprIRO3Rys0a7VefQ', 'tags': [], 'totalCost': 0.058666, 'latency': 5.9, 'observations': 2, 'obs_types': ['GENERATION', 'SPAN'], 'input_preview': 'What does Cadre AI do?', 'metadata_keys': ['cached_tokens', 'citations', 'cost_usd', 'input_tokens', 'model', 'output_tokens', 'redactions', 'request_id', 'resourceAttributes', 'scope']}
### Langfuse trace 84ac170b02a67faa5021fb6665a30d33
{'name': 'turn', 'sessionId': 'NDlVhMQRb91CsXnoprIRO3Rys0a7VefQ', 'tags': ['walkthrough_shown'], 'totalCost': 0.0124152, 'latency': 7.434, 'observations': 4, 'obs_types': ['GENERATION', 'SPAN', 'TOOL'], 'input_preview': 'Which industries do you serve, and how do I book a call?', 'metadata_keys': ['cached_tokens', 'citations', 'cost_usd', 'input_tokens', 'model', 'output_tokens', 'redactions', 'request_id', 'resourceAttributes', 'scope']}
```

The Langfuse project screenshot is the reviewer's to take from the dashboard; the API read-back above is the machine-checkable form.

## Ticket 10 — Strategist Console

| Check | Result |
|---|---|
| `GET /console` | 200, the SPA shell (the Console chunk is lazy-loaded; the Visitor bundle does not include the Firebase SDK) |
| `GET /api/console/leads` without a token | 401 — "This is Cadre's Strategist Console. Sign in with your Cadre Google account to continue." |
| `GET /api/console/leads` with a garbage bearer token | 401 — "That sign-in could not be verified. Please sign in again." |
| `PUT /api/console/availability` without a token | 401 |
| Service environment | `ADMIN_ALLOWED_EMAILS=galo.s.becerra@gmail.com`, `MODEL_PROVIDER=openrouter`, `CONVERSATION_STORE=firestore`, `ENV=production` |
| Firestore rules (unauthenticated REST reads) | `leads`, `sessions`, `strategists` → `PERMISSION_DENIED` |
| Firebase Auth | Google provider enabled; both Cloud Run hostnames are authorized domains |

Still to record (needs the allowlisted Google account in a browser): sign in on `/console`, see the shell, toggle Availability online (a `strategists/{uid}` document appears), and watch a Lead arrive without a refresh while a second tab chats with the Assistant.
