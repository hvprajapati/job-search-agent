# Product Requirements Document (PRD)

## Autonomous AI Career Agent — "Pathfinder"

**Document Version:** 1.0
**Date:** 2026-06-17
**Status:** Draft for Review
**Author:** Product & Engineering Leadership
**Classification:** Confidential — Internal

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Vision & Strategy](#2-product-vision--strategy)
3. [Market & Competitive Landscape](#3-market--competitive-landscape)
4. [User Personas](#4-user-personas)
5. [User Journeys](#5-user-journeys)
6. [Functional Requirements](#6-functional-requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Success Metrics](#8-success-metrics)
9. [MVP Scope — "Pathfinder Core"](#9-mvp-scope--pathfinder-core)
10. [V1 Scope — "Pathfinder Pro"](#10-v1-scope--pathfinder-pro)
11. [V2 Scope — "Pathfinder Scale"](#11-v2-scope--pathfinder-scale)
12. [Future Roadmap — V3 and Beyond](#12-future-roadmap--v3-and-beyond)
13. [System Architecture — High-Level Overview](#13-system-architecture--high-level-overview)
14. [AI/ML Strategy](#14-aiml-strategy)
15. [Data Model — Conceptual Overview](#15-data-model--conceptual-overview)
16. [Risk Register & Mitigation](#16-risk-register--mitigation)
17. [Appendix](#17-appendix)

---

## 1. Executive Summary

### 1.1 The Problem

Job searching is fundamentally broken. The average job seeker spends **11–25 hours per week** across 15+ disconnected tools — job boards, LinkedIn, company career pages, ATS portals, resume builders, cover letter editors, email clients, spreadsheets, and interview prep platforms. The cognitive load is crushing. The process is reactive, repetitive, and emotionally draining.

The asymmetry is staggering: employers deploy AI-powered ATS systems, automated screening, and recruiter tooling. Job seekers are armed with... a PDF resume and hope.

### 1.2 Our Solution

**Pathfinder** is an Autonomous AI Career Agent that acts as a **persistent, proactive, personal career operating system**. It is not a chatbot. It is not a job board wrapper. It is an AI agent system that:

- **Understands** the user's profile, skills, experience, aspirations, and constraints at a deep semantic level
- **Discovers** jobs continuously across hundreds of sources — public boards, company career pages, niche communities, recruiter posts, and hidden markets
- **Matches** with calibrated, explainable relevance scoring that goes far beyond keyword matching
- **Acts autonomously** — tailoring resumes, generating cover letters, tracking applications, scheduling follow-ups
- **Learns** from every interaction — implicit and explicit feedback — to continuously improve recommendations
- **Coaches** — identifying skill gaps, recommending learning pathways, preparing interview strategies
- **Persists** — maintaining a rich, evolving long-term memory of the user's career journey across months or years

### 1.3 Target Outcomes

| Outcome | Target |
|---------|--------|
| Time-to-hire reduction | 35% faster than industry average for role + seniority |
| Application quality | 3× higher interview rate vs. unassisted applications |
| User NPS | 60+ |
| Job discovery coverage | 92%+ of relevant open roles surfaced within 48 hours |
| User retention | 70%+ monthly active users return within 30 days of placement (career growth mode) |

---

## 2. Product Vision & Strategy

### 2.1 Vision Statement

> To become the operating system for every professional's career — starting with job search, expanding into lifelong career management, skill development, and professional networking.

### 2.2 Mission Statement

> Empower every professional with an AI agent that works tirelessly on their behalf — discovering opportunities, advocating for their potential, and guiding their growth — so they can focus on what matters: doing their best work.

### 2.3 Strategic Pillars

1. **Autonomy over Assistance** — The agent acts; it doesn't wait to be asked. It surfaces jobs while the user sleeps. It sends follow-ups when the user forgets. It nudges when deadlines approach.

2. **Depth over Breadth (at launch)** — We serve five technical personas (Freshers, Data Engineers, AI Engineers, ML Engineers, Software Engineers) deeply rather than everyone shallowly. We win a beachhead, then expand.

3. **Memory as Moat** — Every interaction enriches the user model. After 6 months, the agent knows a user's career narrative better than the user's closest mentor. Switching costs become enormous.

4. **Trust through Transparency** — Every AI decision is explainable. Every resume edit is reviewable. The user is always in control. We earn the right to automate more over time.

5. **Platform, not Tool** — The architecture supports eventual multi-sided marketplace dynamics: candidates, employers, recruiters, educators, and career coaches — all with AI-mediated interactions.

### 2.4 Business Model (Outline)

| Tier | Pricing | Target |
|------|---------|--------|
| **Free** | $0/month | Freshers — 50 applications/month, basic matching, 3 resume variants |
| **Pro** | $29/month | Active job seekers — unlimited applications, advanced matching, unlimited resume variants, cover letters, interview prep, analytics |
| **Premium** | $79/month | Career accelerators — proactive agent, priority job discovery, skill-gap coaching, learning plans, recruiter connection requests, custom integrations |
| **Enterprise** | Custom | Outplacement firms, universities, coding bootcamps — white-label, bulk management, analytics dashboard, API access |

---

## 3. Market & Competitive Landscape

### 3.1 Market Sizing

| Segment | Global TAM (2026) |
|---------|-------------------|
| Job board / recruitment tech | $42B |
| Resume building / career services | $8B |
| Interview preparation | $3B |
| Online learning / upskilling | $58B |
| **Total Addressable** | **~$50B (career-tech slice)** |

Initial SAM (US, tech roles, 5 personas): ~$4.2B

### 3.2 Competitive Landscape

| Category | Players | Our Differentiator |
|----------|---------|-------------------|
| Job Aggregators | Indeed, ZipRecruiter, Google Jobs | We are agentic, not just search + alert |
| AI Resume Tools | Teal, Kickresume, Rezi | We are end-to-end, not single-point |
| AI Job Match | LinkedIn Premium, ZipRecruiter AI | We are multi-source + explainable + persistent memory |
| Career Coaching | BetterUp, Pathrise, Gymnasium | We are AI-native, always-on, fraction of cost |
| ATS/CRM | Greenhouse, Lever | We are candidate-side, not employer-side |
| AI Career Agents | Simplify.jobs, Careerflow.ai, Huntr | We are autonomous + memory-driven + proactive, not just workflow tools |

### 3.3 Why Now

- **LLM capability maturity** — Models can now reason, plan, and use tools reliably enough for multi-step autonomous workflows
- **Agent infrastructure** — Frameworks for tool-use, memory, and orchestration have reached production readiness
- **Job market volatility** — AI-driven workforce transformation creates unprecedented demand for career navigation
- **User expectations** — Post-ChatGPT, users expect software to be intelligent and proactive

---

## 4. User Personas

### Persona 1: Priya — The Fresher

| Attribute | Detail |
|-----------|--------|
| **Age** | 22 |
| **Education** | B.Tech in Computer Science, tier-2 college, India |
| **Experience** | 0–1 years (internships only) |
| **Target Roles** | Junior Software Engineer, Graduate Engineer Trainee, SDE-1 |
| **Portfolio** | 2–3 college projects, 1 internship project, moderate GitHub activity |
| **Pain Points** | Doesn't know which companies hire freshers; resume gets filtered by ATS; no idea how to prepare for interviews; overwhelmed by the process; impostor syndrome |
| **Behaviors** | Applies to 30–50 jobs/week via campus placement + job boards; copies same resume everywhere; rarely writes cover letters; uses WhatsApp/Telegram groups for job leads |
| **Goals** | Land first job within 3 months of graduation; understand what skills matter; build confidence |
| **Tech Comfort** | High — grew up with smartphones, comfortable with AI tools |
| **Willingness to Pay** | Low initially — willing to pay after first paycheck (deferred / income-share models attractive) |

### Persona 2: David — The Mid-Career Software Engineer

| Attribute | Detail |
|-----------|--------|
| **Age** | 31 |
| **Education** | B.S. Computer Science, state university, USA |
| **Experience** | 8 years — full-stack, 3 companies |
| **Target Roles** | Senior Software Engineer, Staff Engineer, Tech Lead |
| **Current Stack** | React, Node.js, PostgreSQL, AWS |
| **Pain Points** | Job search is a second job; tailoring resumes for each role is tedious; hard to evaluate cultural fit; wants to avoid toxic environments; negotiation anxiety; ATS black holes |
| **Behaviors** | Passive candidate until actively looking; researches companies on Glassdoor/Blind before applying; networks on LinkedIn; uses multiple job boards; tracks applications in a spreadsheet |
| **Goals** | Find a role with better compensation (+20%), strong engineering culture, and growth path to Staff Engineer within 2 years |
| **Tech Comfort** | High — builds software for a living |
| **Willingness to Pay** | $29–79/month if it demonstrably saves time and improves outcomes |

### Persona 3: Aisha — The Data Engineer

| Attribute | Detail |
|-----------|--------|
| **Age** | 28 |
| **Education** | M.S. Data Science, European university |
| **Experience** | 5 years — data engineering, ETL pipelines, data warehousing |
| **Target Roles** | Senior Data Engineer, Data Platform Engineer, Analytics Engineer |
| **Current Stack** | Python, SQL, Spark, Airflow, dbt, Snowflake, GCP |
| **Pain Points** | Role definitions vary wildly between companies ("Data Engineer" means 6 different things); hard to filter signal from noise in job descriptions; certifications matter but which ones?; wants remote-first roles |
| **Behaviors** | Targeted search — applies to 5–10 carefully chosen roles per week; researches tech stack before applying; active in data engineering Slack/Discord communities; attends virtual meetups |
| **Goals** | Transition from service-based to product-company data engineering; work on modern data stack; maintain remote flexibility |
| **Tech Comfort** | High — builds data infrastructure |
| **Willingness to Pay** | $29/month if it reduces research overhead and improves match quality |

### Persona 4: Marcus — The AI/ML Engineer

| Attribute | Detail |
|-----------|--------|
| **Age** | 34 |
| **Education** | Ph.D. Computer Science (NLP), top-10 US program |
| **Experience** | 6 years — applied ML, 2 years post-PhD in industry |
| **Target Roles** | Senior ML Engineer, Applied Scientist, AI Research Engineer |
| **Current Stack** | PyTorch, JAX, Transformers, CUDA, MLOps (Kubeflow, MLflow), production inference systems |
| **Pain Points** | Distinguishing genuine AI roles from rebranded analytics positions; evaluating whether companies have real ML infrastructure or are just "AI-washing"; publication vs. product impact trade-offs; compensation benchmarking for niche expertise |
| **Behaviors** | Highly selective — applies to 3–5 roles/month; networks through conferences (NeurIPS, ICML); recruited passively via LinkedIn; evaluates companies on ML maturity, compute budget, and research freedom |
| **Goals** | Find a role with meaningful ML problems, strong research culture, top-tier compensation ($300K+ TC), and path to Principal/Manager |
| **Tech Comfort** | Expert — builds AI systems |
| **Willingness to Pay** | $79/month — values premium intelligence and curation |

### Persona 5: Linh — The Career Changer into Tech

| Attribute | Detail |
|-----------|--------|
| **Age** | 27 |
| **Education** | B.A. Economics, bootcamp graduate (12-week full-stack), Vietnam/Australia |
| **Experience** | 3 years in management consulting + 6 months of freelance web development |
| **Target Roles** | Software Engineer, Solutions Engineer, Technical Consultant |
| **Current Stack** | JavaScript, React, Ruby on Rails, basic SQL |
| **Pain Points** | Non-traditional background gets auto-rejected by ATS; doesn't know how to frame consulting experience for tech roles; unsure which companies value diverse backgrounds; imposter syndrome amplified by bootcamp stigma |
| **Behaviors** | Applies broadly (20–30/week); actively networking on LinkedIn and at meetups; completing certifications (AWS, Scrum) to bolster resume; seeking mentorship |
| **Goals** | Land first full-time engineering role within 6 months; find a company that values diverse backgrounds; reach $90K+ salary |
| **Tech Comfort** | Moderate — comfortable with tools, still building engineering depth |
| **Willingness to Pay** | $29/month if it demonstrably improves callback rate |

---

## 5. User Journeys

### Journey 1: Onboarding & Profile Creation (All Personas)

```
DAY 0 — First Launch

1. USER signs up with email or Google/GitHub OAuth.
2. AGENT presents a conversational onboarding flow:
   a. "Welcome! Tell me about your career so far. You can upload your resume,
      link your LinkedIn, or just start typing — whatever's easiest."
   b. USER uploads resume PDF + links LinkedIn profile.
   c. AGENT parses both, extracts structured profile:
      - Work history (company, title, dates, achievements)
      - Education (institution, degree, field, year)
      - Skills (technical + soft, inferred proficiency)
      - Projects (name, description, technologies, links)
      - Certifications
      - Publications
      - Languages
   d. AGENT presents extracted profile for review:
      "Here's what I found. Can you confirm this is accurate?"
      - Highlights low-confidence extractions for user verification
      - Flags gaps: "I notice you don't have any projects listed. Want to add some?"
   e. USER confirms, corrects, and augments.

3. AGENT initiates preference elicitation (adaptive — fewer questions for freshers, more for seniors):
   a. "What roles are you targeting?" → Multi-select with autocomplete
   b. "What locations work for you?" → Multi-select + remote/hybrid/onsite preference
   c. "What's your minimum compensation?" → Free-text + market data comparison
   d. "What matters most in your next role?" → Ranked choice:
      - Compensation & benefits
      - Growth & learning opportunities
      - Work-life balance
      - Mission & impact
      - Team & culture
      - Tech stack & tools
      - Job stability
   e. "Any companies you'd love to work at? Any you'd avoid?"
   f. "What's your timeline?" → Immediately / 1–3 months / 3–6 months / Just exploring
   g. "How hands-on do you want me to be?" → Auto-pilot / Guided / Assist-only

4. AGENT builds initial user model — vector embeddings of profile + preferences + inferred traits.
5. AGENT runs first job discovery sweep → presents dashboard: "I found 247 matching jobs.
   Here are your top 15. Ready to dive in?"

OUTCOME: User has a complete, structured profile and sees immediate value.
```

### Journey 2: Daily Active Job Search (Priya — Fresher)

```
DAY 1–90 — Active Search Phase

WEEKLY RHYTHM:

MONDAY MORNING (Agent-initiated):
  - Push notification: "Good morning Priya! I found 34 new graduate roles this weekend.
    12 are strong matches. Want me to apply to the top 5?"
  - Email digest: Weekly job discovery summary with top matches

DAILY FLOW:
  1. USER opens Pathfinder dashboard.
  2. DASHBOARD shows:
     - "Your Pipeline" — Kanban of applications (Saved → Applied → Screening → Interview → Offer → Accepted)
     - "Today's Top Matches" — 5–10 jobs with match scores and explanations
     - "Actions Needed" — Follow-ups, interview prep, deadlined tasks
     - "Insight of the Day" — One actionable career insight

  3. USER browses matches. For each job:
     - Match breakdown: "85% match — Strong on Python (your top skill), SQL,
       problem-solving. Gap: They want Docker experience (you haven't listed this)."
     - One-click actions: [Save] [Tailor Resume] [Generate Cover Letter] [Apply] [Dismiss]

  4. USER clicks [Tailor Resume] on a Junior Python Developer role at startup X.
     AGENT:
     a. Analyzes job description — extracts keywords, required skills, nice-to-haves,
        inferred company culture, tech stack
     b. Identifies relevant experience from USER profile:
        - College project: "Built REST API with Flask" → emphasized
        - Internship: "Automated data pipeline" → reframed to highlight Python scripting
        - Skill gap: "Docker" not present → flags as honest gap, suggests adding "Learning Docker"
     c. Generates tailored resume:
        - Professional summary rewritten for this role
        - Skills reordered to match JD priority
        - Achievements quantified where possible
        - ATS-friendly formatting maintained
     d. USER reviews in side-by-side diff view, makes edits, approves.
     e. Resume saved as variant: "Junior Python Dev — Startup X"

  5. USER clicks [Generate Cover Letter].
     AGENT generates CL following company research:
     - Opening: Why this company specifically (references their recent product launch,
       tech blog post, or mission)
     - Body: Maps 3 specific experiences to job requirements with evidence
     - Closing: Call to action + enthusiasm
     USER reviews, edits tone, approves.

  6. USER clicks [Apply]. AGENT:
     - If direct apply: Auto-fills application form (where possible) or guides user
     - If external: Opens job posting, provides autofill assistance
     - Logs application with timestamp, resume variant used, cover letter version
     - Moves card to "Applied" column

  7. 5 DAYS LATER — AGENT detects no response from Startup X.
     AGENT: "It's been 5 days since you applied to the Junior Python Dev role at Startup X.
     Want me to draft a follow-up email?"
     USER approves → AGENT generates personalized follow-up → USER sends.

  8. DAY 12 — Startup X responds: Interview invitation!
     AGENT: "Congrats! You have a technical phone screen with Startup X on Thursday.
     Here's what I know about their interview process..."
     AGENT generates interview preparation plan:
     - Company research summary (founded 2023, Series A, 25 employees, Python/Django stack)
     - Likely interview format (based on Glassdoor data: 30-min coding + 30-min behavioral)
     - Suggested practice problems (LeetCode easy/medium — arrays, strings, hash maps)
     - Behavioral question bank with STAR-framework answers populated from USER profile
     - Questions to ask the interviewer (curated for startup stage + role)
     - Compensation research for this role + location

OUTCOME: 90 days later, Priya has applied to 120+ roles, received 8 interviews,
and accepted an offer. Her agent has learned which companies responded, which resume
patterns worked, and which skills mattered — building an ever-improving career model.
```

### Journey 3: Passive Candidate — Always-On Mode (David — Senior SWE)

```
MONTH 1–12 — Passive Monitoring

1. DAVID is employed but open to the right opportunity. He sets mode to "Passive — Alert Me."
2. AGENT runs weekly discovery sweeps with high threshold (match > 80% AND compensation > 20% raise).
3. WEEK 3 — AGENT surfaces a Staff Engineer role at a Series C devtools startup:
   - Match: 91%
   - Compensation: $220K–260K base + equity (David's current: $185K)
   - Culture signal: Engineering blog shows deep technical culture
   - Connection: David's former colleague works there (via LinkedIn graph analysis)
4. AGENT: "This one's special. High match, former colleague there, and their eng blog
   suggests exactly the kind of culture you've described wanting. Worth a conversation?"
5. DAVID is interested. AGENT generates a warm outreach message to former colleague,
   tailored resume, and cover letter — all within minutes.
6. DAVID interviews, negotiates using AGENT's compensation intelligence, and accepts.

OUTCOME: David found his dream role without active searching. His agent monitored for
6 months before the right opportunity appeared. He stays subscribed at Pro tier for
ongoing career growth features.

POST-PLACEMENT (Career Growth Mode):
  - AGENT tracks David's new role, updates his profile
  - Suggests skills to develop for next promotion
  - Monitors internal job market (if integrated) for lateral moves
  - Annual compensation benchmarking against market
  - "Your 1-year anniversary is approaching. Market rates for Staff Engineers
    have increased 8%. Here's data for your performance review."
```

### Journey 4: Skill Gap Remediation (Linh — Career Changer)

```
MONTH 1–3 — Bridging the Gap

1. LINH has been applying for 4 weeks. Dashboard shows:
   - Applications: 47
   - Responses: 3 (6.4% callback rate)
   - Industry benchmark for career changers: 8–12%
   - Top rejection reason (inferred): "Non-traditional background" / "Missing CS fundamentals"

2. AGENT analyzes pattern across all applications:
   a. Jobs that responded positively shared: emphasis on practical skills over credentials,
      smaller companies, industries adjacent to Linh's consulting experience (fintech, adtech)
   b. Jobs that rejected quickly shared: "CS degree required" language, large enterprise ATS,
      roles heavy on algorithms and systems design

3. AGENT generates "Skill Gap Report":
   - CRITICAL GAPS (blocking interviews):
     - Data Structures & Algorithms (cited in 73% of rejections)
     - System Design fundamentals (cited in 41% of rejections)
   - MODERATE GAPS:
     - Distributed systems concepts
     - Testing methodologies (unit, integration, e2e)
   - STRENGTHS (lean into these):
     - Business communication (consulting background)
     - Stakeholder management
     - Full-stack project delivery

4. AGENT recommends a "90-Day Upskilling Plan":
   - Week 1–4: Algorithms (recommends Grokking Algorithms + LeetCode easy)
   - Week 5–8: System Design (recommends System Design Interview + practice problems)
   - Week 9–12: Open-source contribution (recommends 3 beginner-friendly projects)
   - Concurrent: Continue applying to companies flagged as "career-changer-friendly"

5. LINH follows the plan. AGENT tracks progress:
   - "You've completed 24/40 LeetCode problems this week. 82% pass rate on first attempt."
   - "Your callback rate has improved from 6.4% to 11.2%."

6. AGENT adjusts targeting strategy:
   - Prioritizes roles at companies with history of hiring bootcamp grads
   - Emphasizes "Solutions Engineer" roles as stepping stone (higher callback rate)
   - Generates resumes that lead with project impact over educational background

OUTCOME: Linh lands a Solutions Engineer role at a fintech company after 11 weeks.
Callback rate improved 3×. She continues using Pathfinder for internal growth planning.
```

### Journey 5: Full Autopilot (Marcus — AI/ML Engineer, Premium Tier)

```
MONTH 1–2 — Agent-Driven Search

1. MARCUS configures Autopilot with strict constraints:
   - Role: Senior/Staff ML Engineer, Applied Scientist, or AI Research Engineer
   - Compensation: $280K+ total compensation
   - Location: Remote-first or San Francisco Bay Area
   - Company: >50 employees, demonstrated ML investment, no defense contractors
   - Auto-apply threshold: Match > 85%
   - Auto-draft threshold: Match > 70% (drafts for review)

2. AGENT operates continuously:
   - Discovers jobs across 300+ sources
   - Filters against constraints
   - Scores and ranks matches
   - For matches >85%:
     a. Tailors resume
     b. Generates cover letter
     c. Drafts application responses
     d. Queues for Marcus's review (batched daily at 8 AM)
     e. Applies upon single-tap approval (or auto-applies if Marcus enabled it)

3. AGENT also:
   - Monitors Marcus's LinkedIn for recruiter messages → surfaces interesting ones
   - Tracks conference career fairs and company events → suggests attendance
   - Analyzes company tech blogs and engineering Twitter for culture signals
   - Maps Marcus's network to target companies → suggests warm introductions

4. MARCUS reviews a daily briefing over coffee (5 minutes):
   - "Applied to 3 roles yesterday. 2 more ready for your review.
     1 company reached out — here's why it's interesting.
     Your interview at DeepMind is next Tuesday — updated prep materials attached."

OUTCOME: Marcus spends <2 hours/week on job search while his agent works 24/7.
He lands a Staff ML Engineer role at an AI research lab within 7 weeks — a role
he wouldn't have found on his own (it was posted in a private Slack community).
```

---

## 6. Functional Requirements

### FR-1: Profile Management System

| ID | Requirement | Priority | MVP/V1/V2 |
|----|------------|----------|-----------|
| FR-1.1 | Parse resume files (PDF, DOCX, TXT, JSON Resume) and extract structured profile data using LLM + rule-based extraction | P0 | MVP |
| FR-1.2 | Import profile from LinkedIn (via user-consented OAuth or PDF export upload) | P0 | MVP |
| FR-1.3 | Import from GitHub — extract repos, contributions, languages, activity | P1 | V1 |
| FR-1.4 | Build unified, deduplicated, versioned profile from all import sources | P0 | MVP |
| FR-1.5 | User review and editing interface for extracted profile data with confidence indicators | P0 | MVP |
| FR-1.6 | Skill tagging with proficiency levels (Beginner / Intermediate / Advanced / Expert) — inferred and user-confirmed | P0 | MVP |
| FR-1.7 | Auto-generated professional summary (multiple versions, tone-adjustable) | P1 | V1 |
| FR-1.8 | Profile version history and rollback | P2 | V2 |
| FR-1.9 | Multi-language profile support (parse + generate in 10+ languages) | P2 | V2 |
| FR-1.10 | Portfolio integration — link and auto-index GitHub projects, Dribbble, Behance, personal websites | P2 | V2 |
| FR-1.11 | Video/audio intro recording + transcription for profile enrichment | P3 | V3 |

### FR-2: Job Discovery Engine

| ID | Requirement | Priority | MVP/V1/V2 |
|----|------------|----------|-----------|
| FR-2.1 | Multi-source job ingestion pipeline — job boards (Indeed, LinkedIn, ZipRecruiter, Glassdoor, Wellfound, Dice, Monster, CareerBuilder), company career pages (top 500 tech companies), ATS-hosted listings (Greenhouse, Lever, Workday, Ashby, Greenhouse), niche boards (Stack Overflow Jobs, GitHub Jobs, Hacker News "Who's Hiring", Y Combinator jobs), community sources (Reddit, Discord servers, Slack communities), recruiter posts (LinkedIn, Twitter/X), government portals, university job boards | P0 | MVP (top 50 sources), V1 (200+ sources) |
| FR-2.2 | Intelligent deduplication — same job posted across multiple sources merged into single canonical listing | P0 | MVP |
| FR-2.3 | Job freshness tracking — detect first-seen, reposted, refreshed, and stale listings | P0 | MVP |
| FR-2.4 | Continuous discovery — configurable sweep frequency (hourly/daily/weekly) based on user tier and mode | P0 | MVP |
| FR-2.5 | Job description enrichment — infer tech stack, team size, company stage, remote policy, compensation (from text or external data), benefits from JD text analysis | P1 | V1 |
| FR-2.6 | "Hidden market" discovery — jobs shared in private communities, Twitter threads, newsletters, personal websites | P1 | V1 |
| FR-2.7 | Company research enrichment — funding stage (Crunchbase integration), engineering culture signals (tech blog analysis, Glassdoor/Blind sentiment), growth trajectory (headcount trends), recent news, tech radar (stackshare, GitHub org analysis) | P1 | V1 |
| FR-2.8 | Referral opportunity detection — identify 2nd-degree LinkedIn connections at target companies | P2 | V2 |
| FR-2.9 | Event-based discovery — career fairs, hackathons, meetups, conferences with hiring tracks | P2 | V2 |
| FR-2.10 | "Coming soon" detection — pre-launch startups, companies raising rounds (predict hiring surges) | P3 | V3 |
| FR-2.11 | User-contributed job sharing with reward/credit system | P3 | V3 |

### FR-3: Matching & Scoring Engine

| ID | Requirement | Priority | MVP/V1/V2 |
|----|------------|----------|-----------|
| FR-3.1 | Multi-dimensional match scoring: skill match (semantic + keyword), experience level match, domain match, tech stack overlap, culture/value alignment inference, compensation alignment, location fit, career trajectory alignment | P0 | MVP |
| FR-3.2 | Explainable scores — breakdown of why a job matches (or doesn't), with specific evidence | P0 | MVP |
| FR-3.3 | Weighted preference model — user-ranked priorities (compensation, growth, culture, etc.) influence scoring | P0 | MVP |
| FR-3.4 | Negative matching — detect and downrank based on user dislikes, dealbreakers, past rejection patterns | P1 | V1 |
| FR-3.5 | Collaborative filtering — "users with your profile also matched well with..." | P1 | V1 |
| FR-3.6 | Temporal decay — fresh jobs get boost; stale jobs decay; seasonal patterns considered | P1 | V1 |
| FR-3.7 | Diversity-aware matching — surface jobs the user might not search for but would succeed in (adjacent roles, industries where their skills transfer) | P2 | V2 |
| FR-3.8 | Compensation prediction — ML model predicts salary range when not listed, calibrated against market data | P2 | V2 |
| FR-3.9 | Interview probability estimation — predict likelihood of interview based on historical patterns of similar profiles for similar roles | P2 | V2 |
| FR-3.10 | Real-time re-ranking — user feedback (dismiss, save, apply) immediately updates ranking model | P0 | MVP |

### FR-4: Resume Tailoring Engine

| ID | Requirement | Priority | MVP/V1/V2 |
|----|------------|----------|-----------|
| FR-4.1 | Base resume template system with ATS-optimized formatting (clean, parseable, keyword-rich) | P0 | MVP |
| FR-4.2 | Job-specific resume tailoring — reorder skills, rewrite bullets, adjust summary, emphasize relevant experience | P0 | MVP |
| FR-4.3 | ATS keyword optimization — ensure critical JD keywords appear naturally without keyword stuffing | P0 | MVP |
| FR-4.4 | Achievement quantification — suggest/rewrite bullets to include metrics and impact (e.g., "Improved performance" → "Reduced API latency by 40%, saving $120K annually") | P1 | V1 |
| FR-4.5 | Side-by-side diff review interface for tailored resume vs. base | P0 | MVP |
| FR-4.6 | Resume variant management — save, name, version, and organize tailored resumes per job, company, or role type | P0 | MVP |
| FR-4.7 | Gap identification and honest handling — flag missing requirements, suggest framing (e.g., "Learning X" vs. omitting) | P1 | V1 |
| FR-4.8 | Multi-format export — PDF (ATS-optimized), DOCX, plain text, LaTeX | P1 | V1 |
| FR-4.9 | ATS simulation — run tailored resume against simulated ATS parser + JD to predict parse quality and keyword coverage | P2 | V2 |
| FR-4.10 | A/B testing of resume variants — track which versions get better response rates per role type | P2 | V2 |
| FR-4.11 | Industry/role-specific templates — tech vs. consulting vs. design vs. academic formatting conventions | P2 | V2 |
| FR-4.12 | Visual/protfolio resume option for design roles | P3 | V3 |

### FR-5: Cover Letter Generation

| ID | Requirement | Priority | MVP/V1/V2 |
|----|------------|----------|-----------|
| FR-5.1 | Job-specific cover letter generation using user profile + job description + company research | P0 | MVP |
| FR-5.2 | Tone customization — professional, enthusiastic, concise, creative, formal | P1 | V1 |
| FR-5.3 | Company-specific personalization — reference recent news, product launches, tech blog posts, mission alignment | P1 | V1 |
| FR-5.4 | Evidence-based claims — every assertion backed by specific experience from user profile (no hallucinated achievements) | P0 | MVP |
| FR-5.5 | Cover letter review and editing interface with inline suggestions | P0 | MVP |
| FR-5.6 | Cover letter version management linked to applications | P0 | MVP |
| FR-5.7 | Multi-language cover letter generation | P2 | V2 |
| FR-5.8 | Tone-of-voice learning — adapt to user's writing style over time from edits and feedback | P2 | V2 |

### FR-6: Application Tracking System (ATS for Candidates)

| ID | Requirement | Priority | MVP/V1/V2 |
|----|------------|----------|-----------|
| FR-6.1 | Kanban pipeline view — Saved → Applied → Phone Screen → Technical Interview → Onsite → Offer → Accepted / Rejected / Withdrawn | P0 | MVP |
| FR-6.2 | Application logging — timestamp, role, company, resume variant used, cover letter, source, notes | P0 | MVP |
| FR-6.3 | Status tracking with manual and automatic updates (email parsing for status changes) | P1 | V1 |
| FR-6.4 | Email integration — Gmail + Outlook OAuth for automatic status detection (interview invitations, rejections, follow-ups) | P1 | V1 |
| FR-6.5 | Calendar integration — auto-detect interviews from calendar, link to applications, trigger prep reminders | P2 | V2 |
| FR-6.6 | Task management — to-dos linked to applications (follow up, send thank-you, complete assessment, submit reference) | P0 | MVP |
| FR-6.7 | Deadline alerts and nudges — assessment deadlines, follow-up windows, offer expiration | P0 | MVP |
| FR-6.8 | Analytics dashboard — application funnel metrics, response rates by channel/source, time-in-stage analysis, A/B resume performance, interview conversion rates | P1 | V1 |
| FR-6.9 | Document vault — all application documents (resumes, cover letters, portfolios, assessments) organized by application | P0 | MVP |
| FR-6.10 | Offer comparison tool — side-by-side comparison of compensation, benefits, equity, culture, growth | P2 | V2 |
| FR-6.11 | Negotiation support — market data, scripts, counter-offer templates, total compensation calculator | P2 | V2 |

### FR-7: Communication Agent (Follow-ups, Outreach, Thank-Yous)

| ID | Requirement | Priority | MVP/V1/V2 |
|----|------------|----------|-----------|
| FR-7.1 | Follow-up email generation after application (configurable timing — 3/5/7 days) | P0 | MVP |
| FR-7.2 | Thank-you email generation after interviews (personalized to interview content if notes provided) | P1 | V1 |
| FR-7.3 | Networking outreach message generation (warm introductions, LinkedIn connection requests, cold outreach) | P1 | V1 |
| FR-7.4 | Offer acceptance/decline email templates | P2 | V2 |
| FR-7.5 | Recruiter response drafting (salary expectations, availability, screening questions) | P1 | V1 |
| FR-7.6 | Communication tone library — professional, warm, concise, persistent (for follow-ups) | P1 | V1 |
| FR-7.7 | Smart scheduling — suggest optimal send times based on recipient timezone and engagement patterns | P2 | V2 |
| FR-7.8 | Communication history log linked to each application | P0 | MVP |

### FR-8: Interview Preparation System

| ID | Requirement | Priority | MVP/V1/V2 |
|----|------------|----------|-----------|
| FR-8.1 | Company-specific interview guide — format, typical questions, process stages aggregated from Glassdoor, Blind, Reddit, and user-contributed data | P0 | MVP |
| FR-8.2 | Role-specific question bank — technical (coding, system design, data structures) + behavioral + domain-specific (ML system design, data modeling, etc.) | P0 | MVP |
| FR-8.3 | Personalized behavioral answers — STAR-framework responses populated from user's actual experience | P0 | MVP |
| FR-8.4 | Mock interview simulator — AI conducts mock interview with voice input, provides feedback on content and delivery | P2 | V2 |
| FR-8.5 | Technical practice problem recommendation — LeetCode/CodeSignal problems calibrated to company's known interview style | P1 | V1 |
| FR-8.6 | System design interview preparation — frameworks, practice problems, company-specific patterns | P1 | V1 |
| FR-8.7 | "Questions to ask" curator — smart questions for each interviewer type (hiring manager, peer, executive, HR) based on company stage and role | P1 | V1 |
| FR-8.8 | Post-interview reflection tool — structured debrief template, feedback capture, improvement notes for next round | P1 | V1 |
| FR-8.9 | Interview performance tracking — scores, feedback themes, improvement trends across interviews | P2 | V2 |

### FR-9: Learning & Development Engine

| ID | Requirement | Priority | MVP/V1/V2 |
|----|------------|----------|-----------|
| FR-9.1 | Skill gap analysis — compare user profile to target role requirements, identify gaps with severity and frequency | P1 | V1 |
| FR-9.2 | Personalized learning plan generation — courses, projects, certifications, reading, and practice mapped to gaps and timeline | P1 | V1 |
| FR-9.3 | Learning resource curation — aggregate from Coursera, Udemy, edX, Pluralsight, O'Reilly, freeCodeCamp, YouTube, documentation, books, papers | P1 | V1 |
| FR-9.4 | Learning progress tracking — course completions, certification achievements, project milestones | P2 | V2 |
| FR-9.5 | Skill reassessment — periodic re-evaluation after learning, update profile proficiency levels | P2 | V2 |
| FR-9.6 | Market demand signals — "Companies are increasingly asking for X. Here's a 2-week plan to add it." | P2 | V2 |
| FR-9.7 | Certification ROI analysis — which certs actually increase callback rate for target roles | P3 | V3 |
| FR-9.8 | Project-based learning — AI-suggested side projects that fill specific skill gaps and look great in portfolios | P2 | V2 |

### FR-10: Long-Term Memory & Learning System

| ID | Requirement | Priority | MVP/V1/V2 |
|----|------------|----------|-----------|
| FR-10.1 | Persistent user model — evolving profile that improves with every interaction (applications, feedback, interviews, placements) | P0 | MVP (basic), V1 (advanced) |
| FR-10.2 | Implicit feedback learning — which jobs user views, saves, applies to, dismisses → updates preference model | P0 | MVP |
| FR-10.3 | Explicit feedback capture — thumbs up/down on matches, "Why this?" prompts, post-interview feedback | P0 | MVP |
| FR-10.4 | Career narrative construction — agent builds and maintains coherent long-form narrative of user's career, updated as new experiences are added | P1 | V1 |
| FR-10.5 | Preference drift detection — user's preferences change over time; agent detects and adapts without explicit reconfiguration | P2 | V2 |
| FR-10.6 | Cross-session context — agent remembers past interactions, decisions, and rationale across sessions spanning months | P1 | V1 |
| FR-10.7 | Career timeline visualization — interactive timeline of user's career with key decisions, learnings, and growth moments | P2 | V2 |
| FR-10.8 | "Memory export" — user can export their entire agent-learned model and history to take elsewhere | P3 | V3 |

### FR-11: Proactive Agent Capabilities

| ID | Requirement | Priority | MVP/V1/V2 |
|----|------------|----------|-----------|
| FR-11.1 | Scheduled job discovery sweeps with push notifications for high-match roles | P0 | MVP |
| FR-11.2 | Daily/weekly digest emails with top matches and pipeline summary | P0 | MVP |
| FR-11.3 | Deadline-aware nudges — "3 days until Startup X's application deadline" and "5 days since you applied to Y — follow up?" | P0 | MVP |
| FR-11.4 | Market alert triggers — "A new role matching your dream-job profile just appeared" | P1 | V1 |
| FR-11.5 | Passive monitoring mode — low-frequency sweeps for employed users, high threshold alerts only | P1 | V1 |
| FR-11.6 | Interview preparation reminders — "Your interview at Company X is in 2 days. Prep materials ready." | P1 | V1 |
| FR-11.7 | Autopilot mode — auto-apply to jobs above threshold, queue for user review (Premium tier) | P2 | V2 |
| FR-11.8 | Career milestone check-ins — "You've been in your role 18 months. Typical promotion cycles at your level are 18–24 months. Want to prepare?" | P3 | V3 |
| FR-11.9 | Compensation review alerts — annual benchmarking against market, suggestion to negotiate or explore | P3 | V3 |
| FR-11.10 | Burnout detection — usage pattern and sentiment analysis suggesting user take a break or adjust approach | P3 | V3 |

### FR-12: Multi-Agent Orchestration

| ID | Requirement | Priority | MVP/V1/V2 |
|----|------------|----------|-----------|
| FR-12.1 | Modular agent architecture — specialized sub-agents for discovery, matching, resume tailoring, cover letters, interview prep, coaching | P1 | V1 |
| FR-12.2 | Agent handoff protocol — structured context passing between sub-agents (e.g., match agent → resume agent receives full match analysis) | P1 | V1 |
| FR-12.3 | Parallel agent execution — discovery + matching + tailoring run concurrently for efficiency | P1 | V1 |
| FR-12.4 | Agent quality monitoring — success metrics per sub-agent, degradation detection, A/B experiment framework | P2 | V2 |
| FR-12.5 | Human-in-the-loop routing — configurable gates where agent must pause for user approval before proceeding | P0 | MVP |
| FR-12.6 | Agent explainability — every agent action logged with rationale, viewable by user | P1 | V1 |

### FR-13: Analytics & Insights

| ID | Requirement | Priority | MVP/V1/V2 |
|----|------------|----------|-----------|
| FR-13.1 | Personal analytics dashboard — application funnel, response rates, interview conversion, time-to-hire | P1 | V1 |
| FR-13.2 | Market intelligence — "Roles like yours in San Francisco are paying $X–$Y. You're in the Zth percentile." | P1 | V1 |
| FR-13.3 | Competitive positioning — "Among applicants to this role, you rank in the top N% on matching criteria" | P2 | V2 |
| FR-13.4 | Career trajectory modeling — "Based on people with similar profiles, here are 3 likely career paths over the next 5 years" | P3 | V3 |
| FR-13.5 | Recruiter's-eye view — simulate how a recruiter would see your profile vs. the job requirements | P2 | V2 |
| FR-13.6 | Anonymized benchmark comparisons — opt-in sharing of aggregate data for community insights | P3 | V3 |

---

## 7. Non-Functional Requirements

### NFR-1: Performance

| ID | Requirement | Target |
|----|------------|--------|
| NFR-1.1 | Page load time (P95) | < 2 seconds |
| NFR-1.2 | Time-to-first-job-discovery after profile creation | < 30 seconds |
| NFR-1.3 | Resume tailoring generation time | < 15 seconds |
| NFR-1.4 | Cover letter generation time | < 10 seconds |
| NFR-1.5 | Job discovery sweep (per source batch) | < 5 minutes for 50+ sources |
| NFR-1.6 | API response time (P95) | < 500ms for non-AI endpoints |
| NFR-1.7 | LLM inference latency budget | < 8 seconds for generation tasks (streaming to user) |
| NFR-1.8 | Search/filter response | < 300ms for job listing queries |
| NFR-1.9 | Concurrent user support (MVP) | 1,000 concurrent users |
| NFR-1.10 | Concurrent user support (V2 target) | 50,000 concurrent users |

### NFR-2: Reliability & Availability

| ID | Requirement | Target |
|----|------------|--------|
| NFR-2.1 | System uptime | 99.9% (8.76 hours downtime/year) — V1+; 99.5% for MVP |
| NFR-2.2 | Data durability | 99.999999999% (11 nines) — all user data backed up |
| NFR-2.3 | Disaster recovery | RPO < 1 hour, RTO < 4 hours |
| NFR-2.4 | Graceful degradation | Job discovery continues if matching service is degraded; cached matches shown if LLM is unavailable |
| NFR-2.5 | LLM failover | Multi-model fallback chain (primary → secondary → cached response) |

### NFR-3: Security

| ID | Requirement | Detail |
|----|------------|--------|
| NFR-3.1 | Authentication | OAuth 2.0 + OIDC (Google, GitHub, email/password with MFA option) |
| NFR-3.2 | Authorization | RBAC with least-privilege — user data only accessible by owning user + explicitly shared agents |
| NFR-3.3 | Data encryption | AES-256 at rest, TLS 1.3 in transit |
| NFR-3.4 | PII protection | All PII encrypted at field level; resume data treated as PII |
| NFR-3.5 | API security | Rate limiting, input validation, OWASP Top 10 mitigation |
| NFR-3.6 | LLM data handling | No user data used for model training; prompts sanitized; data processing agreements with all LLM providers |
| NFR-3.7 | Penetration testing | Annual third-party pen test; continuous vulnerability scanning |
| NFR-3.8 | SOC 2 Type II | Target certification by V2 |

### NFR-4: Privacy & Compliance

| ID | Requirement | Detail |
|----|------------|--------|
| NFR-4.1 | GDPR compliance | Data residency options, right to erasure, data portability, consent management |
| NFR-4.2 | CCPA compliance | Data disclosure, opt-out mechanisms |
| NFR-4.3 | Data minimization | Only collect data essential to the service; purge inactive accounts after defined period |
| NFR-4.4 | Data export | User can export all data (profile, applications, resumes, agent model) in machine-readable format at any time |
| NFR-4.5 | Account deletion | Full data purge within 30 days of deletion request |
| NFR-4.6 | AI transparency disclosure | Clear disclosure that AI is generating content; all AI-generated content labeled |
| NFR-4.7 | Bias monitoring | Regular audits of matching/recommendation outputs for demographic bias |

### NFR-5: Scalability

| ID | Requirement | Detail |
|----|------------|--------|
| NFR-5.1 | Horizontal scaling | All services stateless where possible; state in managed data stores |
| NFR-5.2 | Job ingestion scale | Handle 1M+ job listings/day at V1, 10M+/day at V2 |
| NFR-5.3 | User profile scale | Support 100K+ user profiles at V1, 1M+ at V2 |
| NFR-5.4 | LLM throughput | Queue-based async processing for non-interactive LLM calls; priority lanes for interactive |
| NFR-5.5 | Multi-region deployment | US, EU, APAC by V2 for data residency and latency |

### NFR-6: Observability

| ID | Requirement | Detail |
|----|------------|--------|
| NFR-6.1 | Centralized logging | Structured JSON logging; all services; log levels configurable |
| NFR-6.2 | Distributed tracing | OpenTelemetry — trace across service boundaries |
| NFR-6.3 | Metrics | Service-level metrics (RED — Rate, Errors, Duration); business metrics (applications, matches, conversions) |
| NFR-6.4 | Alerting | PagerDuty/OpsGenie integration; on-call rotation; SLA-based alert thresholds |
| NFR-6.5 | LLM observability | Token usage, latency, cost, quality metrics per model and per agent |
| NFR-6.6 | Dashboard | Real-time operational dashboard + business metrics dashboard |

### NFR-7: Accessibility & UX

| ID | Requirement | Detail |
|----|------------|--------|
| NFR-7.1 | WCAG compliance | WCAG 2.2 AA by V1 |
| NFR-7.2 | Responsive design | Full functionality on mobile web (V1); native mobile apps (V2) |
| NFR-7.3 | Multi-language UI | English + 5 languages by V2 |
| NFR-7.4 | Dark mode | System-default, manual toggle |
| NFR-7.5 | Loading states | Skeleton screens, progress indicators for all AI generation tasks |

---

## 8. Success Metrics

### 8.1 North Star Metric

> **"Dream Jobs Landed"** — The number of users who accept a job offer where the match score was ≥ 85% AND the user reports satisfaction ≥ 4/5 after 90 days.

### 8.2 Key Performance Indicators (KPIs)

#### Acquisition
| Metric | Target (12 months) |
|--------|-------------------|
| Monthly signups | 50,000 |
| Signup-to-profile-completion rate | > 70% |
| Profile completion rate (all sections filled) | > 60% |
| CAC (blended) | < $15 |
| Organic acquisition % | > 40% |

#### Activation
| Metric | Target |
|--------|--------|
| Time-to-first-value (first job match viewed) | < 2 minutes from profile completion |
| First-week application rate (% who apply through Pathfinder) | > 50% |
| Resume tailoring adoption | > 40% of applications use tailored resume |

#### Engagement
| Metric | Target |
|--------|--------|
| DAU/MAU | > 35% (active searchers), > 15% (passive) |
| Average session duration | > 8 minutes |
| Jobs viewed per active user per week | > 50 |
| Applications per active user per week | > 8 |
| Feature adoption breadth (% using 4+ features) | > 50% |

#### Quality (Agent Performance)
| Metric | Target |
|--------|--------|
| Match precision (user saves or applies to matched jobs) | > 65% |
| Match recall (% of user's eventual applications that were surfaced by agent) | > 80% |
| Resume tailoring acceptance rate (% of AI suggestions kept by user) | > 75% |
| Cover letter acceptance rate | > 70% |
| Job deduplication accuracy | > 98% |
| Job freshness (new listings surfaced within 4 hours) | > 90% |

#### Outcome
| Metric | Target |
|--------|--------|
| Interview rate (interviews / applications) | > 15% (vs. ~5% industry average for tech) |
| Offer rate (offers / interviews) | 1 per 5–8 interviews (role-dependent) |
| Time-to-placement (profile complete → offer accepted) | < 45 days median for active searchers |
| Placement rate (% of active users who accept an offer within 6 months) | > 60% |
| Offer satisfaction score | > 4.0/5.0 |
| 90-day job satisfaction | > 4.0/5.0 |

#### Retention & Revenue
| Metric | Target |
|--------|--------|
| Month-1 retention | > 60% |
| Month-3 retention | > 45% |
| Month-6 retention | > 30% (active searchers churn naturally after placement) |
| Post-placement retention (% who stay subscribed after accepting offer) | > 20% at month 3 |
| Pro conversion rate (free → paid) | > 8% |
| Premium conversion rate (Pro → Premium) | > 15% |
| Monthly churn (paid users) | < 5% |
| LTV:CAC ratio | > 4:1 by month 18 |
| ARPU (blended) | > $18 |

### 8.3 Counter-Metrics (Watch for Negative Externalities)

| Metric | Why It Matters |
|--------|----------------|
| Application spray index (avg apps/user/week) | > 40/week may indicate quality collapse — users mass-applying without discernment |
| Resume homogenization score | If all tailored resumes converge to identical patterns, we're not actually tailoring |
| False positive rate on matches | Users dismissing high-scored matches in quick succession signals model drift |
| Agent override rate | If users reject > 50% of agent actions, trust is broken |
| Diversity of companies applied to | Concentration in top-N companies suggests recommendation bias |
| User-reported stress/anxiety | Job search is emotional — if NPS comments show increased anxiety, we're adding pressure not removing it |

---

## 9. MVP Scope — "Pathfinder Core"

**Timeline:** 12–14 weeks with 4–5 engineers + 1 PM + 1 designer
**Goal:** Prove the core loop — profile → discover → match → tailor → apply → track — delivers value that users will pay for.

### 9.1 MVP Feature Set

#### Profile Management (FR-1 subset)
- Resume upload + parsing (PDF, DOCX)
- LinkedIn profile import (PDF export method — no API dependency)
- Manual profile editing (work history, education, skills with proficiency)
- Skill extraction with auto-tagging (Beginner/Intermediate/Advanced/Expert)
- No GitHub import yet (V1)

#### Job Discovery (FR-2 subset)
- **10 initial sources:** LinkedIn (public listings), Indeed (public), Wellfound (AngelList), Y Combinator Jobs, Hacker News "Who's Hiring" (monthly parse), Greenhouse boards (public), Lever boards (public), Workday boards (top 50 companies), Stack Overflow Jobs, GitHub Jobs
- Daily sweep frequency
- Basic deduplication (exact title + company + location match)
- Freshness scoring (first-seen date)
- No enrichment yet (V1)

#### Matching (FR-3 subset)
- Semantic skill match (embedding similarity + keyword overlap)
- Experience level match (years, title hierarchy)
- Location + remote match
- Simple weighted scoring (configurable slider: skills vs. compensation vs. culture)
- Match explanation: "You match because..." with top 3 reasons
- Real-time re-ranking from user feedback

#### Resume Tailoring (FR-4 subset)
- 3 ATS-optimized base templates
- Job-specific tailoring (skill reorder, summary rewrite, bullet emphasis)
- Side-by-side diff review
- Resume variant saving
- PDF export only

#### Cover Letters (FR-5 subset)
- Job-specific cover letter generation
- Evidence-backed (no hallucination)
- Basic editing interface
- PDF + text export

#### Application Tracking (FR-6 subset)
- Kanban pipeline (Saved → Applied → Interview → Offer → Accepted/Rejected)
- Manual status updates
- Basic task management (to-dos with deadlines)
- Deadline nudges
- No email/calendar integration (V1)

#### Communication (FR-7 subset)
- Follow-up email generation (3 templates)
- Thank-you email generation (post-interview)
- Communication log per application

#### Interview Prep (FR-8 subset)
- Company interview guide (Glassdoor aggregation + LLM synthesis)
- Role-specific question bank
- STAR-framework behavioral answer generation
- "Questions to ask interviewer" generator

#### Memory & Learning (FR-10 subset)
- Basic user preference model (explicit: what user said they want)
- Implicit feedback tracking (view/save/apply/dismiss → preference weight updates)
- Session persistence (user doesn't lose state between logins)

#### Proactive Features (FR-11 subset)
- Daily digest email (top 5 matches)
- Deadline nudges
- "New match" push notification for ≥ 90% matches

### 9.2 MVP Out of Scope (Deferred to V1+)
- GitHub import
- 200+ job sources
- Company enrichment (funding, culture, tech radar)
- Email/calendar integration
- A/B resume testing
- Mock interview simulator
- Learning plans / skill gap analysis
- Passive monitoring mode
- Autopilot mode
- Multi-language support
- Native mobile apps
- Advanced analytics dashboard
- Collaborative filtering
- Compensation prediction
- Offer comparison / negotiation tools

### 9.3 MVP Tech Stack (Recommended)

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Frontend** | Next.js 15 + React 19 + TypeScript + Tailwind CSS + shadcn/ui | SEO-friendly, fast iteration, strong ecosystem |
| **Backend** | Python (FastAPI) + Node.js (for real-time features) | Python for AI/ML pipeline; Node.js for API gateway |
| **Database** | PostgreSQL (primary) + pgvector (vector embeddings) + Redis (caching, queues) | Relational + vector in one DB; Redis for perf |
| **Job Queue** | Celery + Redis / BullMQ | Async job processing for discovery sweeps, LLM calls |
| **LLM Gateway** | LiteLLM / custom proxy | Multi-provider with fallback, cost tracking, rate limiting |
| **LLM Providers** | Claude (Anthropic), GPT-4o (OpenAI) — primary; Gemini, Llama (Meta) — fallback | Quality primary, cost-optimized for bulk tasks |
| **Search** | Meilisearch / Elasticsearch | Fast full-text search over job listings |
| **Infrastructure** | AWS (ECS Fargate / EKS) + Terraform | Managed container orchestration, infra-as-code |
| **CI/CD** | GitHub Actions + Docker | Standard pipeline |
| **Monitoring** | Datadog / Grafana + Sentry | APM + error tracking |
| **Auth** | Clerk / Auth0 | Managed auth with social OAuth |
| **Email** | Resend / SendGrid | Transactional + digest emails |

### 9.4 MVP Success Criteria (Go/No-Go for V1)

1. **Activation:** > 50% of users who complete profile view at least 10 job matches and save at least 3
2. **Engagement:** > 30% of weekly active users apply to at least 1 job through Pathfinder
3. **Quality:** Resume tailoring acceptance rate > 60% (user keeps > 60% of AI suggestions)
4. **Outcome:** > 20% of active users (30+ days on platform) report receiving at least 1 interview
5. **NPS:** > 30 from cohort of users active > 14 days
6. **Paid conversion:** > 5% of free users convert to Pro within 60 days

---

## 10. V1 Scope — "Pathfinder Pro"

**Timeline:** 6 months after MVP (months 3–9)
**Goal:** Expand depth, intelligence, and reach. Become the definitive AI career agent for technical professionals.

### 10.1 V1 Feature Additions

#### Sources & Discovery Expansion
- Scale to 200+ job sources (all major boards, top 500 company career pages, community channels)
- Intelligent deduplication (fuzzy matching for cross-posted jobs)
- Job description enrichment pipeline (inferred tech stack, remote policy, compensation from text)
- "Hidden market" discovery (Twitter/X job threads, Discord communities, newsletter job boards)
- Company enrichment (Crunchbase funding, employee count trend, tech blog analysis, Glassdoor/Blind sentiment extraction)
- Sub-4-hour freshness for high-priority sources

#### Matching Intelligence
- Weighted preference model with ranked priorities (fully implemented)
- Negative matching (dealbreaker detection)
- Collaborative filtering (similar user → similar job patterns)
- Temporal signals (freshness boost, seasonal hiring patterns, urgency detection "urgently hiring")

#### Resume & Documents
- GitHub profile import and skill extraction
- Achievement quantification engine (rewrite bullets with metrics)
- Gap identification with honest handling strategy
- Multi-format export (PDF, DOCX, TXT, LaTeX)
- 10+ ATS-optimized templates with role/industry variants

#### Cover Letter Evolution
- Company-specific personalization (news, product launches, mission alignment)
- Tone customization (professional, enthusiastic, concise)
- Multi-variant cover letter generation

#### Application Intelligence
- Email integration (Gmail OAuth) — auto-detect interview invites, rejections, recruiter messages
- Basic analytics dashboard (funnel metrics, response rates, source effectiveness)
- Recruiter response drafting

#### Interview Preparation
- Technical practice problem recommendation (tagged by company/role)
- System design interview preparation framework
- Post-interview debrief and feedback capture tools

#### Learning & Growth
- Skill gap analysis (MVP version — JD requirement comparison)
- Personalized learning plan generation (3 learning resources per gap)
- Learning resource curation engine

#### Proactive Capabilities
- Passive monitoring mode (low-frequency sweeps, high-threshold alerts)
- "Dream job alert" — user defines dream job profile, agent alerts on rare high matches
- Interview preparation reminders (calendar-aware)
- Weekly market intelligence digest

#### Agent Architecture
- Modular sub-agent architecture (Discovery Agent, Match Agent, Resume Agent, Cover Letter Agent, Interview Prep Agent, Coach Agent)
- Agent handoff protocol with structured context
- Parallel agent execution for independent tasks
- Agent action log with rationale (explainability)

#### Social & Sharing
- Referral opportunity detection (2nd-degree LinkedIn connections at target companies)
- Warm introduction message generation

### 10.2 V1 Tech Expansions
- Vector database optimization (pgvector → dedicated vector DB if scale demands: Pinecone/Qdrant/Milvus)
- Multi-region DB read replicas (US-East, EU-West)
- Caching layer expansion (Redis Cluster)
- LLM cost optimization (fine-tuned smaller models for classification/extraction tasks; large models for generation)
- A/B experiment framework for matching and tailoring algorithms
- Enhanced monitoring and alerting

### 10.3 V1 Success Criteria
1. **Coverage:** > 90% of jobs user would find manually are surfaced by Pathfinder within 48 hours
2. **Match quality:** User save/apply rate on top-10 matches > 70%
3. **Tailoring quality:** > 80% AI suggestion acceptance rate
4. **Interview rate:** Pathfinder users achieve > 2× industry average interview rate
5. **NPS:** > 50
6. **Revenue:** $50K MRR by month 9

---

## 11. V2 Scope — "Pathfinder Scale"

**Timeline:** 12 months after V1 (months 9–21)
**Goal:** Scale to 100K+ users. Add premium features. Become a platform. Expand beyond initial personas.

### 11.1 V2 Feature Additions

#### Platform & Scale
- **Native mobile apps** — iOS + Android (React Native / Flutter) with push notifications, offline job saving, mobile-first application flow
- **Multi-language support** — UI in English, Spanish, Hindi, French, German, Portuguese, Mandarin; resume/CL generation in 10+ languages
- **Calendar integration** — Google Calendar + Outlook — auto-detect interviews, block prep time, schedule follow-ups
- **Browser extension** — one-click job save from any website, auto-detect application forms, autofill from Pathfinder profile

#### Advanced Matching
- Compensation prediction model (ML-based salary estimation when not listed)
- Interview probability estimation (likelihood of interview based on historical patterns)
- Diversity-aware matching (serendipity engine for adjacent roles)
- Culture fit estimation (NLP on company communications, employee reviews, tech blogs)

#### Interview Simulation
- AI mock interviewer — voice-based, role-specific, adapts difficulty in real-time
- Delivery feedback — pacing, filler words, clarity, confidence markers
- Technical assessment simulation — coding challenges, system design whiteboarding, ML case studies
- Interview performance tracking and trend analysis

#### Application Intelligence V2
- ATS simulation — predict how user's tailored resume will parse in major ATS systems
- A/B testing of resume variants with automated performance tracking
- Offer comparison tool — side-by-side compensation, equity, benefits, culture, growth modeling
- Negotiation support — market data comps, script templates, counter-offer strategy, total compensation calculator

#### Learning & Growth V2
- Learning progress tracking and skill reassessment
- Project-based learning recommendations (specific projects that fill gaps)
- Market demand signals — real-time tracking of which skills are trending in job descriptions
- Career timeline visualization

#### Social & Network
- Anonymized community insights — "Engineers in your market with your YOE are getting..."
- User-contributed interview experiences (anonymized, moderated)
- Peer resume review (opt-in community feature)

#### Agent Evolution
- Autopilot mode (Premium tier) — auto-apply to jobs above threshold with user-configurable rules
- Preference drift detection — agent notices user's tastes changing over time
- Agent quality monitoring — per-agent success metrics, degradation alerts
- Cross-agent learning — improvements to one agent (e.g., matching) improve downstream agents (e.g., tailoring)

#### Enterprise Features
- University/career-center dashboard — bulk student management
- Bootcamp partner integration — cohort tracking, placement analytics
- Outplacement firm white-label — branded experience for transition services
- API access for partners

### 11.2 V2 Tech Expansions
- Multi-region active-active deployment (US, EU, APAC)
- Real-time job discovery via streaming (Kafka/Kinesis) for high-frequency sources
- Fine-tuned in-house models for resume tailoring, matching, and skill extraction
- Voice pipeline for mock interviews (STT → LLM → TTS)
- SOC 2 Type II certification
- Enhanced data pipeline with dbt for analytics

### 11.3 V2 Success Criteria
1. **Scale:** 100K+ registered users, 15K+ paid subscribers
2. **Engagement:** DAU/MAU > 40% (active searchers)
3. **Outcomes:** > 5,000 placements attributed to Pathfinder
4. **Revenue:** $500K MRR
5. **NPS:** > 60
6. **Enterprise:** 10+ institutional partnerships

---

## 12. Future Roadmap — V3 and Beyond

### V3: "Pathfinder Network" (Year 3)

**Vision:** Pathfinder becomes a two-sided marketplace connecting candidates, employers, and educators.

| Area | Features |
|------|----------|
| **Employer Side** | Employer profiles with verified culture data, direct application API, "Pathfinder Certified" employer badge for responsive/transparent hiring, employer analytics (who's viewing, applying, converting) |
| **Recruiter Tools** | AI-suggested candidate matches (opt-in by candidates), anonymized candidate discovery, interview scheduling automation |
| **Learning Marketplace** | Integrated course purchases, certification tracking with verified completion, employer-sponsored learning paths, income-share agreement facilitation |
| **Career Management** | Continuous career OS — not just job search but career planning, internal mobility tracking, promotion preparation, compensation benchmarking alerts |
| **AI Career Coach** | Fully conversational career coach with persistent memory, multi-session coaching plans, emotional/mindset support, accountability partnerships |
| **Global Expansion** | Country-specific compliance, local job board integrations, local language models, regional compensation data |

### V4: "Pathfinder Intelligence" (Year 4–5)

**Vision:** Pathfinder becomes the intelligence layer for the global labor market.

| Area | Features |
|------|----------|
| **Labor Market Intelligence** | Real-time skill demand tracking, compensation trend prediction, geographic talent flow analysis, industry transformation signals |
| **Predictive Career Modeling** | "Where will your career be in 5 years?" — ML models trained on millions of career trajectories, scenario planning ("What if I learn Rust?"), optimal path recommendation |
| **Skills Ontology** | Comprehensive global skills taxonomy with relationships, prerequisite chains, and demand forecasting — powering the entire platform |
| **API Economy** | Public API for third-party career tools, embeddable Pathfinder widgets for company career pages, integration with HRIS/ATS systems |
| **Research** | Publish labor market research, partner with academic institutions, contribute to workforce policy |

---

## 13. System Architecture — High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                   │
│                                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐    │
│  │ Web App  │  │ iOS App  │  │ Android  │  │ Browser Extension    │    │
│  │(Next.js) │  │  (V2)    │  │ App (V2) │  │ (V2)                 │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘    │
│       └──────────────┴─────────────┴───────────────────┘                │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────────────┐
│                           API GATEWAY                                    │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              FastAPI + Kong / Envoy (rate limit, auth, routing)   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────────────┐
│                        CORE SERVICES LAYER                               │
│                                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │ Profile  │ │Job Disc. │ │ Matching │ │ Resume   │ │ Cover    │     │
│  │ Service  │ │ Service  │ │ Engine   │ │ Engine   │ │ Letter   │     │
│  │          │ │          │ │          │ │          │ │ Engine   │     │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘     │
│       │            │            │            │            │            │
│  ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐     │
│  │Interview │ │Learning  │ │Appl.Track│ │ Comm.    │ │ Analytics│     │
│  │Prep Svc  │ │Engine    │ │Service   │ │ Service  │ │ Service  │     │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘     │
│       └─────────────┴────────────┴────────────┴────────────┘           │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────────────┐
│                         AI ORCHESTRATION LAYER                           │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     Agent Orchestrator                            │   │
│  │  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────────────┐   │   │
│  │  │Discovery│  │ Match   │  │ Tailor   │  │ Interview Coach  │   │   │
│  │  │ Agent   │  │ Agent   │  │ Agent    │  │ Agent            │   │   │
│  │  └─────────┘  └─────────┘  └──────────┘  └──────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────┐  ┌──────────────────────────────────┐      │
│  │   LLM Gateway           │  │   Memory & Context Service       │      │
│  │   (LiteLLM/custom)      │  │   (vector + relational + graph)  │      │
│  │   Multi-provider        │  │   User model + session +         │      │
│  │   Fallback chains       │  │   career narrative               │      │
│  └─────────────────────────┘  └──────────────────────────────────┘      │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────────────┐
│                          DATA LAYER                                      │
│                                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │PostgreSQL│  │pgvector  │  │  Redis   │  │Elastic-  │  │   S3     │  │
│  │(primary) │  │(vectors) │  │(cache/Q) │  │ search   │  │(docs,    │  │
│  │          │  │          │  │          │  │(jobs)    │  │ resumes) │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

### Key Architecture Decisions

1. **Modular monolith → microservices evolution:** MVP starts as modular monolith (FastAPI with clear service boundaries). Extract to microservices when scale demands (V1+). Premature microservice extraction kills velocity.

2. **Multi-model LLM strategy:** No single model provider. Primary: Claude (complex reasoning, generation) + GPT-4o (fast classification, extraction). Secondary: Gemini (cost-effective for bulk). Local: fine-tuned smaller models (Mistral/Llama) for high-volume extraction tasks.

3. **Vector embeddings everywhere:** User profiles, job descriptions, resumes, company profiles all embedded. Embedding similarity powers matching, deduplication, and discovery. Model: text-embedding-3-large (OpenAI) or voyage-2 (Voyage AI) for quality; all-MiniLM-L6 for cost-sensitive bulk.

4. **Memory as first-class service:** Not just a feature. A dedicated Memory Service manages user models, session context, preference weights, and career narratives. This is our moat — invest heavily.

5. **Async-first for AI workloads:** All LLM calls go through job queues with priority lanes. Interactive (user waiting) → high priority. Batch (discovery sweeps) → normal priority. Background (analytics, enrichment) → low priority.

---

## 14. AI/ML Strategy

### 14.1 Model Selection Philosophy

| Task Type | Model Strategy | Rationale |
|-----------|---------------|-----------|
| Complex reasoning (matching explanation, career coaching, interview prep) | Claude Opus / Sonnet | Best reasoning quality, nuanced output |
| Content generation (resumes, cover letters, emails) | Claude Sonnet / GPT-4o | High quality, good instruction following |
| Structured extraction (resume parsing, JD parsing, skill extraction) | GPT-4o-mini / Claude Haiku + structured output | Fast, cheap, reliable schema adherence |
| Classification & filtering (job categorization, seniority detection, spam filtering) | Fine-tuned small models (Mistral 7B, Llama 8B) or Haiku | Cost-effective at scale, fast |
| Embeddings (semantic search, matching, clustering) | text-embedding-3-large / voyage-2 | Top-tier embedding quality |
| Voice (mock interviews) | Whisper (STT) + Claude/GPT-4o (response) + ElevenLabs/OpenAI TTS (voice) | Best-in-class each component |

### 14.2 Model Fallback Chain

```
Primary Model (e.g., Claude Sonnet)
  ├── Timeout/Error → Secondary Model (e.g., GPT-4o)
  │     ├── Timeout/Error → Tertiary (e.g., Gemini Pro)
  │     │     ├── Timeout/Error → Cached response (if available)
  │     │     └── Timeout/Error → Graceful degradation message to user
```

### 14.3 Quality Assurance for AI Outputs

- **Hallucination prevention:** Resume/CL generation must ONLY reference confirmed profile facts. Prompt engineering + structured output validation + post-generation factuality check.
- **Bias detection:** Regular audits of match scores and recommendations across demographic dimensions. De-biasing prompts and re-ranking.
- **Output validation:** Structured outputs validated against JSON Schema. Free-text outputs run through content safety and factuality classifiers.
- **Human evaluation:** Weekly blind evaluation of 100 random AI outputs by internal team. Quality score tracked over time.

### 14.4 Cost Optimization

| Tier | LLM Spend Target | Strategy |
|------|-----------------|----------|
| Free | < $0.50/user/month | Cached embeddings, smaller models, limited generations |
| Pro | < $3/user/month | Primary models for core features, batch processing off-peak |
| Premium | < $8/user/month | Best models, more frequent sweeps, voice features |

Optimization levers: prompt caching (Anthropic), semantic caching for identical/similar requests, embedding pre-computation, model distillation for high-volume tasks, batch processing during low-cost windows.

---

## 15. Data Model — Conceptual Overview

### 15.1 Core Entities

```
User
├── user_id (PK)
├── email, auth_provider, auth_id
├── full_name, headline, location, timezone
├── tier (free/pro/premium)
├── mode (active/passive/autopilot)
├── preferences (JSONB) — ranked priorities, constraints, dealbreakers
├── user_embedding (vector(3072)) — semantic profile embedding
├── created_at, updated_at

Profile
├── profile_id (PK)
├── user_id (FK)
├── version (integer) — profile versioning
├── raw_source (JSONB) — original parsed data
├── structured_data (JSONB) — canonical profile
│   ├── work_experiences[]
│   ├── education[]
│   ├── skills[{name, proficiency, category, last_used}]
│   ├── projects[]
│   ├── certifications[]
│   ├── publications[]
│   ├── languages[]
│   └── links[]
├── summary (text) — LLM-generated professional summary
├── career_narrative_embedding (vector)
├── is_active, created_at, updated_at

Job
├── job_id (PK)
├── canonical_job_id — deduplication key
├── title, company, location, remote_policy
├── description_raw, description_cleaned
├── source_url, source_type, first_seen_at, last_seen_at, is_active
├── inferred_metadata (JSONB)
│   ├── tech_stack[]
│   ├── seniority_level
│   ├── salary_range {min, max, currency}
│   ├── required_skills[]
│   ├── nice_to_have_skills[]
│   ├── company_stage, team_size
│   └── industry, domain
├── job_embedding (vector(3072))
├── created_at, updated_at

Application
├── application_id (PK)
├── user_id (FK), job_id (FK)
├── status (enum: saved/applied/phone_screen/tech_interview/onsite/offer/accepted/rejected/withdrawn)
├── resume_variant_id (FK), cover_letter_id (FK)
├── applied_at, last_updated_at
├── notes (text)
├── communications[] (JSONB)
├── interviews[] (JSONB)
├── source_channel (how user found this job)

ResumeVariant
├── resume_id (PK)
├── user_id (FK), base_resume_id (FK, nullable)
├── name, description
├── content (JSONB) — structured resume content
├── template_id, formatting_options
├── tailored_for_job_id (FK, nullable)
├── tailored_for_role_type (string)
├── performance_metrics (JSONB) — track callback rate, etc.
├── created_at, updated_at

CoverLetter
├── cover_letter_id (PK)
├── user_id (FK), application_id (FK, nullable)
├── content, tone, version
├── created_at

UserFeedback
├── feedback_id (PK)
├── user_id (FK)
├── target_type (job_match/resume_tailoring/cover_letter/interview_prep)
├── target_id — polymorphic FK
├── feedback_type (explicit_rating/implicit_action/override)
├── value (JSONB)
├── created_at

LearningPlan
├── plan_id (PK)
├── user_id (FK)
├── target_role, target_timeline
├── skill_gaps[] (JSONB)
├── learning_items[{resource_url, resource_type, estimated_hours, priority, status}]
├── created_at, updated_at

AgentAction
├── action_id (PK)
├── user_id (FK)
├── agent_type, action_type
├── input_context (JSONB), output (JSONB)
├── rationale (text) — explainable AI
├── user_approved (bool), user_modified (bool)
├── latency_ms, model_used, tokens_used, cost
├── created_at
```

### 15.2 Key Indices
- `job_embedding` — vector index (IVFFlat / HNSW) for similarity search
- `user_embedding` — vector index for collaborative filtering
- `(user_id, status)` on applications — user pipeline queries
- `(canonical_job_id, source_type)` — deduplication
- `(first_seen_at, is_active)` — freshness filtering
- `(user_id, created_at)` on feedback, agent_actions — user history

---

## 16. Risk Register & Mitigation

| Risk ID | Risk | Severity | Likelihood | Mitigation |
|---------|------|----------|------------|------------|
| R-1 | **LLM quality degradation** — Model updates or provider changes degrade output quality | High | Medium | Multi-model redundancy; regression test suite with golden outputs; canary deployments for model changes; provider abstraction layer |
| R-2 | **ATS blacklisting** — Employers blacklist applications submitted via AI tools | Critical | Medium | Human-in-the-loop gates; randomized submission patterns; authentic, non-spammy behavior; transparency features that employers value |
| R-3 | **Privacy breach** — User resume/application data exposed | Critical | Low | Field-level encryption; SOC 2 compliance; penetration testing; data processing agreements; minimal data retention |
| R-4 | **Bias in matching** — Algorithmic bias disadvantaging protected groups | High | Medium | Regular bias audits; diverse training data; de-biasing prompts; human review; transparency reports |
| R-5 | **Legal/regulatory** — AI-generated employment content regulated (EU AI Act, NYC Local Law 144) | High | Medium | Legal counsel retained; compliance-first architecture; human-in-the-loop; transparency disclosures; audit trails |
| R-6 | **Platform dependency** — LinkedIn/Indeed API access revoked or restricted | High | High | Multi-source strategy; no single-source dependency; web scraping fallbacks; direct company career page integrations |
| R-7 | **LLM cost overrun** — Token costs exceed budget at scale | Medium | High | Tiered model strategy; prompt caching; semantic caching; fine-tuned smaller models; cost monitoring and alerts; per-user cost caps |
| R-8 | **User trust erosion** — Agent applies to wrong jobs or generates inaccurate content | High | Medium | Review gates; explainability; undo/revert; user control granularity; quality metrics tracking; feedback loops |
| R-9 | **Competitive response** — LinkedIn, Indeed, or major players launch competing AI agents | High | Medium | Memory moat (switching cost); community and network effects; depth over breadth in initial personas; move faster |
| R-10 | **Scalability bottlenecks** — System can't handle job discovery at target scale | Medium | Medium | Async architecture from day one; horizontally scalable services; load testing at 10× expected volume; cloud auto-scaling |
| R-11 | **User fatigue** — Too many notifications, agent too proactive, users disengage | Medium | Medium | Intelligent frequency capping; user-controlled notification settings; engagement quality metrics; "snooze" and "pause" features |
| R-12 | **Hallucinated achievements** — AI fabricates experience in tailored resumes | Critical | Low | Strict grounding — generation only from confirmed profile data; post-generation factuality check; user review required before sending; clear diff highlighting changes |

---

## 17. Appendix

### A. Glossary

| Term | Definition |
|------|-----------|
| **ATS** | Applicant Tracking System — software used by employers to manage hiring pipelines (e.g., Greenhouse, Lever, Workday) |
| **JD** | Job Description |
| **Semantic Matching** | Matching based on meaning and context, not just keyword overlap — powered by vector embeddings |
| **Canonical Job** | A deduplicated job listing that merges duplicate postings from different sources |
| **Career Narrative** | The AI-constructed long-form story of a user's career — used for contextual understanding |
| **Autopilot** | Premium feature where the agent auto-applies to high-match jobs within user-defined guardrails |
| **Callback Rate** | Percentage of applications that result in an interview invitation |
| **STAR** | Situation, Task, Action, Result — structured framework for behavioral interview answers |
| **LLM Gateway** | Abstraction layer that routes LLM requests to appropriate providers with fallback, cost tracking, and rate limiting |
| **HITL** | Human-in-the-Loop — the user must approve before the agent acts |

### B. References & Inspiration

- **Teal** — Resume builder and job tracking (UI/UX inspiration)
- **Simplify.jobs** — Autofill job applications (application automation inspiration)
- **Huntr** — Kanban job tracking (pipeline management inspiration)
- **Careerflow.ai** — AI job search CRM (feature breadth inspiration)
- **Rezi** — AI resume builder (ATS optimization inspiration)
- **levels.fyi** — Compensation data (market intelligence inspiration)
- **Blind** — Anonymous company reviews (culture signal inspiration)
- **Prequel** — Chrome extension for job applications

### C. Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-17 | Product & Engineering | Initial PRD — all sections |

### D. Next Steps

1. **Stakeholder review** — Product, Engineering, Design, and Leadership review and align on PRD
2. **Technical design doc** — Detailed architecture, data models, API contracts (2 weeks)
3. **Design sprints** — UX research, wireframes, high-fidelity mockups for MVP (4 weeks)
4. **Staffing plan** — Finalize engineering team composition and hiring needs
5. **MVP development kickoff** — Sprint 0 infrastructure setup, CI/CD, scaffolding
6. **Alpha launch** — Internal team + 50 beta users (target: week 10)
7. **Public MVP launch** — (target: week 14)

---

> *"The best time to look for a job is when you don't need one. The second best time is with Pathfinder."*
> — Product Vision Statement

**End of Document**
