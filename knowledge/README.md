# Knowledge Base

Markdown topics with stable heading ids, compiled into the Assistant's cached system prompt
(ADR-0001). The Assistant may state only what a KB Section here states, and must cite the
section it came from.

- One file per topic. The **file stem is the topic name** in a citation, so renaming a file
  changes every id in it.
- **Every heading is a KB Section**, addressed as `topic#heading-slug` (the slug is the
  kebab-case of the heading text). Renaming a heading changes its id and breaks citations
  already written into evals and Traces — rename deliberately.
- Facts come from `docs/research/cadreai-site-facts.md`. What Cadre does *not* publish is a
  first-class topic, because the Assistant has to escalate rather than invent (ticket 04).

Topics so far: `services`, `industries`, `contact`. The rest arrive with ticket 04.
