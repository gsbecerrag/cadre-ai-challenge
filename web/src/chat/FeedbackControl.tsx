/**
 * The thumbs under an Assistant answer, and what they turn into once pressed.
 *
 * The artboard draws this as the card that closes a call (docs/design/DESIGN-BRIEF.md §2.5,
 * kind 9): a prompt, 👍 and 👎 as white pills that take a green border on hover, and a done
 * state that thanks the Visitor or apologises. The spec asks for the same control after every
 * answer, so it is rendered inline and compact — the same copy, colours and radii, without the
 * card around them, because a full card under every paragraph would be louder than the answer.
 *
 * The comment box appears only after a thumb is pressed. Asking for a sentence before the
 * rating would put a form in front of the one-click thing, and the rating is what the Triage
 * Agent runs on; the sentence is a bonus.
 */

import { useState } from 'react'

import type { Chrome } from './strings'
import type { FeedbackEntry, FeedbackRating } from './types'

const THUMB =
  'rounded-[48px] border border-[#e5e5e5] bg-white px-[18px] py-1.5 text-[15px] leading-none'
const CHOSEN = 'border-[#0c0407]'

// Written out per rating rather than interpolated: Tailwind generates the classes it can see
// in the source, and `hover:border-[${colour}]` is a class it cannot see (artboard §2.5).
const HOVER: Record<FeedbackRating, string> = {
  up: 'hover:border-[#0a7d43]',
  down: 'hover:border-[#db4545]',
}

export function FeedbackControl({
  traceId,
  entry,
  chrome,
  onChoose,
  onSend,
}: {
  /** The Trace of the Turn this rates — the key the Feedback is stored under. */
  traceId: string
  entry: FeedbackEntry | undefined
  chrome: Chrome
  onChoose: (traceId: string, rating: FeedbackRating) => void
  onSend: (traceId: string, rating: FeedbackRating, comment: string) => void
}) {
  const [comment, setComment] = useState('')

  const status = entry?.status ?? 'none'
  const rating = entry?.rating ?? null
  const done = status === 'submitted' || status === 'changed' || status === 'locked'
  // A thumb already sent may be changed exactly once, so the buttons stay up while the
  // Feedback is merely `submitted` and go away once that change has been spent.
  const canPress = status === 'none' || status === 'chosen' || status === 'submitted'

  function thumb(option: FeedbackRating, label: string, glyph: string) {
    return (
      <button
        type="button"
        aria-label={label}
        aria-pressed={rating === option}
        onClick={() => onChoose(traceId, option)}
        className={`${THUMB} ${rating === option ? CHOSEN : HOVER[option]}`}
      >
        {glyph}
      </button>
    )
  }

  return (
    <div className="mt-1.5 flex flex-col items-start gap-1.5">
      {!done && <div className="text-[12.5px] text-[#666]">{chrome.feedbackPrompt}</div>}

      {done && (
        <div className="text-[12.5px] text-[#999]">
          {rating === 'down' ? chrome.feedbackSorry : chrome.feedbackThanks}
        </div>
      )}

      {canPress && (
        <div className="flex gap-2.5">
          {thumb('up', chrome.feedbackUp, '👍')}
          {thumb('down', chrome.feedbackDown, '👎')}
        </div>
      )}

      {status === 'chosen' && rating !== null && (
        <form
          className="flex items-center gap-2 rounded-[48px] border border-[#e5e5e5] bg-white py-1 pr-1 pl-3.5"
          onSubmit={(event) => {
            event.preventDefault()
            onSend(traceId, rating, comment.trim())
          }}
        >
          <input
            type="text"
            aria-label={chrome.feedbackComment}
            placeholder={chrome.feedbackComment}
            value={comment}
            maxLength={500}
            onChange={(event) => setComment(event.target.value)}
            className="min-w-0 flex-1 border-none bg-transparent text-[12.5px] text-[#0c0407] outline-none placeholder:text-[#999]"
          />
          <button
            type="submit"
            aria-label={chrome.send}
            className="flex size-7 flex-shrink-0 items-center justify-center rounded-full bg-[#db4545] text-[13px] text-white"
          >
            ↑
          </button>
        </form>
      )}
    </div>
  )
}
