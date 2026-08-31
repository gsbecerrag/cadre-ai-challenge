/**
 * The chat's wire contract and its state.
 *
 * `ChatEvent` mirrors `core/events.py` exactly — one variant per Server-Sent Event name, with
 * the payload in the server's snake_case, because that is what arrives on the wire. Everything
 * the reducer derives from it uses the app's own camelCase.
 */

export interface Usage {
  input_tokens: number
  output_tokens: number
  cached_tokens: number
  cost_usd: number
}

export interface WalkthroughCard {
  title: string
  steps: string[]
  destination: string
  citations: string[]
}

export type ChatEvent =
  | { event: 'text'; data: { delta: string } }
  | { event: 'tool'; data: { name: string; status: 'started' | 'finished' } }
  | { event: 'card'; data: WalkthroughCard }
  | {
      event: 'escalation'
      data: { title: string; body: string; next_step: string; citations: string[] }
    }
  | { event: 'offer'; data: { request_id: string; prompt: string } }
  | { event: 'handover'; data: { request_id: string; state: string; mode: 'video' | 'callback' } }
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
}

export interface ErrorMessage {
  id: string
  kind: 'error'
  role: 'assistant'
  text: string
}

export type Message = TextMessage | TypingMessage | EscalationMessage | ErrorMessage

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
}

export type ChatAction =
  | { type: 'visitor_message'; text: string }
  | { type: 'event'; event: ChatEvent }
  | { type: 'stream_failed'; message: string }
