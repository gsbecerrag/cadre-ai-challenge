/**
 * Post a Visitor message and feed the streamed events into the reducer.
 *
 * Same origin, so the Session cookie rides along without CORS or a token (ADR-0003). All the
 * logic worth testing lives in the reducer; this is the plumbing around it.
 */

import { useCallback, useReducer, useRef, useState } from 'react'

import { chatReducer, initialChatState } from './reducer'
import { readChatEvents } from './sse'
import type { ChatState, HandoverMode, HandoverState, KBSectionTitle, LeadContact } from './types'

export const CHAT_ENDPOINT = '/api/chat'
export const SECTIONS_ENDPOINT = '/api/knowledge/sections'
export const LEADS_ENDPOINT = '/api/leads'

/** What `POST /api/handover/{id}/accept` and `/decline` answer with. */
interface HandoverAnswer {
  request_id: string
  state: HandoverState
  mode: HandoverMode | null
  lead: LeadContact
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
  /** The Visitor pressed Yes on the Hand-over offer. */
  acceptHandover: (requestId: string) => Promise<void>
  /** The Visitor pressed "Keep chatting". */
  declineHandover: (requestId: string) => Promise<void>
  /** The Visitor filled in the "Your details" card. */
  shareDetails: (details: LeadContact) => Promise<void>
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
        dispatch({ type: 'handover', state: body.state, mode: body.mode, lead: body.lead })
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

  return {
    state,
    send,
    loadSections,
    acceptHandover,
    declineHandover,
    shareDetails,
    handoverBusy,
    handoverFailed,
  }
}
