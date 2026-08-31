/**
 * The Handover Requests a Strategist is looking at, live — and the noise one makes on arrival.
 *
 * Two sources, exactly as the Leads feed has: the API answers the first paint (no Firestore
 * client, no rules evaluation, and it works in the demo mode that has no Firebase sign-in),
 * and a Firestore `onSnapshot` listener then delivers new requests the moment the Assistant
 * writes them. That write *is* the notification (`core/adapters/firestore_notifier.py`): the
 * Console is subscribed to the collection, so there is no second channel to keep in step. If
 * the listener cannot start or the rules deny it, the same list is polled from the API every
 * ten seconds — a Console a few seconds stale beats a Console that is empty.
 *
 * A request the Visitor has *accepted* while the Console is open raises a browser notification
 * and plays a short blip — `pending_strategist`, the state that means somebody is waiting for a
 * call, not `offered`, which only means the Assistant put the card on screen and the Visitor may
 * yet say no. The first delivery is silent whatever it holds: it is the backlog a Strategist
 * opened the page to read, and pinging them once per waiting request would train them to ignore
 * the sound.
 */

import {
  collection,
  type DocumentData,
  limit,
  onSnapshot,
  orderBy,
  query,
} from 'firebase/firestore'
import { useEffect, useRef, useState } from 'react'

import {
  fetchHandovers,
  type Handover,
  type HandoverMode,
  type HandoverState,
  type Lead,
} from './api'
import { FAKE_AUTH, firebaseFirestore } from './firebase'
import { type FeedStatus, SIGNALS } from './leadsFeed'
import { playNotificationSound } from './notificationSound'

/** How many requests the Console holds on screen — the API's page, matched. */
const PAGE = 50
/** How often the fallback asks the API when the realtime listener is not available. */
const POLL_MS = 10_000

/**
 * The label a Strategist reads, derived from the state and the mode (docs/design/README.md
 * ruling). The data model keeps the eight names the spec fixes; the screen shows five.
 */
export type HandoverLabel = 'Pending' | 'In call' | 'Ended' | 'Declined' | 'Callback'

const PENDING_STATES: HandoverState[] = ['offered', 'accepted_by_user', 'pending_strategist']
const IN_CALL_STATES: HandoverState[] = ['strategist_joined', 'in_call']

export function labelOf(request: Handover): HandoverLabel {
  if (request.state === 'declined') {
    return 'Declined'
  }
  if (request.mode === 'callback' || request.state === 'no_strategist_available') {
    return 'Callback'
  }
  if (IN_CALL_STATES.includes(request.state)) {
    return 'In call'
  }
  return request.state === 'ended' ? 'Ended' : 'Pending'
}

/** The colours the design gives each label, and which of them pulses. */
export const LABEL_STYLE: Record<HandoverLabel, { color: string; pulsing: boolean }> = {
  Pending: { color: '#db4545', pulsing: true },
  'In call': { color: '#0a7d43', pulsing: true },
  Ended: { color: '#999999', pulsing: false },
  Declined: { color: '#999999', pulsing: false },
  Callback: { color: '#999966', pulsing: false },
}

/** Work a Strategist has not dealt with yet — what the nav badge counts. */
export function isPending(request: Handover): boolean {
  return PENDING_STATES.includes(request.state)
}

function text(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function leadFrom(sessionId: string, data: DocumentData): Lead {
  const signals = (data.signals ?? {}) as Record<string, string>
  return {
    session_id: sessionId,
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
 * A `handover_requests/{id}` document as the queue card needs it.
 *
 * `present_signals` is recomputed here rather than read, because Firestore stores the request
 * and not the API's view of it. The two agree by construction: a signal is stored only when
 * the Assistant actually learned it.
 */
function handoverFrom(id: string, data: DocumentData): Handover {
  const created = data.created_at as { toDate?: () => Date } | undefined
  return {
    request_id: id,
    session_id: text(data.session_id),
    state: (text(data.state) || 'offered') as HandoverState,
    mode: (data.mode ?? null) as HandoverMode | null,
    prompt: text(data.prompt),
    created_at: created?.toDate ? created.toDate().toISOString() : null,
    trace_id: typeof data.trace_id === 'string' ? data.trace_id : null,
    lead: leadFrom(text(data.session_id), (data.lead ?? {}) as DocumentData),
  }
}

/** A request somebody is waiting on: accepted by the Visitor, not yet picked up. */
function isWaiting(request: Handover): boolean {
  return request.state === 'pending_strategist'
}

/** Tell the Strategist, once, that a Visitor accepted while they were looking elsewhere. */
function announce(request: Handover): void {
  playNotificationSound()
  try {
    if (typeof Notification === 'undefined' || Notification.permission !== 'granted') {
      return
    }
    const who = request.lead.name || request.lead.company || 'A Qualified Lead'
    new Notification('Hand-over accepted', {
      body: `${who} — score ${request.lead.score} of 5`,
      tag: request.request_id,
    })
  } catch {
    // Notifications are unavailable or were revoked mid-session; the sound and the queue card
    // still did their job.
  }
}

/**
 * Ask for permission to raise browser notifications.
 *
 * Called from the Availability toggle and nowhere else: a permission prompt on page load is
 * the thing every browser now warns about, and a Strategist going Online is exactly the
 * moment they have said they want to be interrupted.
 */
export function askToNotify(): void {
  try {
    if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
      void Notification.requestPermission()
    }
  } catch {
    // Some browsers throw on a non-secure origin. Nothing to do; the sound still plays.
  }
}

export function useHandovers(authorize: () => Promise<string>): {
  handovers: Handover[]
  status: FeedStatus
  error?: string
} {
  const [handovers, setHandovers] = useState<Handover[]>([])
  const [status, setStatus] = useState<FeedStatus>('loading')
  const [error, setError] = useState<string>()
  // Which requests this Console has already announced — tracked by *state*, not by existence,
  // because the news is the acceptance and not the offer: a request delivered as `offered` and
  // then accepted has to ring, and one that arrives already accepted has to ring once. The
  // first delivery fills the set silently: it is the backlog, not news.
  const announced = useRef<Set<string> | undefined>(undefined)

  useEffect(() => {
    let live = true
    let poller: number | undefined
    let unsubscribe: (() => void) | undefined

    function deliver(page: Handover[]) {
      if (!live) {
        return
      }
      const waiting = page.filter(isWaiting)
      const heard = announced.current
      if (heard === undefined) {
        announced.current = new Set(waiting.map((request) => request.request_id))
      } else {
        for (const request of waiting) {
          if (!heard.has(request.request_id)) {
            heard.add(request.request_id)
            announce(request)
          }
        }
      }
      setHandovers(page)
      setError(undefined)
    }

    async function loadOnce() {
      try {
        const { handovers: page } = await fetchHandovers(authorize)
        deliver(page)
      } catch (failure) {
        if (live) {
          setError(
            failure instanceof Error ? failure.message : 'Could not load Handover Requests.',
          )
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
        // No Firebase sign-in in the demo mode, so the rules would deny the listener before it
        // delivered anything. Poll rather than log a denial the reviewer cannot act on.
        poll()
        return
      }
      try {
        const feed = query(
          collection(firebaseFirestore(), 'handover_requests'),
          orderBy('created_at', 'desc'),
          limit(PAGE),
        )
        unsubscribe = onSnapshot(
          feed,
          (snapshot) => {
            deliver(
              snapshot.docs.map((document) => handoverFrom(document.id, document.data())),
            )
            setStatus('live')
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

  return { handovers, status, error }
}
