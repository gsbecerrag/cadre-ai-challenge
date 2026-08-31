# Design brief — Claude Design artboards

Source: `Cadre Support Chat.dc.html` (638 lines) and `Strategist Console.dc.html` (255 lines), both Claude Design `.dc.html` artboards with `{{ }}` bindings and a `Component extends DCLogic` mock-data/logic block. The designer's screen map (`github.md`) is kept as [`claude-design-screen-map.md`](claude-design-screen-map.md); rulings on spec-vs-design mismatches are in [`README.md`](README.md).

---

## 1. Tokens

**Color — neutrals / surfaces**
- `#faf9f6` — page/app background (body, chat message area, Portal background)
- `#fff` — card/panel/bubble background, header bars, bot chat bubbles
- `#f2efe4` — cream accent: hero gradient stop, citation-chip background, Walkthrough Card header band, Portal "demo" badge bg, Triage "Knowledge gap" chip bg, Console active-nav-tab bg
- `#e5e5e5` — default borders (cards, inputs, nav divider, quick-reply chips, message bubble border)
- `#eee` / `#f4f4f4` — lighter dividers (nav rail border, table row divider)
- `#333` — default body text
- `#4c4c4c` — secondary body copy (escalation body text, request-panel field values)
- `#666` — muted secondary text (nav links, timestamps, sub-labels)
- `#999` — muted tertiary text/labels (uppercase section eyebrows, offline presence dot, "Ended" state color, muted score)
- `#b3b3b3` — faintest muted (partner-logo wordmarks, inactive EN/ES text, unchecked qualification-signal mark/color)
- `#ccc` — disabled affordances (muted calendar days, inactive toggle track, disabled send button, dashed KB-suggestion border)

**Color — brand / accent**
- `#0c0407` — near-black brand ink: primary buttons, nav CTA, headings, avatar bg, chat header gradient start, in-call banner bg, Console strategist-avatar bg, selected-card border, user chat bubble bg
- `#3a3236` — chat header gradient end (`linear-gradient(115deg,#0c0407,#3a3236)`)
- `#db4545` — coral accent/error/urgency: hero H1 color, link hover, avatar "C" bg, send-button active bg, End-call button, decline-hover border, pending-state color/badge, "Wrong escalation" chip text, escalation card left-border, live-call pulse dot, calendar selected-day bg, high-severity text
- `#08749b` — link color (default `a` tag) and active screen-share icon bg
- `#0a7d43` — success green: thumbs-up hover border, Portal "● Live" status, In-call state color/score-≥4 color, checked qualification-signal mark

**Color — state-specific**
- Chat presence dot: online `#3ddc84`, offline `#999`
- Console availability toggle: online track `#0a7d43` / knob left `20px`; offline track `#ccc` / knob left `2px`
- Handover request state colors (Console `stateMeta`): `pending` → `#db4545` (pulsing), `in_call` → `#0a7d43` (pulsing), `ended` → `#999` (static)
- Score color: `#0a7d43` if score ≥ 4, else `#996` (olive)
- Triage category chip: "Knowledge gap" → bg `#f2efe4` / text `#996`; "Wrong escalation" → bg `#fdeaea` / text `#db4545`
- Triage severity text: MEDIUM `#996`, HIGH `#db4545`

**Typography**
- Body font: `Inter` (weights 400/500/600/700), fallback Arial/sans-serif
- Display font: `'Inter Tight'` (weights 500/600/700), fallback Helvetica — used for all headings, hero H1, panel `h2`s, logo wordmark label, chat header title
- Hero H1: 64px/600, letter-spacing -3px; section H2s: 38px/600 (site) and 24–26px/600 (Console/Portal panel headers)
- Body copy: 13–15px; eyebrow/uppercase labels: 10.5–12px/700, `letter-spacing:1px`, `text-transform:uppercase`, color `#999`
- Monospace (no family declared, browser default monospace): session ids, trace ids, score fractions, citation chips, Daily room URL, eval-case text

**Radii**
- 48px "pill" — every button, badge, chip, toggle track, calendar time-slot, portal demo badge, citation chip
- 30px — site marketing cards, dark CTA banner
- 20–24px — chat panel container, Portal stat cards, Callbacks table, Triage report cards, Console request cards, in-call banner
- 16px — message-kind cards (esc/walk/lead/offer/callback/calendar/ended), Console qualification/request/conversation panels
- 12px — Console/Portal nav-tab rows, KB/eval dashed boxes, sharing-indicator corner
- 14px / 16px 16px 4px 16px (etc.) — asymmetric bubble radii: bot bubble `16px 16px 16px 4px`, user bubble `16px 16px 4px 16px`; Console convo bubbles use `14px 14px 4px 14px` (user) / `14px 14px 14px 4px` (bot)
- 6px — escalation card's sharp corner (`border-radius:6px 16px 16px 6px`, paired with 3px solid `#db4545` left border)
- 50% — all avatars, launcher button, call-control buttons, calendar day cells, typing dots, presence/pulse dots

**Shadows**
- `0 8px 24px rgba(12,4,7,0.3)` — chat launcher button
- `0 16px 48px rgba(12,4,7,0.22)` — open chat panel
- `0 4px 16px rgba(0,0,0,0.05)` — hand-over offer card
- `0 6px 20px rgba(0,0,0,0.18)` — in-call control pill bar
- `0 1px 3px rgba(0,0,0,0.25)` — availability-toggle knob

**Animations**
- `tdot` (1.2s infinite, staggered +0.15s/+0.3s) — typing-indicator three-dot bounce (`translateY`/opacity)
- `livepulse` (1.4–1.6s infinite, opacity 1↔0.45) — "live" pulse dots: call-view live pill, Console in-call banner dot, Console queue-card state dot when pending/in_call
- `spinring` (0.9s linear infinite, `rotate(360deg)`) — connecting spinner ring (border-top `#db4545`)
- `msgin` (0.2s ease, opacity+translateY 6px→0) — every new chat message's entrance

---

## 2. Artboard: Cadre Support Chat

Top-level `state.view` toggles two full-bleed backgrounds (`site` / `portal`); the chat launcher+panel float above both via `position:fixed` and are independent of `view`.

### 2.1 Mock site (`siteView`, default view)
- Sticky nav (`position:sticky;top:0`), 18px/48px padding: Cadre AI logo (SVG), inline nav labels "Services", "Industries", "Case Studies", "About" (decorative, hover-color only, no handlers), "Console →" link (routes to `Strategist Console.dc.html`), button **"Talk to an AI Strategist"** → `openChat`.
- Hero (gradient `#f2efe4`→`#fff`, centered, max-width 820/560px): eyebrow pill **"Cadre AI — Anthropic & OpenAI Partner"**; H1 **"From AI Confusion to AI Confidence."**; body **"We help you pinpoint the right AI opportunities, implement them seamlessly, and deliver real business impact."**; buttons **"Talk to an AI Strategist →"** (`openChat`) and **"See How the Intensive Works"** (no handler, decorative).
- Partner strip: eyebrow **"Partnering with the best"**; wordmarks OpenAI, Anthropic, Microsoft, Snowflake, Salesforce, AWS, Meta (plain text, no logos).
- 3-card grid, heading **"Set your team up to succeed with AI"**: **"Drive Revenue"** / "Find the highest-impact AI opportunities, department by department."; **"Increase Profitability"** / "Select and configure the LLMs that best align with your tech stack and goals."; **"Elevate Employees"** / "Shift the culture with training and champions in every department."
- Dark CTA banner (`#0c0407`, rounded 30px, max-width 1080px): **"Track your AI results"** + "Cadre gives you a centralized portal to track tools, agents, training, and results. Stay aligned, stay accountable, and scale what works." + button **"Get Your AI Results"** → `openPortal`.
- Footer (`#f2efe4`): logo + **hello@gocadre.ai · (619) 324-3223 · San Diego, CA**.

### 2.2 Demo Portal (`portalView`)
- Header: logo, label **"Portal"**, badge **"Demo portal · mock data"**, button **"← Back to site"** → `backToSite`.
- Left nav (210px), 4 tabs (`portalTabs`, default selected = `results`): **Dashboard**, **Tools**, **Agents**, **Results & Training**. Selecting a tab only swaps the `h2`/subtitle pair — the stat cards and table below are static mock data regardless of tab:
  - Dashboard → "Dashboard" / "Company-wide AI overview"
  - Tools → "Tools" / "Activated AI features across your stack"
  - Agents → "Agents" / "Deployed agents and their owners"
  - Results & Training → "Results & Training" / "What your agents saved this month"
- 3 stat cards (max-width 760px): **"Hours saved / mo" = 265** (accent red number), **"Active agents" = 4**, **"Team trained" = 82%**.
- Table, columns "Agent / Runs / mo / Hours saved / Status": Lead Processing Agent (1,540 / 45), Proposal Automation (96 / 160), Email Agent (4,120 / 48), Invoice Query Resolver (310 / 12); every row's Status is a hardcoded **"● Live"** in `#0a7d43`.

### 2.3 Chat launcher (collapsed state)
Fixed bottom:24px/right:24px, 58×58 circle, `#0c0407` bg, "…" glyph, hover `scale(1.06)`. `onClick` = `toggleChat` → opens panel and calls `start()` (idempotent — guarded by `state.started`).

### 2.4 Chat panel shell (`chatOpen`)
Fixed, two size states via `panelGeom`: docked `bottom:96px;right:24px;width:392px;height:min(660px, calc(100vh - 130px))`; expanded `inset:20px` (near-fullscreen). Both `border-radius:24px`.
- Header (gradient `#0c0407→#3a3236`): avatar "C" (red circle), title `t_headerTitle` = **"Cadre AI Assistant"** (ES: "Asistente de Cadre AI"), presence row = colored dot + **"A strategist is online"** (green, when `strategistOnline` prop true) or **"Strategists are offline — we still reply instantly"** (gray); EN/ES pill toggle (`toggleLang`); expand icon "⤢" (`toggleExpand`); close icon "×" (`toggleChat`).
- Body switches between **Chat view** (`chatViewOn`, default) and **Live call view** (`callViewOn`) based on `state.callState`.

### 2.5 Chat view — message kinds (`sc-for messages`)
Each message row is one of 9 kinds, all entering with `msgin`:
1. **text** — plain bubble (user: black/right; bot: white/left), optional citation chips row below (monospace, `#666` on `#f2efe4` pill, e.g. `[services#what-cadre-does]`).
2. **typing** — bot-only, white bubble with 3 bouncing dots (`tdot`), shown for a scripted delay (default 900ms) before every bot reply.
3. **esc (Escalation card)** — 3px `#db4545` left border, sharp/round corner mix; title (`escTitle`), body text, boxed "next step" line (**"Next step:"** label + `escNext` text), optional citations. Used for pricing questions and the generic fallback.
4. **walk (Walkthrough Card)** — cream header band with title, numbered steps (circular numbered badges), CTA button → `openPortalFromChat`, optional citations.
5. **lead** — "Your details" capture form: inputs "Full name" / "Work email" / "Company", button "Share details"; transitions to a done state showing "✓ Details shared with the strategist".
6. **offer (hand-over offer)** — centered card, headline text, Yes/No buttons; transitions to a done state showing only `doneText` ("Connecting…" or "No problem — offer stays open on our side.").
7. **callback** — confirmation card with title, body text, boxed name/company/email summary.
8. **calendar** — month label, day-of-week header row, day grid (Sept 2026 hardcoded, Sep 1 = Tuesday), 4 time-slot pills, "Schedule callback" button; done state shows "✓ Callback scheduled — Sep {day}, {slot}".
9. **ended** — "Call ended" card, body **"How was your conversation with Angel?"**, thumbs 👍/👎 buttons; done state shows only `doneText` (thanks or apology copy).

**Verbatim copy (EN)**: greeting — *"Hi there — I'm Cadre's AI assistant. I answer from what Cadre publishes, with a citation for every claim. What can I help with?"* Quick replies: *"What does Cadre AI do?"*, *"What does it cost?"*, *"Where do I see my agents' results?"*, *"Talk to a strategist"*. Services answer: *"Cadre AI is a consultancy focused on using AI to drive real revenue growth and improve EBITDA. Four core services:\n\n• AI Strategy — the 45-day AI Transformation Intensive\n• AI Leadership & Facilitation — workshops and intensives\n• AI Engineering — automation, integrations, custom agents\n• AI Agents — from prompts to fully fledged agents\n\nEngagements start with the AI Maturity Index: a score across the eight-pillar framework with a grade in each area."* (citations `services#what-cadre-does`, `maturity-index#scoring`). Pricing escalation title *"Cadre doesn't publish pricing"*, body *"I can't quote a price for Strategy, Facilitation, Engineering, or Agents engagements — Cadre doesn't publish them. The only published price is the PE AI Value Creation Playbook at $5,000 per firm."* (citations `not-published#pricing`, `events#pe-playbook`), next-step *"A strategist can scope your engagement — I can connect you right now, or you can write hello@gocadre.ai / (619) 324-3223."* Portal answer *"Here's where that lives — the Portal tracks tools, agents, training, and results:"* (citation `portal#tracking`) then Walkthrough Card *"See your agents' results in the Portal"* with steps *"Open the Cadre Portal from your welcome email"* / *"Go to Results & Training in the left menu"* / *"Pick an agent to see runs, hours saved, and training coverage"*, CTA *"Open demo Portal"* (citation `portal#results`). Lead intro *"Happy to set that up. Mind sharing a few details so the strategist joins informed?"*; ack *"Thanks {firstName}! You're all set."* Offer text *"Do you want to jump into a call with our experts?"* (Yes / "Keep chatting"). Decline copy *"No problem — I'm right here if you change your mind. What else can I help with?"* Callback title *"A strategist will call you back"*, body *"No strategist can join right now. I've logged a callback with your details — or pick a time that suits you below."* Generic fallback (unmatched free text) *"I don't have that information in what Cadre publishes, so I won't guess. Next step: write hello@gocadre.ai, call (619) 324-3223, or use the contact form — or I can connect you with a strategist."* (citation `not-published#general`). Full parallel Spanish strings exist for every line above (`T()` returns an `es` object).

Below the transcript: quick-reply chip row (`hasQuick`, hidden during calls) and the input bar (placeholder **"Ask about services, industries, pricing…"**, send button `↑`, red when text present else gray).

### 2.6 Live call view (`callViewOn`)
Two sub-states on `state.callState`:
- **connecting** — centered spinner (`spinring`) + *"Connecting you with a strategist…"*.
- **live (inCall)** — top bar: *"You're being assisted by"* + name badge **"ANGEL"**, plus a black "live" pill with pulsing red dot. Video area: `<image-slot>` placeholder labeled "strategist video feed — drop an image"; self-view box top-right labeled "you" (visible when `camOn`); "Sharing your screen" badge top-left (visible when `sharing`). Floating control pill (bottom-center): mic toggle (🎙/🔇, red when muted), camera toggle (🎥/⊘, red when off), share-screen toggle (⇱, blue `#08749b` when active), end-call (✆, always red) → `endCall`.

### 2.7 State transitions (from `renderVals`/handlers)
`toggleChat`/`openChat` → opens panel, `start()` pushes greeting + 4 quick replies (once). `handleQuick(id)`/free-text `send()` (keyword-routed EN+ES regex) → `answer(id)` dispatches to services/pricing/portal/strategist/unknown. `answer('strategist')` skips the lead form and jumps straight to `makeOffer()` if `leadDone` is already true; otherwise shows lead-intro text then the lead form. `submitLead()` validates non-empty name, marks lead card done, sends an ack, then after 1.6s calls `makeOffer()`. `makeOffer()` is idempotent (`offerMade` guard). `acceptOffer()`: if **both** demo-control props `strategistOnline` and `liveHandoverEnabled` are true → `callState:'connecting'` then after 2.2s `callState:'live'`; **otherwise** → posts the callback confirmation card immediately followed (1.5s) by the calendar-picker card — this is the artboard's only representation of a "no strategist available" path, and it is modeled as a chat message flow, not a Handover Request state. `declineOffer()` closes the offer card and sends the decline line. `endCall()` clears `callState` and posts the 'ended' feedback card. `schedule()` closes the calendar card with a scheduled-confirmation string. `feedback(up)` closes the 'ended' card with thanks/apology copy. `toggleLang()` swaps all future `T()` strings EN↔ES but does not retranslate already-rendered messages. Two designer-exposed demo props (`data-props`) drive the divergent path: `strategistOnline` (default true) and `liveHandoverEnabled` (default true) — set either false to force the callback/calendar branch instead of the live video branch.

---

## 3. Artboard: Strategist Console

Single-page shell: header + 200px left nav + one of three tab bodies (`queueOn` / `callbacksOn` / `triageOn`, from `state.tab`).

**Header**: logo, label **"Strategist Console"**, link **"← Visitor chat demo"** (routes to `Cadre Support Chat.dc.html`); Availability control = colored label (**"Online"** `#0a7d43` / **"Offline"** `#999`) + pill toggle (`toggleAvail`, track `#0a7d43`/`#ccc`, knob 20px/2px); identity block = avatar circle **"A"** + **"Angel M."** / **"angel@gocadre.ai"**. Note: this Availability toggle is a separate local `state.online` boolean, not wired to the chat artboard's `strategistOnline` demo prop — the two "online" signals are disconnected mocks.

**Left nav** (`navTabs`): **"Handover queue"** (badge = live count of `pending` requests), **"Callbacks"** (badge 0, hidden), **"Triage"** (badge 0, hidden). Active tab: weight 600, color `#db4545`, bg `#f2efe4`; inactive: weight 500, `#666`, transparent.

### 3.1 Handover queue tab (`queueOn`)
- Left list (340px), eyebrow **"Handover requests"**, cards per request: name, state badge (pulsing dot + **Pending**/**In call**/**Ended**, colored per `stateMeta`), "{company} · {industry}" line, relative time + **"score {n}/5"** (monospace, green if ≥4 else olive). Selected card gets a black border. Click → `go` selects the request.
- Detail pane: `h2` name; "{company} · {industry} · {email} · {phone}" line. Action buttons: **"Claim & join call"** (black pill, shown only when state = `pending`) → `joinCall` (sets state → `in_call`); **"End call"** (red pill, shown only when state = `in_call`) → `endReq` (sets state → `ended`).
- **In-call banner** (state = `in_call` only): black rounded bar, pulsing red dot, **"In call — Daily room open in the chat panel"**, monospace **"daily.co/cadre-{id}"**.
- Two-column grid:
  - **Qualification panel** — header **"Qualification · {score}/5"**; 5 signal rows, each ✓ (`#0a7d43`) or — (`#b3b3b3`) + label.
  - **Request panel** — header **"Request"**; fields *Mode* (e.g. "Video (Daily)"), *State* (colored label), *Session* (monospace id), *Trace* (monospace id + "↗", placeholder link).
- **Conversation panel** — header **"Conversation so far"**; replays the request's `convo` array as chat bubbles (user right/black, bot left/cream).

### 3.2 Callbacks tab (`callbacksOn`)
Heading **"Callbacks"**; table (max-width 860px), columns **Lead / Contact / Requested / Scheduled for / Score**. Rows: Jordan Lee (Harbor Retail Group, jordan@harborretail.com, (310) 555-0119, "Today, 9:41 AM", "Sep 8, 10:30 AM", 4/5); Priya Nair (Northgate Lending, priya@northgate.com, (646) 555-0102, "Yesterday", "Sep 9, 1:00 PM", 3/5); Tom Aldana (Vista Hospitality, tom@vistahosp.com, (858) 555-0166, "Yesterday", "Sep 10, 9:00 AM", 4/5).

### 3.3 Triage tab (`triageOn`)
Heading **"Triage reports"**, subtitle **"Written by the Triage Agent on every thumbs-down. Newest first."** Report cards (max-width 760px): category chip + severity label + timestamp + **"Open trace in Langfuse ↗"** link; summary paragraph; italicized quoted evidence block on cream bg; two dashed side-by-side boxes **"Suggested KB addition"** and **"Suggested eval case"** (monospace).

Sample reports: (1) category "Knowledge gap" (MEDIUM), summary about a visitor asking for SOC 2 documentation that the Assistant correctly escalated but couldn't back with published commitments; evidence *"It just said it couldn't confirm anything — I needed the security basics for my vendor form."*; KB suggestion *"Add the three /ai-engineering data-security commitments (black-box data, never used to train, secure compliant tools) to security#commitments so escalations can cite them."*; eval case `trap: "Do you have SOC 2?" → escalate + cite security#commitments`. (2) category "Wrong escalation" (HIGH), summary about the Assistant offering the contact form to an existing client asking about Portal access instead of explaining Cadre-team provisioning; evidence *"I'm already a client — the contact form loops me back to sales."*; KB suggestion *"Clarify portal#access: existing clients get access through their Cadre team; hello@gocadre.ai is the fallback."*; eval case `in-kb: "How do I log into the portal?" → cite portal#access, no form-only answer`.

### 3.4 State machine implied by `reqStates`
Enum is exactly 3 values: `pending → in_call → ended`. Seed data starts all three states simultaneously (r1=pending, r2=in_call, r3=ended) purely to demo every card style at once. Transitions are one-way button clicks with no intermediate "claimed but not yet joined" moment — `joinCall()` jumps `pending` straight to `in_call`, `endReq()` jumps `in_call` straight to `ended`. There is no `declined` or `no_strategist_available` state, and no way to reopen an `ended` request.

---

## 4. Data shapes implied

**Lead** (chat-side capture, `state.leadName/leadEmail/leadCompany/leadDone`): `{ name, email, company }`, plus a `done` boolean flag once submitted. Defaults used if a call is accepted without a filled form: `"Alex Rivera" / "alex@acme.co" / "Acme Co"`.

**Handover Request** (Console `data()` item): `{ id, name, company, industry, email, phone, time, score (0–5 int), mode (string), session (string id "sess_…"), trace (string id "tr_…"), signals: [ [label, boolean] × 5 ], convo: [ [role, text] × n ] }`, plus externally-keyed `reqStates[id]: 'pending'|'in_call'|'ended'`.

**Callback** (Console `callbacks` array item): `{ name, company, email, phone, requested (relative label), slot (concrete scheduled date/time string), score (0–5 int) }`.

**Triage Report** (Console `reports` array item): `{ category, catBg, catColor, severity ('MEDIUM'|'HIGH'), sevColor, time, summary, evidence (visitor's own words, quoted), kb (suggested KB text incl. a `topic#heading` ref), evalCase (string, format `<kind>: "<question>" → <expected behavior + citation>`) }`.

**Qualification Signal**: tuple `[label: string, on: boolean]`, rendered as `{ label, mark: '✓'|'—', color: '#0a7d43'|'#b3b3b3' }`. The five labels, **verbatim, in fixed order**: **"Decision authority"**, **"Budget conversation welcome"**, **"Timeline < 6 months"**, **"Fit industry"**, **"Team size stated"**.

**Chat message** (`state.messages` item): `{ id, role: 'bot'|'user', kind: 'text'|'typing'|'esc'|'walk'|'lead'|'offer'|'callback'|'calendar'|'ended', text?, citations?: string[], open?: boolean, done?: boolean, doneText?, + kind-specific fields (escTitle/escNextLabel/escNext, walkTitle/steps/walkCta, leadTitle, yesLabel/noLabel, cbTitle/cbName/cbCompany/cbEmail, endTitle) }`.

**Citation**: plain string, `topic#heading` shorthand (e.g. `industries#construction`, `case-studies#supplier-automation`, `maturity-index#pe`, `not-published#pricing`, `portal#results`), rendered as a small monospace pill; a single message can carry multiple citation chips.

---

## 5. Vocabulary check

| Design string / concept | Canonical term | Verdict |
|---|---|---|
| "Cadre AI Assistant" (chat header) | Assistant | Match |
| No "Visitor" label anywhere; internal field is `role: 'user'` | Visitor | **Mismatch** — design's data model calls the human party `user`, never `visitor` |
| Console field "Session" = `sess_8f2ka1` | Session | Match |
| No concept of individual conversational Turns anywhere | Turn | **Absent** — not modeled at all |
| "Strategist Console", "A strategist is online", "assisted by … ANGEL" | Strategist | Match |
| "Strategist Console" | Console | Match |
| Toggle labeled "Online"/"Offline", state var `online` | Availability (online/offline) | Match on labels; underlying field name is `online`, not `availability`, and it's duplicated/disconnected between the two artboards (Console's local toggle vs. chat's `strategistOnline` prop) |
| Callbacks table column "Lead" | Lead | Match, but no "Qualified Lead" badge/state exists anywhere |
| Lead-capture card titled "Your details" / done text "Details shared with the strategist" | Contact Details | **Mismatch** — design never says "Contact Details"; also no such labeled section in the Console's Request panel (email/phone are inline under the name header, not a separate block) |
| Console "Qualification · {n}/5" panel, request-card "score {n}/5" | Qualification Score (0–5, threshold 3) | Scale matches (0–5); no visible "qualified" threshold indicator (r3 scores exactly 3 with no distinguishing treatment) |
| 5 signal labels: Decision authority / Budget conversation welcome / Timeline < 6 months / Fit industry / Team size stated | 5 spec signals: industry fit / company size or role / concrete initiative or pain / timeline or budget / explicit intent | **Substantive mismatch** — only "Fit industry" cleanly maps to "industry fit"; "Timeline < 6 months" and "Budget conversation welcome" split what the spec bundles as one "timeline or budget" signal; "Team size stated" covers only company-size, not role; design has **no signal for "a concrete initiative or pain"** and no explicit "intent" signal; design instead adds **"Decision authority,"** which has no counterpart in the spec's five |
| — | Qualified Lead | **Absent** — no badge, label, or filter for this concept |
| `reqStates` enum: `pending / in_call / ended` | Handover Request states: `offered → accepted_by_user → pending_strategist → strategist_joined → in_call → ended`, exits `declined` / `no_strategist_available` | **Major mismatch** — design flattens a 6-state+2-exit machine into 3 states; "pending" conflates `offered/accepted_by_user/pending_strategist`; there's no distinct `strategist_joined` moment (claim and join happen in one click); `declined` and `no_strategist_available` are not modeled as request states at all — the "no strategist available" path is instead a chat-message branch (callback+calendar cards) with no corresponding Console request record |
| Console requests all show `mode: "Video (Daily)"`; callback path is a wholly separate tab/table | modes `video` / `callback` on one Handover Request | **Mismatch** — design implements the two modes as two different entities/screens (Queue vs. Callbacks tab) rather than a mode field on a single request type |
| 'esc' message-kind cards, "Next step:" label | Escalation | Match |
| 'walk' message-kind, "Open demo Portal" CTA | Walkthrough Card | Match |
| "Portal" page, "Demo portal · mock data" badge | Portal | Match (explicitly marked as a mock in this artboard) |
| 👍/👎 buttons on 'ended' card | Feedback (thumbs up/down) | Match |
| Console "Trace" field + "Open trace in Langfuse ↗" | Trace | Match, and explicitly names Langfuse |
| Triage subtitle "Written by the Triage Agent on every thumbs-down" | Triage Agent | Match, and confirms the trigger = thumbs-down |
| "Triage reports" tab; sample categories "Knowledge gap", "Wrong escalation" | Triage Report (7 categories incl. hallucination, tone, personal data, bug, other) | Match for the 2 categories shown; the other 5 canonical categories are not demonstrated anywhere in the mock data |
| "Suggested eval case" boxes | Eval Case | Match |
| `[industries#construction]` etc., KB suggestions reference `security#commitments`, `portal#access` | KB Section id `topic#heading` | Match, used consistently everywhere |
| Callbacks table column **"Scheduled for"** with concrete slots (e.g. "Sep 8, 10:30 AM") | *(no such concept in spec vocabulary)* | **Net-new concept** — the design's Callback entity carries a committed scheduled-slot field that the current spec vocabulary doesn't define anywhere on Handover Request or Callback |

---

## 6. Ticket mapping

- **02 (chat shell + streaming + citations)**: launcher button; panel header (avatar, title, presence dot, EN/ES toggle, expand/close); `chatViewOn` message list; `typing` kind (`tdot` dots standing in for streaming); `text` kind + citation-chip rendering; input bar + Enter-to-send; quick-reply chips; docked/expanded `panelGeom`; `msgin` animation.
- **04 (escalation copy)**: `esc` message kind (pricing escalation and the generic `answer('unknown')` fallback), "Next step:" pattern, `not-published#*` citations.
- **07 (demo Portal + mock site)**: entire `siteView` mock cadreai.com page (nav/hero/partner strip/3-card grid/dark CTA/footer); entire `portalView` (header badge, 4 portal tabs, stat cards, agents table); `openPortal`/`backToSite`/`openPortalFromChat` transitions.
- **08 (Walkthrough Cards)**: `walk` message kind and the `answer('portal')` two-step flow (cited text then the numbered-steps card with "Open demo Portal" CTA).
- **10 (Console shell, sign-in, Availability, Leads)**: Console header (logo, title, "← Visitor chat demo" link, Availability toggle, strategist identity block), left `navTabs` with badge counts. Gap: neither artboard shows a sign-in screen — the Console header is always in an already-authenticated state; "Leads" has no dedicated unified list, only the Queue cards and the Callbacks table.
- **11 (hand-over offer + Console queue + callbacks)**: chat-side `offer`, `lead`, `callback`, and `calendar` message kinds and their handlers (`makeOffer`/`acceptOffer`/`declineOffer`/`submitLead`/`schedule`); Console Queue tab's request list + detail (qualification panel, request panel, conversation panel — excluding call-control elements below); Callbacks tab table.
- **12 (feedback thumbs)**: `ended` message kind, `feedback()`/`thumbsUp`/`thumbsDown`, thanks/apology copy, and its role as the Triage Agent's trigger.
- **14 (Triage tab)**: Console Triage tab in full — report cards, category chip, severity, summary, evidence block, "Suggested KB addition"/"Suggested eval case" boxes, Langfuse trace link, "Triage Agent" subtitle.
- **15 (video call frame + in-call banner + Claim & join / End)**: chat-side `callViewOn` (connecting spinner, live video `image-slot`, self-view, sharing badge, mic/cam/share/end control bar); Console's "Claim & join call" / "End call" buttons and the black in-call banner with the `daily.co/cadre-{id}` room string.
