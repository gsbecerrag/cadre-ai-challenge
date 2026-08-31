/**
 * A tab the design reference shows and this ticket does not fill.
 *
 * It names the ticket that will, rather than rendering mock rows: a Console that shows three
 * invented Handover Requests is a Console nobody can trust the fourth time they open it.
 */
export function PlannedTabPage({
  title,
  ticket,
  children,
}: {
  title: string
  ticket: string
  children: React.ReactNode
}) {
  return (
    <section className="max-w-[560px]">
      <h1 className="font-display mb-3 text-2xl font-semibold tracking-tight text-cadre-ink">
        {title}
      </h1>
      <p className="mb-4 text-sm leading-relaxed text-cadre-muted">{children}</p>
      <p className="inline-block rounded-pill border border-cadre-line bg-cadre-sand-dark px-4 py-1.5 text-xs font-semibold text-[#996]">
        Ticket {ticket}
      </p>
    </section>
  )
}

export function TriagePage() {
  return (
    <PlannedTabPage title="Triage" ticket="14">
      The Triage Agent writes a Triage Report on every thumbs-down — category, evidence, a
      suggested Knowledge Base addition and a suggested Eval Case. They will be listed here,
      newest first.
    </PlannedTabPage>
  )
}
