import { describe, expect, it } from 'vitest'

import { chatReducer, initialChatState } from './reducer'
import type { ChatAction, ChatEvent, ChatState } from './types'

const GREETING = "Hi there — I'm Cadre's AI assistant."

/** Recorded from `POST /api/chat` with the stub provider (api/tests/test_chat.py). */
const GROUNDED_ANSWER: ChatEvent[] = [
  { event: 'text', data: { delta: 'Cadre AI is a consultancy ' } },
  { event: 'text', data: { delta: 'focused on revenue growth ' } },
  { event: 'text', data: { delta: '[services#what-cadre-does]. Four core services' } },
  { event: 'text', data: { delta: ' [services#what-cadre-does].' } },
  {
    event: 'done',
    data: {
      trace_id: null,
      usage: { input_tokens: 12400, output_tokens: 48, cached_tokens: 12200, cost_usd: 0.0031 },
    },
  },
]

const ESCALATED_ANSWER: ChatEvent[] = [
  { event: 'tool', data: { name: 'escalate', status: 'started' } },
  {
    event: 'escalation',
    data: {
      title: "I can't confirm that from what Cadre publishes",
      body: 'Cadre does not publish pricing for its engagements.',
      next_step: 'Write hello@gocadre.ai or call (619) 324-3223.',
      citations: ['contact#how-to-reach-cadre'],
    },
  },
  { event: 'tool', data: { name: 'escalate', status: 'finished' } },
  { event: 'text', data: { delta: 'Happy to help with anything else.' } },
  {
    event: 'done',
    data: {
      trace_id: null,
      usage: { input_tokens: 900, output_tokens: 12, cached_tokens: 800, cost_usd: 0.0004 },
    },
  },
]

const FAILED_ANSWER: ChatEvent[] = [
  { event: 'text', data: { delta: 'Let me check that' } },
  { event: 'error', data: { message: "Something went wrong on my side and I couldn't finish." } },
]

function replay(question: string, events: ChatEvent[]): ChatState {
  const actions: ChatAction[] = [
    { type: 'visitor_message', text: question },
    ...events.map((event): ChatAction => ({ type: 'event', event })),
  ]
  return actions.reduce(chatReducer, initialChatState(GREETING))
}

describe('the chat reducer', () => {
  it('opens with the greeting and nothing pending', () => {
    const state = initialChatState(GREETING)

    expect(state.messages).toEqual([
      { id: 'm1', kind: 'text', role: 'assistant', raw: GREETING, text: GREETING, citations: [] },
    ])
    expect(state.pending).toBe(false)
  })

  it('shows the Visitor their message and a typing bubble until the answer starts', () => {
    const state = chatReducer(initialChatState(GREETING), {
      type: 'visitor_message',
      text: 'What does Cadre AI do?',
    })

    expect(state.messages.map((message) => message.kind)).toEqual(['text', 'text', 'typing'])
    expect(state.pending).toBe(true)
  })

  it('accumulates the streamed deltas into one answer and lifts out its citations', () => {
    const state = replay('What does Cadre AI do?', GROUNDED_ANSWER)

    expect(state.messages.map((message) => message.kind)).toEqual(['text', 'text', 'text'])
    const answer = state.messages[2]
    expect(answer).toMatchObject({
      kind: 'text',
      role: 'assistant',
      raw:
        'Cadre AI is a consultancy focused on revenue growth ' +
        '[services#what-cadre-does]. Four core services [services#what-cadre-does].',
      text: 'Cadre AI is a consultancy focused on revenue growth. Four core services.',
      citations: ['services#what-cadre-does'],
    })
    expect(state.pending).toBe(false)
    expect(state.usage).toEqual({
      input_tokens: 12400,
      output_tokens: 48,
      cached_tokens: 12200,
      cost_usd: 0.0031,
    })
  })

  it('hides a citation marker that is still arriving', () => {
    const state = chatReducer(
      chatReducer(initialChatState(GREETING), { type: 'visitor_message', text: 'go on' }),
      { type: 'event', event: { event: 'text', data: { delta: 'Four core services [servi' } } },
    )

    expect(state.messages[2]).toMatchObject({ text: 'Four core services', citations: [] })
  })

  it('renders an Escalation as its own card and starts a fresh bubble after it', () => {
    const state = replay('What does it cost?', ESCALATED_ANSWER)

    expect(state.messages.map((message) => message.kind)).toEqual([
      'text',
      'text',
      'escalation',
      'text',
    ])
    expect(state.messages[2]).toMatchObject({
      kind: 'escalation',
      role: 'assistant',
      title: "I can't confirm that from what Cadre publishes",
      body: 'Cadre does not publish pricing for its engagements.',
      nextStep: 'Write hello@gocadre.ai or call (619) 324-3223.',
      citations: ['contact#how-to-reach-cadre'],
    })
    expect(state.messages[3]).toMatchObject({ text: 'Happy to help with anything else.' })
    expect(state.activeTool).toBeNull()
  })

  it('names the running tool while it runs, so the Visitor sees work happening', () => {
    const started = [{ type: 'visitor_message', text: 'What does it cost?' } as ChatAction].concat(
      ESCALATED_ANSWER.slice(0, 1).map((event): ChatAction => ({ type: 'event', event })),
    )

    expect(started.reduce(chatReducer, initialChatState(GREETING)).activeTool).toBe('escalate')
  })

  it('renders a failed Turn as a friendly message and keeps what was already streamed', () => {
    const state = replay('break it', FAILED_ANSWER)

    expect(state.messages.map((message) => message.kind)).toEqual(['text', 'text', 'text', 'error'])
    expect(state.messages[3]).toMatchObject({
      kind: 'error',
      role: 'assistant',
      text: "Something went wrong on my side and I couldn't finish.",
    })
    expect(state.pending).toBe(false)
  })

  it('gives every message its own id, so React never reuses a bubble for a new message', () => {
    const state = replay('What does it cost?', ESCALATED_ANSWER)
    const ids = state.messages.map((message) => message.id)

    expect(new Set(ids).size).toBe(ids.length)
  })

  it('learns the title behind every citation id, so a chip can show more than the id', () => {
    const state = chatReducer(initialChatState(GREETING), {
      type: 'sections_loaded',
      sections: [
        { id: 'not-published#pricing', title: 'Pricing', topic: 'not-published' },
        { id: 'services#what-cadre-does', title: 'What Cadre does', topic: 'services' },
      ],
    })

    expect(state.sections).toEqual({
      'not-published#pricing': 'Pricing',
      'services#what-cadre-does': 'What Cadre does',
    })
    expect(state.messages).toEqual(initialChatState(GREETING).messages)
  })

  it('keeps the section titles across the Turns that follow, so they are fetched once', () => {
    const loaded = chatReducer(initialChatState(GREETING), {
      type: 'sections_loaded',
      sections: [{ id: 'not-published#pricing', title: 'Pricing', topic: 'not-published' }],
    })

    const after = [
      { type: 'visitor_message', text: 'What does it cost?' } as ChatAction,
      ...ESCALATED_ANSWER.map((event): ChatAction => ({ type: 'event', event })),
    ].reduce(chatReducer, loaded)

    expect(after.sections).toEqual({ 'not-published#pricing': 'Pricing' })
  })

  it('reports a stream that never arrived in the same shape as a failed Turn', () => {
    const state = chatReducer(
      chatReducer(initialChatState(GREETING), { type: 'visitor_message', text: 'hello' }),
      { type: 'stream_failed', message: 'I lost the connection.' },
    )

    expect(state.messages[2]).toMatchObject({ kind: 'error', text: 'I lost the connection.' })
    expect(state.pending).toBe(false)
  })
})
