import {
  collection,
  type DocumentData,
  limit,
  onSnapshot,
  orderBy,
  query,
} from 'firebase/firestore'
import { useEffect, useState } from 'react'

import { fetchTriageReports, type TriageReport } from './api'
import { type FeedStatus } from './leadsFeed'
import { FAKE_AUTH, firebaseFirestore } from './firebase'

/** How many Triage Reports the tab holds on screen — the API's page, matched. */
const PAGE = 50
/** How often the fallback asks the API when the realtime listener is not available. */
const POLL_MS = 10_000

function text(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

/**
 * A `triage_reports/{feedback_id}` document as the card needs it.
 *
 * Read defensively, the way the Firestore adapter reads it back in Python: a category or a
 * severity this build has no chip for is `other` / `medium` rather than an unstyled card, and
 * a report written by an older Triage Agent is still a report worth reading.
 */
function reportFromDocument(id: string, data: DocumentData): TriageReport {
  const created = data.created_at as { toDate?: () => Date } | undefined
  const evidence = Array.isArray(data.evidence) ? data.evidence : []
  return {
    id,
    session_id: text(data.session_id),
    trace_id: text(data.trace_id) || id,
    category: text(data.category) || 'other',
    summary: text(data.summary),
    evidence: evidence.map((quote) => text(quote)).filter((quote) => quote !== ''),
    suggested_kb_addition: text(data.suggested_kb_addition),
    suggested_eval_case: text(data.suggested_eval_case),
    severity: text(data.severity) || 'medium',
    model: text(data.model),
    created_at: created?.toDate ? created.toDate().toISOString() : null,
  }
}

/**
 * The Triage Reports a Strategist is looking at, and how fresh they are.
 *
 * Two sources, the same two as the Leads feed and for the same reasons: the API answers the
 * first paint (no Firestore client, no rules evaluation, and it works in the demo auth mode
 * that has no Firebase sign-in), and an `onSnapshot` listener then delivers reports as the
 * Triage Agent writes them — which is what makes a thumbs-down in the chat appear here about a
 * minute later without a refresh. If the listener cannot start or the rules deny it, the same
 * list is polled every ten seconds instead.
 */
export function useTriageReports(authorize: () => Promise<string>): {
  reports: TriageReport[]
  status: FeedStatus
  error?: string
} {
  const [reports, setReports] = useState<TriageReport[]>([])
  const [status, setStatus] = useState<FeedStatus>('loading')
  const [error, setError] = useState<string>()

  useEffect(() => {
    let live = true
    let poller: number | undefined
    let unsubscribe: (() => void) | undefined

    async function loadOnce() {
      try {
        const { reports: page } = await fetchTriageReports(authorize)
        if (live) {
          setReports(page)
          setError(undefined)
        }
      } catch (failure) {
        if (live) {
          setError(failure instanceof Error ? failure.message : 'Could not load Triage Reports.')
        }
      }
    }

    function poll() {
      if (poller !== undefined) {
        return
      }
      setStatus('polling')
      poller = window.setInterval(() => void loadOnce(), POLL_MS)
    }

    void loadOnce().then(() => {
      if (!live) {
        return
      }
      if (FAKE_AUTH) {
        // No Firebase sign-in in the demo mode, so the rules would deny the listener before
        // it delivered anything. Poll rather than log a denial the reviewer cannot act on.
        poll()
        return
      }
      try {
        const feed = query(
          collection(firebaseFirestore(), 'triage_reports'),
          orderBy('created_at', 'desc'),
          limit(PAGE),
        )
        unsubscribe = onSnapshot(
          feed,
          (snapshot) => {
            setReports(
              snapshot.docs.map((document) => reportFromDocument(document.id, document.data())),
            )
            setStatus('live')
            setError(undefined)
          },
          () => {
            unsubscribe?.()
            unsubscribe = undefined
            poll()
          },
        )
      } catch {
        poll()
      }
    })

    return () => {
      live = false
      unsubscribe?.()
      if (poller !== undefined) {
        window.clearInterval(poller)
      }
    }
  }, [authorize])

  return { reports, status, error }
}
