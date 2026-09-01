/**
 * The Access Code gate (ticket 21), as the widget sees it.
 *
 * `GET /api/access` says whether the deployment has a code at all and whether this browser has
 * already given it; `POST /api/access` gives it. The unlock is a cookie the server sets, so
 * nothing about the code is kept here — the field's value is sent once and forgotten.
 *
 * A link that carries `?code=…` unlocks before anything is shown and then removes the code
 * from the address bar and the history entry, so the review pack's link works with nothing to
 * type and nothing left behind to copy.
 */

import { useCallback, useEffect, useState } from 'react'

export const ACCESS_ENDPOINT = '/api/access'
export const CODE_QUERY_PARAM = 'code'

export type UnlockResult = 'unlocked' | 'rejected' | 'locked' | 'failed'

export interface Access {
  /** The deployment has a code configured. */
  required: boolean
  /** This browser may chat: there is no gate, or the code has been accepted. */
  unlocked: boolean
  /** Give the code. Resolves to what the server made of it. */
  unlock: (code: string) => Promise<UnlockResult>
}

export function useAccess(): Access {
  // Open until told otherwise: a slow first read must not flash a lock at a Visitor who
  // needs none, and the server refuses a Turn on its own if the read was wrong.
  const [required, setRequired] = useState(false)
  const [unlocked, setUnlocked] = useState(true)

  const read = useCallback(async () => {
    try {
      const response = await fetch(ACCESS_ENDPOINT, { credentials: 'same-origin' })
      if (!response.ok) {
        throw new Error(`the access endpoint answered ${response.status}`)
      }
      const body = (await response.json()) as { required: boolean; unlocked: boolean }
      setRequired(body.required === true)
      setUnlocked(body.unlocked === true)
    } catch {
      // Unknown stays open; the composer is the safe default and the server is the gate.
    }
  }, [])

  const unlock = useCallback(async (code: string): Promise<UnlockResult> => {
    try {
      const response = await fetch(ACCESS_ENDPOINT, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ code }),
        credentials: 'same-origin',
      })
      if (response.status === 204) {
        setUnlocked(true)
        return 'unlocked'
      }
      if (response.status === 401) {
        return 'rejected'
      }
      if (response.status === 429) {
        return 'locked'
      }
      return 'failed'
    } catch {
      return 'failed'
    }
  }, [])

  useEffect(() => {
    const url = new URL(window.location.href)
    const code = url.searchParams.get(CODE_QUERY_PARAM)
    if (code) {
      url.searchParams.delete(CODE_QUERY_PARAM)
      window.history.replaceState(null, '', url.toString())
      void unlock(code).then((result) => {
        if (result !== 'unlocked') {
          void read()
        }
      })
      return
    }
    void read()
  }, [read, unlock])

  return { required, unlocked, unlock }
}
