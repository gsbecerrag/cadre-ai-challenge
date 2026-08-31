/** One Lead as `/api/console/leads` returns it, and as the Console's queue card renders it. */
export type Lead = {
  session_id: string
  name: string
  email: string
  company: string
  phone: string
  role: string
  signals: Record<string, string>
  present_signals: string[]
  score: number
  qualified: boolean
}

export type Availability = {
  online: boolean
  any_online: boolean
}

/** A 403: the account signed in successfully and is not one of Cadre's (ADR-0010). */
export class NotAllowlisted extends Error {}

type Authorize = () => Promise<string>

async function consoleFetch<T>(path: string, authorize: Authorize, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      ...init?.headers,
      Authorization: `Bearer ${await authorize()}`,
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
    },
  })
  if (response.status === 403) {
    // The API's own words: it names the email and says what to do about it, and the sign-in
    // page shows it verbatim rather than guessing at a friendlier version.
    const body = (await response.json().catch(() => ({}))) as { detail?: string }
    throw new NotAllowlisted(body.detail ?? 'This account is not on Cadre’s Strategist allowlist.')
  }
  if (!response.ok) {
    throw new Error(`${path} answered ${response.status}`)
  }
  return (await response.json()) as T
}

export function fetchLeads(authorize: Authorize): Promise<{ leads: Lead[] }> {
  return consoleFetch('/api/console/leads', authorize)
}

export function fetchAvailability(authorize: Authorize): Promise<Availability> {
  return consoleFetch('/api/console/availability', authorize)
}

export function setAvailability(authorize: Authorize, online: boolean): Promise<Availability> {
  return consoleFetch('/api/console/availability', authorize, {
    method: 'PUT',
    body: JSON.stringify({ online }),
  })
}
