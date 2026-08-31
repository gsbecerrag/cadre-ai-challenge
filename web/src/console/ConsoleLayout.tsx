import { useCallback, useEffect, useState } from 'react'
import { NavLink, Outlet, useOutletContext } from 'react-router-dom'

import { type Availability, fetchAvailability, type Lead, NotAllowlisted, setAvailability } from './api'
import { CADRE_LOGO_URL, CONSOLE_TABS, ONLINE_GREEN } from './chrome'
import { type FeedStatus, useLeads } from './leadsFeed'
import { SignInPage } from './SignInPage'
import { type Strategist, useStrategistSession } from './session'

type ConsoleContext = { leads: Lead[]; status: FeedStatus; error?: string }

/** What the tab bodies read, so the nav badge and the Leads list count the same list. */
export function useConsole(): ConsoleContext {
  return useOutletContext<ConsoleContext>()
}

/**
 * The Console's front door (ADR-0010).
 *
 * Three states, and the order matters: Firebase is asked first whether a sign-in is being
 * restored, then the API is asked whether that account is one of Cadre's. The second question
 * is the real one — a valid Google sign-in is not admission — so the refusal is rendered from
 * the API's own 403, never guessed at in the browser.
 */
export function ConsoleLayout() {
  const { session, signIn, leave, authorization } = useStrategistSession()
  const [refusal, setRefusal] = useState<string>()
  const [signingIn, setSigningIn] = useState(false)

  const startSignIn = useCallback(() => {
    setSigningIn(true)
    void signIn().finally(() => setSigningIn(false))
  }, [signIn])

  const startLeave = useCallback(() => {
    setRefusal(undefined)
    void leave()
  }, [leave])

  if (session.status === 'loading') {
    return <Splash>Checking your sign-in…</Splash>
  }
  if (session.status === 'signed-out') {
    return (
      <SignInPage
        onSignIn={startSignIn}
        onLeave={startLeave}
        error={session.error}
        busy={signingIn}
      />
    )
  }
  if (refusal) {
    return <SignInPage onSignIn={startSignIn} onLeave={startLeave} refusal={refusal} />
  }
  return (
    <ConsoleShell
      strategist={session.strategist}
      authorization={authorization}
      onLeave={startLeave}
      onRefused={setRefusal}
    />
  )
}

/** What the Availability control says: the state, or why it cannot say one. */
function availabilityLabel(availability: Availability | undefined, problem?: string): string {
  if (availability !== undefined) {
    return availability.online ? 'Online' : 'Offline'
  }
  return problem ? 'Unavailable' : '…'
}

function Splash({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-cadre-sand font-sans text-sm text-cadre-muted">
      {children}
    </div>
  )
}

/**
 * Header, 200 px left nav, tab body — docs/design §3.
 *
 * A separate component from the gate above so that the Leads feed and the Availability read
 * only ever run for a Strategist who has been admitted: they are hooks, and hooks cannot be
 * conditional.
 */
function ConsoleShell({
  strategist,
  authorization,
  onLeave,
  onRefused,
}: {
  strategist: Strategist
  authorization: () => Promise<string>
  onLeave: () => void
  onRefused: (message: string) => void
}) {
  const [availability, setAvailabilityState] = useState<Availability>()
  const [saving, setSaving] = useState(false)
  // Anything that is not a 403. A 403 means "you are not one of Cadre's" and replaces the
  // whole page; a 500 or a dropped connection means "Availability is not readable right now",
  // and the Strategist has to be told — otherwise the control sits at "…" and disabled
  // forever and they have no idea whether the Assistant thinks they are online.
  const [problem, setProblem] = useState<string>()
  const { leads, status, error } = useLeads(authorization)

  const handleFailure = useCallback(
    (failure: unknown, whenItFailed: string) => {
      if (failure instanceof NotAllowlisted) {
        onRefused(failure.message)
        return
      }
      setProblem(whenItFailed)
    },
    [onRefused],
  )

  useEffect(() => {
    let live = true
    fetchAvailability(authorization)
      .then((state) => {
        if (live) {
          setAvailabilityState(state)
          setProblem(undefined)
        }
      })
      .catch((failure: unknown) => {
        if (live) {
          handleFailure(failure, 'Could not read your Availability. Reload to try again.')
        }
      })
    return () => {
      live = false
    }
  }, [authorization, handleFailure])

  const online = availability?.online ?? false
  const unknown = availability === undefined

  function toggle() {
    setSaving(true)
    setAvailability(authorization, !online)
      .then((state) => {
        setAvailabilityState(state)
        setProblem(undefined)
      })
      .catch((failure: unknown) => {
        handleFailure(failure, 'Could not change your Availability. Please try again.')
      })
      .finally(() => setSaving(false))
  }

  return (
    <div className="flex min-h-screen flex-col bg-cadre-sand font-sans text-cadre-body">
      <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3 border-b border-[#e5e5e5] bg-white px-4 py-3.5 sm:px-8">
        <div className="flex items-center gap-3.5">
          <img src={CADRE_LOGO_URL} alt="Cadre AI" className="h-5 shrink-0" />
          <span className="font-display shrink-0 text-[15px] font-semibold text-cadre-ink">
            Strategist Console
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-4 sm:gap-[18px]">
          <a href="/" className="text-[13px] font-semibold text-cadre-blue hover:text-cadre-red">
            ← Visitor chat demo
          </a>

          <div className="flex items-center gap-2.5 rounded-pill border border-[#e5e5e5] bg-cadre-sand py-1.5 pl-3.5 pr-2">
            <span
              className="text-[13px] font-semibold"
              style={{ color: online ? ONLINE_GREEN : '#999999' }}
            >
              {availabilityLabel(availability, problem)}
            </span>
            <button
              type="button"
              onClick={toggle}
              disabled={unknown || saving}
              // A switch, not a toggle button: `aria-checked` is what a screen reader reads
              // as on/off, and the name carries the state the sighted user can see, so both
              // are told the same thing.
              role="switch"
              aria-checked={online}
              aria-label={`Availability: ${availabilityLabel(availability, problem)}`}
              className="relative h-[22px] w-10 rounded-pill transition-colors disabled:opacity-60"
              style={{ background: online ? ONLINE_GREEN : '#cccccc' }}
            >
              <span
                className="absolute top-[2px] h-[18px] w-[18px] rounded-full bg-white shadow-[0_1px_3px_rgba(0,0,0,0.25)] transition-[left]"
                style={{ left: online ? '20px' : '2px' }}
              />
            </button>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-cadre-ink text-[13px] font-bold text-white">
              {(strategist.name || strategist.email || '?').charAt(0).toUpperCase()}
            </div>
            <div className="text-xs leading-[1.3]">
              <b className="text-cadre-ink">{strategist.name}</b>
              <br />
              <span className="text-[#999]">{strategist.email}</span>
            </div>
            <button
              type="button"
              onClick={onLeave}
              className="ml-1 text-xs font-semibold text-[#999] hover:text-cadre-red"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {problem ? (
        <p
          role="status"
          className="border-b border-[#e5e5e5] bg-cadre-sand-dark px-4 py-2.5 text-[13px] text-[#8a5a5a] sm:px-8"
        >
          {problem}
        </p>
      ) : null}

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <nav
          aria-label="Console"
          className="flex gap-1 overflow-x-auto border-b border-[#eee] bg-white px-3.5 py-3 md:w-[200px] md:flex-col md:overflow-visible md:border-b-0 md:border-r md:py-6"
        >
          {CONSOLE_TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end}
              className={({ isActive }) =>
                `flex shrink-0 items-center justify-between gap-2 whitespace-nowrap rounded-xl px-3.5 py-2.5 text-sm ${
                  isActive
                    ? 'bg-cadre-sand-dark font-semibold text-cadre-red'
                    : 'font-medium text-cadre-muted hover:text-cadre-body'
                }`
              }
            >
              {tab.label}
              {tab.label === 'Leads' && leads.length > 0 ? (
                <span className="rounded-pill bg-cadre-red px-2 py-px text-[11px] font-bold text-white">
                  {leads.length}
                </span>
              ) : null}
            </NavLink>
          ))}
        </nav>

        <main className="min-w-0 flex-1 px-6 py-6 md:px-8">
          <Outlet context={{ leads, status, error } satisfies ConsoleContext} />
        </main>
      </div>
    </div>
  )
}
