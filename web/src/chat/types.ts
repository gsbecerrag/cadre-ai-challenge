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

export type FeedbackRating = 'up' | 'down'

/**
 * How far one answer's Feedback has got. `none` is the two thumbs on their own; `sent` is a
 * rating the server has taken and stored — the note box is open beneath it and the other thumb
 * is still on offer, because one change is allowed; `changed` is that one change spent;
 * `locked` is the server refusing a further change — a second tab, or a reload that lost what
 * this one knew. The last two are terminal, and both render as a control nobody can press
 * again.
 *
 * There is deliberately no state for "a thumb pressed but not yet sent": the press *is* the
 * Feedback, so it goes to the server at once and the sentence follows it as an update. A
 * Visitor who presses 👍 and walks away has still rated the answer.
 */
export type FeedbackStatus = 'none' | 'sent' | 'changed' | 'locked'

export interface FeedbackEntry {
  rating: FeedbackRating | null
  status: FeedbackStatus
}

/**
 * What every Assistant answer carries once its Turn has finished: the Trace the thumbs are
 * attached to. Absent while the answer is still streaming, and absent for good when the
 * service runs untraced — there is then no Trace to score, so no thumbs are offered.
 */
export interface Rateable {
  traceId?: string
}

/**
 * `raw` keeps the deltas exactly as they arrived, markers and all; `text` and `citations` are
 * derived from it on every delta. Deriving rather than accumulating is what lets a marker that
 * is still arriving stay hidden and then resolve into a chip.
 */
export interface TextMessage extends Rateable {
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

export interface EscalationMessage extends Rateable {
  id: string
  kind: 'escalation'
  role: 'assistant'
  title: string
  body: string
  nextStep: string
  citations: string[]
  language?: Language
}

export interface WalkthroughMessage extends Rateable {
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
export type NoteKey = 'handoverDeclined' | 'handoverConnecting'

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

export interface ChatState {
  messages: Message[]
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
  /**
   * The Feedback left in this conversation, keyed by the Trace it judges — the same key the
   * server writes the Feedback document under, so a control's state and a stored rating can
   * never mean two different things.
   */
  feedback: Record<string, FeedbackEntry>
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
  | { type: 'handover'; state: HandoverState; mode: HandoverMode | null; lead: LeadContact }
  | { type: 'details_shared'; lead: LeadContact }
  | { type: 'stream_failed'; message: string }
  | { type: 'sections_loaded'; sections: KBSectionTitle[] }
  /**
   * The server took a rating and holds it. The rating is the receipt's, not the browser's —
   * the server is the one that knows which thumb now stands — and `changed` is its answer to
   * whether that thumb replaced an earlier one, which is the Visitor's one change spent.
   */
  | { type: 'feedback_sent'; traceId: string; rating: FeedbackRating; changed: boolean }
  /** The server refused a further change (409): this answer's rating is final. */
  | { type: 'feedback_locked'; traceId: string }
