import { describe, expect, it } from 'vitest'

import { chatReducer, initialChatState } from './reducer'
import type { ChatAction, ChatEvent, ChatState, LeadContact } from './types'

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
      language: 'en',
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

/** Recorded from `POST /api/chat` with the stub provider (api/tests/test_walkthrough.py). */
const WALKTHROUGH_ANSWER: ChatEvent[] = [
  {
    event: 'text',
    data: {
      delta:
        "Here's where that lives — the Portal tracks tools, agents, training, and results " +
        '[portal#what-the-portal-tracks]:',
    },
  },
  { event: 'tool', data: { name: 'show_walkthrough', status: 'started' } },
  {
    event: 'card',
    data: {
      title: "See your agents' results in the Portal",
      steps: [
        'Open the Cadre Portal from the link your Cadre contact gave you',
        'Go to Agents in the left menu',
        'Pick an agent to see its runs, hours saved and status',
      ],
      destination: {
        id: 'portal.agents',
        label: 'Open demo Portal',
        href: '/portal/agents#portal-agents-results',
        external: false,
      },
      citations: ['portal#how-to-access-the-portal'],
    },
  },
  { event: 'tool', data: { name: 'show_walkthrough', status: 'finished' } },
  { event: 'text', data: { delta: 'Anything else I can look up for you?' } },
  {
    event: 'done',
    data: {
      trace_id: null,
      usage: { input_tokens: 13100, output_tokens: 96, cached_tokens: 12800, cost_usd: 0.0042 },
    },
  },
]

const FAILED_ANSWER: ChatEvent[] = [
  { event: 'text', data: { delta: 'Let me check that' } },
  { event: 'error', data: { message: "Something went wrong on my side and I couldn't finish." } },
]

/** The 32-hex id Langfuse gives a Trace, as the `done` event carries it. */
const TRACE = 'a'.repeat(32)
const SECOND_TRACE = 'b'.repeat(32)

/** The same recorded Turn, answered by a service that has Langfuse keys. */
function traced(events: ChatEvent[], traceId: string): ChatEvent[] {
  return events.map((event) =>
    event.event === 'done' ? { ...event, data: { ...event.data, trace_id: traceId } } : event,
  )
}

/** Recorded from `POST /api/chat` with the stub provider (api/tests/test_handover.py). */
const HANDOVER_OFFER: ChatEvent[] = [
  { event: 'tool', data: { name: 'offer_live_handover', status: 'started' } },
  {
    event: 'offer',
    data: {
      request_id: 'hr-0001',
      prompt: 'Do you want to jump into a call with our experts?',
    },
  },
  { event: 'tool', data: { name: 'offer_live_handover', status: 'finished' } },
  { event: 'text', data: { delta: 'Whenever you are ready.' } },
  {
    event: 'done',
    data: {
      trace_id: null,
      usage: { input_tokens: 900, output_tokens: 24, cached_tokens: 800, cost_usd: 0.0004 },
    },
  },
]

/** Obviously fake, as the Contact Details of a Lead always are in a test. */
const JANE: LeadContact = {
  name: 'Jane Doe',
  email: 'jane@example.com',
  company: 'Acme Manufacturing',
}

const NOBODY_YET: LeadContact = { name: '', email: '', company: '' }

/** Obviously not a real Daily domain, the way a fixture's email is example.com. */
const ROOM_URL = 'https://cadre-demo.daily.invalid/cadre-hr-0001'

/** The Visitor accepted while a Strategist was online: a room, and nobody in it yet. */
function connecting(): ChatState {
  return chatReducer(offered(), {
    type: 'handover',
    state: 'pending_strategist',
    mode: 'video',
    lead: JANE,
    roomUrl: ROOM_URL,
  })
}

function offered(): ChatState {
  return replay('Can I talk to someone?', HANDOVER_OFFER)
}

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
      language: 'en',
    })
    expect(state.messages[3]).toMatchObject({ text: 'Happy to help with anything else.' })
    expect(state.activeTool).toBeNull()
  })

  it('places a Walkthrough Card between the text before it and the text after it', () => {
    const state = replay("How do I see my agents' results?", WALKTHROUGH_ANSWER)

    expect(state.messages.map((message) => message.kind)).toEqual([
      'text',
      'text',
      'text',
      'walkthrough',
      'text',
    ])
    expect(state.messages[2]).toMatchObject({
      text:
        "Here's where that lives — the Portal tracks tools, agents, training, and results:",
      citations: ['portal#what-the-portal-tracks'],
    })
    expect(state.messages[4]).toMatchObject({ text: 'Anything else I can look up for you?' })
  })

  it('keeps the destination the server resolved, so the card links where it was told to', () => {
    const state = replay("How do I see my agents' results?", WALKTHROUGH_ANSWER)

    expect(state.messages[3]).toMatchObject({
      kind: 'walkthrough',
      role: 'assistant',
      title: "See your agents' results in the Portal",
      steps: [
        'Open the Cadre Portal from the link your Cadre contact gave you',
        'Go to Agents in the left menu',
        'Pick an agent to see its runs, hours saved and status',
      ],
      destination: {
        id: 'portal.agents',
        label: 'Open demo Portal',
        href: '/portal/agents#portal-agents-results',
        external: false,
      },
      citations: ['portal#how-to-access-the-portal'],
    })
    expect(state.pending).toBe(false)
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

  it('attaches the Turn\'s Trace to the answer it produced, and to nothing else', () => {
    const state = replay('What does Cadre AI do?', traced(GROUNDED_ANSWER, TRACE))

    expect(state.traceId).toBe(TRACE)
    expect(state.messages[2]).toMatchObject({ kind: 'text', role: 'assistant', traceId: TRACE })
    // The greeting and the Visitor's own message were not answers this Turn produced.
    expect(state.messages[0]).not.toHaveProperty('traceId', TRACE)
    expect(state.messages[1]).not.toHaveProperty('traceId', TRACE)
  })

  it('rates the last thing the Assistant said, so a Turn carries one set of thumbs', () => {
    const state = replay("How do I see my agents' results?", traced(WALKTHROUGH_ANSWER, TRACE))

    expect(state.messages.map((message) => message.kind)).toEqual([
      'text',
      'text',
      'text',
      'walkthrough',
      'text',
    ])
    expect(state.messages.filter((message) => 'traceId' in message && message.traceId)).toEqual([
      state.messages[4],
    ])
  })

  it('leaves an untraced Turn unrateable rather than inventing an id for it', () => {
    // No Langfuse keys — `make dev`, CI, a reviewer's laptop. There is no Trace to score, so
    // the widget has nothing to attach thumbs to and shows none.
    const state = replay('What does Cadre AI do?', GROUNDED_ANSWER)

    expect(state.traceId).toBeNull()
    expect(state.messages.every((message) => !('traceId' in message && message.traceId))).toBe(true)
  })

  it('records the rating the moment the server takes it, and offers the one change', () => {
    const answered = replay('What does Cadre AI do?', traced(GROUNDED_ANSWER, TRACE))

    expect(answered.feedback).toEqual({})

    const rated = chatReducer(answered, {
      type: 'feedback_sent',
      traceId: TRACE,
      rating: 'down',
      changed: false,
    })

    expect(rated.feedback[TRACE]).toEqual({ rating: 'down', status: 'sent' })
  })

  it('takes a note on the rating that stands without spending the change', () => {
    // The widget sends the thumb first and the sentence after it, so the same rating arrives
    // twice for one opinion. The server calls that unchanged, and so does this.
    const noted = [
      { type: 'feedback_sent', traceId: TRACE, rating: 'down', changed: false },
      { type: 'feedback_sent', traceId: TRACE, rating: 'down', changed: false },
    ].reduce(
      (state, action) => chatReducer(state, action as ChatAction),
      replay('What does Cadre AI do?', traced(GROUNDED_ANSWER, TRACE)),
    )

    expect(noted.feedback[TRACE]).toEqual({ rating: 'down', status: 'sent' })
  })

  it('closes the control once the other thumb has spent the one change', () => {
    const changed = [
      { type: 'feedback_sent', traceId: TRACE, rating: 'up', changed: false },
      { type: 'feedback_sent', traceId: TRACE, rating: 'down', changed: true },
    ].reduce(
      (state, action) => chatReducer(state, action as ChatAction),
      replay('What does Cadre AI do?', traced(GROUNDED_ANSWER, TRACE)),
    )

    expect(changed.feedback[TRACE]).toEqual({ rating: 'down', status: 'changed' })

    const pressedAgain = chatReducer(changed, {
      type: 'feedback_sent',
      traceId: TRACE,
      rating: 'up',
      changed: true,
    })

    expect(pressedAgain.feedback[TRACE]).toEqual({ rating: 'down', status: 'changed' })
  })

  it('locks the control when the server says this answer has been rated once too often', () => {
    const locked = [
      { type: 'feedback_sent', traceId: TRACE, rating: 'up', changed: false },
      { type: 'feedback_locked', traceId: TRACE },
    ].reduce(
      (state, action) => chatReducer(state, action as ChatAction),
      replay('What does Cadre AI do?', traced(GROUNDED_ANSWER, TRACE)),
    )

    expect(locked.feedback[TRACE]).toEqual({ rating: 'up', status: 'locked' })

    // Terminal: a late reply from a request that crossed the lock cannot reopen it.
    const late = chatReducer(locked, {
      type: 'feedback_sent',
      traceId: TRACE,
      rating: 'down',
      changed: true,
    })

    expect(late.feedback[TRACE]).toEqual({ rating: 'up', status: 'locked' })
  })

  it("keeps each Turn's Feedback to its own Trace", () => {
    const first = chatReducer(replay('What does Cadre AI do?', traced(GROUNDED_ANSWER, TRACE)), {
      type: 'feedback_sent',
      traceId: TRACE,
      rating: 'down',
      changed: false,
    })

    const second = [
      { type: 'visitor_message', text: 'What does it cost?' } as ChatAction,
      ...traced(ESCALATED_ANSWER, SECOND_TRACE).map(
        (event): ChatAction => ({ type: 'event', event }),
      ),
    ].reduce(chatReducer, first)

    expect(second.feedback[TRACE]).toEqual({ rating: 'down', status: 'sent' })
    expect(second.feedback[SECOND_TRACE]).toBeUndefined()
  })

  it('reports a stream that never arrived in the same shape as a failed Turn', () => {
    const state = chatReducer(
      chatReducer(initialChatState(GREETING), { type: 'visitor_message', text: 'hello' }),
      { type: 'stream_failed', message: 'I lost the connection.' },
    )

    expect(state.messages[2]).toMatchObject({ kind: 'error', text: 'I lost the connection.' })
    expect(state.pending).toBe(false)
  })

  // --- the Callback Hand-over (ticket 11) ---------------------------------------------------

  it('shows the Hand-over offer as a card the Visitor answers with a button', () => {
    const state = offered()

    expect(state.messages.map((message) => message.kind)).toEqual([
      'text',
      'text',
      'offer',
      'text',
    ])
    expect(state.messages[2]).toMatchObject({
      kind: 'offer',
      requestId: 'hr-0001',
      prompt: 'Do you want to jump into a call with our experts?',
      status: 'open',
    })
    // The card closes the bubble that was streaming, so the sentence after it is its own.
    expect(state.messages[3]).toMatchObject({ kind: 'text', text: 'Whenever you are ready.' })
  })

  it('asks for the details a Callback needs when the Lead has no name or email yet', () => {
    const accepted = chatReducer(offered(), {
      type: 'handover',
      state: 'pending_strategist',
      mode: 'callback',
      lead: NOBODY_YET,
    })

    expect(accepted.messages[2]).toMatchObject({ kind: 'offer', status: 'accepted' })
    expect(accepted.messages.at(-1)).toMatchObject({ kind: 'details', done: false })
  })

  it('confirms the Callback with the details the Visitor typed into the card', () => {
    const asked = chatReducer(offered(), {
      type: 'handover',
      state: 'pending_strategist',
      mode: 'callback',
      lead: NOBODY_YET,
    })

    const shared = chatReducer(asked, { type: 'details_shared', lead: JANE })

    expect(shared.messages.map((message) => message.kind)).toEqual([
      'text',
      'text',
      'offer',
      'text',
      'details',
      'callback',
    ])
    expect(shared.messages[4]).toMatchObject({ kind: 'details', done: true })
    expect(shared.messages[5]).toMatchObject({ kind: 'callback', lead: JANE })
  })

  it('confirms the Callback once, however many times the details card is submitted', () => {
    // A double-pressed "Share details", or a retried request, must not leave the Visitor
    // looking at two Callback confirmations for one Callback.
    const asked = chatReducer(offered(), {
      type: 'handover',
      state: 'pending_strategist',
      mode: 'callback',
      lead: NOBODY_YET,
    })
    const shared = chatReducer(asked, { type: 'details_shared', lead: JANE })

    const again = chatReducer(shared, { type: 'details_shared', lead: JANE })

    expect(again).toBe(shared)
    expect(again.messages.filter((message) => message.kind === 'callback')).toHaveLength(1)
  })

  it('confirms the Callback straight away when the Lead is already reachable', () => {
    const accepted = chatReducer(offered(), {
      type: 'handover',
      state: 'pending_strategist',
      mode: 'callback',
      lead: JANE,
    })

    expect(accepted.messages.at(-1)).toMatchObject({ kind: 'callback', lead: JANE })
    expect(accepted.messages.some((message) => message.kind === 'details')).toBe(false)
  })

  it('says a Strategist is being connected when the Hand-over is a video call', () => {
    const accepted = chatReducer(offered(), {
      type: 'handover',
      state: 'pending_strategist',
      mode: 'video',
      lead: JANE,
    })

    expect(accepted.messages.at(-1)).toMatchObject({ kind: 'note', note: 'handoverConnecting' })
  })

  it('takes a decline gracefully and leaves the conversation open', () => {
    const declined = chatReducer(offered(), {
      type: 'handover',
      state: 'declined',
      mode: null,
      lead: NOBODY_YET,
    })

    expect(declined.messages[2]).toMatchObject({ kind: 'offer', status: 'declined' })
    expect(declined.messages.at(-1)).toMatchObject({ kind: 'note', note: 'handoverDeclined' })
    expect(declined.pending).toBe(false)
  })

  it('answers the offer only once, however many times the button is pressed', () => {
    const accepted = chatReducer(offered(), {
      type: 'handover',
      state: 'pending_strategist',
      mode: 'callback',
      lead: JANE,
    })

    const again = chatReducer(accepted, {
      type: 'handover',
      state: 'pending_strategist',
      mode: 'callback',
      lead: JANE,
    })

    expect(again).toBe(accepted)
  })

  // --- the Live Hand-over on video (ticket 15) -----------------------------------------------

  it('opens the call frame with the room the moment the Visitor accepts a video Hand-over', () => {
    const accepted = connecting()

    expect(accepted.call).toEqual({
      state: 'pending_strategist',
      roomUrl: ROOM_URL,
      strategistName: '',
    })
    expect(accepted.messages[2]).toMatchObject({ kind: 'offer', status: 'accepted' })
    expect(accepted.messages.at(-1)).toMatchObject({ kind: 'note', note: 'handoverConnecting' })
  })

  it('shows the connecting state until there is a room to open', () => {
    // The accept answered `video` but the room is not on the request yet: the panel spins
    // rather than mounting an iframe with nowhere to point it.
    const accepted = chatReducer(offered(), {
      type: 'handover',
      state: 'pending_strategist',
      mode: 'video',
      lead: JANE,
    })

    expect(accepted.call).toEqual({ state: 'pending_strategist', roomUrl: '', strategistName: '' })
  })

  it('names the Strategist once they have joined, without saying anything new', () => {
    const waiting = connecting()

    const joined = chatReducer(waiting, {
      type: 'handover',
      state: 'in_call',
      mode: 'video',
      lead: JANE,
      roomUrl: ROOM_URL,
      strategistName: 'Angel M.',
    })

    expect(joined.call).toEqual({
      state: 'in_call',
      roomUrl: ROOM_URL,
      strategistName: 'Angel M.',
    })
    // A status poll is not a thing the Assistant said, so the transcript does not grow.
    expect(joined.messages).toEqual(waiting.messages)
  })

  it('closes the call frame and says so when the call has ended', () => {
    const joined = chatReducer(connecting(), {
      type: 'handover',
      state: 'in_call',
      mode: 'video',
      lead: JANE,
      roomUrl: ROOM_URL,
      strategistName: 'Angel M.',
    })

    const over = chatReducer(joined, {
      type: 'handover',
      state: 'ended',
      mode: 'video',
      lead: JANE,
    })

    expect(over.call).toBeNull()
    expect(over.messages.at(-1)).toMatchObject({ kind: 'note', note: 'callEnded' })
  })

  it('turns a call nobody joined into the Callback the Visitor was promised', () => {
    // The server's join timeout: `no_strategist_available` with the mode flipped to
    // `callback`, and the Lead already captured — so this is the ticket 11 confirmation.
    const timedOut = chatReducer(connecting(), {
      type: 'handover',
      state: 'no_strategist_available',
      mode: 'callback',
      lead: JANE,
    })

    expect(timedOut.call).toBeNull()
    expect(timedOut.messages.at(-1)).toMatchObject({ kind: 'callback', lead: JANE })
  })

  it('asks for the details the Callback needs when a call nobody joined times out', () => {
    const timedOut = chatReducer(connecting(), {
      type: 'handover',
      state: 'no_strategist_available',
      mode: 'callback',
      lead: NOBODY_YET,
    })

    expect(timedOut.messages.at(-1)).toMatchObject({ kind: 'details', done: false })
  })

  it('leaves the state untouched while the poll keeps saying the same thing', () => {
    // Every five seconds, for as long as the Visitor waits. A new state object per poll would
    // re-render the panel — and remount the iframe, which drops them out of the call.
    const waiting = connecting()

    const again = chatReducer(waiting, {
      type: 'handover',
      state: 'pending_strategist',
      mode: 'video',
      lead: JANE,
      roomUrl: ROOM_URL,
    })

    expect(again).toBe(waiting)
  })

  it('says the call ended once, however many times the poll reports it', () => {
    const over = chatReducer(connecting(), {
      type: 'handover',
      state: 'ended',
      mode: 'video',
      lead: JANE,
    })

    const again = chatReducer(over, {
      type: 'handover',
      state: 'ended',
      mode: 'video',
      lead: JANE,
    })

    expect(again).toBe(over)
  })

  it('lets the Visitor leave the call and go back to the conversation', () => {
    // Nothing server-side: the Strategist may still be in the room, and the Lead is still a
    // Lead. What changes is that the Visitor is looking at the transcript again — which
    // without this they cannot do, because the call takes the message area and the composer.
    const joined = chatReducer(connecting(), {
      type: 'handover',
      state: 'in_call',
      mode: 'video',
      lead: JANE,
      roomUrl: ROOM_URL,
      strategistName: 'Angel M.',
    })

    const left = chatReducer(joined, { type: 'left_call' })

    expect(left.call).toBeNull()
    expect(left.messages.at(-1)).toMatchObject({ kind: 'note', note: 'callLeft' })
  })

  it('says nothing when there is no call to leave', () => {
    const state = offered()

    expect(chatReducer(state, { type: 'left_call' })).toBe(state)
  })

  it('reduces a Hand-over that arrives on the wire the same way as one the browser asked for', () => {
    const state = [
      ...HANDOVER_OFFER.map((event): ChatAction => ({ type: 'event', event })),
      {
        type: 'event',
        event: {
          event: 'handover',
          data: { request_id: 'hr-0001', state: 'declined', mode: null },
        },
      } as ChatAction,
    ].reduce(chatReducer, chatReducer(initialChatState(GREETING), {
      type: 'visitor_message',
      text: 'Can I talk to someone?',
    }))

    expect(state.messages[2]).toMatchObject({ kind: 'offer', status: 'declined' })
    expect(state.messages.at(-1)).toMatchObject({ kind: 'note', note: 'handoverDeclined' })
  })
})
