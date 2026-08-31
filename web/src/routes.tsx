import { useEffect } from 'react'
import { Outlet, createBrowserRouter, useNavigate } from 'react-router-dom'

import { NAVIGATE_EVENT } from './chat/ChatWidget'
import { ConsoleLayout } from './console/ConsoleLayout'
import { LeadsPage } from './console/LeadsPage'
import { CallbacksPage, HandoverQueuePage, TriagePage } from './console/PlannedTabPage'
import { AgentsPage } from './portal/AgentsPage'
import { DashboardPage } from './portal/DashboardPage'
import { PortalLayout } from './portal/PortalLayout'
import { ResultsTrainingPage } from './portal/ResultsTrainingPage'
import { ToolsPage } from './portal/ToolsPage'
import { HostPage } from './site/HostPage'

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

/** Renders on every route, so the bridge above is always listening. */
function Root() {
  return (
    <>
      <WalkthroughNavigation />
      <Outlet />
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
        element: <ConsoleLayout />,
        children: [
          { index: true, element: <LeadsPage /> },
          { path: 'handover', element: <HandoverQueuePage /> },
          { path: 'callbacks', element: <CallbacksPage /> },
          { path: 'triage', element: <TriagePage /> },
        ],
      },
    ],
  },
])
