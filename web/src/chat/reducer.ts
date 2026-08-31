/**
 * Turn the Server-Sent Events of one Turn into chat state.
 *
 * A pure function of (state, action), so the whole streaming contract can be tested by
 * replaying a recorded event sequence — no component, no network, no timers (seam S4).
 */

import { splitCitations } from './citations'
import type { ChatAction, ChatEvent, ChatState, Message, TextMessage } from './types'

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
      }
      // A card closes the bubble that was streaming, so text after it starts a new one.
      return nextState(state, [...withoutTyping(state.messages), escalation], {
        seq: state.seq + 1,
        streamingId: null,
      })
    }

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

    // `card`, `offer` and `handover` are part of the contract but nothing emits them yet:
    // ticket 08 fills in the Walkthrough Card, ticket 11 the Hand-over offer and its states.
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
  }
}
