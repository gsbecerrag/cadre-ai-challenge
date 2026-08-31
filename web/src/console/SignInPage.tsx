import { type FormEvent, useState } from 'react'

import { CADRE_LOGO_URL } from './chrome'
import { FAKE_AUTH, FAKE_STRATEGIST_EMAIL } from './firebase'

/** The email + password inputs, styled like the rest of the app's form fields. */
const FIELD =
  'w-full rounded-[10px] border border-cadre-line bg-cadre-sand px-3.5 py-2.5 text-sm text-cadre-ink outline-none placeholder:text-[#999] focus:border-cadre-ink'

/**
 * The email + password form (ticket 20): a second way in for a reviewer without a Google
 * account, using the demo Strategist credentials. Google stays primary — this is the "or"
 * underneath it — and both paths end at the same `onAuthStateChanged` listener in
 * `session.ts`, so nothing downstream (the ID token, the allowlist check, sign-out) needs to
 * know which one ran.
 */
function EmailSignInForm({
  onSignInWithEmail,
  busy,
}: {
  onSignInWithEmail: (email: string, password: string) => void
  busy?: boolean
}) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSignInWithEmail(email.trim(), password)
  }

  return (
    <>
      <div className="my-5 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-wide text-[#bbb]">
        <span className="h-px flex-1 bg-cadre-line" />
        or sign in with email
        <span className="h-px flex-1 bg-cadre-line" />
      </div>
      <form className="flex flex-col gap-3 text-left" onSubmit={handleSubmit}>
        <label className="flex flex-col gap-1.5 text-xs font-semibold text-cadre-muted">
          Email
          <input
            className={FIELD}
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-xs font-semibold text-cadre-muted">
          Password
          <input
            className={FIELD}
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="mt-1 w-full rounded-pill border border-cadre-ink px-6 py-3 text-sm font-semibold text-cadre-ink disabled:opacity-60"
        >
          {busy ? 'Signing in…' : 'Sign in with email'}
        </button>
      </form>
    </>
  )
}

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
  onSignInWithEmail,
  onLeave,
  refusal,
  error,
  busy,
  emailBusy,
}: {
  onSignIn: () => void
  onSignInWithEmail: (email: string, password: string) => void
  onLeave: () => void
  refusal?: string
  error?: string
  busy?: boolean
  emailBusy?: boolean
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
              {busy
                ? 'Signing in…'
                : FAKE_AUTH
                  ? 'Continue as demo Strategist'
                  : 'Sign in with Google'}
            </button>
            {FAKE_AUTH ? (
              // A button labelled "Sign in with Google" that does not use Google would be a
              // lie on a screenshot. The deployed Console refuses to start in this mode. The
              // fake-auth build already has a one-click demo path, so the email form (a real
              // Firebase call) does not apply here.
              <p className="mt-4 rounded-2xl bg-cadre-sand-dark px-4 py-3 text-left text-xs leading-relaxed text-[#996]">
                Demo mode: this build signs in as {FAKE_STRATEGIST_EMAIL} without Google.
              </p>
            ) : (
              <EmailSignInForm onSignInWithEmail={onSignInWithEmail} busy={emailBusy} />
            )}
            {error ? (
              <p role="alert" className="mt-4 rounded-2xl bg-cadre-sand-dark px-4 py-3 text-left text-xs leading-relaxed text-[#8a5a5a]">
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
