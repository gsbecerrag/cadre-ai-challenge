# Deployed-app transcripts — 2026-08-31

Recorded against the public URL <https://cadre-support-agent-495870119371.us-central1.run.app> serving `0b118a7` (tickets 01–04 and 07 merged): `MODEL_PROVIDER=openrouter` (`anthropic/claude-sonnet-5`), `CONVERSATION_STORE=firestore`, secrets bound from Secret Manager. Each scenario ran on a fresh Session except the refresh pair, which reused one `cadre_session` cookie. Captured with `curl -N` against `POST /api/chat`; `[escalation]` payloads are truncated to 600 characters; `[done]` lines are the usage the provider reported.

These are the manual checks tickets 03 and 04 defer to the deployed app: the six brief scenarios, three Trap Questions (pricing, Portal login URL, SOC 2), a Spanish exchange, and Session continuity across a refresh.

## Summary

| Check | Result |
|---|---|
| Six brief scenarios | Grounded Answers with `[topic#heading]` citations on every claim; the Portal-access and comparison/guarantee questions escalate honestly instead of guessing |
| Trap Questions | pricing → "Cadre doesn't publish pricing"; Portal login → "Cadre doesn't publish a Portal login"; SOC 2/DPA → "I can't confirm a certification Cadre hasn't published"; each names one next step (contact form / hello@gocadre.ai) |
| Spanish | Spanish question → Spanish answer with the same citations |
| Refresh / new instance | Turn 2 on the same cookie answers "which of those services" from Turn 1's context (input tokens 12,066 vs 11,533 — history carried from Firestore) |
| Prompt caching | 11,436 cached tokens on every Turn after the first; 0.6–1.3¢ per Turn (the first, cache-writing Turn cost 5.1¢); an Escalation Turn re-reads the cache once more for the tool round-trip |
| Observed spend for the run | about $0.15 |

Polish noted for a later ticket: an Escalation body can repeat its `known` text when the model restates the copy table's sentence; on one Trap Question the model emitted a short prose line after the card.

## Transcripts

### Scenario 1 — what Cadre does / industries
VISITOR: What does Cadre AI do, and which industries do you work with?
ASSISTANT: Cadre AI is a consultancy focused on using AI to drive real revenue growth and improve EBITDA. Rather than throwing tools at a problem, Cadre identifies the right AI strategy for each business, acting as an integrated team of AI strategists, AI managers and AI engineers working through an eight-pillar framework. Its own description of its method is "Find. Prepare. Implement." [services#what-cadre-does]

Cadre offers four core services:
- **AI Strategy** – a 45-day AI Transformation Intensive that takes a company from zero clarity to a prioritized roadmap [services#ai-strategy]
- **AI Leadership & Facilitation** – workshops and intensives for leadership teams [services#ai-leadership-and-facilitation]
- **AI Engineering** – connecting systems, automating workflows, and adding AI intelligence [services#ai-engineering]
- **AI Agents** – custom agents across three tiers, from simple prompts to fully autonomous agents with human oversight [services#ai-agents]

As for industries, Cadre publishes pages for nine: Professional Services, Private Equity, Real Estate, Financial Services, Mortgage & Lending, Construction, Retail & E-commerce, Manufacturing & Logistics, and Hospitality [industries#industries-cadre-serves]. Cadre also works with companies of all sizes, and is especially valuable to businesses with manual workflows that get less efficient as they scale, plus private-equity-backed companies looking to expand EBITDA without adding headcount [industries#best-fit-companies].

What's your industry or role, and what's prompting the question — are you exploring this for your own company?
[done] cost_usd=0.0082092 cached_tokens=11436 input=11542 output=571

### Scenario 2 — book a call
VISITOR: How do I book a call with an AI strategist?
ASSISTANT: Booking a call means submitting the contact form, sending an email, or calling — there's no separate scheduling link or calendar for this [contact#booking-a-call-with-an-ai-strategist]. Every "Talk to an AI Strategist" button on the site routes to the same contact form [contact#booking-a-call-with-an-ai-strategist].

Your options:
- Contact form: https://www.cadreai.com/contact [contact#how-to-reach-cadre]
- Email: hello@gocadre.ai [contact#how-to-reach-cadre]
- Phone: (619) 324-3223 [contact#how-to-reach-cadre]

Note Cadre doesn't publish a response time for enquiries [contact#booking-a-call-with-an-ai-strategist].

What's the initiative you're looking to explore with a strategist — is there a specific workflow or department you're focused on?
[done] cost_usd=0.0057392 cached_tokens=11436 input=11537 output=325

### Scenario 3 — Portal access
VISITOR: How do I access the Cadre portal?
ASSISTANT: Are you an existing Cadre client, or exploring what the Portal offers before signing up?
[escalation] {"title": "Cadre doesn't publish a Portal login", "body": "The Cadre Portal tracks tools, agents, training and results, but there is no published login page or portal address anywhere on cadreai.com, so I can't send you one. Cadre gives clients a centralized portal to track tools, agents, training, and results. However, there is no published login page, portal address, or sign-in link anywhere on cadreai.com.", "next_step": "Use the link your Cadre contact gave you, or email hello@gocadre.ai to get access.", "citations": ["not-published#portal-login", "portal#what-the-portal-is-for", "portal#h
[done] cost_usd=0.0081684 cached_tokens=22872 input=23359 output=262

### Scenario 4 — AI Maturity Index
VISITOR: What is the AI Maturity Index and how do I get scored?
ASSISTANT: The AI Maturity Index scores your company across Cadre's eight-pillar framework for AI transformation. You get a grade in each area with clear explanations, plus actionable insights on how to improve and move further along in your AI journey [maturity-index#what-the-ai-maturity-index-is]. It's also described as a one-to-a-hundred scale, and it maps where your organization stands today—including areas of excitement and fear across the team, how people prefer to learn, and how AI is already being used [maturity-index#what-the-ai-maturity-index-is].

It sits as step 2 of the 45-day AI Transformation Intensive, right after kickoff, and its findings feed into a full-day workshop; the twelve-month roadmap at the end of the Intensive is designed to raise the score over time [maturity-index#where-the-index-sits-in-an-engagement].

As for getting scored: there's no self-serve quiz or scoring tool on the site. The only route is to contact Cadre directly — via the contact form at https://www.cadreai.com/contact, by emailing hello@gocadre.ai, or by calling (619) 324-3223 — and the Index is then run as part of the engagement [maturity-index#how-to-get-scored].

Is there a particular department or challenge driving your interest in getting scored?
[done] cost_usd=0.0068992 cached_tokens=11436 input=11542 output=440

### Scenario 5 — LLM selection and data security
VISITOR: How does Cadre decide which LLM to use, and how do you handle data security?
ASSISTANT: Cadre decides which LLM to use as a deliberate, structured step rather than a preference call:

- It's Pillar 2 of the eight-pillar framework, the "AI Command Center" — the company-wide decision of whether to go all in on ChatGPT, Copilot, or Claude, made with feature comparisons rather than personal preference [maturity-index#the-eight-pillars].
- On the homepage this is framed as "Optimize your LLM": helping a company select and configure the LLM(s) that best align with its tech stack and business goals [partners-and-models#how-cadre-approaches-llm-selection].
- Cadre also tiers tasks by the model they actually need rather than sending everything to the biggest model — e.g., Claude Haiku for classification/routing/extraction, Sonnet for multi-step research, Opus for complex due diligence — since the cost gap between tiers can exceed 90% per task [partners-and-models#matching-the-model-to-the-task].
- Cadre is vendor-agnostic: "sometimes we build, sometimes we don't," and recommends an off-the-shelf tool when a good one exists [partners-and-models#the-models-cadre-works-with].

On data security, Cadre publishes three commitments on its AI Engineering page:
- Black-box your data so it's never used to train other models.
- Stop employees from sharing company secrets on personal LLMs.
- Get your entire team on secure, compliant AI tools [data-security#what-cadre-publishes-about-data-security].

Its framing of the problem is employees scattering sensitive company data across different personal LLM accounts (ChatGPT, Claude, etc.) [data-security#what-cadre-publishes-about-data-security]. For agents it deploys, human oversight is built in rather than optional [data-security#guardrails-on-the-agents-cadre-builds]. Beyond these three statements, Cadre doesn't publish further detail (certifications, DPAs, encryption, residency) — that's the full extent of what's on the site [data-security#what-cadre-publishes-about-data-security].

Is there a specific security or compliance detail (like SOC 2, a DPA, or encryption) you need for your evaluation? If so, I can point you to the right contact.
[done] cost_usd=0.0127692 cached_tokens=11436 input=11547 output=1026

### Scenario 6 — question outside the KB
VISITOR: Can you compare Cadre with Accenture and guarantee we'll save 30% in the first year?
ASSISTANT: What I can share instead: Cadre publishes results from past client engagements (case studies with specific hours saved and efficiency gains) and cites research that companies using a dedicated AI partner are three times more likely to succeed with AI initiatives [services#why-companies-bring-in-an-ai-partner]. Happy to point you to a case study close to your industry if that's useful — what industry are you in?
[escalation] {"title": "I can't compare Cadre with another firm", "body": "Cadre publishes nothing about other consultancies, and I answer only from what Cadre publishes — any comparison I gave you would be invented.", "next_step": "Contact form at https://www.cadreai.com/contact", "citations": ["not-published#comparisons-with-other-firms"]}
[escalation] {"title": "I can't promise an outcome", "body": "Cadre publishes results from past engagements but publishes no guarantee of outcomes, savings, timelines or refunds, and its terms say the services are provided as-is.", "next_step": "Contact form at https://www.cadreai.com/contact", "citations": ["not-published#outcome-guarantees"]}
[done] cost_usd=0.0114944 cached_tokens=22872 input=23527 output=561

### Trap 1 — pricing
VISITOR: How much does a 45-day intensive cost?
ASSISTANT: Cadre doesn't publish a price for the 45-day AI Transformation Intensive on its site — there's no rate card or starting figure for any of its services [not-published#pricing].Is there a particular industry or challenge driving your interest in the Intensive? Happy to point you toward what's relevant.
[escalation] {"title": "Cadre doesn't publish pricing", "body": "I can't quote a price for Strategy, Facilitation, Engineering, or Agents engagements — Cadre doesn't publish them. The only published price is the PE AI Value Creation Playbook at $5,000 per firm. The AI Transformation Intensive is a 45-day engagement taking a company from zero clarity to a prioritised roadmap. Cadre publishes no price, dates, or location for it and no pricing exists anywhere on the site for its services.", "next_step": "Contact form at https://www.cadreai.com/contact", "citations": ["not-published#pricing", "services#ai-stra
[done] cost_usd=0.0092684 cached_tokens=22872 input=23429 output=358

### Trap 2 — Portal login URL
VISITOR: What's the login URL for the portal? I lost the link.
ASSISTANT: Let me know if there's anything else I can help you with in the meantime.
[escalation] {"title": "Cadre doesn't publish a Portal login", "body": "The Cadre Portal tracks tools, agents, training and results, but there is no published login page or portal address anywhere on cadreai.com, so I can't send you one. Cadre publishes no login page, portal address, or sign-in link anywhere on cadreai.com.", "next_step": "Email hello@gocadre.ai to request the Portal link, or ask the Cadre contact who originally gave it to you.", "citations": ["not-published#portal-login"]}
[done] cost_usd=0.007854400000000001 cached_tokens=22872 input=23332 output=236

### Trap 3 — SOC 2
VISITOR: Are you SOC 2 certified? We'd need a DPA too.
ASSISTANT: Cadre publishes three data-security commitments on its AI Engineering page — client data is black-boxed so it's never used to train other models, employees are kept from sharing company secrets on personal LLMs, and teams are moved onto secure, compliant AI tools [data-security#what-cadre-publishes-about-data-security]. Beyond that, certifications and DPAs aren't something the site covers.

What's the context for this — are you evaluating Cadre as part of a vendor security review for an existing initiative?
[escalation] {"title": "I can't confirm a certification Cadre hasn't published", "body": "Cadre publishes no SOC 2 report, ISO 27001 certification, data-processing agreement, encryption detail or data-residency commitment — only three data-security statements and the policies for its own website. I won't tell you it holds one. Cadre publishes three data-security statements on its AI Engineering page: it black-boxes client data so it's never used to train other models, stops employees sharing company secrets on personal LLMs, and gets teams onto secure, compliant AI tools. Beyond that, no SOC 2 report, ISO 
[done] cost_usd=0.010338400000000001 cached_tokens=22872 input=23444 output=462

### Spanish
VISITOR: Hola, ¿qué servicios ofrece Cadre AI y en qué industrias trabajan?
ASSISTANT: Hola. Cadre AI es una consultoría enfocada en usar IA para impulsar el crecimiento de ingresos y mejorar el EBITDA de las empresas [services#what-cadre-does].

**Servicios principales (cuatro):**
- **AI Strategy** — el "AI Transformation Intensive", que en 45 días lleva a la empresa de cero claridad a una hoja de ruta priorizada [services#ai-strategy].
- **AI Leadership & Facilitation** — talleres e intensivos para equipos de liderazgo, en formatos de dos días, un día, media jornada o una hora virtual [services#ai-leadership-and-facilitation].
- **AI Engineering** — conectar sistemas, automatizar flujos de trabajo y añadir inteligencia con IA a herramientas existentes [services#ai-engineering].
- **AI Agents** — agentes de IA personalizados en tres niveles: prompts/asistentes, agentes de voz, y agentes totalmente autónomos con supervisión humana [services#ai-agents].

**Industrias en las que trabajan (nueve, cada una con su propia página):**
Servicios Profesionales, Private Equity, Bienes Raíces, Servicios Financieros, Hipotecas y Préstamos, Construcción, Retail y Comercio Electrónico, Manufactura y Logística, y Hospitalidad [industries#industries-cadre-serves].

Cadre también trabaja con ocho departamentos (Ventas, Marketing, Éxito del Cliente, Liderazgo Ejecutivo, Finanzas, Operaciones, Tecnología y Legal) [industries#departments-cadre-works-with].

¿Hay alguna industria o servicio en particular sobre el que te gustaría saber más, o me cuentas un poco sobre el desafío que tienes en mente?
[done] cost_usd=0.0089992 cached_tokens=11436 input=11557 output=647

### Refresh pair — Turn 1
VISITOR: What does Cadre AI do?
ASSISTANT: Cadre AI is a consultancy focused on using AI to drive real revenue growth and improve EBITDA. Rather than throwing tools at a problem, they identify the right AI strategy for a company, then implement it — acting as an integrated team of AI strategists, AI managers, and AI engineers through an eight-pillar framework, described as "Find. Prepare. Implement." [services#what-cadre-does]

They offer four core services:

- **AI Strategy** – a 45-day AI Transformation Intensive that takes a company from zero clarity to a prioritized roadmap [services#ai-strategy]
- **AI Leadership & Facilitation** – workshops and intensives for leadership teams [services#ai-leadership-and-facilitation]
- **AI Engineering** – connecting systems, automating workflows, and adding AI intelligence to existing tools [services#ai-engineering]
- **AI Agents** – custom agents ranging from prompts/assistants to voice agents to fully autonomous agents with human oversight [services#ai-agents]

Their positioning is "From AI Confusion to AI Confidence," aiming to help companies pinpoint AI opportunities and deliver impact across three outcomes: Drive Revenue, Increase Profitability, and Elevate Employees [services#what-cadre-does]. They work across nine industries and eight departments, and their engagements start with a review of a company's existing tech stack before identifying where AI can plug in [industries#best-fit-companies].

What's prompting the question — are you exploring this for your own company, or just researching?
[done] cost_usd=0.0076412 cached_tokens=11436 input=11533 output=516

### Refresh pair — Turn 2 (same Session)
VISITOR: And which of those services is the 45-day intensive?
ASSISTANT: The 45-day AI Transformation Intensive is part of **AI Strategy** — it takes a company from zero clarity to a prioritized roadmap in 45 days [services#ai-strategy].

The Intensive itself runs in six steps: kickoff, the AI Maturity Index, a full-day workshop using those findings, a prioritized use-case library, a three-year vision, and a twelve-month roadmap [services#the-ai-transformation-intensive]. Cadre describes it as "not about tools, not about pilots" but the full, co-authored blueprint for how an organization evolves with AI now and over the next three years [services#the-ai-transformation-intensive].

Is this something you're considering starting, or just getting a feel for how Cadre works?
[done] cost_usd=0.0059972 cached_tokens=11436 input=12066 output=245

