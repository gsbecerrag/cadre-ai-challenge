/**
 * The chat's wire contract and its state.
 *
 * `ChatEvent` mirrors `core/events.py` exactly — one variant per Server-Sent Event name, with
 * the payload in the server's snake_case, because that is what arrives on the wire. Everything
 * the reducer derives from it uses the app's own camelCase.
 */

import type { Language } from './strings'

export interface Usage {
  input_tokens: number
  output_tokens: number
  cached_tokens: number
  cost_usd: number
}

/** One row of `GET /api/knowledge/sections` — what the citation chips show. */
export interface KBSectionTitle {
  id: string
  title: string
  topic: string
}

/**
 * Where a Walkthrough Card's call to action goes, resolved by the server from a destination
 * id (`core/tools/walkthroughs.py`). The browser links where it was told to rather than
 * working an id out — and `external` is the difference the Visitor feels: a Portal route is a
 * client-side navigation that leaves the chat panel and its transcript mounted, an external
 * link opens in a new tab.
 */
export interface CardDestination {
  id: string
  label: string
  href: string
  external: boolean
}

/**
 * The states a Handover Request may be in, mirroring `core/handover.py`. The Console derives
 * the labels a Strategist reads (Pending, In call, Ended, Declined, Callback) from these and
 * the mode; the chat only needs to know whether the Hand-over is a Callback, a call, or a no.
 */
export type HandoverState =
  | 'offered'
  | 'accepted_by_user'
  | 'pending_strategist'
  | 'strategist_joined'
  | 'in_call'
  | 'ended'
  | 'declined'
  | 'no_strategist_available'

export type HandoverMode = 'video' | 'callback'

/** The Contact Details the Callback confirmation reads back — the Visitor's own. */
export interface LeadContact {
  name: string
  email: string
  company: string
}

export interface WalkthroughCard {
  title: string
  steps: string[]
  destination: CardDestination
  citations: string[]
}

export type ChatEvent =
  | { event: 'text'; data: { delta: string } }
  | { event: 'tool'; data: { name: string; status: 'started' | 'finished' } }
  | { event: 'card'; data: WalkthroughCard }
  | {
      event: 'escalation'
      data: {
        title: string
        body: string
        next_step: string
        citations: string[]
        /** The language the Escalation copy was looked up in; absent on an Escalation that
         * did not name one, which then follows the widget's own EN/ES toggle. */
        language?: Language
      }
    }
  | { event: 'offer'; data: { request_id: string; prompt: string } }
  | {
      event: 'handover'
      data: { request_id: string; state: HandoverState; mode: HandoverMode | null }
    }
  | { event: 'done'; data: { trace_id: string | null; usage: Usage } }
  | { event: 'error'; data: { message: string } }

export type MessageRole = 'visitor' | 'assistant'

/**
 * `raw` keeps the deltas exactly as they arrived, markers and all; `text` and `citations` are
 * derived from it on every delta. Deriving rather than accumulating is what lets a marker that
 * is still arriving stay hidden and then resolve into a chip.
 */
export interface TextMessage {
  id: string
  kind: 'text'
  role: MessageRole
  raw: string
  text: string
  citations: string[]
}

export interface TypingMessage {
  id: string
  kind: 'typing'
  role: 'assistant'
}

export interface EscalationMessage {
  id: string
  kind: 'escalation'
  role: 'assistant'
  title: string
  body: string
  nextStep: string
  citations: string[]
  language?: Language
}

export interface WalkthroughMessage {
  id: string
  kind: 'walkthrough'
  role: 'assistant'
  title: string
  steps: string[]
  destination: CardDestination
  citations: string[]
}

/**
 * The Hand-over offer card: the Assistant's question and two buttons.
 *
 * `status` is what the card does after the Visitor answers, and it is a status rather than the
 * done-text the design draws because the reducer holds no copy: the widget renders the line
 * for the status in the Visitor's chrome language, so a card answered in Spanish does not
 * close in English.
 */
export interface OfferMessage {
  id: string
  kind: 'offer'
  role: 'assistant'
  requestId: string
  /** What the Assistant phrased the offer with, or empty for Cadre's own wording. */
  prompt: string
  status: 'open' | 'accepted' | 'declined'
}

/** The "Your details" card: shown when a Visitor accepts and the Lead is not reachable yet. */
export interface DetailsMessage {
  id: string
  kind: 'details'
  role: 'assistant'
  done: boolean
  lead: LeadContact
}

/** The Callback confirmation: a Strategist will reach out, and here is what they will use. */
export interface CallbackMessage {
  id: string
  kind: 'callback'
  role: 'assistant'
  lead: LeadContact
}

/**
 * A line of the Assistant's own chrome — the decline reply, the "connecting you" placeholder.
 *
 * A key rather than a string, for the same reason as `OfferMessage.status`: the reducer is
 * pure and language-agnostic, and the copy lives in `strings.ts` with the rest of the chrome.
 */
export type NoteKey = 'handoverDeclined' | 'handoverConnecting' | 'callEnded' | 'callLeft'

export interface NoteMessage {
  id: string
  kind: 'note'
  role: 'assistant'
  note: NoteKey
}

export interface ErrorMessage {
  id: string
  kind: 'error'
  role: 'assistant'
  text: string
}

export type Message =
  | TextMessage
  | TypingMessage
  | EscalationMessage
  | WalkthroughMessage
  | OfferMessage
  | DetailsMessage
  | CallbackMessage
  | NoteMessage
  | ErrorMessage

/**
 * The Live Hand-over's call, as the panel draws it (docs/design/DESIGN-BRIEF.md §2.6).
 *
 * Not a message: the call is a view over the transcript rather than a line in it, and it
 * comes and goes while the transcript only ever grows. `roomUrl` is empty until the server
 * has a Daily room — the panel shows the connecting spinner until it does — and
 * `strategistName` is empty until somebody has claimed the request.
 */
export interface CallState {
  state: HandoverState
  roomUrl: string
  strategistName: string
}

export interface ChatState {
  messages: Message[]
  /** The call in the panel, or null when there is not one. */
  call: CallState | null
  /** A Turn is in flight: the composer waits and the typing bubble shows. */
  pending: boolean
  /** The tool the Assistant is running right now, if any. */
  activeTool: string | null
  usage: Usage | null
  traceId: string | null
  /** The bubble the next text delta appends to; null starts a new one. */
  streamingId: string | null
  /** Message ids are minted here so the reducer stays a pure function of its input. */
  seq: number
  /**
   * KB Section id to its heading, fetched once when the panel opens. Empty until it arrives,
   * and a chip falls back to showing the id — a citation is still a citation without a title.
   */
  sections: Record<string, string>
}

export type ChatAction =
  | { type: 'visitor_message'; text: string }
  | { type: 'event'; event: ChatEvent }
  /**
   * A Handover Request changed state. It arrives from the accept and decline endpoints rather
   * than over the stream — the Visitor pressed a button, so the answer is an HTTP response —
   * and carries the Visitor's own Contact Details, which is what tells the widget whether to
   * ask for them before confirming the Callback.
   */
  | {
      type: 'handover'
      state: HandoverState
      mode: HandoverMode | null
      lead: LeadContact
      /** The Daily room, once the server has one. Absent on a Callback and on a decline. */
      roomUrl?: string
      /** Who claimed the request, once somebody has. */
      strategistName?: string
    }
  | { type: 'details_shared'; lead: LeadContact }
  /**
   * The Visitor closed the call frame themselves — "Back to the chat", or Daily telling us
   * they left the meeting. Local only: the Handover Request is untouched, because leaving a
   * room is not declining a Hand-over and a Strategist may still be in it.
   */
  | { type: 'left_call' }
  | { type: 'stream_failed'; message: string }
  | { type: 'sections_loaded'; sections: KBSectionTitle[] }
