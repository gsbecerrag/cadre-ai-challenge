# OpenRouter facts for a FastAPI support chatbot (OpenRouter as sole LLM provider)

Gathered 2026-08-30 from openrouter.ai docs pages, the public `GET /api/v1/models` and
`GET /api/v1/models/{id}/endpoints` endpoints (no API key), and langfuse.com docs.
Anything the docs/API did not state is marked **unconfirmed**.

Sources
- https://openrouter.ai/api/v1/models (public JSON, 396 models on 2026-08-30)
- https://openrouter.ai/api/v1/models/anthropic/claude-sonnet-5/endpoints (public)
- https://openrouter.ai/docs/api-reference/overview
- https://openrouter.ai/docs/features/prompt-caching
- https://openrouter.ai/docs/guides/features/tool-calling  (old /docs/features/tool-calling is 404)
- https://openrouter.ai/docs/api-reference/streaming
- https://openrouter.ai/docs/use-cases/usage-accounting
- https://openrouter.ai/docs/api-reference/get-a-generation
- https://openrouter.ai/docs/features/structured-outputs
- https://openrouter.ai/docs/features/provider-routing
- https://openrouter.ai/docs/guides/routing/model-fallbacks  (/docs/features/model-routing now documents the Auto Router)
- https://openrouter.ai/docs/api-reference/limits, https://openrouter.ai/docs/faq
- https://openrouter.ai/docs/api/api-reference/api-keys/get-current-api-key
- https://openrouter.ai/docs/app-attribution
- https://openrouter.ai/docs/use-cases/reasoning-tokens
- https://openrouter.ai/docs/features/message-transforms (now "Context Compression")
- https://langfuse.com/integrations/gateways/openrouter

---

## 1. Model catalog & pricing (USD per 1M tokens; from `pricing.*` strings x 1e6)

Anthropic ids that exist: claude-sonnet-5, claude-haiku-4.5, claude-opus-5, claude-opus-5-fast,
plus older 4.x lines and `:batch` variants. No "haiku-5" exists. Pricing fields present for Claude:
`prompt`, `completion`, `input_cache_read`, `input_cache_write` (5-min), `input_cache_write_1h`, `web_search`.

| id | context_length | max_completion_tokens | input | output | cache read | cache write (5m) | cache write (1h) |
|---|---|---|---|---|---|---|---|
| anthropic/claude-sonnet-5 | 1,000,000 | 128,000 | 2.00 | 10.00 | 0.20 | 2.50 | 4.00 |
| anthropic/claude-haiku-4.5 | 200,000 | 64,000 | 1.00 | 5.00 | 0.10 | 1.25 | 2.00 |
| anthropic/claude-opus-5 | 1,000,000 | 128,000 | 5.00 | 25.00 | 0.50 | 6.25 | 10.00 |
| anthropic/claude-opus-5-fast | 1,000,000 | 128,000 | 10.00 | 50.00 | 1.00 | 12.50 | (not extracted) |

OpenAI `gpt-5*` naming differs from "flagship + mini/nano" for the newest line. Newest by `created`:
GPT-5.6 series (2026-07-09) uses tiers **sol** (flagship) / **terra** (balanced) / **luna** (fast, cheap),
each also with a `-pro` variant priced identically in the catalog. gpt-5.5 (2026-04-24) is the prior
flagship; gpt-5.4 has classic `-mini` / `-nano`. OpenAI models list `input_cache_read` only
(`input_cache_write` present only on GPT-5.6, which the caching docs say bills writes at 1.25x).

| id | context_length | max_completion_tokens | input | output | cache read | cache write |
|---|---|---|---|---|---|---|
| openai/gpt-5.6-sol | 1,050,000 | 128,000 | 2.00 | 10.00 | 0.20 | 2.50 |
| openai/gpt-5.6-terra | 1,050,000 | 128,000 | 2.00 | 12.00 | 0.20 | 2.50 |
| openai/gpt-5.6-luna | 1,050,000 | 128,000 | 0.20 | 1.20 | 0.02 | 0.25 |
| openai/gpt-5.5 | 1,050,000 | 128,000 | 5.00 | 30.00 | 0.50 | n/a (automatic) |
| openai/gpt-5.4 | 1,050,000 | 128,000 | 2.50 | 15.00 | 0.25 | n/a |
| openai/gpt-5.4-mini | 400,000 | 128,000 | 0.75 | 4.50 | 0.075 | n/a |
| openai/gpt-5.4-nano | 400,000 | 128,000 | 0.20 | 1.25 | 0.02 | n/a |

Google: the only current "pro" text model is `gemini-3.1-pro-preview` (no GA 3.x Pro in catalog).
Newest flash: `gemini-3.7-flash` (2026-08-13), then 3.6-flash, 3.5-flash, 3.5-flash-lite.
Gemini `input_cache_write` is listed as a per-token figure; whether it is a per-hour storage rate is **unconfirmed**.

| id | context_length | max_completion_tokens | input | output | cache read | input_cache_write (as listed) |
|---|---|---|---|---|---|---|
| google/gemini-3.1-pro-preview | 1,048,576 | 65,536 | 2.00 | 12.00 | 0.20 | 0.375 |
| google/gemini-3.7-flash | 1,048,576 | 65,536 | 0.75 | 3.75 | 0.075 | 0.042 |
| google/gemini-3.6-flash | 1,048,576 | 65,536 | 0.75 | 3.75 | 0.075 | 0.042 |
| google/gemini-3.5-flash | 1,048,576 | 65,536 | 1.50 | 9.00 | 0.15 | 0.083 |
| google/gemini-3.5-flash-lite | 1,048,576 | 65,536 | 0.30 | 2.50 | 0.03 | 0.083 |

Capability flags from `supported_parameters` (catalog, model-level):
- All benchmark candidates above list `tools`, `tool_choice`, `response_format`, `structured_outputs`, `reasoning`.
- **`anthropic/claude-sonnet-5` does NOT list `temperature`/`top_p`/`top_k`** (Opus 5 and Haiku 4.5 do). No `openai/gpt-5*` lists `temperature`. Per the API reference, unsupported params are "silently ignored per model" — so a benchmark harness should not rely on temperature for Sonnet 5 / GPT-5.x.
- Sonnet 5 `supported_parameters`: include_reasoning, max_completion_tokens, max_tokens, reasoning, reasoning_effort, response_format, stop, structured_outputs, tool_choice, tools, verbosity. Modalities: text, image, file. `canonical_slug`: anthropic/claude-sonnet-5-20260630. `per_request_limits`: null.
- `GET /api/v1/models?supported_parameters=structured_outputs` works unauthenticated (297 of 396 models); `?supported_parameters=tools` -> 315.

Per-provider endpoints for Sonnet 5 (`/models/anthropic/claude-sonnet-5/endpoints`): provider tags
`anthropic`, `claude-on-aws`, `azure/global`, `azure/us`, `google-vertex/global|us|europe`,
`amazon-bedrock/global|us-east-1`. All at $2/$10 except `amazon-bedrock/us-east-1`, `google-vertex/us`,
`google-vertex/europe` at $2.20/$11 (cache read 0.22, write 2.75). **The `google-vertex/*` endpoints do
not list `structured_outputs`** (only `response_format`); so `provider.require_parameters: true` with a
json_schema request steers away from Vertex. `supports_implicit_caching: false` on every Sonnet 5 endpoint.

---

## 2. Prompt caching through OpenRouter

Anthropic (docs: "supported on the Anthropic, Google Vertex AI, Azure, and Amazon Bedrock providers"):
- Two mechanisms:
  1. **Automatic**: put `cache_control: {"type":"ephemeral"}` at the **top level of the request body**; "the system automatically caches all content up to the last cacheable block". Example verbatim:
     `{"model": "...", "cache_control": {"type": "ephemeral"}, "messages": [...]}`
  2. **Explicit breakpoints**: add `cache_control: {"type":"ephemeral"}` to individual content parts; **limit of four explicit breakpoints per request**.
- System messages: yes — docs' own example caches a `system` message whose `content` is an array of `{"type":"text", ...}` parts with `cache_control` on the large part. Docs examples show system and user; whether `cache_control` is honoured on `assistant`/`tool` parts or on `tools` definitions via OpenRouter is **unconfirmed** (not stated).
- TTL: default 5 min at 1.25x input for writes, 0.1x for reads; optional 1 h via `"cache_control": {"type":"ephemeral","ttl":"1h"}` at 2x input for writes (matches catalog `input_cache_write_1h`).
- Minimum cacheable prompt (docs list): 4,096 tokens for Opus 4.5–4.8 **and Haiku 4.5**; 1,024 for Sonnet 4/4.5/4.6, Opus 4/4.1; 2,048 for Haiku 3.5. **Sonnet 5 and Opus 5 minimums are not listed — unconfirmed.**
- Usage reporting (Chat Completions): `usage.prompt_tokens_details.cached_tokens` (read) and `usage.prompt_tokens_details.cache_write_tokens` (written). A `cache_discount` value is documented on the `/generation` endpoint response; the caching page also mentions `cache_discount` generally.
- OpenAI: "automated and does not require any additional configuration"; min 1,024 tokens; reads 0.25x–0.5x; GPT-5.6+ bills writes at 1.25x and supports explicit `prompt_cache_breakpoint` on content blocks / `prompt_cache_options` at request root.
- Gemini: implicit caching (2.5+) is automatic, no write/storage cost, reads at 0.25x, min 1,024 (2.5 Flash) / 4,096 (2.5 Pro), TTL ~3–5 min. Explicit caching uses `cache_control` breakpoints; "OpenRouter will use only the last breakpoint for Gemini caching". (Endpoints API: `supports_implicit_caching: true` for gemini-3.7-flash endpoints, false for gemini-3.1-pro-preview endpoints.)
- Sticky routing: `session_id` (<=256 chars) in body or `x-session-id` header; expires after 10 min idle.

Minimal Python (OpenAI SDK) request with a cached system prompt for an Anthropic model:

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
    default_headers={"HTTP-Referer": "https://<your-app-url>", "X-OpenRouter-Title": "Cadre AI Support"},
)

resp = client.chat.completions.create(
    model="anthropic/claude-sonnet-5",
    messages=[
        {
            "role": "system",
            "content": [
                {"type": "text", "text": SHORT_INSTRUCTIONS},
                {"type": "text", "text": CADRE_KNOWLEDGE_BASE,          # large, static
                 "cache_control": {"type": "ephemeral"}},               # explicit breakpoint
            ],
        },
        {"role": "user", "content": "How do I book a call with a strategist?"},
    ],
    # alternative documented form (automatic caching): extra_body={"cache_control": {"type": "ephemeral"}}
)
d = resp.usage.prompt_tokens_details      # .cached_tokens / .cache_write_tokens (OpenRouter extension)
```
Note: OpenRouter's docs show raw JSON; that the OpenAI Python SDK forwards the non-standard
`cache_control` key inside message content parts unchanged is **unconfirmed by OpenRouter docs**
(the top-level `extra_body` form is the safe, documented path).

---

## 3. Tool calling

- Request: OpenAI shape — `tools: [{"type":"function","function":{"name","description","parameters":{JSON Schema}}}]`.
- Response: `choices[0].message.tool_calls[] = {id, type:"function", function:{name, arguments(JSON string)}}`; `finish_reason: "tool_calls"` (normalized; raw provider value in `native_finish_reason`).
- Return results with `{"role":"tool","tool_call_id": <id>, "content": <JSON-stringified result>}`.
- Docs: "The `tools` parameter must be included in every request (Steps 1 and 3) so the router can validate the tool schema on each call."
- `tool_choice`: `"auto"` (default), `"none"`, or `{"type":"function","function":{"name":"..."}}`. **`"required"` is not listed in OpenRouter's docs — unconfirmed.**
- `parallel_tool_calls`: boolean, default true; `false` forces one tool call at a time.
- Streaming: accumulate `choices[0].delta.tool_calls` across chunks; completion signalled by `finish_reason: "tool_calls"`. Exact delta fragment layout (index/id/arguments fragments) is not spelled out in the doc.
- "Interleaved thinking" is described (model reasons between tool calls); the reasoning-tokens page adds that to preserve reasoning across tool calls you pass back `message.reasoning` or `message.reasoning_details` and "the entire sequence of consecutive reasoning blocks must match the outputs generated by the model during the original request."
- No Anthropic- or Gemini-specific tool-calling caveats are stated on the tool-calling page (**unconfirmed** beyond that). Discovery: `openrouter.ai/models?supported_parameters=tools` or the same query param on `/api/v1/models`. OpenRouter tracks a per-provider "Tool Call Error Rate".

---

## 4. Streaming + usage/cost

- `stream: true` -> SSE, lines `data: {chat.completion.chunk JSON}`; keep-alive comment lines `: OPENROUTER PROCESSING` (ignore lines starting with `:`); terminator `data: [DONE]`.
- "Every stream ends with an extra chunk that carries the `usage` object for the request, sent just before the `[DONE]` message" (empty-content delta, repeats `finish_reason`).
- Mid-stream errors arrive as an SSE event with a top-level `error` field, HTTP 200, `finish_reason: "error"`. Pre-stream errors are normal JSON with 400/401/402/429/502/503.
- Cancelling: close the connection; supported providers stop processing and billing.
- Usage accounting: **`usage: {include: true}` and `stream_options.include_usage` are now deprecated — "Full usage details are now always included automatically in every response."** Fields: `prompt_tokens`, `completion_tokens`, `total_tokens`, `prompt_tokens_details.{cached_tokens, cache_write_tokens, audio_tokens, video_tokens}`, `completion_tokens_details.{reasoning_tokens, audio_tokens, image_tokens}`, `cost` (credits charged), `cost_details.upstream_inference_cost` (BYOK only, else 0/null), `is_byok`, `server_tool_use`. Docs say "credits"; `/generation` docs say `total_cost` is in USD.
- `GET /api/v1/generation?id=<response.id>` (auth required; 401 without key — verified): returns `id, upstream_id, request_id, model, provider_name, latency, generation_time, moderation_latency, tokens_prompt, tokens_completion, native_tokens_prompt, native_tokens_completion, native_tokens_reasoning, native_tokens_cached, total_cost (USD), usage, upstream_inference_cost, cache_discount, finish_reason, native_finish_reason, streamed, cancelled, created_at, data_region, is_byok, service_tier, router, provider_responses[], http_referer, user_agent, external_user, session_id, app_id, ...`. Any delay before a generation becomes queryable is **unconfirmed** (not documented).

---

## 5. Structured outputs

- `response_format: {"type":"json_schema","json_schema":{"name":"...","strict":true,"schema":{...}}}`; also `{"type":"json_object"}`.
- "Supported by select models"; support is per endpoint/provider, not just per model. Find via `?supported_parameters=structured_outputs` (models page or `/api/v1/models`). Set `provider.require_parameters: true` to route only to endpoints supporting every parameter in the request. Unsupported models return explicit errors; invalid schemas return validation errors.
- Works with `stream: true`. A "Response Healing" plugin exists for non-streaming requests.
- Catalog: sonnet-5, haiku-4.5, opus-5, gpt-5.4/5.5/5.6 family, gemini-3.1-pro-preview, gemini-3.5/3.6/3.7-flash all list `structured_outputs`. Endpoint-level gaps: Sonnet 5 on `google-vertex/*` and gpt-5.5 on `amazon-bedrock/us-east-1` lack `structured_outputs`.

---

## 6. Provider routing & fallbacks

`provider` object fields (defaults): `order: string[]` (slugs to try in order), `allow_fallbacks: true`,
`require_parameters: false`, `data_collection: "allow"|"deny"` (default allow), `only: string[]`,
`ignore: string[]`, `quantizations: string[]`, `sort: "price"|"throughput"|"latency"` or
`{by, partition: "model"|"none"}`, `max_price: {...}`, `zdr: bool` (zero-data-retention endpoints only),
`preferred_min_throughput`, `preferred_max_latency` (number or percentile object; failing endpoints are
deprioritised, not excluded), `enforce_distillable_text`.
Default routing: skip providers with outages in the last 30 s, then weight by inverse-square of price
($1/M provider gets ~9x the traffic of a $3/M one), remaining providers are fallbacks.
Slugs: base slug (e.g. `google-vertex`) matches all regions; specific `google-vertex/us-east5`.
Shortcuts: `model:nitro` = sort by throughput + priority service tier; `model:floor` = sort by price +
flex tier. (`:exacto` curated-quality variant exists; `:free`, `:batch` variants in catalog.)
Model fallbacks: `models: ["a","b",...]` in priority order (OpenAI SDK: `extra_body={"models":[...]}`);
"by default, any error can trigger the use of a fallback model" — context-length errors, moderation
flags, rate limiting, downtime. Billed at "the model that was ultimately used, which will be returned
in the `model` attribute of the response body". No documented max for `models`. (Separate
Anthropic-Messages-API `fallbacks` param: max 3, cannot be combined with `models`.)
`route: "fallback"` is in the request schema; a blog says provider failover is on by default and
`route="fallback"` just states it explicitly. `transforms: ["middle-out"]` has been superseded by the
`context-compression` plugin (`plugins: [{"id":"context-compression"}]`, disable with `enabled:false`);
compression is on by default only for endpoints with <=8,192 context.
Also: `user: "<stable end-user id>"` for abuse detection; `openrouter/auto` Auto Router (7-day
community-spend based; `allowed_models`, `excluded_models`, `cost_tier` via the `auto-router` plugin).

---

## 7. Key limits, rate limits, headers

- Documented endpoint is **`GET https://openrouter.ai/api/v1/key`** (Bearer auth). `/api/v1/auth/key` also answers (401 without auth, verified) but the docs use `/key`. Returns `data: {label, limit (null = unlimited), limit_reset, limit_remaining, include_byok_in_limit, usage, usage_daily, usage_weekly, usage_monthly, byok_usage(_daily/_weekly/_monthly), is_free_tier}`; a `rate_limit` object is present but "deprecated ... safe to ignore".
- Rate limits: only free-model (`:free`) limits are documented — 20 req/min; 50 req/day (<$10 lifetime credits) or 1,000 req/day (>=$10). **No numeric rate limit for paid models/keys is documented — unconfirmed**; docs say Cloudflare DDoS protection blocks requests that "dramatically exceed reasonable usage", 402 = out of credits/key limit, 429 = platform/DDoS/upstream limit, and OpenRouter platform 429s carry `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
- Billing: "no markup on inference pricing"; platform fee only on credit purchase (5.5%, $0.80 min via Stripe; 5% crypto).
- Headers: `Authorization: Bearer <key>`; `HTTP-Referer: <app URL>` ("required for app attribution"); `X-OpenRouter-Title` (alias `X-Title`) sets the display name and "must be paired with HTTP-Referer"; optional `X-OpenRouter-Categories`. Docs show these via the OpenAI SDK `extra_headers=` (per-call); Langfuse docs use `default_headers=` on the client.

---

## 8. Reasoning / effort control

`reasoning: {effort, max_tokens, exclude, enabled}` (legacy `include_reasoning: true|false` = `reasoning: {}` / `{exclude: true}`).
- `effort`: `"max"|"xhigh"|"high"|"medium"|"low"|"minimal"|"none"`; used natively by OpenAI reasoning models (o-series, GPT-5 series) and Grok. For Anthropic/Gemini/Qwen the effort is converted to a budget: max/xhigh ~95%, high ~80%, medium ~50%, low ~20%, minimal ~10% of `max_tokens`; `"none"` disables reasoning. Anthropic formula: `budget_tokens = max(min(max_tokens * effort_ratio, 128000), 1024)`.
- `max_tokens`: direct thinking budget for Gemini thinking models, Anthropic (min 1,024, cap 128,000), some Qwen.
- `exclude: true`: model still reasons but reasoning is not returned. `enabled: true`: default (medium) reasoning.
- Response: `message.reasoning` (string) and `message.reasoning_details[]` (`reasoning.summary` | `reasoning.encrypted` | `reasoning.text` with optional signature). Reasoning tokens are billed as output tokens; count in `usage.completion_tokens_details.reasoning_tokens`.
- Catalog also exposes `reasoning_effort` in `supported_parameters` for sonnet-5/opus-5/gpt-5.x/gemini-3.x.

---

## 9. Langfuse with OpenRouter

Confirmed by https://langfuse.com/integrations/gateways/openrouter: the Langfuse OpenAI drop-in works
with OpenRouter. Documented import is `from langfuse.openai import openai` then `openai.OpenAI(...)`
(the `from langfuse.openai import OpenAI` spelling is not shown on that page — **unconfirmed** there,
though it is the general Langfuse OpenAI-integration form). Env: `OPENAI_API_KEY=<OpenRouter key>`,
`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`.
Cost: Langfuse says enabling OpenRouter Usage Accounting means "Langfuse token and cost tracking can
directly capture the OpenRouter cost instead of calculating it" — i.e. cost is taken from the
response's `usage.cost` rather than inferred from Langfuse's model-price table (which improves accuracy
for "less popular models"). Langfuse's page still passes `extra_body={"usage": {"include": True}}`;
OpenRouter now says that flag is deprecated because usage/cost is always included. A no-code
alternative is OpenRouter's "Broadcast" setting, which forwards traces to Langfuse (no nested
tracing/custom metadata).

```python
from langfuse.openai import openai            # documented import
from langfuse import observe

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",  # OPENAI_API_KEY holds the OpenRouter key
    default_headers={"HTTP-Referer": "<YOUR_SITE_URL>", "X-Title": "<YOUR_SITE_NAME>"},
)

@observe()
def answer(question: str) -> str:
    r = client.chat.completions.create(
        model="anthropic/claude-sonnet-5",
        messages=[{"role": "system", "content": "..."}, {"role": "user", "content": question}],
        extra_body={"usage": {"include": True}},   # harmless; OpenRouter now always returns usage.cost
        name="support-answer",
    )
    return r.choices[0].message.content
```
