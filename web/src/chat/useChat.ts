/**
 * Post a Visitor message and feed the streamed events into the reducer.
 *
 * Same origin, so the Session cookie rides along without CORS or a token (ADR-0003). All the
 * logic worth testing lives in the reducer; this is the plumbing around it.
 */

import { useCallback, useReducer, useRef, useState } from 'react'

import { chatReducer, initialChatState } from './reducer'
import { readChatEvents } from './sse'
import type { ChatState, FeedbackRating, KBSectionTitle } from './types'

export const CHAT_ENDPOINT = '/api/chat'
export const SECTIONS_ENDPOINT = '/api/knowledge/sections'
export const FEEDBACK_ENDPOINT = '/api/feedback'

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

  return { state, send, loadSections, sendFeedback }
}
