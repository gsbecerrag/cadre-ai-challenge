/**
 * Post a Visitor message and feed the streamed events into the reducer.
 *
 * Same origin, so the Session cookie rides along without CORS or a token (ADR-0003). All the
 * logic worth testing lives in the reducer; this is the plumbing around it.
 */

import { useCallback, useEffect, useReducer, useRef, useState } from 'react'

import { chatReducer, initialChatState } from './reducer'
import { readChatEvents } from './sse'
import type {
  ChatAction,
  ChatState,
  FeedbackRating,
  HandoverMode,
  HandoverState,
  KBSectionTitle,
  LeadContact,
} from './types'

export const CHAT_ENDPOINT = '/api/chat'
export const SECTIONS_ENDPOINT = '/api/knowledge/sections'
export const FEEDBACK_ENDPOINT = '/api/feedback'
export const LEADS_ENDPOINT = '/api/leads'

/**
 * How often the widget asks what its own Hand-over is doing.
 *
 * Five seconds, and only while a Live Hand-over is unfinished, so the cost of the whole
 * feature is a handful of tiny reads per call rather than a socket per open panel. The state
 * changes it is waiting for are made by a human pressing a button on the Console, so a wait of
 * up to five seconds is inside the time it takes them to move their hand.
 */
export const HANDOVER_POLL_MS = 5000

/** The states a Live Hand-over is still going in — what the widget keeps polling through. */
const UNFINISHED: HandoverState[] = ['pending_strategist', 'strategist_joined', 'in_call']

/** What `POST /api/handover/{id}/accept`, `/decline` and `GET /api/handover/{id}` answer. */
interface HandoverAnswer {
  request_id: string
  state: HandoverState
  mode: HandoverMode | null
  lead: LeadContact
  room_url: string | null
  strategist_name: string | null
}

function handoverAction(answer: HandoverAnswer): ChatAction {
  return {
    type: 'handover',
    state: answer.state,
    mode: answer.mode,
    lead: answer.lead,
    roomUrl: answer.room_url ?? '',
    strategistName: answer.strategist_name ?? '',
  }
}

interface CapturedLead {
  lead: LeadContact
  score: number
  qualified: boolean
}

export interface Chat {
  state: ChatState
  send: (text: string) => Promise<void>
  /** Fetch the KB Section titles the citation chips reveal. Idempotent; called when the
   * panel first opens, so a Visitor who never opens it never pays for the request. */
  loadSections: () => Promise<void>
  /**
   * Post the Feedback for one Trace — the rating on the press, and again with the Visitor's
   * sentence if they add one. Resolves to whether the server took it, which is what tells the
   * control it may clear the note box rather than leave the Visitor retyping.
   */
  sendFeedback: (traceId: string, rating: FeedbackRating, comment: string) => Promise<boolean>
  /** The Visitor pressed Yes on the Hand-over offer. */
  acceptHandover: (requestId: string) => Promise<void>
  /** The Visitor pressed "Keep chatting". */
  declineHandover: (requestId: string) => Promise<void>
  /** The Visitor filled in the "Your details" card. */
  shareDetails: (details: LeadContact) => Promise<void>
  /** The Visitor closed the call frame. Local only — the Handover Request is untouched. */
  leaveCall: () => void
  /** One of the three above is in flight, and whether the last one failed. */
  handoverBusy: boolean
  handoverFailed: boolean
}

export function useChat(greeting: string, connectionError: string): Chat {
  const [state, dispatch] = useReducer(chatReducer, greeting, initialChatState)
  // One Turn at a time: the composer is disabled while `state.pending`, and this guards the
  // case where it is submitted anyway (a double Enter, a stale click).
  const [inFlight, setInFlight] = useState(false)
  const sectionsRequested = useRef(false)

  const send = useCallback(
    async (text: string) => {
      const message = text.trim()
      if (!message || inFlight) {
        return
      }
      setInFlight(true)
      dispatch({ type: 'visitor_message', text: message })
      try {
        const response = await fetch(CHAT_ENDPOINT, {
          method: 'POST',
          headers: { 'content-type': 'application/json', accept: 'text/event-stream' },
          body: JSON.stringify({ message }),
          credentials: 'same-origin',
        })
        if (!response.ok || !response.body) {
          throw new Error(`the chat endpoint answered ${response.status}`)
        }
        let ended = false
        for await (const event of readChatEvents(response.body)) {
          ended = event.event === 'done' || event.event === 'error'
          dispatch({ type: 'event', event })
        }
        if (!ended) {
          // The connection dropped mid-Turn: without this the typing bubble never stops.
          throw new Error('the stream ended before the Turn did')
        }
      } catch {
        dispatch({ type: 'stream_failed', message: connectionError })
      } finally {
        setInFlight(false)
      }
    },
    [connectionError, inFlight],
  )

  // One answer at a time, and one place that knows whether the last one failed: the buttons
  // wait while a request is in flight, so a double press cannot send two answers to one offer.
  const [handoverBusy, setHandoverBusy] = useState(false)
  const [handoverFailed, setHandoverFailed] = useState(false)
  // The Handover Request whose status is being polled, or null when there is nothing waiting.
  const [watching, setWatching] = useState<string | null>(null)

  const answerOffer = useCallback(
    async (requestId: string, answer: 'accept' | 'decline') => {
      if (handoverBusy) {
        return
      }
      setHandoverBusy(true)
      setHandoverFailed(false)
      try {
        const response = await fetch(`/api/handover/${encodeURIComponent(requestId)}/${answer}`, {
          method: 'POST',
          credentials: 'same-origin',
        })
        if (!response.ok) {
          throw new Error(`the Hand-over endpoint answered ${response.status}`)
        }
        const body = (await response.json()) as HandoverAnswer
        dispatch(handoverAction(body))
        // Only a Live Hand-over has anything left to happen on the server: a Callback is
        // finished the moment it is recorded, and polling one would be a request every five
        // seconds for an answer that cannot change.
        if (body.mode === 'video' && UNFINISHED.includes(body.state)) {
          setWatching(body.request_id)
        }
      } catch {
        // The offer card stays exactly as it was, so the Visitor can press again.
        setHandoverFailed(true)
        dispatch({ type: 'stream_failed', message: connectionError })
      } finally {
        setHandoverBusy(false)
      }
    },
    [connectionError, handoverBusy],
  )

  const acceptHandover = useCallback(
    (requestId: string) => answerOffer(requestId, 'accept'),
    [answerOffer],
  )

  const declineHandover = useCallback(
    (requestId: string) => answerOffer(requestId, 'decline'),
    [answerOffer],
  )

  const shareDetails = useCallback(
    async (details: LeadContact) => {
      if (handoverBusy) {
        return
      }
      setHandoverBusy(true)
      setHandoverFailed(false)
      try {
        const response = await fetch(LEADS_ENDPOINT, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(details),
          credentials: 'same-origin',
        })
        if (!response.ok) {
          throw new Error(`the Lead endpoint answered ${response.status}`)
        }
        const body = (await response.json()) as CapturedLead
        dispatch({ type: 'details_shared', lead: body.lead })
      } catch {
        // The form keeps what was typed and says so, rather than losing it to an error bubble.
        setHandoverFailed(true)
      } finally {
        setHandoverBusy(false)
      }
    },
    [handoverBusy],
  )

  /**
   * Follow one Live Hand-over until it is over.
   *
   * The Visitor learns everything that happens on the Console's side from here: the room, the
   * Strategist's name when they claim the request, and the server's own join timeout, which
   * is answered on this read rather than by a background job. A failed poll is not news —
   * the next one is five seconds away — so it is swallowed rather than shown.
   */
  useEffect(() => {
    if (watching === null) {
      return
    }
    let live = true
    const timer = window.setInterval(() => {
      void (async () => {
        try {
          const response = await fetch(`/api/handover/${encodeURIComponent(watching)}`, {
            credentials: 'same-origin',
          })
          if (!response.ok) {
            throw new Error(`the Hand-over endpoint answered ${response.status}`)
          }
          const body = (await response.json()) as HandoverAnswer
          if (!live) {
            return
          }
          dispatch(handoverAction(body))
          if (!UNFINISHED.includes(body.state)) {
            setWatching(null)
          }
        } catch {
          // One poll that did not arrive changes nothing: the reducer keeps the frame it has.
        }
      })()
    }, HANDOVER_POLL_MS)
    return () => {
      live = false
      window.clearInterval(timer)
    }
  }, [watching])

  const leaveCall = useCallback(() => {
    // Stop polling as well as closing the frame. The reducer would ignore the answers anyway
    // once there is no call, and a request every five seconds for an answer nobody will act
    // on is a request not worth making.
    setWatching(null)
    dispatch({ type: 'left_call' })
  }, [])

  const loadSections = useCallback(async () => {
    if (sectionsRequested.current) {
      return
    }
    sectionsRequested.current = true
    try {
      const response = await fetch(SECTIONS_ENDPOINT, { credentials: 'same-origin' })
      if (!response.ok) {
        throw new Error(`the sections endpoint answered ${response.status}`)
      }
      const body = (await response.json()) as { sections: KBSectionTitle[] }
      dispatch({ type: 'sections_loaded', sections: body.sections })
    } catch {
      // A chip without its title still shows the id it cites, so this failure is not worth
      // interrupting the Visitor over — it just leaves the next open free to try again.
      sectionsRequested.current = false
    }
  }, [])

  const sendFeedback = useCallback(
    async (traceId: string, rating: FeedbackRating, comment: string): Promise<boolean> => {
      try {
        const response = await fetch(FEEDBACK_ENDPOINT, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ trace_id: traceId, rating, comment }),
          credentials: 'same-origin',
        })
        if (response.status === 409) {
          // Already rated and changed once — another tab, or a reload that lost what this
          // one knew. The rating that stands is the server's, so the control locks.
          dispatch({ type: 'feedback_locked', traceId })
          return true
        }
        if (!response.ok) {
          // Any other refusal leaves the control as it is, with what the Visitor typed still
          // in the box: they can send it again, and a rating is not worth an error bubble in
          // the middle of a conversation.
          return false
        }
        // The rating comes back from the receipt rather than being assumed from the request:
        // the server is the one that knows which thumb now stands, and on a repeat it may be
        // holding the sentence this request did not carry.
        const body = (await response.json()) as { rating: FeedbackRating; changed: boolean }
        dispatch({ type: 'feedback_sent', traceId, rating: body.rating, changed: body.changed })
        return true
      } catch {
        return false
      }
    },
    [],
  )

  return {
    state,
    send,
    loadSections,
    sendFeedback,
    acceptHandover,
    declineHandover,
    shareDetails,
    leaveCall,
    handoverBusy,
    handoverFailed,
  }
}
