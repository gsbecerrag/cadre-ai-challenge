/**
 * The Handover queue — docs/design §3.1.
 *
 * A list of requests on the left and one request open on the right, because that is the shape
 * of the job: a Strategist is deciding which conversation to pick up, and then reading enough
 * of it to join informed.
 *
 * Callbacks are filtered out here and shown in their own tab (§3.2). They are the same type
 * with `mode: 'callback'` — one collection, two views (the design ruling) — but they are
 * different work: a queue is what to do now, a Callbacks table is what to do today.
 */

import { useEffect, useState } from 'react'

import {
  endHandover,
  fetchHandover,
  type Handover,
  type HandoverDetail,
  joinHandover,
  type Lead,
} from './api'
import { ONLINE_GREEN } from './chrome'
import { useConsole } from './ConsoleLayout'
import { LABEL_STYLE, labelOf } from './handoverFeed'
import { SIGNALS } from './leadsFeed'
import { relativeTime } from './time'

/** The Session id is long and opaque; a Strategist only ever needs enough of it to match. */
function shortId(id: string): string {
  return id.length > 14 ? `${id.slice(0, 14)}…` : id
}

/** What the card's second line says about a Lead: their company, and what they do. */
function describe(lead: Lead): string {
  const industry = lead.signals.industry_fit ?? ''
  return [lead.company, industry || lead.role].filter(Boolean).join(' · ') || 'No company yet'
}

export function StateBadge({ request }: { request: Handover }) {
  const label = labelOf(request)
  const { color, pulsing } = LABEL_STYLE[label]
  return (
    <span
      className="flex shrink-0 items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.5px]"
      style={{ color }}
    >
      <span
        className={`inline-block size-[7px] rounded-full ${pulsing ? 'cadre-livepulse' : ''}`}
        style={{ background: color }}
      />
      {label}
    </span>
  )
}

function scoreColor(score: number): string {
  return score >= 4 ? ONLINE_GREEN : '#8a8a3a'
}

const INK_PILL =
  'rounded-[48px] bg-cadre-ink px-4 py-2 text-[12.5px] font-semibold text-white hover:bg-[#3a3236] disabled:opacity-60'

const RED_PILL =
  'rounded-[48px] bg-[#db4545] px-4 py-2 text-[12.5px] font-semibold text-white hover:bg-[#c33] disabled:opacity-60'

/** A request a Strategist can walk into: a Live Hand-over the Visitor accepted, unclaimed. */
export function canJoin(request: Handover): boolean {
  return request.mode === 'video' && request.state === 'pending_strategist'
}

/** A call somebody is in, which is the only thing "End call" may end. */
export function inCall(request: Handover): boolean {
  return request.state === 'strategist_joined' || request.state === 'in_call'
}

function QueueCard({
  request,
  selected,
  busy,
  onSelect,
  onJoin,
}: {
  request: Handover
  selected: boolean
  busy: boolean
  onSelect: () => void
  onJoin: () => void
}) {
  return (
    <div
      className={`rounded-2xl border bg-white ${
        selected ? 'border-cadre-ink' : 'border-[#e5e5e5] hover:border-[#ccc]'
      }`}
    >
      <button type="button" onClick={onSelect} aria-current={selected} className="w-full p-3.5 text-left">
        <div className="mb-1.5 flex items-start justify-between gap-3">
          <span className="text-sm font-semibold text-cadre-ink">
            {request.lead.name || 'Unnamed Lead'}
          </span>
          <StateBadge request={request} />
        </div>
        <div className="mb-2 text-[12.5px] text-cadre-muted">{describe(request.lead)}</div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-[11px] text-[#999]">{relativeTime(request.created_at)}</span>
          <span
            className="font-mono text-[11px] font-bold"
            style={{ color: scoreColor(request.lead.score) }}
          >
            score {request.lead.score}/5
          </span>
        </div>
      </button>
      {/* On the card and not only in the detail: a Visitor accepting is watching a spinner,
          and the shortest path from hearing the notification to being in the room is one
          click on the row that just arrived. */}
      {canJoin(request) ? (
        <div className="px-3.5 pb-3.5">
          <button type="button" disabled={busy} onClick={onJoin} className={INK_PILL}>
            Claim &amp; join call
          </button>
        </div>
      ) : null}
    </div>
  )
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-[#e5e5e5] bg-white p-4">
      <h3 className="mb-3 text-[11px] font-bold uppercase tracking-[1px] text-[#999]">{title}</h3>
      {children}
    </section>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1 text-[13px]">
      <span className="text-cadre-muted">{label}</span>
      <span className="text-right text-[#4c4c4c]">{children}</span>
    </div>
  )
}

/**
 * The in-call banner and the buttons beside it — docs/design §3.1.
 *
 * The banner carries the room URL because a Strategist may need it somewhere this frame will
 * not go: a second monitor, a phone, a colleague. The frame under it is the same room the
 * Visitor is in, which is what makes "Join" mean joining rather than marking a state.
 */
function CallBanner({
  handover,
  busy,
  onEnd,
}: {
  handover: Handover
  busy: boolean
  onEnd: () => void
}) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3 rounded-2xl bg-cadre-ink px-4 py-3 text-white">
        <span className="cadre-livepulse inline-block size-[7px] shrink-0 rounded-full bg-[#db4545]" />
        <span className="text-[13px] font-semibold">In call — Daily room open in the chat panel</span>
        {handover.room_url ? (
          <a
            href={handover.room_url}
            target="_blank"
            rel="noopener noreferrer"
            className="truncate font-mono text-[12px] text-[#b3b3b3] underline hover:text-white"
          >
            {handover.room_url.replace(/^https?:\/\//, '')}
          </a>
        ) : (
          <span className="font-mono text-[12px] text-[#b3b3b3]">no room on this request</span>
        )}
        <button type="button" disabled={busy} onClick={onEnd} className={`${RED_PILL} ml-auto`}>
          End call
        </button>
      </div>
      {handover.room_url ? (
        <iframe
          title="Cadre live hand-over"
          src={handover.room_url}
          allow="camera; microphone; fullscreen; display-capture; autoplay"
          className="h-[420px] w-full rounded-2xl border border-[#e5e5e5] bg-black"
        />
      ) : null}
    </div>
  )
}

function RequestDetail({
  detail,
  busy,
  onJoin,
  onEnd,
}: {
  detail: HandoverDetail
  busy: boolean
  onJoin: () => void
  onEnd: () => void
}) {
  const { handover, lead, conversation } = detail
  const present = new Set(lead.present_signals)
  const contact = [lead.company, lead.role, lead.email, lead.phone].filter(Boolean)

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl font-semibold tracking-tight text-cadre-ink">
            {lead.name || 'Unnamed Lead'}
          </h2>
          <p className="mt-1 text-[13px] text-cadre-muted">{contact.join(' · ')}</p>
        </div>
        {canJoin(handover) ? (
          <button type="button" disabled={busy} onClick={onJoin} className={INK_PILL}>
            Claim &amp; join call
          </button>
        ) : null}
      </header>

      {inCall(handover) ? (
        <CallBanner handover={handover} busy={busy} onEnd={onEnd} />
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={`Qualification · ${lead.score}/5`}>
          <div className="flex flex-col gap-1.5">
            {SIGNALS.map((signal) => {
              const on = present.has(signal.name)
              return (
                <div
                  key={signal.name}
                  className="flex items-baseline gap-2.5 text-[13px]"
                  style={{ color: on ? ONLINE_GREEN : '#b3b3b3' }}
                >
                  <span className="font-bold">{on ? '✓' : '—'}</span>
                  <span>{signal.label}</span>
                  {on ? (
                    <span className="text-[12px] text-cadre-muted">
                      {lead.signals[signal.name]}
                    </span>
                  ) : null}
                </div>
              )
            })}
          </div>
        </Panel>

        <Panel title="Request">
          <Field label="Mode">
            {/* Mode is decided when the Visitor accepts, so an offer that has not been
                answered has none — saying "Callback" here would promise the wrong thing. */}
            {handover.mode === 'video'
              ? 'Video (Daily)'
              : handover.mode === 'callback'
                ? 'Callback'
                : 'Not decided yet'}
          </Field>
          <Field label="State">
            <StateBadge request={handover} />
          </Field>
          <Field label="Session">
            <span className="font-mono text-[12px]">{shortId(handover.session_id)}</span>
          </Field>
          <Field label="Trace">
            {/* Ticket 06 fills the Trace in; until then the row says so rather than
                pretending there is a link behind it. */}
            <span className="font-mono text-[12px]">
              {handover.trace_id ? shortId(handover.trace_id) : 'not traced yet'}
            </span>
          </Field>
          <Field label="Requested">{relativeTime(handover.created_at)}</Field>
          {handover.strategist_name ? (
            <Field label="Claimed by">{handover.strategist_name}</Field>
          ) : null}
        </Panel>
      </div>

      <Panel title="Conversation so far">
        {conversation.length === 0 ? (
          <p className="text-[13px] text-cadre-muted">
            No conversation was stored for this Session.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {conversation.map((line, index) => (
              <div
                key={index}
                className={
                  line.role === 'visitor'
                    ? 'max-w-[80%] self-end rounded-[14px_14px_4px_14px] bg-cadre-ink px-3.5 py-2.5 text-[13px] leading-[1.5] whitespace-pre-line text-white'
                    : 'max-w-[80%] self-start rounded-[14px_14px_14px_4px] bg-cadre-sand-dark px-3.5 py-2.5 text-[13px] leading-[1.5] whitespace-pre-line text-[#4c4c4c]'
                }
              >
                {line.text}
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  )
}

export function HandoverQueuePage() {
  const { handovers, status, error, authorize } = useConsole()
  // The Callbacks tab is the other half of the same collection.
  const queue = handovers.filter((request) => request.mode !== 'callback')
  const [selectedId, setSelectedId] = useState<string>()
  const [detail, setDetail] = useState<HandoverDetail>()
  const [problem, setProblem] = useState<string>()
  // One call action at a time: Join and End both move the state machine, and a double click
  // on either is a 409 the Strategist should never have been able to send.
  const [busy, setBusy] = useState(false)

  const openId = selectedId ?? queue[0]?.request_id

  useEffect(() => {
    if (!openId) {
      setDetail(undefined)
      return
    }
    let live = true
    fetchHandover(authorize, openId)
      .then((loaded) => {
        if (live) {
          setDetail(loaded)
          setProblem(undefined)
        }
      })
      .catch(() => {
        if (live) {
          setProblem('Could not open that Handover Request. Try again.')
        }
      })
    return () => {
      live = false
    }
    // The request's own state changes as a Strategist works it, so the detail is re-read when
    // the feed delivers a new version of it.
  }, [authorize, openId, handovers])

  /**
   * Move one request through the machine and show the answer the server gave.
   *
   * The updated request is written straight into the open detail rather than waited for: the
   * realtime feed will deliver the same document a moment later, but a Strategist who just
   * pressed "Claim & join call" should be looking at the room by then, not at a button that
   * still says the same thing.
   */
  async function act(
    requestId: string,
    move: (authorize: () => Promise<string>, id: string) => Promise<Handover>,
    refusal: string,
  ) {
    if (busy) {
      return
    }
    setBusy(true)
    setProblem(undefined)
    try {
      const moved = await move(authorize, requestId)
      setSelectedId(moved.request_id)
      setDetail((open) =>
        open && open.handover.request_id === moved.request_id
          ? { ...open, handover: moved }
          : open,
      )
    } catch {
      setProblem(refusal)
    } finally {
      setBusy(false)
    }
  }

  const join = (requestId: string) =>
    void act(
      requestId,
      joinHandover,
      'Could not join that call — it may have been claimed or ended already.',
    )

  const end = (requestId: string) =>
    void act(requestId, endHandover, 'Could not end that call. Reload the queue and try again.')

  return (
    <section>
      <div className="mb-5 flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-cadre-ink">
          Handover queue
        </h1>
        <span className="text-[11px] font-bold uppercase tracking-[1px] text-[#999]">
          {status === 'loading' ? 'Loading' : status === 'live' ? 'Live' : 'Polling every 10s'}
        </span>
      </div>

      {error || problem ? (
        <p className="mb-4 rounded-2xl bg-cadre-sand-dark px-4 py-3 text-sm text-[#8a5a5a]">
          {problem ?? error}
        </p>
      ) : null}

      {queue.length === 0 && status !== 'loading' ? (
        <p className="max-w-[520px] text-sm leading-relaxed text-cadre-muted">
          No Hand-overs waiting. One appears here the moment a Qualified Lead accepts the
          Assistant’s offer — with a notification and a sound, so you do not have to watch this
          page.
        </p>
      ) : (
        <div className="flex flex-col gap-6 lg:flex-row">
          <div className="flex shrink-0 flex-col gap-2.5 lg:w-[340px]">
            <h2 className="text-[11px] font-bold uppercase tracking-[1px] text-[#999]">
              Handover requests
            </h2>
            {queue.map((request) => (
              <QueueCard
                key={request.request_id}
                request={request}
                selected={request.request_id === openId}
                busy={busy}
                onSelect={() => setSelectedId(request.request_id)}
                onJoin={() => join(request.request_id)}
              />
            ))}
          </div>
          <div className="min-w-0 flex-1">
            {detail ? (
              <RequestDetail
                detail={detail}
                busy={busy}
                onJoin={() => join(detail.handover.request_id)}
                onEnd={() => end(detail.handover.request_id)}
              />
            ) : (
              <p className="text-sm text-cadre-muted">Opening the request…</p>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
