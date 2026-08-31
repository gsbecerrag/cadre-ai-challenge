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

/** The states a Handover Request may be in, mirroring `core/handover.py`. */
export type HandoverState =
  | 'offered'
  | 'accepted_by_user'
  | 'pending_strategist'
  | 'strategist_joined'
  | 'in_call'
  | 'ended'
  | 'declined'
  | 'no_strategist_available'

export type HandoverMode = 'video' | 'callback'

/**
 * One Handover Request as the queue card and the Callbacks row need it.
 *
 * The Lead travels as the snapshot taken when the Hand-over was offered, in the same shape as
 * a Lead from `/api/console/leads` — so the Console has one Lead type and the queue is one
 * read per screen rather than a join across two collections for every row.
 */
export type Handover = {
  request_id: string
  session_id: string
  state: HandoverState
  mode: HandoverMode | null
  prompt: string
  created_at: string | null
  trace_id: string | null
  lead: Lead
  /** The Daily room, once the Visitor has accepted in `video` mode. Empty otherwise. */
  room_url: string
  /** Who claimed the request, once somebody has. Empty otherwise. */
  strategist_name: string
}

/** One line of "Conversation so far" in the request detail. */
export type ConversationLine = {
  role: string
  text: string
}

export type HandoverDetail = {
  handover: Handover
  /** The Lead as it stands now — Contact Details keep arriving after the offer. */
  lead: Lead
  conversation: ConversationLine[]
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

export function fetchHandovers(
  authorize: Authorize,
  mode?: HandoverMode,
): Promise<{ handovers: Handover[] }> {
  const query = mode ? `?mode=${mode}` : ''
  return consoleFetch(`/api/console/handovers${query}`, authorize)
}

export function fetchHandover(authorize: Authorize, requestId: string): Promise<HandoverDetail> {
  return consoleFetch(`/api/console/handovers/${encodeURIComponent(requestId)}`, authorize)
}

/**
 * "Claim & join call": the Strategist takes the request and enters the room.
 *
 * One call for both hops the server makes (`strategist_joined` then `in_call`), because it is
 * one button — and the server is the one that decides whether the move is allowed at all: an
 * out-of-order claim comes back 409, whatever this page believed about the state.
 */
export function joinHandover(authorize: Authorize, requestId: string): Promise<Handover> {
  return consoleFetch(`/api/console/handovers/${encodeURIComponent(requestId)}/join`, authorize, {
    method: 'POST',
  })
}

/** "End call": the Hand-over is over, for both sides. */
export function endHandover(authorize: Authorize, requestId: string): Promise<Handover> {
  return consoleFetch(`/api/console/handovers/${encodeURIComponent(requestId)}/end`, authorize, {
    method: 'POST',
  })
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
