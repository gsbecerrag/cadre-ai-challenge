import { Suspense, lazy, useEffect } from 'react'
import { Outlet, createBrowserRouter, useLocation, useNavigate } from 'react-router-dom'

import { ChatWidget, NAVIGATE_EVENT } from './chat/ChatWidget'
import { AgentsPage } from './portal/AgentsPage'
import { DashboardPage } from './portal/DashboardPage'
import { PortalLayout } from './portal/PortalLayout'
import { ResultsTrainingPage } from './portal/ResultsTrainingPage'
import { ToolsPage } from './portal/ToolsPage'
import { HostPage } from './site/HostPage'

/**
 * The Console is loaded on demand, and that is the whole point of these five lines.
 *
 * It is the only part of the app that needs the Firebase SDK — Google sign-in and the
 * realtime Leads listener — which is a little over 200 kB gzipped. A Visitor reading the host
 * page never opens the Console, so a static import would make every prospect download
 * Cadre's staff tooling before they could read the first answer. `React.lazy` puts it in its
 * own chunk that is fetched the first time somebody routes to `/console`.
 */
const ConsoleLayout = lazy(() =>
  import('./console/ConsoleLayout').then((module) => ({ default: module.ConsoleLayout })),
)
const LeadsPage = lazy(() =>
  import('./console/LeadsPage').then((module) => ({ default: module.LeadsPage })),
)
const HandoverQueuePage = lazy(() =>
  import('./console/HandoverQueuePage').then((module) => ({ default: module.HandoverQueuePage })),
)
const CallbacksPage = lazy(() =>
  import('./console/CallbacksPage').then((module) => ({ default: module.CallbacksPage })),
)
const TriagePage = lazy(() =>
  import('./console/PlannedTabPage').then((module) => ({ default: module.TriagePage })),
)

/**
 * What a Strategist sees for the moment the Console chunk is in flight. Deliberately built
 * from the Cadre tokens in index.css rather than from anything in `console/` — importing a
 * component from there to render the loading state would pull the chunk back into this
 * bundle and undo the split.
 */
function ConsoleChunk({ children }: { children: React.ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-cadre-sand font-sans text-sm text-cadre-muted">
          Loading the Console…
        </div>
      }
    >
      {children}
    </Suspense>
  )
}

/**
 * The bridge between a Walkthrough Card and the router.
 *
 * The chat widget is mounted beside the router, not inside it (see `App.tsx`), because it
 * floats over every page and must survive every navigation with its transcript intact — which
 * also means it has no `useNavigate` of its own. So the card's call to action announces the
 * href on the window and this component, which does sit inside the router, navigates. The
 * panel is untouched: same component, same state, new page behind it.
 *
 * The fragment is the stable id of the thing the card was talking about, and it is scrolled to
 * a tick later, once the route it belongs to has rendered.
 */
function WalkthroughNavigation() {
  const navigate = useNavigate()

  useEffect(() => {
    function follow(event: Event) {
      const href = (event as CustomEvent<{ href?: string }>).detail?.href
      // Only a relative, same-origin path is ours to navigate. `//evil.example` is a
      // protocol-relative URL, not a route, and anything absolute belongs in a new tab —
      // the event is on the window, so this guard does not assume a trustworthy dispatcher.
      if (!href || !href.startsWith('/') || href.startsWith('//')) {
        return
      }
      void navigate(href)
      const fragment = href.split('#')[1]
      if (fragment) {
        window.setTimeout(() => {
          document.getElementById(fragment)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }, 0)
      }
    }
    window.addEventListener(NAVIGATE_EVENT, follow)
    return () => window.removeEventListener(NAVIGATE_EVENT, follow)
  }, [navigate])

  return null
}

/**
 * Renders on every route, so the bridge above is always listening — and so the chat widget
 * mounts once and survives every navigation with its transcript intact.
 *
 * The widget is hidden on the Console. It is the Visitor's channel to the Assistant, and the
 * Console is where a Strategist reads what that channel produced; a chat bubble hovering over
 * a Lead's Contact Details belongs to neither audience. Every other route keeps it exactly as
 * before.
 */
function Root() {
  const onConsole = useLocation().pathname.startsWith('/console')
  return (
    <>
      <WalkthroughNavigation />
      <Outlet />
      {onConsole ? null : <ChatWidget />}
    </>
  )
}

/**
 * The app's route table: `/` is the mock cadreai.com host page the chat widget floats
 * over; `/portal/*` is the demo Portal, sharing `PortalLayout` for its header, "Demo
 * portal · mock data" badge, and left nav (ticket 07); `/console/*` is the Strategist
 * Console behind Google sign-in and the allowlist (ticket 10). Client-side navigation
 * only — the server already falls back to the SPA for any non-`/api` path.
 */
export const router = createBrowserRouter([
  {
    element: <Root />,
    children: [
      {
        path: '/',
        element: <HostPage />,
      },
      {
        path: '/portal',
        element: <PortalLayout />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: 'tools', element: <ToolsPage /> },
          { path: 'agents', element: <AgentsPage /> },
          { path: 'results', element: <ResultsTrainingPage /> },
        ],
      },
      {
        path: '/console',
        element: (
          <ConsoleChunk>
            <ConsoleLayout />
          </ConsoleChunk>
        ),
        children: [
          {
            index: true,
            element: (
              <ConsoleChunk>
                <LeadsPage />
              </ConsoleChunk>
            ),
          },
          {
            path: 'handover',
            element: (
              <ConsoleChunk>
                <HandoverQueuePage />
              </ConsoleChunk>
            ),
          },
          {
            path: 'callbacks',
            element: (
              <ConsoleChunk>
                <CallbacksPage />
              </ConsoleChunk>
            ),
          },
          {
            path: 'triage',
            element: (
              <ConsoleChunk>
                <TriagePage />
              </ConsoleChunk>
            ),
          },
        ],
      },
    ],
  },
])
