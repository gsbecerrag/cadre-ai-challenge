import { RouterProvider } from 'react-router-dom'

import { router } from './routes'

/**
 * The app root: renders the route table (the mock cadreai.com host page at `/`, the demo
 * Portal under `/portal`). The chat widget is fixed-position and independent of routing,
 * so it mounts here as a sibling of the router output, not inside any route.
 */
export function App() {
  return (
    <>
      <RouterProvider router={router} />
      {/* Ticket 02 mounts <ChatWidget /> here. */}
    </>
  )
}
