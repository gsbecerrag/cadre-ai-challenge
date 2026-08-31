import { Link } from 'react-router-dom'

import { OPEN_CHAT_EVENT } from '../chat/ChatWidget'

const CADRE_LOGO_URL =
  'https://cdn.prod.website-files.com/6910dd217f94a50bd2e308d3/6910e3a5178f856fe5289ae1_Cadre_AI_Logo_Web.svg'

const NAV_LINKS = ['Services', 'Industries', 'Case Studies', 'About']

const VALUE_CARDS = [
  {
    title: 'Drive Revenue',
    body: 'Find the highest-impact AI opportunities, department by department.',
  },
  {
    title: 'Increase Profitability',
    body: 'Select and configure the LLMs that best align with your tech stack and goals.',
  },
  {
    title: 'Elevate Employees',
    body: 'Shift the culture with training and champions in every department.',
  },
]

const PARTNERS = ['OpenAI', 'Anthropic', 'Microsoft', 'Snowflake', 'Salesforce', 'AWS', 'Meta']

/**
 * Dispatched by every "Talk to an AI Strategist" control on this page; the chat widget
 * listens for it and opens. The name is the widget's own constant rather than a literal, so
 * the two cannot drift apart.
 */
function openChat() {
  window.dispatchEvent(new CustomEvent(OPEN_CHAT_EVENT))
}

/**
 * The mock cadreai.com host page (ticket 07): the page the chat widget floats over,
 * replacing ticket 01's placeholder shell. Matches docs/design §2.1.
 */
export function HostPage() {
  return (
    <div className="bg-cadre-sand font-sans text-cadre-body">
      <nav className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-black/[0.06] bg-cadre-sand px-4 py-3 sm:px-6 md:px-12 md:py-4.5">
        <img src={CADRE_LOGO_URL} alt="Cadre AI" className="h-[22px] shrink-0 md:h-[26px]" />
        <div className="hidden items-center gap-7 text-sm font-medium text-cadre-body md:flex">
          {NAV_LINKS.map((label) => (
            <span key={label} className="cursor-default hover:text-cadre-red">
              {label}
            </span>
          ))}
          <a href="/console" className="text-[#999] hover:text-cadre-red">
            Console →
          </a>
        </div>
        <button
          type="button"
          onClick={openChat}
          className="shrink-0 whitespace-nowrap rounded-pill bg-cadre-ink px-3.5 py-2 text-xs font-semibold text-white sm:px-[22px] sm:py-3 sm:text-sm"
        >
          Talk to an AI Strategist
        </button>
      </nav>

      <div className="bg-linear-to-b from-cadre-sand-dark to-white px-6 py-16 text-center md:px-12 md:py-24">
        <div className="mb-7 inline-flex items-center gap-2 rounded-pill border border-cadre-line bg-white px-4 py-1.5 text-xs font-semibold text-cadre-muted">
          Cadre AI — Anthropic &amp; OpenAI Partner
        </div>
        <h1 className="font-display mx-auto mb-5 max-w-[820px] text-[40px] font-semibold leading-[1.05] tracking-[-0.03em] text-cadre-red md:text-[64px] md:tracking-[-3px]">
          From AI Confusion to AI Confidence.
        </h1>
        <p className="mx-auto mb-8 max-w-[560px] text-lg leading-relaxed text-[#4c4c4c]">
          We help you pinpoint the right AI opportunities, implement them seamlessly, and
          deliver real business impact.
        </p>
        <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
          <button
            type="button"
            onClick={openChat}
            className="rounded-pill bg-cadre-ink px-7 py-4 text-[15px] font-semibold text-white"
          >
            Talk to an AI Strategist →
          </button>
          <button
            type="button"
            className="rounded-pill border border-cadre-line bg-white px-7 py-4 text-[15px] font-semibold text-cadre-ink"
          >
            See How the Intensive Works
          </button>
        </div>
      </div>

      <div className="border-b border-black/[0.06] px-6 py-9 text-center md:px-12">
        <div className="mb-4.5 text-xs font-semibold uppercase tracking-[1.5px] text-[#999]">
          Partnering with the best
        </div>
        <div className="flex flex-wrap justify-center gap-10 text-lg font-semibold text-[#b3b3b3]">
          {PARTNERS.map((partner) => (
            <span key={partner} className="font-display">
              {partner}
            </span>
          ))}
        </div>
      </div>

      <div className="mx-auto max-w-[1080px] px-6 py-18 md:px-12">
        <h2 className="font-display mb-10 text-center text-3xl font-semibold tracking-tight text-cadre-body md:text-[38px] md:tracking-[-1.5px]">
          Set your team up to succeed with AI
        </h2>
        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          {VALUE_CARDS.map((card) => (
            <div
              key={card.title}
              className="rounded-card border border-black/10 bg-white p-7.5"
            >
              <div className="font-display mb-2.5 text-xl font-semibold text-cadre-ink">
                {card.title}
              </div>
              <div className="text-sm leading-relaxed text-cadre-muted">{card.body}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="mx-auto mb-18 max-w-[1080px] px-6 md:px-12">
        <div className="flex flex-col items-start gap-8 rounded-card bg-cadre-ink p-9 md:flex-row md:items-center md:justify-between md:p-14">
          <div>
            <div className="font-display mb-2.5 text-2xl font-semibold tracking-tight text-white md:text-[30px] md:tracking-[-1px]">
              Track your AI results
            </div>
            <div className="max-w-[480px] text-[15px] leading-relaxed text-[#b3b3b3]">
              Cadre gives you a centralized portal to track tools, agents, training, and
              results. Stay aligned, stay accountable, and scale what works.
            </div>
          </div>
          <Link
            to="/portal"
            className="whitespace-nowrap rounded-pill bg-white px-7 py-4 text-[15px] font-semibold text-cadre-ink"
          >
            Get Your AI Results
          </Link>
        </div>
      </div>

      <footer className="flex flex-col items-center gap-4 bg-cadre-sand-dark px-6 py-10 text-sm text-cadre-muted md:flex-row md:justify-between md:px-12">
        <img src={CADRE_LOGO_URL} alt="Cadre AI" className="h-5 opacity-70" />
        <div className="flex flex-wrap justify-center gap-6">
          <span>hello@gocadre.ai</span>
          <span>(619) 324-3223</span>
          <span>San Diego, CA</span>
        </div>
      </footer>
    </div>
  )
}
