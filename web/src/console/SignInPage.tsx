import { CADRE_LOGO_URL } from './chrome'

/**
 * The way into the Console, and the way it says no.
 *
 * The design reference has no sign-in screen, so this is built from the same tokens as the
 * Console shell: the sand background, the card, the ink pill. Two states — an invitation, and
 * the refusal a signed-in stranger reads, which is the API's own message so that what the
 * server decided and what the person is told cannot disagree (ADR-0010).
 */
export function SignInPage({
  onSignIn,
  onLeave,
  refusal,
  error,
  busy,
}: {
  onSignIn: () => void
  onLeave: () => void
  refusal?: string
  error?: string
  busy?: boolean
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-cadre-sand px-6 font-sans text-cadre-body">
      <div className="w-full max-w-[420px] rounded-card border border-cadre-line bg-white p-9 text-center">
        <img src={CADRE_LOGO_URL} alt="Cadre AI" className="mx-auto mb-5 h-5" />
        <div className="font-display mb-2 text-xl font-semibold tracking-tight text-cadre-ink">
          Strategist Console
        </div>

        {refusal ? (
          <>
            <p className="mb-6 text-sm leading-relaxed text-cadre-muted">{refusal}</p>
            <button
              type="button"
              onClick={onLeave}
              className="w-full rounded-pill border border-cadre-line px-6 py-3.5 text-sm font-semibold text-cadre-body hover:text-cadre-red"
            >
              Sign in with a different account
            </button>
          </>
        ) : (
          <>
            <p className="mb-6 text-sm leading-relaxed text-cadre-muted">
              Leads, Availability and the hand-over queue. Cadre Strategists only — sign in with
              the Google account on Cadre’s allowlist.
            </p>
            <button
              type="button"
              onClick={onSignIn}
              disabled={busy}
              className="w-full rounded-pill bg-cadre-ink px-6 py-3.5 text-sm font-semibold text-white disabled:opacity-60"
            >
              {busy ? 'Signing in…' : 'Sign in with Google'}
            </button>
            {error ? (
              <p className="mt-4 rounded-2xl bg-cadre-sand-dark px-4 py-3 text-left text-xs leading-relaxed text-[#8a5a5a]">
                {error}
              </p>
            ) : null}
          </>
        )}
      </div>
      <a href="/" className="mt-6 text-[13px] font-semibold text-cadre-muted hover:text-cadre-red">
        ← Visitor chat demo
      </a>
    </div>
  )
}
