/**
 * How long ago something happened, for a Strategist reading a queue.
 *
 * A queue card answers one question about time — is this warm? — so it says "3 min ago" rather
 * than a timestamp, and falls back to the date once "ago" stops meaning anything. The times
 * are rendered in the reader's own locale and time zone, because the server sends ISO 8601
 * with an offset and the browser is the only party that knows where the Strategist is.
 */

const MINUTE = 60_000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

export function relativeTime(iso: string | null, now: number = Date.now()): string {
  if (!iso) {
    return '—'
  }
  const at = new Date(iso)
  const elapsed = now - at.getTime()
  if (Number.isNaN(at.getTime())) {
    return '—'
  }
  if (elapsed < MINUTE) {
    return 'Just now'
  }
  if (elapsed < HOUR) {
    return `${Math.floor(elapsed / MINUTE)} min ago`
  }
  if (elapsed < DAY) {
    return `Today, ${at.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}`
  }
  if (elapsed < 2 * DAY) {
    return 'Yesterday'
  }
  return at.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}
