/**
 * Lift the `[topic#heading]` markers out of an answer so they render as citation chips.
 *
 * The markers arrive inside the text deltas, one character at a time like everything else, so
 * the parser has to cope with half a marker: a trailing `[servi` is hidden until it resolves,
 * or the Visitor watches raw syntax appear and disappear mid-sentence.
 */

const CITATION = /\[([a-z0-9][a-z0-9-]*#[a-z0-9][a-z0-9-]*)\]/g
const PARTIAL_CITATION = /\[[a-z0-9#-]*$/
const SPACE_BEFORE_PUNCTUATION = / +([.,;:!?)])/g
const REPEATED_SPACES = /[ \t]{2,}/g

export interface CitedText {
  text: string
  citations: string[]
}

export function splitCitations(raw: string): CitedText {
  const citations: string[] = []
  const withoutMarkers = raw.replace(CITATION, (_marker, id: string) => {
    if (!citations.includes(id)) {
      citations.push(id)
    }
    return ''
  })

  const text = withoutMarkers
    .replace(PARTIAL_CITATION, '')
    .replace(REPEATED_SPACES, ' ')
    .replace(SPACE_BEFORE_PUNCTUATION, '$1')
    .trimEnd()

  return { text, citations }
}
