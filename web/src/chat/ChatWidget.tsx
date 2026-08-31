/**
 * The Cadre AI Assistant chat widget: a launcher and the panel it opens.
 *
 * Geometry, colours, radii and copy come from the design artboard
 * (docs/design/DESIGN-BRIEF.md §2.3–2.5): docked 392px bottom-right or expanded to `inset:20px`,
 * radius 24px, the header gradient with the "C" avatar, the presence line, the EN/ES chrome
 * toggle, and the composer with the `↑` send button.
 *
 * The presence line shows the offline copy until ticket 11 wires Availability.
 */

import { useEffect, useRef, useState } from 'react'

import './chat.css'
import { MessageView } from './MessageView'
import { chromeFor, type Language } from './strings'
import { useChat } from './useChat'

const DOCKED = 'right-6 bottom-24 h-[min(660px,calc(100vh-130px))] w-[392px]'
const EXPANDED = 'inset-5'

export function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [language, setLanguage] = useState<Language>('en')
  const [draft, setDraft] = useState('')
  const [usedQuickReplies, setUsedQuickReplies] = useState<string[]>([])

  const chrome = chromeFor(language)
  const { state, send } = useChat(chromeFor('en').greeting, chrome.connectionError)

  const transcript = useRef<HTMLDivElement>(null)
  useEffect(() => {
    transcript.current?.scrollTo({ top: transcript.current.scrollHeight })
  }, [state.messages])

  // A chip disappears once it has been used; the others stay, as in the artboard.
  const quickReplies = chrome.quickReplies.filter((quick) => !usedQuickReplies.includes(quick.id))
  const canSend = draft.trim().length > 0 && !state.pending

  function submit(text: string) {
    setDraft('')
    void send(text)
  }

  function submitQuickReply(id: string, label: string) {
    setUsedQuickReplies([...usedQuickReplies, id])
    submit(label)
  }

  if (!open) {
    return (
      <button
        type="button"
        aria-label={chrome.openChat}
        onClick={() => setOpen(true)}
        className="fixed right-6 bottom-6 z-60 flex size-[58px] items-center justify-center rounded-full bg-[#0c0407] text-[22px] leading-none tracking-[2px] text-white shadow-[0_8px_24px_rgba(12,4,7,0.3)] transition-transform hover:scale-105"
      >
        <span className="pb-2">…</span>
      </button>
    )
  }

  return (
    <section
      aria-label={chrome.headerTitle}
      className={`fixed z-70 flex flex-col overflow-hidden rounded-[24px] bg-white shadow-[0_16px_48px_rgba(12,4,7,0.22)] ${expanded ? EXPANDED : DOCKED}`}
    >
      <header className="flex flex-shrink-0 items-center gap-3 bg-[linear-gradient(115deg,#0c0407,#3a3236)] px-[18px] py-4">
        <div className="flex size-9 items-center justify-center rounded-full bg-[#db4545] font-display text-[15px] font-bold text-white">
          C
        </div>
        <div className="min-w-0 flex-1">
          <div className="font-display text-[15px] font-semibold text-white">
            {chrome.headerTitle}
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-[#b3b3b3]">
            <span className="inline-block size-[7px] rounded-full bg-[#999]" />
            {chrome.presenceOffline}
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            aria-label={chrome.language}
            onClick={() => setLanguage(language === 'en' ? 'es' : 'en')}
            className="flex overflow-hidden rounded-[48px] border border-white/25 text-[10px] font-bold"
          >
            <span className={language === 'en' ? 'bg-white px-2 py-1 text-[#0c0407]' : 'px-2 py-1 text-[#b3b3b3]'}>
              EN
            </span>
            <span className={language === 'es' ? 'bg-white px-2 py-1 text-[#0c0407]' : 'px-2 py-1 text-[#b3b3b3]'}>
              ES
            </span>
          </button>
          <button
            type="button"
            aria-label={expanded ? chrome.collapse : chrome.expand}
            onClick={() => setExpanded(!expanded)}
            className="flex size-7 items-center justify-center rounded-full text-[13px] text-[#b3b3b3] hover:bg-white/10 hover:text-white"
          >
            ⤢
          </button>
          <button
            type="button"
            aria-label={chrome.closeChat}
            onClick={() => setOpen(false)}
            className="flex size-7 items-center justify-center rounded-full text-[15px] text-[#b3b3b3] hover:bg-white/10 hover:text-white"
          >
            ×
          </button>
        </div>
      </header>

      <div
        ref={transcript}
        role="log"
        aria-live="polite"
        className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto bg-[#faf9f6] px-4 pt-[18px] pb-2"
      >
        {state.messages.map((message) => (
          <MessageView key={message.id} message={message} />
        ))}
      </div>

      {quickReplies.length > 0 && (
        <div className="flex flex-shrink-0 flex-wrap gap-2 bg-[#faf9f6] px-4 pt-2 pb-1">
          {quickReplies.map((quick) => (
            <button
              key={quick.id}
              type="button"
              disabled={state.pending}
              onClick={() => submitQuickReply(quick.id, quick.label)}
              className="rounded-[48px] border border-[#e5e5e5] bg-white px-3.5 py-2 text-[12.5px] font-semibold text-[#0c0407] hover:border-[#db4545] hover:text-[#db4545]"
            >
              {quick.label}
            </button>
          ))}
        </div>
      )}

      <form
        className="flex flex-shrink-0 items-center gap-2.5 border-t border-[#eee] bg-white px-4 py-3"
        onSubmit={(event) => {
          event.preventDefault()
          if (canSend) {
            submit(draft)
          }
        }}
      >
        <input
          type="text"
          aria-label={chrome.placeholder}
          placeholder={chrome.placeholder}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          className="min-w-0 flex-1 border-none bg-transparent text-[14px] text-[#0c0407] outline-none placeholder:text-[#999]"
        />
        <button
          type="submit"
          aria-label={chrome.send}
          disabled={!canSend}
          className={`flex size-9 flex-shrink-0 items-center justify-center rounded-full text-[15px] text-white ${canSend ? 'bg-[#db4545]' : 'bg-[#ccc]'}`}
        >
          ↑
        </button>
      </form>
    </section>
  )
}
