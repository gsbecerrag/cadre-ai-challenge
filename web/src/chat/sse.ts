/**
 * Read the chat endpoint's Server-Sent Events off a `fetch` response body.
 *
 * `EventSource` is the obvious tool and cannot be used: it only issues GETs, and a Turn is a
 * POST with the Visitor's message in the body. So the stream is read by hand — chunks are
 * decoded, split on the blank line that ends a frame, and parsed into the same `ChatEvent`
 * union the server writes.
 */

import type { ChatEvent } from './types'

const FRAME_SEPARATOR = '\n\n'
const EVENT_FIELD = 'event: '
const DATA_FIELD = 'data: '

function parseFrame(frame: string): ChatEvent | null {
  let name = ''
  let data = ''
  for (const line of frame.split('\n')) {
    if (line.startsWith(EVENT_FIELD)) {
      name = line.slice(EVENT_FIELD.length)
    } else if (line.startsWith(DATA_FIELD)) {
      data = line.slice(DATA_FIELD.length)
    }
  }
  if (!name || !data) {
    return null
  }
  // The server is the only writer of this stream and it always writes JSON; a frame that
  // does not parse is dropped rather than allowed to end the Turn.
  try {
    return { event: name, data: JSON.parse(data) } as ChatEvent
  } catch {
    return null
  }
}

export async function* readChatEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<ChatEvent> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  for (;;) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }
    buffer += decoder.decode(value, { stream: true })

    let boundary = buffer.indexOf(FRAME_SEPARATOR)
    while (boundary !== -1) {
      const event = parseFrame(buffer.slice(0, boundary))
      buffer = buffer.slice(boundary + FRAME_SEPARATOR.length)
      if (event) {
        yield event
      }
      boundary = buffer.indexOf(FRAME_SEPARATOR)
    }
  }
}
