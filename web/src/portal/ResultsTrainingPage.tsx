import { statCards, trainingModules } from './mockData'

/** Portal results & training tab: what the Demo client's agents saved this month, plus training progress. */
export function ResultsTrainingPage() {
  const teamTrained = statCards.find((card) => card.label === 'Team trained')

  return (
    <div>
      <h2 className="font-display text-2xl font-semibold tracking-tight text-cadre-ink md:text-[26px]">
        Results &amp; Training
      </h2>
      <p className="mb-7 mt-1.5 text-sm text-[#999]">What your agents saved this month</p>

      <div
        id="portal-training-progress"
        className="max-w-[760px] rounded-[20px] border border-cadre-line bg-white p-[22px]"
      >
        <div className="mb-5 flex items-baseline justify-between">
          <div className="text-xs font-semibold uppercase tracking-wide text-[#999]">
            Team trained
          </div>
          <div className="font-display text-lg font-semibold text-cadre-ink">
            {teamTrained?.value}
          </div>
        </div>

        <div className="flex flex-col gap-4">
          {trainingModules.map((module) => (
            <div key={module.name}>
              <div className="mb-1.5 flex items-center justify-between text-sm">
                <span className="font-medium text-cadre-ink">{module.name}</span>
                <span className="text-cadre-muted">{module.completion}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-pill bg-cadre-sand-dark">
                <div
                  className="h-full rounded-pill bg-cadre-red"
                  style={{ width: `${module.completion}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
