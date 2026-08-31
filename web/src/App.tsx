import { RouterProvider } from 'react-router-dom'

import { ChatWidget } from './chat/ChatWidget'
import { router } from './routes'

/**
 * The app root: renders the route table (the mock cadreai.com host page at `/`, the demo
 * Portal under `/portal`) and the Assistant's chat widget. The widget is fixed-position and
 * independent of routing, so it mounts here as a sibling of the router output, not inside
 * any route — it floats over every page, as on cadreai.com.
 */
export function App() {
  return (
    <>
      <RouterProvider router={router} />
      <ChatWidget />
    </>
  )
}
