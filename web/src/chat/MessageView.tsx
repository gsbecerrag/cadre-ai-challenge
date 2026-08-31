/**
 * One row of the transcript. Kinds, radii, colours and copy follow the design artboard
 * (docs/design/DESIGN-BRIEF.md §2.5): a Visitor bubble is ink and right-aligned, an Assistant
 * bubble is white and left-aligned, and citation chips sit under the bubble they belong to.
 */

import { type ReactNode, useState } from 'react'

import { type Chrome, chromeFor } from './strings'
import type { CardDestination, LeadContact, Message, OfferMessage } from './types'

/**
 * What the Visitor's two buttons and the details form do. They are handlers rather than
 * fetches because a message row should not know the API exists: `useChat` owns the requests,
 * the reducer owns what the transcript then shows, and this file draws it.
 */
export interface HandoverActions {
  accept: (requestId: string) => void
  decline: (requestId: string) => void
  shareDetails: (details: LeadContact) => void
  /** A request in flight: both buttons wait, so a double press cannot send two answers. */
  busy: boolean
  failed: boolean
}

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

const CARD = 'max-w-[88%] rounded-[16px] border border-[#e5e5e5] bg-white px-4 py-3.5'

/**
 * The Hand-over offer: the Assistant's question and two buttons, or — once it is answered —
 * one line saying what happens next. The card keeps its place in the transcript rather than
 * disappearing, because a Visitor scrolling back should still see what they were asked.
 */
function OfferCard({
  message,
  chrome,
  actions,
}: {
  message: OfferMessage
  chrome: Chrome
  actions: HandoverActions
}) {
  if (message.status !== 'open') {
    return (
      <div className={`${CARD} text-center text-[13px] text-[#666]`}>
        {message.status === 'accepted' ? chrome.offerAccepted : chrome.offerDeclined}
      </div>
    )
  }
  return (
    <div
      className={`${CARD} flex flex-col items-center gap-3 text-center shadow-[0_4px_16px_rgba(0,0,0,0.05)]`}
    >
      <p className="text-[14px] leading-[1.5] font-semibold text-[#0c0407]">
        {message.prompt || chrome.offerPrompt}
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        <button
          type="button"
          disabled={actions.busy}
          onClick={() => actions.accept(message.requestId)}
          className="rounded-[48px] bg-[#0c0407] px-[22px] py-2.5 text-[13px] font-semibold text-white hover:bg-[#3a3236] disabled:opacity-60"
        >
          {chrome.offerYes}
        </button>
        <button
          type="button"
          disabled={actions.busy}
          onClick={() => actions.decline(message.requestId)}
          className="rounded-[48px] border border-[#e5e5e5] px-[22px] py-2.5 text-[13px] font-semibold text-[#666] hover:border-[#db4545] hover:text-[#db4545] disabled:opacity-60"
        >
          {chrome.offerKeepChatting}
        </button>
      </div>
    </div>
  )
}

const FIELD =
  'w-full rounded-[10px] border border-[#e5e5e5] bg-[#faf9f6] px-3 py-2 text-[13px] text-[#0c0407] outline-none placeholder:text-[#999] focus:border-[#0c0407]'

/**
 * The "Your details" card, shown when a Visitor accepts a Hand-over and the Lead has no name
 * or work email yet — the two things a Strategist needs to come back to them. It posts to the
 * same Lead the Assistant has been filling in through `capture_lead`, so what the Visitor
 * types and what the Assistant learned are one person in the Console.
 */
function DetailsCard({
  lead,
  done,
  chrome,
  actions,
}: {
  lead: LeadContact
  done: boolean
  chrome: Chrome
  actions: HandoverActions
}) {
  const [name, setName] = useState(lead.name)
  const [email, setEmail] = useState(lead.email)
  const [company, setCompany] = useState(lead.company)

  if (done) {
    return <div className={`${CARD} text-[13px] text-[#0a7d43]`}>{chrome.detailsDone}</div>
  }
  return (
    <form
      className={`${CARD} flex w-[88%] flex-col gap-2`}
      onSubmit={(event) => {
        event.preventDefault()
        actions.shareDetails({ name: name.trim(), email: email.trim(), company: company.trim() })
      }}
    >
      <div className="text-[13.5px] font-semibold text-[#0c0407]">{chrome.detailsTitle}</div>
      <input
        className={FIELD}
        aria-label={chrome.detailsName}
        placeholder={chrome.detailsName}
        value={name}
        onChange={(event) => setName(event.target.value)}
      />
      <input
        className={FIELD}
        type="email"
        aria-label={chrome.detailsEmail}
        placeholder={chrome.detailsEmail}
        value={email}
        onChange={(event) => setEmail(event.target.value)}
      />
      <input
        className={FIELD}
        aria-label={chrome.detailsCompany}
        placeholder={chrome.detailsCompany}
        value={company}
        onChange={(event) => setCompany(event.target.value)}
      />
      {actions.failed ? (
        <p role="alert" className="text-[12px] text-[#db4545]">
          {chrome.detailsFailed}
        </p>
      ) : null}
      <button
        type="submit"
        disabled={actions.busy || (name.trim() === '' && email.trim() === '')}
        className="self-start rounded-[48px] bg-[#0c0407] px-[18px] py-2.5 text-[13px] font-semibold text-white hover:bg-[#3a3236] disabled:bg-[#ccc]"
      >
        {chrome.detailsSubmit}
      </button>
    </form>
  )
}

/** The Callback confirmation, with the details a Strategist will use to reach the Visitor. */
function CallbackCard({ lead, chrome }: { lead: LeadContact; chrome: Chrome }) {
  const details = [lead.name, lead.company, lead.email].filter((value) => value.trim() !== '')
  return (
    <div className={CARD}>
      <div className="mb-1.5 text-[13.5px] font-semibold text-[#0c0407]">
        {chrome.callbackTitle}
      </div>
      <p className="mb-2.5 text-[13.5px] leading-[1.55] text-[#4c4c4c]">{chrome.callbackBody}</p>
      {details.length > 0 ? (
        <div className="rounded-[10px] bg-[#faf9f6] px-3 py-2.5 text-[12.5px] text-[#666]">
          {details.join(' · ')}
        </div>
      ) : null}
    </div>
  )
}

export function MessageView({
  message,
  chrome,
  sectionTitles,
  onNavigate,
  feedback,
  handover,
}: {
  message: Message
  /** The widget's chrome in the Visitor's chosen language: every label a card draws. */
  chrome: Chrome
  sectionTitles: Record<string, string>
  /** Follow a Walkthrough Card into the app, without unmounting the panel. */
  onNavigate: (href: string) => void
  /** The thumbs for this answer, when it has a Trace to attach them to. Passed in rather than
   * built here so that one component owns which answers are rateable. */
  feedback?: ReactNode
  handover: HandoverActions
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
          aria-label={chrome.typing}
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
              {message.language ? chromeFor(message.language).nextStep : chrome.nextStep}
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

      {message.kind === 'offer' && (
        <OfferCard message={message} chrome={chrome} actions={handover} />
      )}

      {message.kind === 'details' && (
        <DetailsCard
          lead={message.lead}
          done={message.done}
          chrome={chrome}
          actions={handover}
        />
      )}

      {message.kind === 'callback' && <CallbackCard lead={message.lead} chrome={chrome} />}

      {message.kind === 'note' && (
        <div className="max-w-[82%] rounded-[16px_16px_16px_4px] border border-[#e5e5e5] bg-white px-[15px] py-[11px] text-[14px] leading-[1.55] text-[#333]">
          {chrome[message.note]}
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
