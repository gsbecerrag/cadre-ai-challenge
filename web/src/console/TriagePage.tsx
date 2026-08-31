/**
 * Triage reports — docs/design §3.3.
 *
 * What the Triage Agent wrote about every thumbs-down (ADR-0005), newest first: the category
 * it picked, how bad it thinks it was, the Visitor's own words as evidence, and the two
 * suggestions a Strategist can act on — a Knowledge Base addition and an Eval Case.
 *
 * The list is realtime (`triageFeed.ts`), so a thumbs-down given in the chat during a demo
 * appears here about a minute later without a refresh: the Function writes the report, the
 * listener delivers it. Nothing on this page is editable — approving a suggestion is Phase 2,
 * and a button that did nothing would be worse than no button.
 */

import { type TriageCategory, type TriageReport, type TriageSeverity } from './api'
import { useConsole } from './ConsoleLayout'
import { relativeTime } from './time'
import { useTriageReports } from './triageFeed'

/**
 * Where a Trace opens. Langfuse's own deep link is `/project/{projectId}/traces/{traceId}`,
 * and the project id is not something this bundle knows — so the base is one constant, and a
 * deployment that wants the exact link sets `VITE_LANGFUSE_TRACE_BASE` to
 * `https://us.cloud.langfuse.com/project/<project id>/traces`. Either way the Trace id is on
 * the card, which is what a Cadre engineer pastes into Langfuse's search.
 */
const LANGFUSE_TRACE_BASE =
  import.meta.env.VITE_LANGFUSE_TRACE_BASE || 'https://us.cloud.langfuse.com/traces'

/**
 * The seven categories, with the chip the design gives them. Two are the design reference's
 * own — Knowledge gap on cream, Wrong escalation on the coral tint — and the other five are
 * built the same way: a pale tint of the text colour, so the row of chips reads as one family
 * however many categories a week of Feedback produces.
 */
const CATEGORIES: Record<TriageCategory, { label: string; background: string; color: string }> = {
  kb_gap: { label: 'Knowledge gap', background: '#f2efe4', color: '#999966' },
  wrong_escalation: { label: 'Wrong escalation', background: '#fdeaea', color: '#db4545' },
  hallucination: { label: 'Hallucination', background: '#f7e4e4', color: '#a32828' },
  tone: { label: 'Tone', background: '#eaf2f7', color: '#08749b' },
  pii: { label: 'Personal data', background: '#f3edf7', color: '#6b3f8f' },
  bug: { label: 'Bug', background: '#eef0f2', color: '#4c5c66' },
  other: { label: 'Other', background: '#f4f4f4', color: '#666666' },
}

/** MEDIUM olive and HIGH coral are the design's; LOW is the muted grey it uses everywhere. */
const SEVERITIES: Record<TriageSeverity, string> = {
  low: '#999999',
  medium: '#999966',
  high: '#db4545',
}

function category(name: string) {
  return CATEGORIES[name as TriageCategory] ?? CATEGORIES.other
}

function severityColor(name: string): string {
  return SEVERITIES[name as TriageSeverity] ?? SEVERITIES.medium
}

/** One dashed box: a suggestion in monospace, drawn only when the Agent made one. */
function Suggestion({ title, children }: { title: string; children: string }) {
  if (!children.trim()) {
    return null
  }
  return (
    <div className="flex-1 basis-[280px] rounded-xl border border-dashed border-[#ccc] p-3.5">
      <div className="mb-1.5 text-[10.5px] font-bold uppercase tracking-[1px] text-[#999]">
        {title}
      </div>
      <p className="font-mono text-[12px] leading-relaxed text-[#4c4c4c]">{children}</p>
    </div>
  )
}

function ReportCard({ report }: { report: TriageReport }) {
  const chip = category(report.category)
  return (
    <article className="rounded-[20px] border border-[#e5e5e5] bg-white p-5">
      <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-2">
        <span
          className="rounded-pill px-3 py-1 text-[11px] font-bold"
          style={{ background: chip.background, color: chip.color }}
        >
          {chip.label}
        </span>
        <span
          className="text-[11px] font-bold uppercase tracking-[1px]"
          style={{ color: severityColor(report.severity) }}
        >
          {report.severity}
        </span>
        <span className="text-[12px] text-[#999]">{relativeTime(report.created_at)}</span>
        <a
          className="ml-auto text-[12px] font-semibold text-cadre-blue hover:underline"
          href={`${LANGFUSE_TRACE_BASE}/${encodeURIComponent(report.trace_id)}`}
          target="_blank"
          rel="noreferrer"
        >
          Open trace in Langfuse ↗
        </a>
      </div>

      <p className="mb-3 text-[13.5px] leading-relaxed text-[#4c4c4c]">{report.summary}</p>

      {report.evidence.length > 0 ? (
        <blockquote className="mb-3 rounded-xl bg-cadre-sand-dark px-4 py-3">
          {report.evidence.map((quote, index) => (
            <p key={index} className="text-[13px] italic leading-relaxed text-[#4c4c4c]">
              “{quote}”
            </p>
          ))}
        </blockquote>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <Suggestion title="Suggested KB addition">{report.suggested_kb_addition}</Suggestion>
        <Suggestion title="Suggested eval case">{report.suggested_eval_case}</Suggestion>
      </div>
    </article>
  )
}

export function TriagePage() {
  const { authorize } = useConsole()
  const { reports, status, error } = useTriageReports(authorize)

  return (
    <section>
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-cadre-ink">
          Triage reports
        </h1>
        <span className="text-[11px] font-bold uppercase tracking-[1px] text-[#999]">
          {status === 'loading' ? 'Loading' : status === 'live' ? 'Live' : 'Polling every 10s'}
        </span>
      </div>
      <p className="mb-5 text-sm leading-relaxed text-cadre-muted">
        Written by the Triage Agent on every thumbs-down. Newest first.
      </p>

      {error ? (
        <p className="mb-4 max-w-[760px] rounded-xl border border-[#fdeaea] bg-[#fdeaea] px-4 py-3 text-[13px] text-cadre-red">
          {error}
        </p>
      ) : null}

      {reports.length === 0 && status !== 'loading' ? (
        <p className="max-w-[560px] text-sm leading-relaxed text-cadre-muted">
          No Triage Reports yet. When a Visitor gives the Assistant a thumbs-down, the Triage
          Agent reads that conversation and writes up what went wrong — with a suggested
          Knowledge Base addition and a suggested Eval Case — and it appears here.
        </p>
      ) : (
        <div className="flex max-w-[760px] flex-col gap-4">
          {reports.map((report) => (
            <ReportCard key={report.id} report={report} />
          ))}
        </div>
      )}
    </section>
  )
}
