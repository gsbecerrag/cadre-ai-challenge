import { Link, NavLink, Outlet } from 'react-router-dom'

const CADRE_LOGO_URL =
  'https://cdn.prod.website-files.com/6910dd217f94a50bd2e308d3/6910e3a5178f856fe5289ae1_Cadre_AI_Logo_Web.svg'

const tabs = [
  { to: '/portal', label: 'Dashboard', end: true },
  { to: '/portal/tools', label: 'Tools', end: false },
  { to: '/portal/agents', label: 'Agents', end: false },
  { to: '/portal/results', label: 'Results & Training', end: false },
]

/**
 * Shared chrome for every demo Portal page (ticket 07): header with the "Demo portal ·
 * mock data" badge — shown on every Portal page per the docs/design ruling — and the
 * left nav. `<Outlet />` renders the active tab's page.
 */
export function PortalLayout() {
  return (
    <div className="min-h-screen bg-cadre-sand font-sans text-cadre-body">
      <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-cadre-line bg-white px-4 py-3.5 sm:px-8">
        <div className="flex flex-wrap items-center gap-3.5">
          <img src={CADRE_LOGO_URL} alt="Cadre AI" className="h-5 shrink-0" />
          <span className="shrink-0 font-display text-[15px] font-semibold text-cadre-ink">
            Portal
          </span>
          <span className="shrink-0 whitespace-nowrap rounded-pill border border-cadre-line bg-cadre-sand-dark px-3 py-1 text-[11px] font-semibold text-[#996]">
            Demo portal · mock data
          </span>
        </div>
        <Link
          to="/"
          className="shrink-0 whitespace-nowrap rounded-pill border border-cadre-line px-[18px] py-2 text-[13px] font-semibold text-cadre-body hover:text-cadre-red"
        >
          ← Back to site
        </Link>
      </header>

      <div className="flex min-h-[calc(100vh-57px)] flex-col md:flex-row">
        <nav
          id="portal-nav"
          aria-label="Portal"
          className="flex gap-1 overflow-x-auto border-b border-[#eee] px-4 py-3 md:w-[210px] md:flex-col md:overflow-visible md:border-b-0 md:border-r md:px-4 md:py-6"
        >
          {tabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end}
              className={({ isActive }) =>
                `whitespace-nowrap rounded-xl px-3.5 py-2.5 text-sm ${
                  isActive
                    ? 'bg-white font-semibold text-cadre-red'
                    : 'font-medium text-cadre-muted hover:text-cadre-body'
                }`
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>

        <main className="flex-1 px-6 py-8 md:px-10">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
