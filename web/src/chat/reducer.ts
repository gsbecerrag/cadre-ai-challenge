/**
 * Turn the Server-Sent Events of one Turn into chat state.
 *
 * A pure function of (state, action), so the whole streaming contract can be tested by
 * replaying a recorded event sequence — no component, no network, no timers (seam S4).
 */

import { splitCitations } from './citations'
import type {
  CallState,
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
    call: null,
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

/**
 * The states in which a video Hand-over has a call to draw.
 *
 * `pending_strategist` is one of them because the Visitor is already in the room: Daily's
 * prebuilt frame is what they wait in, not a placeholder that is swapped for it when somebody
 * joins. `ended` and `no_strategist_available` are not, which is what closes the frame.
 */
const LIVE_CALL_STATES: HandoverState[] = ['pending_strategist', 'strategist_joined', 'in_call']

function liveCall(
  handoverState: HandoverState,
  mode: HandoverMode | null,
  roomUrl: string,
  strategistName: string,
): CallState | null {
  if (mode !== 'video' || !LIVE_CALL_STATES.includes(handoverState)) {
    return null
  }
  return { state: handoverState, roomUrl, strategistName }
}

function sameCall(one: CallState | null, other: CallState | null): boolean {
  if (one === null || other === null) {
    return one === other
  }
  return (
    one.state === other.state &&
    one.roomUrl === other.roomUrl &&
    one.strategistName === other.strategistName
  )
}

/** A Lead a Strategist could actually reach: the Callback is confirmed rather than asked for. */
function reachable(lead: LeadContact): boolean {
  return lead.name.trim() !== '' && lead.email.trim() !== ''
}

function note(state: ChatState, key: NoteKey): Message {
  return { id: `m${state.seq + 1}`, kind: 'note', role: 'assistant', note: key }
}

/**
 * What a Callback looks like in the transcript: the confirmation when a Strategist could
 * already reach the Visitor, and the card that asks for the two details they need when not.
 *
 * One function because there are two ways into it — accepting with nobody online, and a call
 * nobody joined timing out — and a Visitor who waited two minutes for a Strategist should not
 * meet a different Callback from one who never had a room.
 */
function callbackReply(state: ChatState, lead: LeadContact): Message {
  return reachable(lead)
    ? { id: `m${state.seq + 1}`, kind: 'callback', role: 'assistant', lead }
    : { id: `m${state.seq + 1}`, kind: 'details', role: 'assistant', done: false, lead }
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
  roomUrl = '',
  strategistName = '',
): ChatState {
  const call = liveCall(handoverState, mode, roomUrl, strategistName)
  const open = state.messages.find(
    (message): message is OfferMessage => message.kind === 'offer' && message.status === 'open',
  )
  if (open) {
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
        : callbackReply(state, lead)
    return nextState(state, [...withoutTyping(answered), reply], {
      seq: state.seq + 1,
      streamingId: null,
      call,
    })
  }
  // Everything below is a status poll rather than an answered offer. It arrives every five
  // seconds for as long as the Visitor waits, so it returns the state it was given whenever
  // nothing has changed: a new object per poll would re-render the panel, and re-rendering
  // the panel remounts the iframe, which drops the Visitor out of their own call.
  if (state.call === null) {
    return state
  }
  if (call !== null) {
    return sameCall(call, state.call) ? state : { ...state, call }
  }
  // The call is over. Either somebody ended it, or nobody joined it and the server turned it
  // into the Callback it promised — which is the same confirmation ticket 11 already draws.
  const reply =
    handoverState === 'no_strategist_available' ? callbackReply(state, lead) : note(state, 'callEnded')
  return nextState(state, [...state.messages, reply], { seq: state.seq + 1, call: null })
}

/**
 * The details card is answered, and the Callback is confirmed with what was typed into it.
 *
 * Once. A card that is already done is a Callback already confirmed, so a double-pressed
 * "Share details" or a retried request returns the state untouched rather than stacking a
 * second confirmation under the first — the same rule the offer card's answer follows.
 */
function detailsShared(state: ChatState, lead: LeadContact): ChatState {
  const open = state.messages.some((message) => message.kind === 'details' && !message.done)
  if (!open) {
    return state
  }
  const messages = state.messages.map((message) =>
    message.kind === 'details' && !message.done ? { ...message, done: true, lead } : message,
  )
  return nextState(
    state,
    [...messages, { id: `m${state.seq + 1}`, kind: 'callback', role: 'assistant', lead }],
    { seq: state.seq + 1 },
  )
}

/**
 * The Visitor closed the call frame themselves.
 *
 * Local only, and deliberately: leaving a room is not declining a Hand-over. The Handover
 * Request keeps whatever state the server has for it, the Strategist may still be in the room,
 * and the Lead is still a Lead — all that changes is that the Visitor is looking at the
 * transcript again, which without this they cannot do, because the call takes the message area
 * and the composer with it.
 */
function leftCall(state: ChatState): ChatState {
  if (state.call === null) {
    return state
  }
  return nextState(state, [...state.messages, note(state, 'callLeft')], {
    seq: state.seq + 1,
    call: null,
  })
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
      return handover(
        state,
        action.state,
        action.mode,
        action.lead,
        action.roomUrl,
        action.strategistName,
      )

    case 'details_shared':
      return detailsShared(state, action.lead)

    case 'left_call':
      return leftCall(state)

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
