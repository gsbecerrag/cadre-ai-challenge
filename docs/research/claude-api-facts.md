# Claude API facts for a customer-support chatbot (TypeScript / Next.js, Python)

Source: the bundled `claude-api` skill only (base dir `/private/tmp/claude-501/bundled-skills/2.1.250/ca1d59cbecc7fd367a6c1fe71f61bc1e/claude-api`). Model table cached 2026-06-24. Anything the skill does not state is marked **not in skill**. Live docs the skill points at: `shared/live-sources.md` (pricing: `https://platform.claude.com/docs/en/pricing.md`, rate limits: `https://platform.claude.com/docs/en/api/rate-limits.md`).

---

## 1. Models, pricing, context, max output

Skill's mandated default: **`claude-opus-5`** ("ALWAYS use `claude-opus-5` unless the user explicitly names a different model … Never downgrade for cost - that's the user's decision"). Use exact IDs, never date-suffixed variants.

| Model | ID | Context | Max output | Input $/M | Output $/M | Cache read $/M (0.1x) | Cache write 5m $/M (1.25x) | Cache write 1h $/M (2x) |
|---|---|---|---|---|---|---|---|---|
| Claude Opus 5 (skill default) | `claude-opus-5` | 1M | 128K | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 |
| Claude Sonnet 5 | `claude-sonnet-5` | 1M | 128K | $2.00 | $10.00 | $0.20 | $2.50 | $4.00 |
| Claude Haiku 4.5 | `claude-haiku-4-5` (full: `claude-haiku-4-5-20251001`) | 200K | 64K | $1.00 | $5.00 | $0.10 | $1.25 | $2.00 |
| (ref) Claude Fable 5 | `claude-fable-5` | 1M | 128K | $10.00 | $50.00 | $1.00 | $12.50 | $20.00 |
| (ref) Claude Sonnet 4.6 | `claude-sonnet-4-6` | 1M | 128K | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 |

Notes:
- The skill gives only input/output prices per model. The cache columns are **derived** from the multipliers it states ("Cache reads cost ~0.1x base input price. Cache writes cost 1.25x for 5-minute TTL, 2x for 1-hour TTL") - not a per-model published table. `shared/cost-optimization.md` says to confirm the multipliers against the Pricing URL.
- Prices are first-party API rates (also apply on Microsoft Foundry). Bedrock/Vertex have separate partner pricing (links in SKILL.md).
- Opus 5 fast mode (`speed: "fast"`, beta `fast-mode-2026-02-01`) is $10/$50 - first-party only.
- Batch API: 50% off every token including cache reads/writes.
- Opus 5: thinking on by default (omit `thinking` = adaptive); `budget_tokens`, `temperature/top_p/top_k` removed (400). Sonnet 5: adaptive on by default, sampling params rejected, new tokenizer (~30% more tokens than Sonnet 4.6 for same text). Haiku 4.5: older API surface (`thinking: {type:"enabled", budget_tokens}`; `effort` errors on it). 128K output on Opus 5/Sonnet 5 requires streaming; Haiku 4.5 caps at 64K.
- Model-choice guidance (`shared/cost-optimization.md` § 2.6/2.7): chat/classification routes "often do well at `low` effort"; "Claude Haiku 4.5 answered knowledge questions at about a tenth of Claude Opus 5's cost per question at 63% accuracy versus 92% - it fits high-volume work with checkable outputs, not long agentic loops." "For most agent workloads, start with Claude Opus 5." Measure "the most capable model at lower effort" before building a multi-model cascade (caches are model-scoped).
- Effort: `output_config: {effort: "low"|"medium"|"high"|"xhigh"|"max"}`, default `high`.
- Prefill (trailing assistant message) is removed on Opus 5 / Sonnet 5 / 4.6+ family (400) - use structured outputs or system-prompt instructions.
- Live capability lookup: `client.models.retrieve("claude-opus-5")` returns `max_input_tokens`, `max_tokens`, `capabilities`.

## 2. Prompt caching

- Minimum cacheable prefix (shorter silently doesn't cache; `cache_creation_input_tokens: 0`, no error):

| Model | Minimum |
|---|---:|
| Claude Opus 5, Fable 5, Mythos 5 | 512 tokens |
| Opus 4.8, **Sonnet 5**, Sonnet 4.6, Sonnet 4.5, Opus 4.1, Opus 4, Sonnet 4 | 1024 tokens |
| Opus 4.7, Mythos Preview, Haiku 3.5 | 2048 tokens |
| Opus 4.6, Opus 4.5, **Haiku 4.5** | 4096 tokens |

- TTL: `{type: "ephemeral"}` = 5 min (default); `{type: "ephemeral", ttl: "1h"}` = 1 hour. Reads refresh the timer at no extra cost; lifetime measured from the *start* of the writing/reading request. Pick 5m for start-to-start gaps < 5 min; 1h for 5-60 min gaps (e.g. user replies after 20 min); over an hour neither helps (pre-warm with `max_tokens: 0` or accept the miss).
- Max 4 breakpoints per request. Render order `tools -> system -> messages`; breakpoint on last system block caches tools+system together. Prefix match: any byte change earlier invalidates everything after. Keep the system prompt frozen (no `Date.now()`, UUIDs, user names); put volatile content after the last breakpoint. Serialize tools deterministically.
- Top-level automatic caching: `cache_control: {type:"ephemeral"}` on `messages.create()` auto-places on the last cacheable block (best default for multi-turn chat). Robust combo for chat/agent loops: one explicit breakpoint on the static system prefix + top-level automatic for the growing conversation tail.
- Mid-conversation operator instructions: append `{role: "system", content: "..."}` to `messages[]` (Opus 5 / Opus 4.8 / Fable 5 / Mythos 5 only - **not Sonnet 5**; 400 there, fall back to a `<system-reminder>` text block in the user turn). Not available on Bedrock/Vertex/Foundry.
- Verify with `response.usage.cache_read_input_tokens` / `cache_creation_input_tokens`. Cache reads don't count toward input-token rate limits on most models (Claude API).
- Caches are per workspace (Claude API), per organization on Bedrock/Vertex; model-scoped (switching models = cold cache).
- Invalidation hierarchy: model or tool-definition change invalidates all; system-prompt change invalidates system+messages caches (tools survive); `tool_choice`/images invalidate only messages; `thinking`/`effort` change invalidates the messages cache - pin them per route.

TypeScript - mark a system prompt cacheable (from `typescript/claude-api/README.md`):

```typescript
const response = await client.messages.create({
  model: "claude-opus-5",
  max_tokens: 16000,
  system: [
    { type: "text", text: SYSTEM_PROMPT, cache_control: { type: "ephemeral" } }, // or { type: "ephemeral", ttl: "1h" }
  ],
  messages: [{ role: "user", content: "Summarize the key points" }],
});
console.log(response.usage.cache_read_input_tokens);
```

Python equivalent: `system=[{"type": "text", "text": ..., "cache_control": {"type": "ephemeral"}}]`.

## 3. Tool use

Tool definition (raw JSON; TS `Anthropic.Tool`):

```json
{ "name": "get_weather", "description": "Get current weather for a location",
  "input_schema": { "type": "object",
    "properties": { "location": { "type": "string", "description": "City and state" },
                    "unit": { "type": "string", "enum": ["celsius", "fahrenheit"] } },
    "required": ["location"] } }
```

Best practice: descriptions should say *when* to call the tool (trigger conditions), not just what it does.

`tool_choice`: `{type:"auto"}` (default), `{type:"any"}` (must use >=1 tool), `{type:"tool", name:"..."}` (force a specific tool), `{type:"none"}`. Any value may add `disable_parallel_tool_use: true`. Bedrock only: forced `tool_choice` (`tool`/`any`) requires `thinking: {type:"disabled"}`. `tool_choice` changes don't invalidate tools+system cache.

Parallel tool use is on by default; return all `tool_result` blocks in one user message; failed tools -> `tool_result` with `is_error: true`.

TS tool runner (beta): `betaZodTool({name, description, inputSchema: z.object(...), run})` from `@anthropic-ai/sdk/helpers/beta/zod` (or `betaTool()` from `.../helpers/beta/json-schema` for raw JSON Schema) + `client.beta.messages.toolRunner({model, max_tokens, tools, messages, stream?: true})`. Hooks: `setMessagesParams()`, `pushMessages()`, `generateToolResponse()`, `max_iterations`. Does not auto-resume `pause_turn`. Manual loop: loop while `stop_reason === "tool_use"`, append full `response.content`, then a user message of `tool_result` blocks.

Built-in server tools (no beta header, declared in `tools`, run on Anthropic infra):
- Web search: `{ type: "web_search_20260209", name: "web_search" }` - params `max_uses`, `allowed_domains`/`blocked_domains`, `user_location`. Result block `web_search_tool_result` (content is a list on success, an error object e.g. `{error_code:"max_uses_exceeded"}` on failure - HTTP 200). `_20260209` (dynamic filtering) needs Opus 5/4.8/4.7/4.6, Sonnet 5, or Sonnet 4.6 - do not also declare `code_execution`. Older models / Vertex: `web_search_20250305`. Availability: 1P Yes, Bedrock **No**, Vertex basic only, Foundry beta.
- Web fetch: `{ type: "web_fetch_20260209", name: "web_fetch" }` - params `max_uses`, `allowed_domains`/`blocked_domains`, `citations`, `max_content_tokens`; only fetches URLs already in the conversation. Availability: 1P Yes, Bedrock No, Vertex No, Foundry beta.
- Web search pricing: the only figure in the skill is in the Managed Agents session-budget section: "web searches at $10 per 1,000" (list cost). No Messages-API web-search price table in the skill; web-fetch pricing **not in skill**. Code execution (which `_20260209` web tools use under the hood) is "Free when used with web search/web fetch tools; otherwise $0.05/hour after 1,550 free hours/month per organization."
- Server tools may end with `stop_reason: "pause_turn"` after 10 server iterations - re-send assistant content to resume. Server tools auto-insert a 5-min cache write after results when the request already uses caching.

Structured outputs (Opus 5, Sonnet 5, Haiku 4.5, Fable 5, Opus 4.8 supported):
- JSON outputs: `output_config: { format: zodOutputFormat(Schema) }` with `client.messages.parse()` (TS: `import { zodOutputFormat } from "@anthropic-ai/sdk/helpers/zod"`; read `response.parsed_output`). `output_format` param is deprecated - use `output_config.format`.
- Strict tool use: `strict: true` on the tool definition; schema needs `additionalProperties: false` + `required`.
- Schema limits: no recursive schemas, no min/max/minLength/maxLength (SDK strips and validates client-side). First request with a new schema pays a compile cost; 24h schema cache. **Incompatible with citations (400)** and prefill. Works with streaming, batches, thinking.

MCP connector (beta `mcp-client-2025-11-20`): `mcp_servers=[{type:"url", url, name}]` + `tools=[{type:"mcp_toolset", mcp_server_name}]` - both required. Not on Bedrock/Vertex.

## 4. Agent Skills via the API

- Messages API Agent Skills (beta): `client.beta.messages.create({ container: { skills: [{ type: "anthropic", skill_id: "pptx", version: "latest" }] }, tools: [{ type: "code_execution_20260521", name: "code_execution" }], betas: ["code-execution-2025-08-25", "skills-2025-10-02"], ... })`. Requires **both** beta headers and the code-execution tool; skills execute inside the code-execution container. Outputs come back as file IDs, downloaded via Files API. Availability: 1P beta, P-AWS beta, Foundry beta, Bedrock/Vertex No.
- The Messages-API examples show only `type: "anthropic"` (pre-built `pptx`/`xlsx`/`docx`/`pdf`). Whether `container.skills` accepts `type: "custom"` on the Messages API is **not in skill**.
- Custom skills exist via the **Skills API** (`skills-2025-10-02`): `POST /v1/skills`, `GET /v1/skills`, `POST /v1/skills/{id}/versions`, etc. (also `ant beta:skills` CLI). The skill folder/`SKILL.md` format is the same as repo skills ("Each skill is a folder with a `SKILL.md`. The skill's description sits in context by default; Claude reads the full file when the task calls for it"). The request body/upload shape for `POST /v1/skills` (zip vs files) is **not in skill** - WebFetch `https://platform.claude.com/docs/en/agents-and-tools/skills.md`.
- Custom skills are documented as attachable on **Managed Agents** agents: `skills: [{ type: "custom", skill_id: "skill_abc123", version: "latest" }]` (max 20 per agent), or auto-discovered from a mounted GitHub repo's `.claude/skills/<name>/SKILL.md`. Managed Agents is 1P/P-AWS beta only (no Bedrock/Vertex/Foundry).
- Practical note for a "PII handling" skill on a plain chat API: the skill's own guidance is that Skills == container/code-execution feature; for chat-time instructions the documented lightweight options are the system prompt and (Opus 5, not Sonnet 5) mid-conversation `role: "system"` messages.

TS snippet (from `typescript/claude-api/tool-use.md`):

```typescript
const response = await client.beta.messages.create({
  model: "claude-opus-5", max_tokens: 16000,
  container: { skills: [{ type: "anthropic", skill_id: "pptx", version: "latest" }] },
  tools: [{ type: "code_execution_20260521", name: "code_execution" }],
  betas: ["code-execution-2025-08-25", "skills-2025-10-02"],
  messages: [{ role: "user", content: "Create a 3-slide deck about X." }],
});
```

## 5. Citations / Files API

- Citations (no beta): set `citations: { enabled: true }` on each `document` content block (all or none). Response is split into multiple `text` blocks; cited blocks carry a `citations` array with `cited_text`, `document_index`, `document_title`, and a location by `type`: `char_location` (`start_char_index`/`end_char_index`, plain text), `page_location` (1-indexed pages, PDF), `content_block_location` (custom content). Incompatible with `output_config.format` (400). Availability: Yes on 1P/P-AWS/Bedrock/Vertex, beta Foundry. Toggling citations invalidates the tools cache tier.
- Passing documents:
  - Base64 PDF (no beta): `{ type: "document", source: { type: "base64", media_type: "application/pdf", data }, title?, citations? }` placed before the text block. Limits 32 MB request, 600 pages (100 on 200K-context models).
  - Files API (beta `files-api-2025-04-14`, needed on upload **and** the `messages.create` that references it): `client.beta.files.upload({ file: await toFile(fs.createReadStream("report.pdf"), undefined, { type: "application/pdf" }), betas: [...] })` -> `{ type: "document", source: { type: "file", file_id: uploaded.id }, title: "Q4 Report", citations: { enabled: true } }` (PDF/text). 500 MB/file, 100 GB/org, files persist until deleted, uploads free, content billed as input tokens. Not on Bedrock/Vertex.
  - Exact source shape for inline plain-text / custom-content documents: **not in skill** (only implied by the `char_location`/`content_block_location` citation types). "Search results content blocks" are listed as a feature in `platform-availability.md` but their shape is **not in skill**.
- Web fetch tool also has a `citations` param.

## 6. Streaming in TypeScript

- Recommended: `const stream = client.messages.stream({...})`; iterate `for await (const event of stream)` filtering `content_block_delta` / `text_delta`, or `stream.on("text", delta => ...)`; then `await stream.finalMessage()` for the full `Anthropic.Message` (usage, stop_reason). Don't wrap `.on()` in `new Promise()`. Default `max_tokens` ~64000 when streaming (~16000 non-streaming). Buffer a few tokens before DOM updates for web UIs. Raw SSE events: `message_start`, `content_block_start`, `content_block_delta`, `content_block_stop`, `message_delta` (stop_reason, usage), `message_stop`.
- Thinking display: if streaming reasoning to users, set `thinking: {type:"adaptive", display:"summarized"}` (default `omitted` on Opus 5/Sonnet 5 shows as a long pause).
- Streaming + tools: `client.beta.messages.toolRunner({..., stream: true})` yields a stream per iteration; or manual loop with `client.messages.stream()` + `finalMessage()`.
- SDK: the skill mandates the official `@anthropic-ai/sdk` (`npm install @anthropic-ai/sdk`; `new Anthropic()` reads `ANTHROPIC_API_KEY`). "Never fall back to OpenAI-compatible shims." Vercel AI SDK / `@ai-sdk/anthropic`: **not in skill** (never mentioned).
- Client config: TS `timeout` is in **milliseconds** (default 10 min; auto-scaled up to 60 min for large non-streaming `max_tokens`); `maxRetries` default 2 (retries 408/409/429/5xx). Per-request: `client.messages.create({...}, { timeout: 5_000 })`.
- Errors: `Anthropic.BadRequestError`, `AuthenticationError`, `RateLimitError`, `APIConnectionError` (check before `APIError` - it is a subclass in TS), `APIError` (has `.status`, `.type`).

## 7. Rate limits / tiers / batch

- No RPM/TPM tier table in the skill. 429 causes: "Exceeded requests per minute (RPM) / tokens per minute (TPM) / tokens per day (TPD)". Headers: `retry-after`, `x-ratelimit-limit-*`, `x-ratelimit-remaining-*`. SDKs auto-retry 429/5xx with exponential backoff (`max_retries` default 2). Python example reads `e.response.headers.get("retry-after")`.
- Pool facts: Claude Opus 5 is a **separate rate-limit bucket** from the combined Opus 4.x pool; Haiku 4.5 has its own pool separate from Haiku 3/3.5 ("may need a tier bump for the same volume"); fast mode has its own limit; cache reads don't count toward input-token limits on most models (raises effective throughput). Rate limits are "tier-based"; live table: `https://platform.claude.com/docs/en/api/rate-limits.md`.
- How to raise limits: procedure **not in skill** (only "check your tier's limits" / "tier bump"). Admin API (beta, `client.beta.organization`) exposes org and workspace rate-limit reports (`GET /v1/organizations/rate_limits`, `.../workspaces/{id}/rate_limits`).
- Priority Tier exists (`service_tier` dimension in usage reports) but "does not cover Claude Opus 5" - also excludes Sonnet 5 and Mythos; supported on Fable 5 / Opus 4.8 and others. Pricing/mechanics **not in skill**.
- Batch API: `client.messages.batches.create({requests:[{custom_id, params}]})`, poll `retrieve(id).processing_status === "ended"`, iterate `results(id)` keyed by `custom_id`. 50% off all tokens (stacks with caching), up to 100,000 requests / 256 MB per batch, most finish < 1 h, max 24 h, results kept 29 days, no mid-batch tool loop, 1P/P-AWS only (not Bedrock/Vertex/Foundry). Relevance to live chat: none for user-facing turns ("A user is waiting" -> not batch); useful for offline evals, backfills, summarization jobs.
- Concurrency and caching: N parallel identical-prefix requests all miss until the first response starts streaming - fire one, await first token, then the rest.

## 8. Bedrock / Vertex / OpenRouter / other platforms

- **OpenRouter: not in skill** (no mention anywhere).
- **Amazon Bedrock** (partner-operated): use `AnthropicBedrockMantle` (`@anthropic-ai/bedrock-sdk` -> `new AnthropicBedrockMantle({ awsRegion })`; Python `from anthropic import AnthropicBedrockMantle`). Model IDs get an `anthropic.` prefix: `anthropic.claude-opus-5`, `anthropic.claude-sonnet-5`, `anthropic.claude-haiku-4-5`. Feature gaps: no web search, no web fetch, no code execution, no Agent Skills, no MCP connector, no Managed Agents, no Batches, no Files API, no Models API, no mid-conversation system messages, no server-side fallbacks, no fast mode, no task budgets, no `inference_geo`, no programmatic tool calling, no advisor tool. Supported: messages/streaming/tool use, PDF, structured outputs/strict tools, adaptive thinking/effort, prompt caching 5m+1h and automatic caching (legacy Bedrock integration on Opus 4.6-and-earlier rejects top-level `cache_control`), token counting, citations, tool search (InvokeModel only), compaction/context editing (beta). Forced `tool_choice` needs `thinking: {type:"disabled"}`. Caches isolated per organization. Separate partner pricing.
- **Google Vertex AI**: `AnthropicVertex` (`@anthropic-ai/vertex-sdk` -> `new AnthropicVertex({ projectId, region })`, region `"global"` recommended; auth via GCP ADC). Model IDs have **no prefix** (`claude-opus-5`, `claude-sonnet-5`); dated snapshots use `@` (e.g. `claude-opus-4-5@20251101`). Gaps: web search basic `web_search_20250305` only, no web fetch, no code execution, no Agent Skills, MCP connector, Managed Agents, Batches, Files API, Models API, mid-conversation system messages, server-side fallbacks, fast mode, task budgets, `inference_geo`. Prompt caching (5m/1h, automatic), citations, structured outputs, thinking/effort supported. Separate partner pricing.
- **Microsoft Foundry**: `@anthropic-ai/foundry-sdk` (`new AnthropicFoundry({...})`); billed at standard Anthropic API rates; most features beta; no Batches/Models API/Managed Agents/mid-conversation system/fallbacks.
- **Claude Platform on AWS** (Anthropic-operated, same-day parity): `@anthropic-ai/aws-sdk` -> `new AnthropicAws()`; bare model IDs; needs `AWS_REGION` + `ANTHROPIC_AWS_WORKSPACE_ID`; full first-party surface except fast mode and cache diagnostics.
- Third-party clients expose the same `messages.create` / `.stream` surface; do not use `new Anthropic({ baseURL })` for them. Refusal fallbacks on Bedrock/Vertex/Foundry use the client-side `betaRefusalFallbackMiddleware` instead of the server-side `fallbacks` param.
