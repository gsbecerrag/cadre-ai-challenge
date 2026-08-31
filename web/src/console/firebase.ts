import { type FirebaseApp, getApps, initializeApp } from 'firebase/app'
import { type Auth, getAuth } from 'firebase/auth'
import { type Firestore, getFirestore } from 'firebase/firestore'

/**
 * The Firebase web configuration, committed on purpose.
 *
 * Firebase's own documentation says this config is public: it identifies the project to
 * Google's servers, it is shipped inside every browser bundle that uses Firebase, and it
 * grants nothing on its own. What protects the data is Firestore's security rules and the
 * allowlist the API checks — `firestore.rules` and `api/console.py`, not this file. Hiding it
 * in an environment variable would buy no security and would break `make build-web` for
 * anyone without a `.env`.
 *
 * `VITE_FIREBASE_*` still overrides each value, so the Console can be pointed at a different
 * Firebase project without a code change.
 */
const FIREBASE_CONFIG = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || 'AIzaSyBEyuaYyPcGxY2zvT2h9lIMicR4q28myP0',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'cadre-ai-challenge.firebaseapp.com',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'cadre-ai-challenge',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '1:495870119371:web:b5182894b304440778ba4e',
}

/**
 * `fake` swaps Google sign-in for a demo Strategist whose credential is `fake:<email>`. The
 * API accepts it only when `CONSOLE_AUTH=fake` and `ENV=development` — it refuses to start in
 * production — so this is a local-demo and screenshot path, never a way into a deployment.
 */
export const FAKE_AUTH = import.meta.env.VITE_CONSOLE_AUTH === 'fake'
export const FAKE_STRATEGIST_EMAIL =
  import.meta.env.VITE_CONSOLE_FAKE_EMAIL || 'strategist@example.com'

/**
 * Firebase is initialised on first use rather than at module load, so importing anything from
 * the Console route group does not construct an app — the chat widget and the host page share
 * this bundle and neither of them signs anyone in.
 */
function app(): FirebaseApp {
  return getApps()[0] ?? initializeApp(FIREBASE_CONFIG)
}

export function firebaseAuth(): Auth {
  return getAuth(app())
}

export function firebaseFirestore(): Firestore {
  return getFirestore(app())
}
