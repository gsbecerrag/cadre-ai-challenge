/**
 * One row of the transcript. Kinds, radii, colours and copy follow the design artboard
 * (docs/design/DESIGN-BRIEF.md §2.5): a Visitor bubble is ink and right-aligned, an Assistant
 * bubble is white and left-aligned, and citation chips sit under the bubble they belong to.
 */

import { type ReactNode, useState } from 'react'

import { chromeFor } from './strings'
import type { CardDestination, Message } from './types'

const CHIP =
  'rounded-[48px] border border-[#e5e5e5] bg-[#f2efe4] px-2.5 py-[3px] font-mono text-[10px] text-[#666]'

/**
 * `[not-published#pricing]` is honest and tells the Visitor nothing, so the chip carries the
 * KB Section's heading: on the pointer as a tooltip and to a screen reader as its label, and
 * on tap by swapping the id for the title, which is the only one of the three a touch screen
 * can do. Until the titles arrive the chip is a plain span — a citation is still a citation
 * without one, and a control that does nothing when pressed is worse than no control.
 */
function CitationChip({ id, title }: { id: string; title?: string }) {
  const [revealed, setRevealed] = useState(false)

  if (!title) {
    return <span className={CHIP}>[{id}]</span>
  }
  return (
    <button
      type="button"
      title={title}
      aria-label={`${title} — ${id}`}
      onClick={() => setRevealed(!revealed)}
      className={`${CHIP} cursor-help hover:border-[#db4545] hover:text-[#db4545]`}
    >
      {revealed ? title : `[${id}]`}
    </button>
  )
}

function Citations({ ids, titles }: { ids: string[]; titles: Record<string, string> }) {
  if (ids.length === 0) {
    return null
  }
  return (
    <div className="mt-1.5 flex flex-wrap gap-1.5">
      {ids.map((id) => (
        <CitationChip key={id} id={id} title={titles[id]} />
      ))}
    </div>
  )
}

const CTA =
  'self-start rounded-[48px] bg-[#0c0407] px-[18px] py-2.5 text-[13px] font-semibold text-white hover:bg-[#3a3236]'

/**
 * The Walkthrough Card's call to action. A Portal destination is a route in this app, so it
 * announces itself on the window and the listener inside the router navigates — a plain `<a>`
 * would reload the document and take the chat panel, its transcript and the Session with it.
 * Anything external is an ordinary link, opened in a new tab for the same reason.
 */
function WalkthroughCta({
  destination,
  onNavigate,
}: {
  destination: CardDestination
  onNavigate: (href: string) => void
}) {
  if (destination.external) {
    return (
      <a
        href={destination.href}
        target="_blank"
        rel="noopener noreferrer"
        className={`${CTA} inline-block`}
      >
        {destination.label} →
      </a>
    )
  }
  return (
    <button type="button" onClick={() => onNavigate(destination.href)} className={CTA}>
      {destination.label} →
    </button>
  )
}

export function MessageView({
  message,
  typingLabel,
  nextStepLabel,
  sectionTitles,
  onNavigate,
  feedback,
}: {
  message: Message
  typingLabel: string
  /** The Escalation card's "Next step:" label when the Escalation names no language of its
   * own; localised with the rest of the chrome. */
  nextStepLabel: string
  sectionTitles: Record<string, string>
  /** Follow a Walkthrough Card into the app, without unmounting the panel. */
  onNavigate: (href: string) => void
  /** The thumbs for this answer, when it has a Trace to attach them to. Passed in rather than
   * built here so that one component owns which answers are rateable. */
  feedback?: ReactNode
}) {
  const alignment = message.role === 'visitor' ? 'items-end' : 'items-start'

  return (
    <div className={`cadre-msgin flex flex-col ${alignment}`}>
      {message.kind === 'text' && (
        <>
          <div
            className={
              message.role === 'visitor'
                ? 'max-w-[82%] rounded-[16px_16px_4px_16px] bg-[#0c0407] px-[15px] py-[11px] text-[14px] leading-[1.55] whitespace-pre-line text-white'
                : 'max-w-[82%] rounded-[16px_16px_16px_4px] border border-[#e5e5e5] bg-white px-[15px] py-[11px] text-[14px] leading-[1.55] whitespace-pre-line text-[#333]'
            }
          >
            {message.text}
          </div>
          <Citations ids={message.citations} titles={sectionTitles} />
        </>
      )}

      {message.kind === 'typing' && (
        <div
          aria-label={typingLabel}
          className="flex gap-[5px] rounded-[16px_16px_16px_4px] border border-[#e5e5e5] bg-white px-4 py-3.5"
        >
          <span className="cadre-tdot size-1.5 rounded-full bg-[#999]" />
          <span className="cadre-tdot size-1.5 rounded-full bg-[#999] [animation-delay:0.15s]" />
          <span className="cadre-tdot size-1.5 rounded-full bg-[#999] [animation-delay:0.3s]" />
        </div>
      )}

      {message.kind === 'escalation' && (
        <div className="max-w-[88%] rounded-[6px_16px_16px_6px] border border-[#e5e5e5] border-l-[3px] border-l-[#db4545] bg-white px-4 py-3.5 text-[13.5px] leading-[1.55]">
          <div className="mb-1.5 font-semibold text-[#0c0407]">{message.title}</div>
          <div className="mb-2 whitespace-pre-line text-[#4c4c4c]">{message.body}</div>
          <div className="rounded-[10px] bg-[#faf9f6] px-3 py-2.5 text-[12.5px] text-[#666]">
            {/* The copy above was looked up in the Escalation's own language, so its label
                follows the card rather than the widget's EN/ES toggle. */}
            <b className="text-[#0c0407]">
              {message.language ? chromeFor(message.language).nextStep : nextStepLabel}
            </b>{' '}
            {message.nextStep}
          </div>
          <Citations ids={message.citations} titles={sectionTitles} />
        </div>
      )}

      {message.kind === 'walkthrough' && (
        <div className="max-w-[88%] overflow-hidden rounded-[16px] border border-[#e5e5e5] bg-white">
          <div className="bg-[#f2efe4] px-4 py-[11px] text-[13.5px] font-semibold text-[#0c0407]">
            {message.title}
          </div>
          <div className="flex flex-col items-start gap-[9px] px-4 py-3">
            <ol className="flex flex-col gap-[9px]">
              {message.steps.map((step, index) => (
                <li
                  key={index}
                  className="flex items-start gap-2.5 text-[13.5px] leading-[1.45] text-[#4c4c4c]"
                >
                  {/* The `<ol>` already numbers these for a screen reader, so the badge is
                      decoration: without this it hears "one one Open the Cadre Portal". */}
                  <span
                    aria-hidden="true"
                    className="mt-px flex size-5 flex-shrink-0 items-center justify-center rounded-full bg-[#0c0407] text-[11px] font-bold text-white"
                  >
                    {index + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
            <WalkthroughCta destination={message.destination} onNavigate={onNavigate} />
          </div>
          {message.citations.length > 0 && (
            <div className="px-4 pb-3">
              <Citations ids={message.citations} titles={sectionTitles} />
            </div>
          )}
        </div>
      )}

      {message.kind === 'error' && (
        <div
          role="alert"
          className="max-w-[88%] rounded-[16px_16px_16px_4px] border border-[#e5e5e5] bg-[#fdeaea] px-[15px] py-[11px] text-[13.5px] leading-[1.55] text-[#4c4c4c]"
        >
          {message.text}
        </div>
      )}

      {feedback}
    </div>
  )
}
