import { statCards } from './mockData'

/** Portal dashboard tab: company-wide summary tiles for the Demo client. */
export function DashboardPage() {
  return (
    <div>
      <h2 className="font-display text-2xl font-semibold tracking-tight text-cadre-ink md:text-[26px]">
        Dashboard
      </h2>
      <p className="mb-7 mt-1.5 text-sm text-[#999]">Company-wide AI overview</p>

      <div className="grid max-w-[760px] grid-cols-1 gap-4 sm:grid-cols-3">
        {statCards.map((card) => (
          <div
            key={card.label}
            className="rounded-[20px] border border-cadre-line bg-white p-[22px]"
          >
            <div className="text-xs font-semibold uppercase tracking-wide text-[#999]">
              {card.label}
            </div>
            <div
              className={`font-display mt-1.5 text-[34px] font-semibold ${
                card.accent === 'red' ? 'text-cadre-red' : 'text-cadre-ink'
              }`}
            >
              {card.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
