/**
 * Turn the Server-Sent Events of one Turn into chat state.
 *
 * A pure function of (state, action), so the whole streaming contract can be tested by
 * replaying a recorded event sequence — no component, no network, no timers (seam S4).
 */

import { splitCitations } from './citations'
import type {
  ChatAction,
  ChatEvent,
  ChatState,
  HandoverMode,
  HandoverState,
  LeadContact,
  Message,
  NoteKey,
  OfferMessage,
  TextMessage,
} from './types'

function nextState(state: ChatState, messages: Message[], patch: Partial<ChatState>): ChatState {
  return { ...state, ...patch, messages }
}

function withoutTyping(messages: Message[]): Message[] {
  return messages.filter((message) => message.kind !== 'typing')
}

function textMessage(id: string, role: TextMessage['role'], raw: string): TextMessage {
  return { id, kind: 'text', role, raw, ...splitCitations(raw) }
}

export function initialChatState(greeting: string): ChatState {
  return {
    messages: [textMessage('m1', 'assistant', greeting)],
    pending: false,
    activeTool: null,
    usage: null,
    traceId: null,
    streamingId: null,
    seq: 1,
    sections: {},
  }
}

function reduceEvent(state: ChatState, event: ChatEvent): ChatState {
  switch (event.event) {
    case 'text': {
      const open = state.messages.find(
        (message): message is TextMessage =>
          message.id === state.streamingId && message.kind === 'text',
      )
      if (open) {
        const grown = textMessage(open.id, 'assistant', open.raw + event.data.delta)
        return nextState(
          state,
          state.messages.map((message) => (message.id === open.id ? grown : message)),
          {},
        )
      }
      const id = `m${state.seq + 1}`
      return nextState(
        state,
        [...withoutTyping(state.messages), textMessage(id, 'assistant', event.data.delta)],
        { seq: state.seq + 1, streamingId: id },
      )
    }

    case 'tool':
      return nextState(state, state.messages, {
        activeTool: event.data.status === 'started' ? event.data.name : null,
      })

    case 'escalation': {
      const id = `m${state.seq + 1}`
      const escalation: Message = {
        id,
        kind: 'escalation',
        role: 'assistant',
        title: event.data.title,
        body: event.data.body,
        nextStep: event.data.next_step,
        citations: event.data.citations,
        language: event.data.language,
      }
      // A card closes the bubble that was streaming, so text after it starts a new one.
      return nextState(state, [...withoutTyping(state.messages), escalation], {
        seq: state.seq + 1,
        streamingId: null,
      })
    }

    case 'card': {
      const id = `m${state.seq + 1}`
      const walkthrough: Message = {
        id,
        kind: 'walkthrough',
        role: 'assistant',
        title: event.data.title,
        steps: event.data.steps,
        destination: event.data.destination,
        citations: event.data.citations,
      }
      // Same as an Escalation: the card closes the bubble that was streaming, so the text
      // that follows it starts a new one rather than growing around the card.
      return nextState(state, [...withoutTyping(state.messages), walkthrough], {
        seq: state.seq + 1,
        streamingId: null,
      })
    }

    case 'offer': {
      const id = `m${state.seq + 1}`
      const offer: Message = {
        id,
        kind: 'offer',
        role: 'assistant',
        requestId: event.data.request_id,
        prompt: event.data.prompt,
        status: 'open',
      }
      // A card, like an Escalation or a Walkthrough Card: it closes the streaming bubble.
      return nextState(state, [...withoutTyping(state.messages), offer], {
        seq: state.seq + 1,
        streamingId: null,
      })
    }

    // The same Hand-over reduction as the button's own answer, for a state change that
    // arrives on the wire instead. It carries no Contact Details — the stream is not the
    // Visitor's own request — so the widget asks for them exactly as it does after an accept.
    case 'handover':
      return handover(state, event.data.state, event.data.mode, EMPTY_CONTACT)

    case 'done':
      return nextState(state, withoutTyping(state.messages), {
        pending: false,
        streamingId: null,
        activeTool: null,
        usage: event.data.usage,
        traceId: event.data.trace_id,
      })

    case 'error':
      return failed(state, event.data.message)

    default:
      return state
  }
}

const EMPTY_CONTACT: LeadContact = { name: '', email: '', company: '' }

/** A Lead a Strategist could actually reach: the Callback is confirmed rather than asked for. */
function reachable(lead: LeadContact): boolean {
  return lead.name.trim() !== '' && lead.email.trim() !== ''
}

function note(state: ChatState, key: NoteKey): Message {
  return { id: `m${state.seq + 1}`, kind: 'note', role: 'assistant', note: key }
}

/**
 * What the Visitor sees after they answer the offer.
 *
 * The offer card goes to its answered state — once, so a double-pressed button or a retried
 * request does not stack two confirmations — and the reply that belongs to the answer follows
 * it: the Callback confirmation, the details card when the Lead is not reachable yet, the
 * decline line, or the connecting line that ticket 15 replaces with the call itself.
 */
function handover(
  state: ChatState,
  handoverState: HandoverState,
  mode: HandoverMode | null,
  lead: LeadContact,
): ChatState {
  const open = state.messages.find(
    (message): message is OfferMessage => message.kind === 'offer' && message.status === 'open',
  )
  if (!open) {
    return state
  }
  const declined = handoverState === 'declined'
  const answered = state.messages.map((message) =>
    message.id === open.id
      ? { ...open, status: declined ? ('declined' as const) : ('accepted' as const) }
      : message,
  )
  const reply: Message = declined
    ? note(state, 'handoverDeclined')
    : mode === 'video'
      ? note(state, 'handoverConnecting')
      : reachable(lead)
        ? { id: `m${state.seq + 1}`, kind: 'callback', role: 'assistant', lead }
        : { id: `m${state.seq + 1}`, kind: 'details', role: 'assistant', done: false, lead }
  return nextState(state, [...withoutTyping(answered), reply], {
    seq: state.seq + 1,
    streamingId: null,
  })
}

/** The details card is answered, and the Callback is confirmed with what was typed into it. */
function detailsShared(state: ChatState, lead: LeadContact): ChatState {
  const messages = state.messages.map((message) =>
    message.kind === 'details' && !message.done ? { ...message, done: true, lead } : message,
  )
  return nextState(
    state,
    [...messages, { id: `m${state.seq + 1}`, kind: 'callback', role: 'assistant', lead }],
    { seq: state.seq + 1 },
  )
}

function failed(state: ChatState, message: string): ChatState {
  const id = `m${state.seq + 1}`
  return nextState(
    state,
    [...withoutTyping(state.messages), { id, kind: 'error', role: 'assistant', text: message }],
    { seq: state.seq + 1, pending: false, streamingId: null, activeTool: null },
  )
}

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'visitor_message': {
      const visitorId = `m${state.seq + 1}`
      const typingId = `m${state.seq + 2}`
      return nextState(
        state,
        [
          ...withoutTyping(state.messages),
          textMessage(visitorId, 'visitor', action.text),
          { id: typingId, kind: 'typing', role: 'assistant' },
        ],
        { seq: state.seq + 2, pending: true, streamingId: null, activeTool: null },
      )
    }

    case 'event':
      return reduceEvent(state, action.event)

    case 'handover':
      return handover(state, action.state, action.mode, action.lead)

    case 'details_shared':
      return detailsShared(state, action.lead)

    case 'stream_failed':
      return failed(state, action.message)

    case 'sections_loaded':
      return {
        ...state,
        sections: Object.fromEntries(
          action.sections.map((section) => [section.id, section.title]),
        ),
      }
  }
}
