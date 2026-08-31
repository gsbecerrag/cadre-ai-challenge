import { RouterProvider } from 'react-router-dom'

import { router } from './routes'

/**
 * The app root: renders the route table — the mock cadreai.com host page at `/`, the demo
 * Portal under `/portal`, the Strategist Console under `/console`.
 *
 * The chat widget used to mount here, as a sibling of the router output, so that it floated
 * over every page as on cadreai.com. It now mounts inside the router's root layout instead:
 * it still floats over every Visitor page and still survives every navigation between them,
 * but the Console is a Strategist's surface and the Visitor's chat bubble has no business
 * hovering over it. Reading the location is the only way to know, and only a component inside
 * the router can.
 */
export function App() {
  return <RouterProvider router={router} />
}
