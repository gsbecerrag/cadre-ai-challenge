import {
  collection,
  type DocumentData,
  limit,
  onSnapshot,
  orderBy,
  query,
} from 'firebase/firestore'
import { useEffect, useState } from 'react'

import { fetchLeads, type Lead } from './api'
import { FAKE_AUTH, firebaseFirestore } from './firebase'

/**
 * The five Qualification Signals, in the fixed order the Console draws its rows in. Same five
 * names as `core/qualification.py` and as `capture_lead`'s arguments — a rename on either side
 * has to be a rename on both, which is why the labels live next to the names.
 */
export const SIGNALS = [
  { name: 'industry_fit', label: 'Industry fit' },
  { name: 'company_size_or_role', label: 'Company size or role' },
  { name: 'initiative_or_pain', label: 'Initiative or pain' },
  { name: 'timeline_or_budget', label: 'Timeline or budget' },
  { name: 'explicit_intent', label: 'Explicit intent' },
] as const

/** How many Leads the Console holds on screen — the API's page, matched. */
const PAGE = 50
/** How often the fallback asks the API when the realtime listener is not available. */
const POLL_MS = 10_000

export type FeedStatus = 'loading' | 'live' | 'polling'

function text(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

/**
 * A `leads/{session_id}` document as the queue card needs it.
 *
 * `present_signals` is recomputed here rather than read, because Firestore stores the Lead and
 * not the API's view of it. The two agree by construction: `capture_lead` strips the filler a
 * model writes instead of omitting a field, so a signal is stored only when it was learned.
 */
function leadFromDocument(id: string, data: DocumentData): Lead {
  const signals = (data.signals ?? {}) as Record<string, string>
  return {
    session_id: text(data.session_id) || id,
    name: text(data.name),
    email: text(data.email),
    company: text(data.company),
    phone: text(data.phone),
    role: text(data.role),
    signals,
    present_signals: SIGNALS.map((signal) => signal.name).filter(
      (name) => text(signals[name]).trim() !== '',
    ),
    score: typeof data.score === 'number' ? data.score : 0,
    qualified: data.qualified === true,
  }
}

/**
 * The Leads a Strategist is looking at, and how fresh they are.
 *
 * Two sources, deliberately: the API answers the first paint (no Firestore client, no rules
 * evaluation, and it works in the demo mode that has no Firebase sign-in), and a Firestore
 * `onSnapshot` listener then delivers new Leads as the Assistant captures them — that is the
 * "appears without a refresh" the ticket asks for. If the listener cannot start or is denied
 * by the rules, the same list is polled from the API every ten seconds instead: a Console that
 * is a few seconds stale beats a Console that is empty.
 */
export function useLeads(authorize: () => Promise<string>): {
  leads: Lead[]
  status: FeedStatus
  error?: string
} {
  const [leads, setLeads] = useState<Lead[]>([])
  const [status, setStatus] = useState<FeedStatus>('loading')
  const [error, setError] = useState<string>()

  useEffect(() => {
    let live = true
    let poller: number | undefined
    let unsubscribe: (() => void) | undefined

    async function loadOnce() {
      try {
        const { leads: page } = await fetchLeads(authorize)
        if (live) {
          setLeads(page)
          setError(undefined)
        }
      } catch (failure) {
        if (live) {
          setError(failure instanceof Error ? failure.message : 'Could not load Leads.')
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
          collection(firebaseFirestore(), 'leads'),
          orderBy('updated_at', 'desc'),
          limit(PAGE),
        )
        unsubscribe = onSnapshot(
          feed,
          (snapshot) => {
            setLeads(snapshot.docs.map((document) => leadFromDocument(document.id, document.data())))
            setStatus('live')
            setError(undefined)
          },
          () => {
            // Denied by the rules, offline, or Firestore unreachable: the API still works.
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

  return { leads, status, error }
}
