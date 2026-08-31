import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  type User,
} from 'firebase/auth'
import { useCallback, useEffect, useState } from 'react'

import { FAKE_AUTH, FAKE_STRATEGIST_EMAIL, firebaseAuth } from './firebase'

/** The Strategist the browser believes is signed in. The API decides whether they are ours. */
export type Strategist = {
  uid: string
  email: string
  name: string
}

export type Session =
  /** Firebase has not yet said whether a sign-in is being restored from the last visit. */
  | { status: 'loading' }
  | { status: 'signed-out'; error?: string }
  | { status: 'signed-in'; strategist: Strategist }

/** Where the demo Strategist is remembered across a reload, in `fake` mode only. */
const FAKE_SESSION_KEY = 'cadre.console.fake-strategist'

function strategistFrom(user: User): Strategist {
  const email = (user.email ?? '').toLowerCase()
  return {
    uid: user.uid,
    email,
    name: user.displayName?.trim() || email.split('@')[0] || 'Strategist',
  }
}

function fakeStrategist(): Strategist {
  const email = FAKE_STRATEGIST_EMAIL.toLowerCase()
  return { uid: `dev-${email}`, email, name: email.split('@')[0] }
}

/**
 * A message for the sign-in page. Firebase's own codes are the useful part; its messages are
 * written for developers, and the one failure a reviewer will actually hit — an unauthorised
 * domain — deserves an answer rather than "auth/unauthorized-domain".
 */
function signInError(error: unknown): string | undefined {
  const code = typeof error === 'object' && error && 'code' in error ? String(error.code) : ''
  if (code === 'auth/popup-closed-by-user' || code === 'auth/cancelled-popup-request') {
    return undefined
  }
  if (code === 'auth/unauthorized-domain') {
    return 'This address is not an authorised domain for Cadre’s Firebase project, so Google sign-in was refused. Add it under Authentication → Settings → Authorized domains.'
  }
  if (code === 'auth/operation-not-allowed') {
    return 'Google sign-in is not enabled on Cadre’s Firebase project yet. Enable the Google provider under Authentication → Sign-in method.'
  }
  return 'Google sign-in did not complete. Please try again.'
}

/**
 * A message for the email + password form (ticket 20, for a reviewer without a Google
 * account). Firebase collapses "wrong password" and "no such user" into `auth/invalid-credential`
 * on current SDK versions, and the two older codes are kept here for the same reason: telling a
 * stranger *which* half was wrong is how you let them enumerate valid emails, so all three earn
 * the identical, honest sentence.
 */
function emailSignInError(error: unknown): string {
  const code = typeof error === 'object' && error && 'code' in error ? String(error.code) : ''
  if (
    code === 'auth/invalid-credential' ||
    code === 'auth/wrong-password' ||
    code === 'auth/user-not-found'
  ) {
    return 'That email or password is not right. Please check them and try again.'
  }
  if (code === 'auth/invalid-email') {
    return 'That does not look like a valid email address.'
  }
  if (code === 'auth/too-many-requests') {
    return 'Too many attempts. Please wait a moment and try again.'
  }
  return 'Sign-in did not complete. Please try again.'
}

/**
 * Who is signed in, and how to change that.
 *
 * The ID token is deliberately *not* held in state: `getIdToken()` returns a cached token and
 * refreshes it when it is close to expiring, so asking per request is both correct and free,
 * where a token copied into state would go stale after an hour of a Console left open.
 */
export function useStrategistSession(): {
  session: Session
  signIn: () => Promise<void>
  signInWithEmail: (email: string, password: string) => Promise<void>
  leave: () => Promise<void>
  authorization: () => Promise<string>
} {
  const [session, setSession] = useState<Session>({ status: 'loading' })

  useEffect(() => {
    if (FAKE_AUTH) {
      const remembered = window.sessionStorage.getItem(FAKE_SESSION_KEY)
      setSession(
        remembered ? { status: 'signed-in', strategist: fakeStrategist() } : { status: 'signed-out' },
      )
      return
    }
    return onAuthStateChanged(firebaseAuth(), (user) => {
      setSession(
        user ? { status: 'signed-in', strategist: strategistFrom(user) } : { status: 'signed-out' },
      )
    })
  }, [])

  const signIn = useCallback(async () => {
    if (FAKE_AUTH) {
      window.sessionStorage.setItem(FAKE_SESSION_KEY, FAKE_STRATEGIST_EMAIL)
      setSession({ status: 'signed-in', strategist: fakeStrategist() })
      return
    }
    try {
      await signInWithPopup(firebaseAuth(), new GoogleAuthProvider())
    } catch (error) {
      setSession({ status: 'signed-out', error: signInError(error) })
    }
  }, [])

  /**
   * The reviewer path (ticket 20): a demo Strategist account provisioned server-side in
   * Firebase Auth with `emailVerified: true`, so it reaches the Console exactly like a Google
   * sign-in — the API's `TokenVerifier` and `firestore.rules` check the token's claims, not
   * which provider issued it. `onAuthStateChanged` above picks up success the same way it
   * does for Google; only the failure path needs handling here.
   */
  const signInWithEmail = useCallback(async (email: string, password: string) => {
    try {
      await signInWithEmailAndPassword(firebaseAuth(), email, password)
    } catch (error) {
      setSession({ status: 'signed-out', error: emailSignInError(error) })
    }
  }, [])

  const leave = useCallback(async () => {
    if (FAKE_AUTH) {
      window.sessionStorage.removeItem(FAKE_SESSION_KEY)
      setSession({ status: 'signed-out' })
      return
    }
    await signOut(firebaseAuth())
  }, [])

  const authorization = useCallback(async () => {
    if (FAKE_AUTH) {
      return `fake:${FAKE_STRATEGIST_EMAIL}`
    }
    const user = firebaseAuth().currentUser
    if (!user) {
      throw new Error('Not signed in.')
    }
    return user.getIdToken()
  }, [])

  return { session, signIn, signInWithEmail, leave, authorization }
}
