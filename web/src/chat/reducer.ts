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
  FeedbackEntry,
  FeedbackStatus,
  Message,
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
    feedback: {},
  }
}

/** The kinds of message that are an answer, and so can be rated. A typing bubble is not one,
 * an error is the Assistant failing rather than answering, and the Visitor's own message is
 * not the Assistant's to judge. */
function isAnswer(message: Message): boolean {
  return (
    message.role === 'assistant' &&
    (message.kind === 'text' || message.kind === 'escalation' || message.kind === 'walkthrough')
  )
}

/**
 * Mark the answer the Trace belongs to — the last thing the Assistant said this Turn.
 *
 * One Turn is one Trace and the server keeps one Feedback per Trace, so a Turn that produced a
 * card and two paragraphs still gets one set of thumbs, under the last of them.
 */
function rateable(messages: Message[], traceId: string): Message[] {
  const last = messages.map(isAnswer).lastIndexOf(true)
  if (last < 0) {
    return messages
  }
  return messages.map((message, index) => (index === last ? { ...message, traceId } : message))
}

/** The state a control is in before anything has been pressed. */
const UNRATED: FeedbackEntry = { rating: null, status: 'none' }

/** Whether a thumb may still be pressed, and pressing it would mean something new. */
function acceptsAThumb(entry: FeedbackEntry, rating: FeedbackEntry['rating']): boolean {
  if (entry.status === 'chosen' || entry.status === 'none') {
    return true
  }
  // Submitted: one change is allowed, and only a change — pressing the thumb that already
  // stands would spend it on the rating the server already holds.
  return entry.status === 'submitted' && entry.rating !== rating
}

function withFeedback(state: ChatState, traceId: string, entry: FeedbackEntry): ChatState {
  return { ...state, feedback: { ...state.feedback, [traceId]: entry } }
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

    case 'done': {
      const answered = withoutTyping(state.messages)
      return nextState(
        state,
        event.data.trace_id ? rateable(answered, event.data.trace_id) : answered,
        {
          pending: false,
          streamingId: null,
          activeTool: null,
          usage: event.data.usage,
          traceId: event.data.trace_id,
        },
      )
    }

    case 'error':
      return failed(state, event.data.message)

    // `offer` and `handover` are part of the contract but nothing emits them yet: ticket 11
    // fills in the Hand-over offer and its states.
    default:
      return state
  }
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

    case 'stream_failed':
      return failed(state, action.message)

    case 'sections_loaded':
      return {
        ...state,
        sections: Object.fromEntries(
          action.sections.map((section) => [section.id, section.title]),
        ),
      }

    case 'feedback_chosen': {
      const entry = state.feedback[action.traceId] ?? UNRATED
      if (!acceptsAThumb(entry, action.rating)) {
        return state
      }
      return withFeedback(state, action.traceId, { rating: action.rating, status: 'chosen' })
    }

    case 'feedback_sent': {
      const entry = state.feedback[action.traceId] ?? UNRATED
      const status: FeedbackStatus = action.changed ? 'changed' : 'submitted'
      return withFeedback(state, action.traceId, { rating: entry.rating, status })
    }

    case 'feedback_locked': {
      const entry = state.feedback[action.traceId] ?? UNRATED
      return withFeedback(state, action.traceId, { rating: entry.rating, status: 'locked' })
    }
  }
}
