/**
 * One row of the transcript. Kinds, radii, colours and copy follow the design artboard
 * (docs/design/DESIGN-BRIEF.md §2.5): a Visitor bubble is ink and right-aligned, an Assistant
 * bubble is white and left-aligned, and citation chips sit under the bubble they belong to.
 */

import type { Message } from './types'

function Citations({ ids }: { ids: string[] }) {
  if (ids.length === 0) {
    return null
  }
  return (
    <div className="mt-1.5 flex flex-wrap gap-1.5">
      {ids.map((id) => (
        <span
          key={id}
          className="rounded-[48px] border border-[#e5e5e5] bg-[#f2efe4] px-2.5 py-[3px] font-mono text-[10px] text-[#666]"
        >
          [{id}]
        </span>
      ))}
    </div>
  )
}

export function MessageView({ message }: { message: Message }) {
  const alignment = message.role === 'visitor' ? 'items-end' : 'items-start'

  return (
    <div className={`cadre-msgin flex flex-col ${alignment}`}>
      {message.kind === 'text' && (
        <>
          <div
            className={
              message.role === 'visitor'
                ? 'max-w-[82%] rounded-[16px_16px_4px_16px] bg-[#0c0407] px-[15px] py-[11px] text-[14px] leading-[1.55] whitespace-pre-line text-white'
                : 'max-w-[82%] rounded-[16px_16px_16px_4px] border border-[#e5e5e5] bg-white px-[15px] py-[11px] text-[14px] leading-[1.55] whitespace-pre-line text-[#333]'
            }
          >
            {message.text}
          </div>
          <Citations ids={message.citations} />
        </>
      )}

      {message.kind === 'typing' && (
        <div
          aria-label="The Assistant is typing"
          className="flex gap-[5px] rounded-[16px_16px_16px_4px] border border-[#e5e5e5] bg-white px-4 py-3.5"
        >
          <span className="cadre-tdot size-1.5 rounded-full bg-[#999]" />
          <span className="cadre-tdot size-1.5 rounded-full bg-[#999] [animation-delay:0.15s]" />
          <span className="cadre-tdot size-1.5 rounded-full bg-[#999] [animation-delay:0.3s]" />
        </div>
      )}

      {message.kind === 'escalation' && (
        <div className="max-w-[88%] rounded-[6px_16px_16px_6px] border border-[#e5e5e5] border-l-[3px] border-l-[#db4545] bg-white px-4 py-3.5 text-[13.5px] leading-[1.55]">
          <div className="mb-1.5 font-semibold text-[#0c0407]">{message.title}</div>
          <div className="mb-2 whitespace-pre-line text-[#4c4c4c]">{message.body}</div>
          <div className="rounded-[10px] bg-[#faf9f6] px-3 py-2.5 text-[12.5px] text-[#666]">
            <b className="text-[#0c0407]">Next step:</b> {message.nextStep}
          </div>
          <Citations ids={message.citations} />
        </div>
      )}

      {message.kind === 'error' && (
        <div
          role="alert"
          className="max-w-[88%] rounded-[16px_16px_16px_4px] border border-[#e5e5e5] bg-[#fdeaea] px-[15px] py-[11px] text-[13.5px] leading-[1.55] text-[#4c4c4c]"
        >
          {message.text}
        </div>
      )}
    </div>
  )
}
