import { agentResults } from './mockData'

/** Portal agents tab: deployed agents and their per-agent results table. */
export function AgentsPage() {
  return (
    <div>
      <h2 className="font-display text-2xl font-semibold tracking-tight text-cadre-ink md:text-[26px]">
        Agents
      </h2>
      <p className="mb-7 mt-1.5 text-sm text-[#999]">Deployed agents and their owners</p>

      <div
        id="portal-agents-results"
        className="max-w-[760px] overflow-hidden rounded-[20px] border border-cadre-line bg-white"
      >
        <div className="grid grid-cols-[2fr_1fr_1fr_1fr] gap-2 border-b border-[#eee] px-[22px] py-3.5 text-[11px] font-semibold uppercase tracking-wide text-[#999]">
          <span>Agent</span>
          <span>Runs / mo</span>
          <span>Hours saved</span>
          <span>Status</span>
        </div>
        {agentResults.map((agent) => (
          <div
            key={agent.name}
            className="grid grid-cols-[2fr_1fr_1fr_1fr] items-center gap-2 border-b border-[#f4f4f4] px-[22px] py-4 text-sm last:border-b-0"
          >
            <span className="font-semibold text-cadre-ink">{agent.name}</span>
            <span className="text-cadre-muted">{agent.runsPerMonth}</span>
            <span className="text-cadre-muted">{agent.hoursSaved}</span>
            <span className="text-xs font-semibold text-[#0a7d43]">● Live</span>
          </div>
        ))}
      </div>
    </div>
  )
}
