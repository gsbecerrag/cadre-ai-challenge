import { tools } from './mockData'

/** Portal tools tab: the AI features activated across the Demo client's stack. */
export function ToolsPage() {
  return (
    <div>
      <h2 className="font-display text-2xl font-semibold tracking-tight text-cadre-ink md:text-[26px]">
        Tools
      </h2>
      <p className="mb-7 mt-1.5 text-sm text-[#999]">Activated AI features across your stack</p>

      <div
        id="portal-tools-list"
        className="max-w-[760px] overflow-hidden rounded-[20px] border border-cadre-line bg-white"
      >
        {tools.map((tool, index) => (
          <div
            key={tool.name}
            className={`flex items-center justify-between gap-4 px-[22px] py-4 ${
              index < tools.length - 1 ? 'border-b border-[#f4f4f4]' : ''
            }`}
          >
            <div>
              <div className="font-display text-sm font-semibold text-cadre-ink">{tool.name}</div>
              <div className="mt-0.5 text-sm text-cadre-muted">{tool.description}</div>
            </div>
            <span
              className={`whitespace-nowrap text-xs font-semibold ${
                tool.status === 'Live' ? 'text-[#0a7d43]' : 'text-[#996]'
              }`}
            >
              {tool.status === 'Live' ? '● Live' : '● In pilot'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
