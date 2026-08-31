/**
 * The thumbs under an Assistant answer, and what they turn into once pressed.
 *
 * The artboard draws this as the card that closes a call (docs/design/DESIGN-BRIEF.md §2.5,
 * kind 9): a prompt, 👍 and 👎 as white pills that take a green border on hover, and a done
 * state that thanks the Visitor or apologises. The spec asks for the same control after every
 * answer, so it is rendered inline and compact — the same copy, colours and radii, without the
 * card around them, because a full card under every paragraph would be louder than the answer.
 *
 * The press is the Feedback. A thumb goes to the server the moment it is pressed — the
 * artboard closes its card on the press, and a Visitor who rates an answer and walks away has
 * still rated it. Only then does the note box appear, and sending a sentence from it is the
 * same rating again with the sentence attached: an update of the Feedback that already stands,
 * not a second one. Asking for the sentence first would put a form in front of the one-click
 * thing, and the rating is what the Triage Agent runs on; the sentence is a bonus.
 */

import { useState } from 'react'

import type { Chrome } from './strings'
import type { FeedbackEntry, FeedbackRating } from './types'

const THUMB = 'rounded-[48px] border bg-white px-[18px] py-1.5 text-[15px] leading-none'

// The thumb that stands is outlined in ink, so a Visitor coming back to a rated answer can see
// which way they voted and that the other thumb is the change still on offer. The border
// colour is chosen here rather than overridden on top of a default: two arbitrary Tailwind
// border colours on one element are resolved by stylesheet order, not by the order they are
// written in, and the marked thumb loses that race about half the time.
const RESTING: Record<FeedbackRating, string> = {
  // Hover colours from the artboard (§2.5, kind 9): green for the thumbs-up, the Cadre red
  // for the thumbs-down. Written out per rating because Tailwind generates the classes it can
  // see in the source, and `hover:border-[${colour}]` is a class it cannot see.
  up: 'border-[#e5e5e5] hover:border-[#0a7d43]',
  down: 'border-[#e5e5e5] hover:border-[#db4545]',
}
const CHOSEN = 'border-[#0c0407]'

export function FeedbackControl({
  traceId,
  entry,
  chrome,
  onSend,
}: {
  /** The Trace of the Turn this rates — the key the Feedback is stored under. */
  traceId: string
  entry: FeedbackEntry | undefined
  chrome: Chrome
  /** Post the rating, and resolve to whether the server took it. */
  onSend: (traceId: string, rating: FeedbackRating, comment: string) => Promise<boolean>
}) {
  const [comment, setComment] = useState('')

  const status = entry?.status ?? 'none'
  const rating = entry?.rating ?? null
  const done = status !== 'none'
  // A rating already sent may be changed exactly once, so the buttons stay up while the
  // Feedback is merely `sent` and go away once that change has been spent.
  const canPress = status === 'none' || status === 'sent'

  async function send(option: FeedbackRating, note: string) {
    if (await onSend(traceId, option, note)) {
      // Only on success: a send that failed leaves the sentence in the box, because retyping
      // it is a worse outcome than seeing it sit there.
      setComment('')
    }
  }

  function thumb(option: FeedbackRating, label: string, glyph: string) {
    return (
      <button
        type="button"
        aria-label={label}
        aria-pressed={rating === option}
        // The thumb that already stands is the rating the server holds, so pressing it again
        // would be a request that says nothing new; the note box is how that opinion grows.
        onClick={() => option !== rating && void send(option, '')}
        className={`${THUMB} ${rating === option ? CHOSEN : RESTING[option]}`}
      >
        {glyph}
      </button>
    )
  }

  return (
    <div className="mt-1.5 flex w-full flex-col items-start gap-1.5">
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

      {status === 'sent' && rating !== null && (
        <form
          className="flex w-[88%] items-center gap-2 rounded-[48px] border border-[#e5e5e5] bg-white py-1 pr-1 pl-3.5"
          onSubmit={(event) => {
            event.preventDefault()
            // An empty box is nothing to say, not a sentence to erase: the rating is already
            // with the server, so there is no request to make.
            if (comment.trim()) {
              void send(rating, comment.trim())
            }
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
