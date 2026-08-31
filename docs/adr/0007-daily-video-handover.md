---
status: accepted
date: 2026-08-30
---

# Daily.co prebuilt rooms for live video hand-over

When a qualified prospect accepts a live hand-over and a Strategist is online, the server creates a Daily.co room per handover request over REST and both sides join through the prebuilt iframe with no login. We chose Daily over Jitsi (public or self-hosted), JaaS, Google Meet or a text-only hand-over because the prospect is anonymous and must not face a lobby or a sign-in, and the feature has a two-hour build budget.

## Context

- Vocabulary: escalation is the bot redirecting to a human channel (contact form, email, phone) without a human joining; hand-over is a Strategist taking the conversation. cadreai.com offers no booking calendar anywhere (no Calendly, HubSpot Meetings or cal.com); every "Talk to an AI Strategist" CTA lands on the /contact form. An in-chat live call is therefore a differentiator, not a nicety: it keeps a warm lead warm.
- The prospect is anonymous (ADR-0010) and mid-conversation; any sign-up, download or lobby wait loses them. The Strategist is already signed in to the console and should not need a second account either.
- Public meet.jit.si now requires an authenticated moderator to open a room, so an anonymous prospect sits in a lobby until someone with an account arrives. Self-hosting Jitsi is the vision target (no per-minute vendor cost) but is hours of infrastructure the schedule does not have.
- A hand-over must be gated or Strategists get pulled into unqualified conversations: the qualification score (ADR-0009) and Strategist presence decide whether the offer is made at all.
- The offer needs a fallback because nobody may be online during the review: a callback mode that captures the lead and creates a handover request without a room.

## Decision

- Provider: Daily.co. The server creates one room per handover request via REST with a short expiry and stores the room URL on the request; the chat renders the prebuilt iframe; the console renders the same room for the Strategist. No account for either side.
- Gating: `offer_live_handover` is available to the model only when the session's qualification score is ≥ 3 and at least one Strategist is `online`; it is offered once per session. The `LIVE_HANDOVER_ENABLED` flag switches the feature to callback mode for environments without Daily credentials.
- State machine on the handover request: offered → accepted_by_user → pending_strategist → strategist_joined → in_call → ended, with exits to declined (user) and no_strategist_available (timeout). Every transition is a Firestore write, so the console and the chat react through realtime listeners.
- Notification: a Strategist sees the pending request in the console immediately (Firestore listener plus browser Notification); Slack and email are out of scope.
- Timeout: if no Strategist joins within the window, the request becomes no_strategist_available, the lead is already captured, and the bot escalates to the contact channels.

## Considered Options

- Public Jitsi (meet.jit.si) — lost because the anonymous prospect lands in a moderator lobby.
- Self-hosted Jitsi — lost on infrastructure time; remains the vision target if per-minute cost matters.
- JaaS (8x8) — lost because it requires a signed JWT per participant and a second vendor console for no MVP gain over Daily.
- Google Meet — lost because room creation needs a Workspace identity and guests are often forced to sign in.
- Text-only hand-over in the chat — lost because callback mode already covers it and it does not demonstrate the "keep the lead warm" vision.

## Consequences

- Positive: two-hour build; no login friction on either side; rooms are ephemeral so nothing persists at the vendor by default; the state machine is testable without video.
- Positive: presence and gating mean the demo degrades to callback mode instead of failing when nobody is online.
- Negative: a paid third party at scale; browser camera and microphone permissions or corporate firewalls can block the iframe; no recording or transcript, so the call is invisible to the session and to Langfuse (Phase 2: transcript into the session).
- Negative: Strategist presence is a manual toggle; a stale `online` flag produces offers that time out.
- Negative: an in-call session has no bot; if the Strategist drops, the user is back in chat with no summary of the call.
- Reopen when: per-minute cost or vendor terms become a problem (self-hosted Jitsi), Cadre's CRM wants calendar-backed meetings instead (HubSpot Meetings, Phase 2), or transcripts become a requirement.

## Links

- Absence of any booking calendar on cadreai.com: [cadreai-site-facts](../research/cadreai-site-facts.md)
- Related: [ADR-0003](0003-gcp-with-seams.md), [ADR-0004](0004-raw-tool-loop.md), [ADR-0009](0009-bant-lite-qualification.md), [ADR-0010](0010-firebase-auth-console.md)
