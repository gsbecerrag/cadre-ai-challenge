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

import { useCallback, useEffect, useRef, useState } from 'react'

import './chat.css'
import { MessageView } from './MessageView'
import { chromeFor, type Language } from './strings'
import { useChat } from './useChat'

const DOCKED = 'right-6 bottom-24 h-[min(660px,calc(100vh-130px))] w-[392px]'
const EXPANDED = 'inset-5'

/**
 * The host page's "Talk to an AI Strategist" controls do not know about this component; they
 * announce intent on the window and the widget listens. That keeps ticket 07's page and this
 * widget independently mountable — the page works with no widget, the widget with no page.
 * Dispatched from `web/src/site/HostPage.tsx`.
 */
export const OPEN_CHAT_EVENT = 'cadre:open-chat'

/**
 * A Walkthrough Card's call to action, announced the same way and for the opposite reason: the
 * widget is mounted outside the router (see `App.tsx`), so it cannot navigate itself. The
 * listener in `web/src/routes.tsx` does the navigation and the panel stays exactly as it is —
 * open, with the whole transcript still in it. The detail is `{ href }`.
 */
export const NAVIGATE_EVENT = 'cadre:navigate'

const LANGUAGES: Language[] = ['en', 'es']

export function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [language, setLanguage] = useState<Language>('en')
  const [draft, setDraft] = useState('')
  const [usedQuickReplies, setUsedQuickReplies] = useState<string[]>([])

  const chrome = chromeFor(language)
  const { state, send, loadSections } = useChat(chromeFor('en').greeting, chrome.connectionError)

  const transcript = useRef<HTMLDivElement>(null)
  const composer = useRef<HTMLInputElement>(null)
  const launcher = useRef<HTMLButtonElement>(null)
  const wasOpen = useRef(false)

  useEffect(() => {
    transcript.current?.scrollTo({ top: transcript.current.scrollHeight })
  }, [state.messages])

  // Opening moves focus into the composer, closing puts it back on the launcher — otherwise
  // a keyboard Visitor is dropped at the top of the document by both.
  useEffect(() => {
    if (open) {
      composer.current?.focus()
      // The titles behind the citation chips, fetched once and only for a Visitor who
      // actually opens the panel.
      void loadSections()
    } else if (wasOpen.current) {
      launcher.current?.focus()
    }
    wasOpen.current = open
  }, [open, loadSections])

  useEffect(() => {
    function openFromHostPage() {
      setOpen(true)
      // Already open: the effect above will not re-run, so ask for focus here.
      composer.current?.focus()
    }
    window.addEventListener(OPEN_CHAT_EVENT, openFromHostPage)
    return () => window.removeEventListener(OPEN_CHAT_EVENT, openFromHostPage)
  }, [])

  useEffect(() => {
    if (!open) {
      return
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [open])

  // A chip disappears once it has been used; the others stay, as in the artboard.
  const quickReplies = chrome.quickReplies.filter((quick) => !usedQuickReplies.includes(quick.id))
  const canSend = draft.trim().length > 0 && !state.pending

  const submit = useCallback((text: string) => {
    setDraft('')
    void send(text)
  }, [send])

  const followCard = useCallback((href: string) => {
    // Expanded, the panel covers the page the card is opening, so it docks itself first —
    // as the artboard's `openPortalFromChat` does.
    setExpanded(false)
    window.dispatchEvent(new CustomEvent(NAVIGATE_EVENT, { detail: { href } }))
  }, [])

  function submitQuickReply(id: string, label: string) {
    setUsedQuickReplies([...usedQuickReplies, id])
    submit(label)
  }

  if (!open) {
    return (
      <button
        ref={launcher}
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
          <div
            role="group"
            aria-label={chrome.language}
            className="flex overflow-hidden rounded-[48px] border border-white/25 text-[10px] font-bold"
          >
            {LANGUAGES.map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={language === option}
                onClick={() => setLanguage(option)}
                className={
                  language === option
                    ? 'bg-white px-2 py-1 text-[#0c0407]'
                    : 'px-2 py-1 text-[#b3b3b3]'
                }
              >
                {option.toUpperCase()}
              </button>
            ))}
          </div>
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
          <MessageView
            key={message.id}
            message={message}
            typingLabel={chrome.typing}
            nextStepLabel={chrome.nextStep}
            sectionTitles={state.sections}
            onNavigate={followCard}
          />
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
          ref={composer}
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
