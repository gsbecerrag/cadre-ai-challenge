/**
 * The Live Hand-over's call, inside the chat panel — docs/design/DESIGN-BRIEF.md §2.6.
 *
 * Two sub-states and one iframe. While the server has no room yet the panel shows the
 * connecting spinner and "Connecting you with a strategist…"; once it has one, Daily's
 * prebuilt frame takes the whole video area, and its own controls are the mic, camera, share
 * and end buttons the artboard drew by hand — a control pill of ours would be a second set of
 * buttons that cannot actually mute anything.
 *
 * The header is the artboard's: "You're being assisted by" with the Strategist's name once
 * somebody has claimed the request, and the live pill with its pulsing dot throughout.
 *
 * The `allow` list is what makes the call work at all: without `camera` and `microphone` the
 * iframe is a spectator, and Chrome grants neither to a cross-origin frame that has not been
 * given permission by the embedding page.
 */

import type { Chrome } from './strings'
import type { CallState } from './types'

export const CALL_PERMISSIONS = 'camera; microphone; fullscreen; display-capture; autoplay'

const JOINED = ['strategist_joined', 'in_call']

export function CallFrame({ call, chrome }: { call: CallState; chrome: Chrome }) {
  const assisted = JOINED.includes(call.state) && call.strategistName !== ''

  return (
    <section
      aria-label={chrome.callTitle}
      className="flex min-h-0 flex-1 flex-col bg-[#0c0407]"
    >
      <div className="flex flex-shrink-0 items-center justify-between gap-2 px-4 py-2.5">
        <div className="min-w-0 truncate text-[12px] text-[#b3b3b3]">
          {assisted ? (
            <>
              {chrome.callAssistedBy}{' '}
              <span className="ml-1 rounded-[48px] bg-white/15 px-2 py-[3px] text-[11px] font-bold tracking-[0.5px] text-white uppercase">
                {call.strategistName}
              </span>
            </>
          ) : (
            chrome.handoverConnecting
          )}
        </div>
        <span className="flex flex-shrink-0 items-center gap-1.5 rounded-[48px] bg-black/50 px-2.5 py-1 text-[10px] font-bold tracking-[1px] text-white uppercase">
          <span className="cadre-livepulse inline-block size-[7px] rounded-full bg-[#db4545]" />
          {chrome.callLive}
        </span>
      </div>

      <div className="min-h-0 flex-1">
        {call.roomUrl ? (
          <iframe
            title={chrome.callTitle}
            src={call.roomUrl}
            allow={CALL_PERMISSIONS}
            className="size-full border-0"
          />
        ) : (
          <div className="flex size-full flex-col items-center justify-center gap-3 px-6 text-center text-[13px] text-[#b3b3b3]">
            <span className="cadre-spinring inline-block size-8 rounded-full border-2 border-white/20 border-t-white" />
            {chrome.handoverConnecting}
          </div>
        )}
      </div>
    </section>
  )
}
