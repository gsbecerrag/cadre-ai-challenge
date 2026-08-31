/**
 * Callbacks — docs/design §3.2.
 *
 * The same Handover Requests as the queue, filtered to `mode: 'callback'` (the design ruling:
 * one type with a mode, not two entities). A table rather than cards, because this is a list
 * to work through rather than a decision to make: Lead, how to reach them, when they asked,
 * and what the Assistant learned about them.
 *
 * There is no "Scheduled for" column. The design drew one, and the MVP has no scheduling —
 * a Callback means a Strategist reaches out, so the honest column is "Requested".
 */

import { ONLINE_GREEN } from './chrome'
import { useConsole } from './ConsoleLayout'
import { relativeTime } from './time'

const HEAD = 'px-4 py-2.5 text-[11px] font-bold uppercase tracking-[1px] text-[#999]'
const CELL = 'px-4 py-3 text-[13px] text-[#4c4c4c] align-top'

export function CallbacksPage() {
  const { handovers, status } = useConsole()
  const callbacks = handovers.filter((request) => request.mode === 'callback')

  return (
    <section>
      <div className="mb-5 flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-cadre-ink">
          Callbacks
        </h1>
        <span className="text-[11px] font-bold uppercase tracking-[1px] text-[#999]">
          {status === 'loading' ? 'Loading' : status === 'live' ? 'Live' : 'Polling every 10s'}
        </span>
      </div>

      {callbacks.length === 0 && status !== 'loading' ? (
        <p className="max-w-[520px] text-sm leading-relaxed text-cadre-muted">
          No Callbacks yet. When a Qualified Lead accepts a Hand-over and no Strategist is
          online, the request lands here with the Contact Details they shared.
        </p>
      ) : (
        <div className="max-w-[860px] overflow-x-auto rounded-2xl border border-[#e5e5e5] bg-white">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-[#eee]">
                <th className={HEAD}>Lead</th>
                <th className={HEAD}>Contact</th>
                <th className={HEAD}>Requested</th>
                <th className={HEAD}>Score</th>
              </tr>
            </thead>
            <tbody>
              {callbacks.map((request) => (
                <tr key={request.request_id} className="border-b border-[#f4f4f4] last:border-0">
                  <td className={CELL}>
                    <b className="text-cadre-ink">{request.lead.name || 'Unnamed Lead'}</b>
                    <br />
                    <span className="text-[12.5px] text-cadre-muted">
                      {request.lead.company || 'No company yet'}
                    </span>
                  </td>
                  <td className={CELL}>
                    {request.lead.email ? <div>{request.lead.email}</div> : null}
                    {request.lead.phone ? <div>{request.lead.phone}</div> : null}
                    {!request.lead.email && !request.lead.phone ? (
                      <span className="text-[#999]">No Contact Details shared</span>
                    ) : null}
                  </td>
                  <td className={CELL}>{relativeTime(request.created_at)}</td>
                  <td className={CELL}>
                    <span
                      className="font-mono text-[12px] font-bold"
                      style={{ color: request.lead.score >= 4 ? ONLINE_GREEN : '#8a8a3a' }}
                    >
                      {request.lead.score}/5
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
