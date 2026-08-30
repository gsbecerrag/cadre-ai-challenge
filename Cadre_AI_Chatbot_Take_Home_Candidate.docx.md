*Cadre AI | Candidate Take-Home Challenge* 

**CADRE AI** 

**AI Engineer & FDE Technical Take-Home** 

Chatbot Challenge | Candidate Guide | v1.0 

*We don't test what you've memorized. We test how fast you can build.* 

Read this guide before starting. It covers exactly what to expect, what to deliver, and how you'll be evaluated. 

cadreai.com 

**Welcome** 

Thanks for taking the time to work through this challenge. We're excited to see what you can build. 

Our engineers build production AI systems every day using Claude Code as their primary development tool. We don't believe LeetCode tells us anything useful about whether you'll thrive in that environment. Instead, we're asking you to do what our team does daily: take a product brief, break it down, make deliberate decisions, build it with AI-augmented tooling, and ship it. 

This guide tells you everything you need to know. There are no trick questions and no gotchas. We want you to perform at your best. 

**Challenge Format** 

This is an async take-home challenge followed by a 1-hour live review with your interviewer.

| Phase  | What Happens |
| :---- | :---- |
| **The Build**  | Complete the challenge on your own time before your scheduled review. We recommend budgeting 4–6 hours. Build, deploy, and push to GitHub. |
| **The Review**  | A 1-hour live conversation. You'll demo your deployed app, walk through your architecture and decisions, and discuss your AI workflow. A conversation, not a quiz. |

| ⏱ Submit your completed challenge — with a live deployed URL — at least one full business day before your scheduled review. This gives your interviewer time to review your repo before the session. |
| :---- |

|  We recommend spending 4–6 hours on the build. There's no hard time limit — quality and judgment matter more than speed — but a strong senior engineer should be able to ship a solid MVP in that window. Don't spend your whole weekend on it. |
| :---- |

**Your Challenge** 

**The Brief** 

You have been brought in to build a customer support chatbot for Cadre AI. 

Cadre AI is an AI strategy and implementation consultancy. We help businesses move from AI confusion to AI confidence — going department by department to identify high-ROI AI opportunities, build workflows and agents, and train teams so the changes actually stick. Our clients range from lower middle market private equity-backed companies to professional services firms and financial services organizations. 

Cadre's inbound team is receiving a growing volume of inquiries from prospective clients, existing clients, and people who want to learn more about what we do. Your job is to build a chatbot that handles the most common interactions so the team can focus on high-value conversations. 

**About Cadre AI**

| Item  | Detail |
| :---- | :---- |
| **What we do**  | AI strategy, workflow automation, AI agents, and leadership facilitation for businesses |
| **Who we serve**  | B2B companies: professional services, private equity, financial services, real estate, construction, manufacturing, retail, and more |
| **Core services**  | AI Strategy, AI Leadership & Facilitation, AI Engineering, AI Agents |
| **Key partners**  | OpenAI, Anthropic (Claude), Google, Microsoft, AWS, Salesforce, Snowflake — plus OpenRouter for model access |

| Common inquiries  | What does Cadre AI do, how to get started, service pricing, AI Maturity Index, case studies, how to book a strategy call, what industries we work in |
| :---- | :---- |

**What to Build** 

Build a customer support chatbot for Cadre AI that can handle common inbound inquiries. The prompt is intentionally underspecified — how you scope and prioritize is part of the evaluation. 

| Minimum bar: a functional chatbot that a prospective or existing Cadre AI client could plausibly use to get answers. Everything beyond that is your call. |
| :---- |

Some scenarios the bot should be able to handle (treat this as a starting point, not an exhaustive spec): 

• A prospective client asking what Cadre AI does and whether we work with their industry • Someone asking how to book a call with an AI strategist 

• A client asking how to access the Cadre portal to track their AI tools, agents, and results 

• A business leader asking what the AI Maturity Index is and how to get scored • Someone asking about Cadre's approach to LLM selection and data security • A user asking a question the bot can't answer — and needs to escalate or redirect 

|  You decide what the bot knows. You decide where it draws the line. You decide what's in scope. We're watching those decisions closely. |
| :---- |

**Deliverables** 

Before your review session, make sure you have the following ready: 

• A deployed, publicly accessible URL of your chatbot 

• Your code pushed to a GitHub repository you will share with us 

• A CLAUDE.md at the root of the project 

• A plan.md at the root of the project

|  Create a CLAUDE.md and plan.md at the root of your project. Commit your code to a fresh repo you will share. The app must be deployed and accessible on a public URL. You will walk through your code, architecture, and Claude Code workflow in the review. |
| :---- |

**What We're Looking For** 

We evaluate five dimensions, weighted by importance to Cadre AI's engineering culture: 

| Dimension  | Weight  | In Practice |
| :---- | :---- | :---- |
| **Claude Code Proficiency**  | 30%  | How you set up CLAUDE.md, plan.md, use subagents, custom commands, and manage AI context. The most important dimension. |
| **System Design & Architecture**  | 25%  | Your data model, API structure, system prompt design, separation of concerns, and scaling trade-offs. |
| **Development Speed & Scope**  | 20%  | How you prioritize features, where you draw scope boundaries, and how you manage complexity. |
| **Code Quality & Verification**  | 15%  | Clean code, error handling, catching AI bugs, knowing what your code does. |
| **Communication & Reasoning**  | 10%  | Explaining decisions, articulating trade-offs, productive technical dialogue. |

|  We're not testing whether you can code. We're testing whether you can think clearly enough to direct and verify a system that codes with you. |
| :---- |

**How to Prepare** 

**1\. Get Comfortable with Claude Code** 

If you haven't used Claude Code before, spend time with it first. Key things to practice: 

• Running /init on a new project and customizing the generated CLAUDE.md • Writing a plan.md that breaks a project into phases Claude can execute sequentially • Using subagents to parallelize independent tasks 

• Debugging when Claude generates broken code — providing error output and context back to Claude  
• Knowing when to accept Claude's output, modify it, or reject it entirely 

**2\. Have a Go-To Tech Stack** 

Speed matters. Pick what you know. There is no required tech stack — the only requirement is that it deploys and works on a public URL. 

| Stack  | Strengths  | Good For |
| :---- | ----- | :---- |
| **Next.js \+ Supabase**  | Auth built-in, fast Vercel deploys  | Great default choice |
| **Python \+ FastAPI \+ React**  | Flexible, great for AI integrations  | AI-heavy apps |
| **T3 Stack**  | Full type safety, tRPC  | Complex UIs, real-time |
| **Rails / Django**  | Batteries included, fast  scaffolding | Rapid prototyping |

**3\. Practice the Full Loop** 

The review tests the complete cycle: plan → build → deploy → iterate. Practice building a small app end-to-end using Claude Code before the challenge. Your goal is a working, deployed MVP without scrambling. 

**4\. Know Your CLAUDE.md Strategy** 

During the review we'll ask about your CLAUDE.md. Think of it as onboarding documentation for an extremely fast but context-limited junior developer. The best CLAUDE.md files are opinionated and specific — not generic boilerplate. 

**What Happens in the Review** 

After you submit, we'll have a 1-hour live conversation:

| Section  | \~Time  | What We'll Discuss |
| :---- | :---- | :---- |
| **Live Demo**  | 10 min  | Walk through the deployed app. Show what works, be upfront about what's broken or out of scope. |
| **Architecture**  | 15 min  | System prompt design, API structure, data model, scaling considerations. |

| Claude Code Workflow  | 15 min  | CLAUDE.md, plan.md, subagents, prompting strategy, how you handled AI errors. |
| :---- | :---- | :---- |
| **Code Deep Dive**  | 10 min  | Specific functions explained. What Claude generated vs. what you modified, and why. |
| **Decisions & Trade-offs**  | 10 min  | Scope choices, what you left out intentionally, what you'd do with more time. |

| ✅ We expect trade-offs. We expect incomplete features. The best candidates are honest about what's broken and articulate about what they'd do with more time. |
| :---- |

**Tips from the Cadre AI Engineering Team**

| ✅ Do This  | ❌ Avoid This |
| :---- | :---- |
| **Plan before coding. Write CLAUDE.md and plan.md first.** | Starting to code immediately with no plan or context. |
| **Deploy early. Get something live before you start iterating.** | Waiting until the end — deployment issues are real. |
| **Small, frequent commits with descriptive messages.** | One giant commit at the end. |
| **Read and verify Claude's output. Test as you go.** | Blindly accepting everything Claude generates. |
| **Use subagents for independent tasks.**  | One massive prompt, long wait, wall of unverified code. |
| **Cut scope aggressively. 3 working features \> 8 broken ones.** | Trying to build everything and shipping nothing. |
| **Give Claude error messages \+ context when debugging.** | Re-running the same failing prompt repeatedly. |
| **Make your scope decisions explicit in plan.md.** | Leaving scope ambiguous and hoping for the best. |

**Frequently Asked Questions** 

**Can I use other AI tools besides Claude Code?** 

Claude Code is the primary tool we evaluate on. You can use the internet freely, but lean into Claude Code — it's 30% of your score. 

**What if I've never used Claude Code?** 

Spend several hours practicing before the challenge. It's free to install. Familiarity matters — it's the highest-weighted dimension. 

**Which LLM should I use for the chatbot?** 

That's part of the challenge. You have full flexibility on model selection. Choose what you think is right for the job and be ready to explain why during the review. 

**What if my deployment breaks?** 

Deployment issues happen. How you handle them is part of the evaluation. Your interviewer can help with platform configuration but not code issues. 

**What if I don't finish everything?** 

Nobody builds everything. A focused MVP with clear trade-offs beats an ambitious mess every time. Be explicit about what you left out and why. 

**Can I use component libraries and third-party packages?** 

Yes. Use whatever helps you move fast and build well. We're testing engineering judgment and AI workflow, not your ability to write CSS from scratch. 

**Good luck. Build something great.** 

*We're rooting for you.* 

— The Cadre AI Engineering Team