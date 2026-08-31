import type { Lead } from './api'
import { ONLINE_GREEN } from './chrome'
import { useConsole } from './ConsoleLayout'
import { SIGNALS } from './leadsFeed'

/** The Session id is long and opaque; a Strategist only ever needs enough of it to match. */
function shortSession(sessionId: string): string {
  return sessionId.length > 12 ? `${sessionId.slice(0, 12)}…` : sessionId
}

/** The queue card of docs/design §3.1, carrying a Lead instead of a Handover Request. */
function LeadCard({ lead }: { lead: Lead }) {
  const present = new Set(lead.present_signals)
  const contact = [lead.email, lead.phone].filter(Boolean)
  return (
    <article className="rounded-2xl border border-[#e5e5e5] bg-white p-4">
      <div className="mb-1.5 flex items-start justify-between gap-3">
        <span className="text-sm font-semibold text-cadre-ink">{lead.name || 'Unnamed Lead'}</span>
        {lead.qualified ? (
          <span
            className="shrink-0 rounded-pill px-2.5 py-0.5 text-[11px] font-bold text-white"
            style={{ background: ONLINE_GREEN }}
          >
            Qualified
          </span>
        ) : null}
      </div>

      <div className="mb-2 text-[12.5px] text-cadre-muted">
        {[lead.company, lead.role].filter(Boolean).join(' · ') || 'No company or role yet'}
      </div>

      {contact.length > 0 ? (
        <div className="mb-3 text-[12.5px] text-cadre-body">{contact.join(' · ')}</div>
      ) : null}

      <div className="mb-3 flex flex-col gap-1.5 border-t border-[#f0f0f0] pt-3">
        {SIGNALS.map((signal) => {
          const on = present.has(signal.name)
          return (
            <div
              key={signal.name}
              className="flex items-center gap-2.5 text-[13px]"
              style={{ color: on ? ONLINE_GREEN : '#b3b3b3' }}
            >
              <span className="font-bold">{on ? '✓' : '—'}</span>
              {signal.label}
            </div>
          )
        })}
      </div>

      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-[11px] text-[#999]">{shortSession(lead.session_id)}</span>
        <span
          className="font-mono text-[11px] font-bold"
          style={{ color: lead.score >= 4 ? ONLINE_GREEN : '#8a8a3a' }}
        >
          score {lead.score} of 5
        </span>
      </div>
    </article>
  )
}

/**
 * Every Lead the Assistant has captured, newest first (ticket 10).
 *
 * The list is loaded from the API and then kept live by a Firestore listener, so a Lead
 * captured mid-conversation appears here without a refresh; the header line says which of the
 * two is currently feeding it, because "live" and "polled every ten seconds" are a different
 * promise to a Strategist deciding whether to keep the tab open.
 */
export function LeadsPage() {
  const { leads, status, error } = useConsole()

  return (
    <section>
      <div className="mb-5 flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-cadre-ink">Leads</h1>
        <span className="text-[11px] font-bold uppercase tracking-[1px] text-[#999]">
          {status === 'loading' ? 'Loading' : status === 'live' ? 'Live' : 'Polling every 10s'}
        </span>
      </div>

      {error ? (
        <p className="mb-4 rounded-2xl bg-cadre-sand-dark px-4 py-3 text-sm text-[#8a5a5a]">
          {error}
        </p>
      ) : null}

      {leads.length === 0 && status !== 'loading' ? (
        <p className="max-w-[520px] text-sm leading-relaxed text-cadre-muted">
          No Leads yet. One appears here the moment the Assistant captures a Visitor’s Contact
          Details — with the five Qualification Signals and the score counted in code.
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {leads.map((lead) => (
            <LeadCard key={lead.session_id} lead={lead} />
          ))}
        </div>
      )}
    </section>
  )
}
