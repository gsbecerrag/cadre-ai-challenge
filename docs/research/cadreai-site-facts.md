# cadreai.com — verified site facts for the support-bot knowledge base

Gathered 2026-08-30 via plain HTTPS fetches (curl + WebFetch). Everything below is what the pages actually say; items marked NOT FOUND were searched for across all 33 non-article pages in the sitemap and did not appear.

## 0. Crawl summary

- `robots.txt`: `User-agent: * / Disallow:` (nothing blocked). `Sitemap: https://www.cadreai.com/sitemap.xml`
- `sitemap.xml`: 111 URLs — 27 site/legal pages, 27 articles, 26 podcast episodes, 8 author pages, 9 industry pages, 8 department pages, 3 event pages, 1 hiring assessment.
- All 33 non-article pages returned HTTP 200 to plain curl with full text content (homepage: 130 KB HTML, ~22 KB of visible text). No JS rendering needed.
- Legal entity: **AI Gurus LLC dba Cadre AI**. Office: **3580 Carmel Mountain Rd, #150, San Diego, CA 92130**. Support email: **hello@gocadre.ai**. Phone: **(619) 324-3223**. Privacy email: **privacy@gocadre.ai**. (Note the email domain is gocadre.ai, not cadreai.com.)

## 1. Site map (URL -> what it is)

### Core / services
| URL | Description |
|---|---|
| `/` | Home. Hero "From AI Confusion to AI Confidence." Services, partners, FAQ, "Track your AI results" portal blurb. |
| `/strategy` | AI Strategy. "The AI Transformation Intensive: From Idea to Execution in 45 Days"; the 8 Pillars of AI Transformation. |
| `/leadership-facilitation` | AI Leadership & Facilitation. Workshops/intensives (2-day, 1-day, half-day, 1-hr virtual). |
| `/ai-engineering` | AI Engineering. Automation, integrations, custom agents; the only page with data-security wording. |
| `/agents` | AI Agents. Filterable catalog of named agents (Prompts & Assistants / Voice Agents / Fully Fledged Agents). |
| `/ai-transformation-intensive` | The 45-day Intensive: 6-step process incl. the AI Maturity Index. |
| `/industries` | Index of 9 industry pages. |
| `/industries/{professional-services, private-equity, real-estate, financial-services, mortgage-lending, construction, retail-e-commerce, manufacturing-logistics, hospitality}` | Per-industry pages: headline, 10 named agents each, video transcript, testimonials. |
| `/departments` | Index of 8 department pages. |
| `/departments/{sales, marketing, customer-success, executive-leadership, finance, operations, technology, legal}` | Per-department agent catalogs. |
| `/case-studies` | 8 anonymized case studies with quantified results (single page, no sub-pages). |
| `/about` | Company description, "The Cadre Way" values, 8 leadership bios, stats. |
| `/contact` | Contact form (Name/Email/Subject/Message), office address, hello@gocadre.ai, phone. No calendar embed. |
| `/careers` | Culture page; says "See below to learn more about available positions" but lists no roles and no apply link. |
| `/careers/assessments/fde-assessment` | Forward Deployed Engineer take-home case (Meridian Logistics). Marked "Confidential Candidate Materials". Submit to moriah.davis@gocadre.ai. |
| `/next-generation-education` | "The Ultimate Career Edge" — AI program for high-school/college students. Not in nav. All CTAs -> /contact. |

### Content
| URL | Description |
|---|---|
| `/articles` | Blog index (27 articles). |
| `/articles/ai-model-selection` | "AI Model Selection: Matching Cost and Quality to Each Task" (Ben Shapiro, May 29 2026). |
| `/articles/cadre-ai-selected-as-an-official-openai-service-partner` | OpenAI Service Partner announcement (Riley Stricklin, Jan 5 2026). |
| `/articles/ai-readiness-starts-with-your-data-not-the-model` | Data-readiness article (Grayson Lafrenz). |
| `/articles/...` (24 more) | See sitemap; topics: AI readiness, roadmap-first strategy, why in-house AI hiring fails, voice agents, process mapping, notetakers, prospecting, ROI formula. |
| `/ai-2030-podcast` | "AI 2030 Podcast" — "Conversations about the future of AI, with the builders building it." 17 episodes. Hosts referenced: Keith, Chad. |
| `/2030-podcast` | "2030 Podcast" — host Keith Jensen; "strategies top executives are using to future-proof their business." 8 episodes. |
| `/podcasts/{slug}` (26) | Individual episodes (Canva, ClickUp, TZP Group, True Ventures, Slow Ventures, Vectara, Kognitos, Koah Labs, etc.). |
| `/authors` and `/authors/{8 names}` | Author bio pages for the 8 leaders. |
| `/events` | Events index (2 upcoming, 1 past). |
| `/events/the-executive-ai-conversation` | Invite-only San Diego exec event at Mintz. Register: `https://luma.com/event/evt-BHnk7jFvutW5rMU` |
| `/events/ai-leadership-workshop` | Workshop at C3 Bank, Encinitas CA. Register: `https://luma.com/event/evt-gH9jbC7J6ehZfV9` |
| `/events/pe-ai-value-creation-playbook` | 3-session virtual PE program, **$5,000 per Firm**. Register: `https://events.zoom.us/e/view/hp4SviCkS_C_l2RXoEZv4g` |
| `/eventsold` | Legacy events page (linked from nav as "Events"). |

### Legal
| URL | Description |
|---|---|
| `/terms-of-service` | ToS, "Last updated: June 15, 2026". Entity "Cadre AI (Also known as AI Gurus LLC)". California law; arbitration in San Diego. |
| `/legal/privacy-policy` | Updated 06/25/2026. privacy@gocadre.ai. Retention "2 years". |
| `/legal/privacy-rights` | Privacy rights page. |
| `/legal/cookie-policy` | Cookie policy; defers vendor list to Cookie Declaration. |
| `/legal/cookie-declaration` | Auto-generated by Consent Pro; the inventory table is JS-injected (not in static HTML). |
| `/scroller-test-page` | Test page in sitemap (not fetched; ignore). |

### External links found anywhere on the site
- Social: `https://www.linkedin.com/company/cadre-ai-services`, `https://www.instagram.com/cadre.ai/`, `https://www.youtube.com/@CadreAI`, `https://x.com/cadreai`
- Leader LinkedIn profiles on /about
- Event registration: the two Luma links and one Zoom Events link above
- One PDF citation: `https://mlq.ai/media/quarterly_decks/v0.1_State_of_AI_in_Business_2025_Report.pdf` (MIT "State of AI in Business 2025" report — source of the "90% of AI initiatives fail" stat)

## 2. Page-by-page facts

### Homepage — `https://www.cadreai.com/`
- `<title>`: "Cadre AI | AI Strategy & Implementation for Business Growth & EBITDA Improvement". Meta description: "Turn AI from buzzword to bottom-line growth. We deliver AI strategy, workflow automation, and training that drive measurable EBITDA impact."
- Hero: "From AI Confusion to AI Confidence." / "We help you pinpoint the right AI opportunities, implement them seamlessly, and deliver real business impact." Badge above hero: "Cadre AI — Anthropic & OpenAI Partner" (links to the OpenAI partner article).
- Positioning (video transcript): "We act as your integrated AI team. From AI strategists to AI managers and AI engineers, all utilizing an eight pillar framework..." Warns about "Some employees using ChatGPT, others using Claude, and no doubt putting sensitive company information into them."
- "Partnering with the best" logo row: Meta, OpenAI, Snowflake, Salesforce, Microsoft, AWS.
- Three outcomes: Drive Revenue / Increase Profitability / Elevate Employees.
- "Set your team up to succeed with AI": Find the highest impact ("department by department"), **Optimize your LLM** ("Help you select and configure the LLM(s) that best align with your tech stack and business goals"), Shift the culture.
- Framework: "Find. Prepare. Implement."
- LLM logo row ("Supercharge your tech stack with AI"): Google Gemini, Kimi, Claude, Qwen, OpenAI, OpenRouter, Grok, Deepseek, Meta AI, Mistral, Copilot, Perplexity.
- Testimonials: Fred Crosetto (iSupport, Founder & Chairman) — Copilot training; Evelise Rodriguez Simon (Avanti Capital Partners, Managing Partner) — legal-document AI tool "saved literally hundreds of thousands of dollars"; TZP Group portfolio exec — from zero AI licenses to daily use.
- **FAQ (verbatim, use as canonical answers):**
  - *How will the AI Maturity Index help me?* "It scores your company across our eight-pillar framework for AI transformation. You'll get a grade in each area with clear explanations, plus actionable insights on how to improve and move further along in your AI journey."
  - *What does Cadre AI actually do?* "We're a consultancy focused on using AI to drive real revenue growth and improve EBITDA. Many companies get less efficient as they scale. We help you scale with less overhead by identifying the right AI strategy, not just throwing tools at the problem."
  - *What kind of tools does Cadre AI build?* "Sometimes we build, sometimes we don't. If a tool you already use has AI features available, we help you activate and use them quickly. When off-the-shelf tools exist, we'll recommend the best fit. We only build custom solutions when there's no faster or smarter option."
  - *Why not just do AI in-house?* "According to MIT, over 90% of AI initiatives fail... Companies that bring in a dedicated AI partner are three times more likely to succeed. Cadre gives you that partner."
  - *Can you work with our current tools and systems?* "Yes. We start with a deep review of your current tech stack and processes. Then we identify where AI can plug in, whether it's simple workflow automation or agents that connect multiple tools together for fully automated execution."
  - *What types of companies are the best fit?* "We work with companies of all sizes, but we're especially valuable to businesses with manual workflows that get less efficient as they grow. B2B and B2C services companies often fit this profile. We also support private equity backed companies looking to grow efficiently and expand EBITDA without ballooning headcount."
- **Portal blurb (verbatim, appears in the footer CTA of every page):** "Track your AI results — Cadre gives you a centralized portal to track tools, agents, training, and results. Stay aligned, stay accountable, and scale what works." Button "Get Your AI Results" -> **`/contact`**.
- Every "Talk to an AI Strategist" button -> `/contact`. Nav item "Get Your AI Maturity Index — Discover how your business can improve" -> `/contact`.

### AI Strategy — `https://www.cadreai.com/strategy`
- Headline: "The AI Transformation Intensive: From Idea to Execution in 45 Days"; "zero clarity to a prioritized roadmap" in 45 days.
- 4-step engagement model: Discover Use Cases -> Survey the Landscape -> Implement Solutions -> Scale with Confidence (expand departments, establish champions, 3-year roadmap).
- **The 8 Pillars of AI Transformation** (exact headings): 1 Build your dedicated AI team; 2 Deploy your AI Command Center; 3 Create an AI-First Culture Shift; 4 Connect & Enable your Tech Stack; 5 AI-Healthy Data Assessment; 6 Build your Framework for AI Agent Readiness; 7 Departmental AI Deep Dives; 8 Find your 3-Year AI Vision.
- Pillar 2 ("AI command center") is the company-wide LLM decision: "deciding if you're gonna go all in on ChatGPT, on Copilot, on Claude." Pillar 3 "starts with an AI policy." Pillar 4 covers API access to the tech stack and unpacking built-in AI features (e.g., Salesforce).
- Section "Choose the Right LLM for Your Business" exists on this page.
- Departmental deep dives "assess each team's people, processes, and technology."
- CTAs: "Talk to an AI Strategist" -> /contact; "See How the Intensive Works" -> /ai-transformation-intensive; "Get started" -> /contact.
- Industries listed: Professional Services, Private Equity, Real Estate, Financial Services, Mortgage & Lending, Construction, Retail & E-commerce, Manufacturing & Logistics, Hospitality. No pricing.

### AI Transformation Intensive — `https://www.cadreai.com/ai-transformation-intensive`
- "It's not about tools. It's not about pilots. It's the full, co-authored blueprint for how your organization will evolve with AI now and over the next 3 years." Duration 45 days.
- Six steps: 1 Kickoff; **2 AI Maturity Index** ("map where your organization stands today on its AI journey... areas of excitement and fear across your team, their preferred learning [styles]... how AI is currently being used"); 3 Full-Day Workshop (uses Maturity Index findings); 4 Use Case Library (prioritized: immediate / future / not prioritized); 5 Three-Year Vision; 6 Twelve-Month Roadmap ("designed to systematically increase your organization's AI Maturity Index score").
- No price, dates, or location. CTA "Start your AI Transformation today" -> /contact.

### AI Maturity Index — NO dedicated page/quiz
- Mentioned on: home/contact FAQ (eight-pillar scoring, grade per area), /ai-transformation-intensive (step 2 of the Intensive), /industries/private-equity transcript ("an AI maturity index, a one to one hundred scale to see where they are in the path of AI maturity"), /events/pe-ai-value-creation-playbook ("PE Portfolio AI Maturity Index for portfolio-wide assessment" included with the $5,000 program).
- **How to get scored:** the only path on the site is the "Get Your AI Maturity Index" nav link -> `/contact` form. There is no self-serve quiz, form, or scoring tool.

### AI Leadership & Facilitation — `https://www.cadreai.com/leadership-facilitation`
- Headline: "Human Empowerment + Technical Expertise = Reliable AI Transformation".
- Formats: 2-Day Leadership Intensive; 1-Day Workshop; Half-Day Executive Session; 1-Hour Virtual Kickoff.
- Structure: 30% Teaching / 30% Interaction / 40% Application ("Work on Your Real Business Challenges"). Teaching includes "Understand the Eight Pillars Framework, how to spot AI-ready use cases, and how to message AI adoption to teams who are skeptical or scared."
- Outcomes: Spot AI-Ready Use Cases, Address Fear & Uncertainty, Build Alignment, Leave with Actionable Plans. "facilitation backed by behavioral science."
- CTAs: "Schedule Executive Facilitation" -> /contact. No pricing.

### AI Engineering — `https://www.cadreai.com/ai-engineering`
- Headline: "Connect your systems, automate your workflows, and multiply your impact".
- Offerings: Automate the Repetitive Work; Connect Disconnected Systems; Add AI Intelligence; Deploy Custom AI Agents.
- Process: Understand the Problem -> Pick the Right Approach (research tools / automate workflows / build custom agents) -> Integrate & Automate ("Connect APIs across your tech stack").
- **Data-security statements (the only explicit ones on the site):** "Black-box your data so it's never used to train other models"; "Stop employees from sharing company secrets on personal LLMs"; "Get your entire team on secure, compliant AI tools".
- LLM logos: Google Gemini, Claude, OpenAI, Qwen, DeepSeek, Kimi, Mistral, Grok, Meta AI, Perplexity, Microsoft Copilot, OpenRouter. N8N referenced in image alt text.
- No pricing.

### AI Agents — `https://www.cadreai.com/agents`
- Headline: "Custom AI Agents for Every Team & Workflow". Three tiers: Prompts & Assistants; Voice Agents ("intake, qualification, support, and internal routing"); Fully Fledged AI Agents ("plan, take actions across tools, and run end to end processes" with "guardrails and human oversight").
- Filterable catalog (18 per page). Named examples: Change Order Tracker, Quote Approval Router, Team Check-in Facilitator, Training Module Builder, Escalation Decision Advisor, Slack IT Supporter, Sales Objection Coach, Investment Committee Prep, Automated Takeoff Generator, Invoice Query Resolver, Delegation Advisor, Project Docs.
- CTAs: "Get Your AI Results" -> /contact; "Get Your AI Maturity Index" -> /contact. No pricing.

### Contact — `https://www.cadreai.com/contact`
- Headline "Contact us" / "As your partner in AI Strategy & Implementation, we're here for you."
- Form fields: Full Name*, Email*, Subject* (placeholder "How can we help?"), Message*. Webflow form `wf-form-Contact-Form` with Cloudflare Turnstile; a HubSpot form embed is also present (portal 48297872, form b3f89597-66de-48df-9984-03dc3b1cdda1, region na1). Success text: "Thank you! Your submission has been received!"
- Office Location: 3580 Carmel Mountain Rd, #150 San Diego CA, 92130. Support: hello@gocadre.ai, (619) 324-3223.
- **No booking calendar** (no Calendly / HubSpot Meetings / cal.com / SavvyCal) anywhere on the site. "Book a call" = submit this form, email, or phone. No response-time promise stated.

### About — `https://www.cadreai.com/about`
- "The Cadre Way" values: Growth Mindset, Extreme Ownership, Team First, Scrappy.
- Leadership: Grayson Lafrenz (Founder/CEO); Keith Jensen (President); Riley Stricklin (Founder, Chief Strategy Officer); Nicole Kelley (CFO); Sarah McLoughlin (Chief Client Officer); Chad Lohrli (Founder, Chief AI Officer); Katie Boes (VP, Client Strategy and Partnerships); Ben Shapiro (Co-Founder, Head of AI Strategy).
- Stats: "100+ high-ROI use cases delivered across 50+ companies"; "3x higher success rate with strategic AI partner"; specialized vendors "300% higher" success than in-house.
- NOT stated: founding year, team size, HQ (address only on /contact).

### Case Studies — `https://www.cadreai.com/case-studies`
All clients are "Non-Disclosed Company". Eight studies:
1. Lead Processing Agent (Professional Services): 45 hrs/month saved; 1,500+ emails, 650+ leads/month across 5 branches.
2. Supplier Automation (Manufacturing & Logistics; Zendesk + NetSuite): 220 hrs/month saved; 60% faster; 90% accuracy.
3. Proposal Automation (Manufacturing & Logistics): 8,000+ hrs/yr saved; 20–30 proposals/week; 1–2 days -> 20 minutes.
4. AI-Powered Housing Visibility System (Hospitality): $420,000 saved annually (was $35,000/month in expedited cleaning fees).
5. AI Scheduling System (Real Estate): +57% daily efficiency; +50% field capacity; -72% fuel; +$136,000 revenue per field specialist.
6. Email Agent Automation (Manufacturing & Logistics): 3,500 hrs/yr; 4,000+ emails/month across 55 sales reps; 9 hrs -> ~55 min/week.
7. Loan Intelligence Assistant "LIA" (Financial Services / Mortgage & Lending): 2,500 hrs/yr; 1–2 days -> <15 min; 27 loan officers; 3,960+ chats in first 90 days.
8. AI Voice and Chat Agents (Professional Services): 1,500 hrs/yr; 500–700 appointment requests/month automated.

### Industries — `https://www.cadreai.com/industries`
- Nine industries with one-liners: Professional Services ("Transform billable hours into scalable profit..."), Private Equity ("Accelerate deal flow, compress due diligence timelines..."), Real Estate, Financial Services ("Accelerate client onboarding, automate compliance..."), Mortgage & Lending ("automates underwriting, accelerates approvals"), Construction ("automates takeoffs, tracks project health"), Retail & E-commerce, Manufacturing & Logistics, Hospitality.
- Framing: "From hospitality to private equity, we've found the opportunities that actually move the needle and deliver ROI." Note: the site lists **9** industries; the take-home brief lists 7 (omits Mortgage & Lending and Hospitality).

### Private Equity — `https://www.cadreai.com/industries/private-equity` (representative industry page)
- 10 named agents: CIM Analyst, Deal Sourcer, Market Research Analyst, NDA Analyst, Due Diligence Analyst, Predictive Portco Performance, Data Room Analyst, LP/Industry Monitor, Investment Committee Prep, CRM Analyst.
- Transcript describes the engagement: Maturity Index (1–100) -> LLM selection ("show them Copilot, OpenAI, feature comparisons") -> 30-day departmental deep dive -> solutions catalog with time/ROI estimates -> prioritize by revenue/profitability/employee elevation -> implement.
- Stats quoted: 9.1 hrs/week searching for information; 11 hrs/week on email; "Only 12% of companies leveraging data properly"; MIT 2025 "90% of AI implementations failing".

### LLM selection / partner statements
- OpenAI partner article (Jan 5 2026, Riley Stricklin): Cadre is an "Official OpenAI Service Partner" to "help organizations integrate ChatGPT for Business, design CustomGPTs, deploy AI agents, and lead workforce up-skilling programs." CEO quote: "This partnership with OpenAI positions us to help companies go beyond experimentation, driving measurable business results."
- Homepage badge: "Anthropic & OpenAI Partner". Logo rows name Meta, OpenAI, Snowflake, Salesforce, Microsoft, AWS, Google Gemini, Claude, OpenRouter, and others. **Google, AWS, Snowflake, Salesforce appear only as logos — no page describes those partnerships.**
- Model-selection article (Ben Shapiro, May 29 2026, "AI Model Selection: Matching Cost and Quality to Each Task"): tier tasks by model — Claude Haiku (classification/routing, form extraction), Sonnet (multi-step research/synthesis), Opus ("complex due diligence where errors carry significant consequences"); cost gap Haiku->Opus "can exceed 90 percent per task". Policy steps: define task tiers, exception process, usage monitoring, quarterly review.
- Stance: vendor-agnostic; "Sometimes we build, sometimes we don't"; recommend off-the-shelf when it exists.

### Security / privacy / data handling
- Marketing claims: only the three bullets on /ai-engineering (black-box data / not used to train / secure compliant tools) plus "guardrails and human oversight" on /agents.
- Privacy Policy (06/25/2026): AI Gurus LLC dba Cadre AI; collects name, email, phone, IP, cookies, usage, device, geolocation; retention "2 years"; privacy@gocadre.ai.
- ToS (June 15 2026): services "AS-IS and AS-AVAILABLE"; users "solely responsible for all data that you transmit"; California law, San Diego arbitration.
- NOT FOUND anywhere: SOC 2, ISO 27001, GDPR/CCPA commitments, DPA, encryption, data residency, sub-processor list, or any client-data-handling policy for engagements.
- Tracking present: Google Analytics G-2SWW2G2HC2, Consent Pro CMP, RB2B visitor identification, HubSpot forms, Wistia video, Luma checkout embed.

## 3. Things the site does NOT contain (bot must escalate / redirect)

| Topic | Status | Suggested bot behavior |
|---|---|---|
| Pricing for services (Strategy, Facilitation, Engineering, Agents, Intensive) | NOT on site. Only price anywhere: PE Playbook event "$5,000 per Firm — Unlimited Attendees". | Escalate to /contact, hello@gocadre.ai, (619) 324-3223. |
| Booking / calendar link | NONE (no Calendly, HubSpot Meetings, cal.com). | Point to /contact form, email, phone. Event RSVPs: Luma/Zoom links above. |
| Client portal URL / login | NONE. No app.*, /login, /portal, or sign-in link anywhere. Portal is described only in marketing copy; CTA goes to /contact. | Say the portal exists for clients, no public login on the site; direct existing clients to their Cadre contact / hello@gocadre.ai. |
| AI Maturity Index page / self-serve quiz | NONE. Described only (eight pillars, 1–100 score, grade per area). | Explain what it is; getting scored = contact form ("Get Your AI Maturity Index"). |
| Security certifications, DPA, data residency | NONE. | Escalate; quote only the /ai-engineering statements. |
| Founding year, headcount, funding | NOT stated. | Don't guess. |
| Open job listings / how to apply | NONE on /careers (only culture text). | Direct to /careers + /contact. |
| Individual case-study pages, named clients | Single page, all anonymized. | Cite the 8 studies; don't name clients. |
| Partnership details for Google, AWS, Snowflake, Salesforce, Microsoft, Meta | Logos only. | Say "listed as partners"; no details. |
| Upcoming event dates | Two Luma events have no date in HTML (Luma page holds it). PE Playbook dates: Feb 18 / Mar 4 / Mar 18 (year not stated). | Link to the registration URLs. |
| Cookie vendor inventory | JS-injected; not in static HTML. | N/A |

## 4. Brand / design tokens (from the Webflow CSS `cadre-ai-new-brand-site.shared.3cb335fae.min.css` and homepage HTML)

- **Generator:** Webflow (`data-wf-site="6910dd217f94a50bd2e308d3"`, `cdn.prod.website-files.com`, jQuery 3.5.1, GSAP 3.15). Custom scripts: Consent Pro, RB2B, HubSpot forms, Wistia, Luma embed, GA4.
- **Rendering:** fully server-rendered static HTML. Plain `curl` returns complete page text (nav, FAQ, case studies, agent catalogs, video transcripts). Only the cookie-declaration table and the `/agents` filter UI are JS-driven. **No headless browser / Firecrawl needed** — plain fetch + HTML-to-text is sufficient.
- **Theme:** light. Page background "sand" `#faf9f6`, hero gradient `#f2efe4 -> #fff`, footer gradient `#f2efe4 -> #faf9f6`, nav scroll color `#f4f0e6`. Dark colors are used for text, not backgrounds.
- **CSS custom properties (verbatim):**
  - `--cadre-red: #db4545` (h1 color, hover accents) — **primary accent**
  - `--cadre-blue: #08749b` — secondary accent (defined; rarely used in CSS)
  - `--cadre-sand: #faf9f6`, `--cadre-sand-dark: #f2efe4` — backgrounds
  - `--colors--primary-backgroud: #faf9f6` (sic), `--colors--primary-black: #0b0707`, `--colors--black-900: #0c0407`, `--colors--black-800: #333` (h2/h3/body text), `--colors--black-700: #4c4c4c`, `--colors--black-600: #666`, `--colors--black-400: #999`, `--colors--black-300: #b3b3b3`, `--colors--black-200: #ccc`, `--colors--black-100: #e5e5e5`, `--colors--black-50: #f9f9f9`
  - Secondary highlight seen in CSS: `#b9fd3b` (lime, 4 background uses). Footer/newsletter button: `#000` bg, white text, `border-radius: 1.5rem`.
- **Typography:**
  - Headings h1/h2: `Inter Tight` (self-hosted variable TTF on website-files.com), weight 600; h1 4.5rem, letter-spacing -4.32px, color `--cadre-red`; h2 3.75rem, color `#333`.
  - Body/h3/UI: `Inter, Arial, sans-serif` (`--fonts--inter`), weights 400/500/600/700. Google Fonts link (`css2?family=Inter:wght@400;500;600;700`) is only on the FDE assessment page; main site serves Inter via Webflow.
  - `Poppins` self-hosted (secondary/legacy). Icon font "Line Rounded Icons".
- **Logo:** `https://cdn.prod.website-files.com/6910dd217f94a50bd2e308d3/6910e3a5178f856fe5289ae1_Cadre_AI_Logo_Web.svg`
- **Favicon:** `https://cdn.prod.website-files.com/6910dd217f94a50bd2e308d3/6952d8f4962a6a6eed4ffa34_website-favicon%2032x32.png`; webclip `.../6952d571d310b3d7e50b56b3_website-webclip%20256x256.png`
- **OG image:** `https://cdn.prod.website-files.com/6910dd217f94a50bd2e308d3/695dd986c735e0d6f8da06ec_2026-01-07_19-56-14_opengraph-home.jpg`
- **Buttons:** pill-shaped (`border-radius: 48px`/`1.5rem`), dark fill with white arrow icon (`.button_arrow-white`). Cards use `border-radius: 1.875rem` with `1px solid #0000001a` border on sand background.

## 5. Pages not loaded / caveats
- `/scroller-test-page` and the 24 remaining articles / 26 podcast episodes were not fetched individually (sitemap only).
- `/legal/cookie-declaration` vendor table is injected client-side; not captured.
- Luma event pages (dates) were not fetched (external).
- Article dates on the site (e.g., "July 14, 2026") are as published; no adjustment made.
