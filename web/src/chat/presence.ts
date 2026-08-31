/**
 * Availability, as the chat header's presence line reads it.
 *
 * `GET /api/availability` is public and answers one boolean about the team — whether at least
 * one Strategist is online — and names nobody: who Cadre's Strategists are and which of them
 * is at their desk stay behind the Console's allowlist.
 *
 * It is polled, not streamed. A Server-Sent Events channel for one boolean would be a second
 * long-lived connection per open panel, on a service whose whole point is to be cheap when
 * nobody is talking; a minute of staleness on a presence dot costs the Visitor nothing,
 * because the offer of a Hand-over is gated by Availability on the server at the moment they
 * accept — not by what this line said when the panel opened.
 */

import { useEffect, useState } from 'react'

export const AVAILABILITY_ENDPOINT = '/api/availability'

const REFRESH_MS = 60_000

export function useAvailability(open: boolean): boolean {
  const [anyOnline, setAnyOnline] = useState(false)

  useEffect(() => {
    if (!open) {
      return
    }
    let live = true

    async function read() {
      try {
        const response = await fetch(AVAILABILITY_ENDPOINT, { credentials: 'same-origin' })
        if (!response.ok) {
          throw new Error(`the availability endpoint answered ${response.status}`)
        }
        const body = (await response.json()) as { any_online: boolean }
        if (live) {
          setAnyOnline(body.any_online === true)
        }
      } catch {
        // Offline is the honest default and the safe one: it promises nothing. The Assistant
        // still answers instantly, which is what the offline line says.
        if (live) {
          setAnyOnline(false)
        }
      }
    }

    void read()
    const timer = window.setInterval(() => void read(), REFRESH_MS)
    return () => {
      live = false
      window.clearInterval(timer)
    }
  }, [open])

  return anyOnline
}
