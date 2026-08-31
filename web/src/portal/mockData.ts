/**
 * Mock data for the demo Portal (ticket 07). The Portal has no authentication and no
 * state — every value here is a plausible, hardcoded fact about a fictional "Demo client",
 * not a real Cadre client, matching the artboard's `portalAgents` array and stat cards
 * (docs/design/cadre-support-chat.dc.html, docs/design/DESIGN-BRIEF.md §2.2).
 */

export interface StatCard {
  label: string
  value: string
  accent?: 'red' | 'ink'
}

/** The three stat cards shown on the Dashboard tab, verbatim from the design. */
export const statCards: StatCard[] = [
  { label: 'Hours saved / mo', value: '265', accent: 'red' },
  { label: 'Active agents', value: '4', accent: 'ink' },
  { label: 'Team trained', value: '82%', accent: 'ink' },
]

export interface AgentResult {
  name: string
  runsPerMonth: string
  hoursSaved: string
}

/** The agents results table on the Agents tab, verbatim from the design. */
export const agentResults: AgentResult[] = [
  { name: 'Lead Processing Agent', runsPerMonth: '1,540', hoursSaved: '45' },
  { name: 'Proposal Automation', runsPerMonth: '96', hoursSaved: '160' },
  { name: 'Email Agent', runsPerMonth: '4,120', hoursSaved: '48' },
  { name: 'Invoice Query Resolver', runsPerMonth: '310', hoursSaved: '12' },
]

export interface Tool {
  name: string
  description: string
  status: 'Live' | 'In pilot'
}

/**
 * AI tools activated across the Demo client's stack, shown on the Tools tab. Not specified
 * verbatim by the design (which reuses the agents table on every tab) — these are plausible
 * mock entries consistent with Cadre's published partner list.
 */
export const tools: Tool[] = [
  { name: 'Claude for Sales Enablement', description: 'Drafts proposals and call prep from CRM data.', status: 'Live' },
  { name: 'Email Drafting Assistant', description: 'Suggests replies for the shared support inbox.', status: 'Live' },
  { name: 'Meeting Notes & Follow-ups', description: 'Summarizes calls and files action items in Salesforce.', status: 'Live' },
  { name: 'Snowflake Data Sync', description: 'Keeps agent context current with warehouse data.', status: 'Live' },
  { name: 'Invoice Query Resolver Copilot', description: 'Drafts responses to vendor invoice questions.', status: 'In pilot' },
]

export interface TrainingModule {
  name: string
  completion: number
}

/** Training completion by module, shown on the Results & Training tab. */
export const trainingModules: TrainingModule[] = [
  { name: 'AI Fundamentals', completion: 100 },
  { name: 'Prompting for Agents', completion: 88 },
  { name: 'Data Security & Governance', completion: 76 },
  { name: 'Agent Escalation Playbooks', completion: 64 },
]
