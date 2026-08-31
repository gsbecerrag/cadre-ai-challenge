import { createBrowserRouter } from 'react-router-dom'

import { AgentsPage } from './portal/AgentsPage'
import { DashboardPage } from './portal/DashboardPage'
import { PortalLayout } from './portal/PortalLayout'
import { ResultsTrainingPage } from './portal/ResultsTrainingPage'
import { ToolsPage } from './portal/ToolsPage'
import { HostPage } from './site/HostPage'

/**
 * The app's route table (ticket 07): `/` is the mock cadreai.com host page the chat
 * widget floats over; `/portal/*` is the demo Portal, sharing `PortalLayout` for its
 * header, "Demo portal · mock data" badge, and left nav. Client-side navigation only —
 * the server already falls back to the SPA for any non-`/api` path.
 */
export const router = createBrowserRouter([
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
])
