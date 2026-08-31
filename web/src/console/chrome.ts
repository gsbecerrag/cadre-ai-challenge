/** The one Cadre logo used across the site, the Portal and the Console. */
export const CADRE_LOGO_URL =
  'https://cdn.prod.website-files.com/6910dd217f94a50bd2e308d3/6910e3a5178f856fe5289ae1_Cadre_AI_Logo_Web.svg'

/** The green the design reference uses for "Online" — Availability, and a present signal. */
export const ONLINE_GREEN = '#0a7d43'

/**
 * The Console's tabs (docs/design §3). Leads is this ticket; the badge rides on it for now,
 * because a Lead is the only thing the Console has to count yet. The other three are shells
 * that name the ticket which fills them, so the nav is honest about what exists.
 */
export const CONSOLE_TABS = [
  { to: '/console', label: 'Leads', end: true },
  { to: '/console/handover', label: 'Handover queue', end: false },
  { to: '/console/callbacks', label: 'Callbacks', end: false },
  { to: '/console/triage', label: 'Triage', end: false },
] as const
