# Pathfinder — Multi-Agent System Design

**Document Version:** 1.0
**Date:** 2026-06-17
**Role:** Staff AI Engineer
**Framework:** LangGraph (StateGraph + Subgraphs)
**Classification:** Confidential — Internal

---

## Table of Contents

1. [Agent Architecture Overview](#1-agent-architecture-overview)
2. [Agent Specifications](#2-agent-specifications)
   - [2.1 Profile Agent](#21-profile-agent)
   - [2.2 Job Discovery Agent](#22-job-discovery-agent)
   - [2.3 Job Matching Agent](#23-job-matching-agent)
   - [2.4 Resume Agent](#24-resume-agent)
   - [2.5 Cover Letter Agent](#25-cover-letter-agent)
   - [2.6 Memory Agent](#26-memory-agent)
   - [2.7 Interview Agent](#27-interview-agent)
   - [2.8 Career Coach Agent](#28-career-coach-agent)
   - [2.9 Application Tracking Agent](#29-application-tracking-agent)
   - [2.10 Follow-up Agent](#210-follow-up-agent)
3. [Supervisor Agent](#3-supervisor-agent)
4. [Agent Orchestration](#4-agent-orchestration)
5. [Agent Communication](#5-agent-communication)
6. [State Management](#6-state-management)
7. [Retry Mechanisms](#7-retry-mechanisms)
8. [Human Approval Workflows](#8-human-approval-workflows)
9. [Agent Evaluation Framework](#9-agent-evaluation-framework)

---

## 1. Agent Architecture Overview

### 1.1 Agent Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MULTI-AGENT SYSTEM TOPOLOGY                           │
│                                                                              │
│                          ┌─────────────────┐                                  │
│                          │  ENTRY GATEWAY   │                                  │
│                          │  (User Intent)   │                                  │
│                          └────────┬────────┘                                  │
│                                   │                                           │
│                          ┌────────┴────────┐                                  │
│                          │   SUPERVISOR    │                                  │
│                          │     AGENT       │◄──────── MEMORY AGENT ───────┐  │
│                          │                 │                             │  │
│                          │  Intent Router  │                             │  │
│                          │  Task Planner   │                             │  │
│                          │  Result Merger  │                             │  │
│                          │  Quality Gate   │                             │  │
│                          └───┬───┬───┬───┬─┘                             │  │
│                              │   │   │   │                               │  │
│     ┌────────────────────────┼───┼───┼───┼──────────────────┐            │  │
│     │                        │   │   │   │                  │            │  │
│     ▼                        ▼   ▼   ▼   ▼                  ▼            │  │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐ │  │
│  │PROFILE │  │ JOB    │  │ MATCH  │  │RESUME  │  │COVER   │  │INTERVW │ │  │
│  │ AGENT  │  │DISCVRY │  │ AGENT  │  │ AGENT  │  │LETTER  │  │ AGENT  │ │  │
│  │        │  │ AGENT  │  │        │  │        │  │ AGENT  │  │        │ │  │
│  │Parse & │  │Scrape &│  │Score & │  │Tailor &│  │Generate│  │Prep &  │ │  │
│  │Enrich  │  │Dedup   │  │Rank    │  │Format  │  │& Adapt │  │Simulate│ │  │
│  └────┬───┘  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘ │  │
│       │          │           │           │           │           │       │  │
│  ┌────┴───┐  ┌───┴────┐  ┌───┴────┐  ┌───┴────┐  ┌───┴────┐  ┌───┴────┐ │  │
│  │CAREER  │  │APPLCTN │  │FOLLOWUP│  │MEMORY  │  │        │  │        │ │  │
│  │COACH   │  │TRACKING│  │ AGENT  │  │ AGENT  │  │        │  │        │ │  │
│  │ AGENT  │  │ AGENT  │  │        │  │        │  │        │  │        │ │  │
│  │        │  │        │  │Generate│  │Persist │  │        │  │        │ │  │
│  │Gap &   │  │Track & │  │& Send  │  │&Retriev│  │        │  │        │ │  │
│  │Learn   │  │Analyze │  │        │  │        │  │        │  │        │ │  │
│  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘ │  │
│                                                                          │
│  LEGEND:                                                                  │
│  ──── Synchronous handoff (Supervisor routes directly)                    │
│  ◄─── Asynchronous context injection (Memory Agent enriches state)        │
│  ···· Parallel execution possible (independent agents)                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Agent Classification

| Tier | Agents | Trigger | Latency Budget | User-Facing |
|------|--------|---------|---------------|-------------|
| **Interactive** | Supervisor, Profile, Resume, Cover Letter, Interview, Career Coach, Follow-up | User request | < 8s (streaming) | Direct |
| **Near-Real-Time** | Job Matching | User request or event | < 2s (cached), < 8s (fresh) | Direct |
| **Background** | Job Discovery | Cron / event | Minutes to hours | Indirect (results surfaced later) |
| **System** | Memory, Application Tracking | Event-driven | < 1s (write), < 500ms (read) | Indirect |

### 1.3 Design Principles

| Principle | Description |
|-----------|-------------|
| **Single Responsibility** | Each agent does exactly one thing. No agent overlaps another's core function. |
| **Stateless Execution** | Agents are stateless functions. State lives in the LangGraph state object + checkpointer. |
| **Explicit Context** | Agents receive exactly the context they need — no more, no less. Context is assembled by the Supervisor from Memory. |
| **Fail Independently** | An agent failure does not crash the graph. Supervisor catches, logs, and routes to fallback or graceful degradation. |
| **Observable by Default** | Every agent execution logged with input hash, output hash, latency, tokens, tool calls, and success/failure. |
| **Human Gate Configurable** | Every agent can be configured with a pre-execution or post-execution human approval gate. |

---

## 2. Agent Specifications

### 2.1 Profile Agent

#### Purpose
Extract, structure, enrich, and maintain the user's professional identity from raw inputs (resume files, LinkedIn exports, GitHub profiles, manual text). Produces a unified, deduplicated, versioned profile that serves as the single source of truth for all other agents.

#### Inputs

| Input | Source | Format | Required |
|-------|--------|--------|----------|
| Resume file | User upload | PDF, DOCX, TXT (max 10MB) | On first use |
| LinkedIn export | User upload or OAuth | PDF export or API JSON | Optional |
| GitHub username | User input | String | Optional |
| Manual profile data | User form input | Structured JSON | Optional (fill gaps) |
| Existing profile version | Database (PostgreSQL) | Profile schema | On update |

#### Outputs

| Output | Destination | Schema |
|--------|-------------|--------|
| Structured profile | PostgreSQL (profile table) + pgvector (embedding) | See state schema below |
| Extraction confidence report | User UI + Supervisor | `{field: confidence_0_to_1}` |
| Suggested enrichments | User UI (review queue) | `[{field, current, suggested, source}]` |
| Profile embedding vector | pgvector | 3072-dimensional vector |
| Skill vectors (per skill) | pgvector | 1536-dimensional vector per skill |

#### Tools

| Tool | Type | Description |
|------|------|-------------|
| `parse_resume` | LLM + Rules | Extracts structured data from resume text. Uses DeepSeek for semantic extraction, regex for phone/email/date patterns. |
| `parse_linkedin` | API + LLM | Parses LinkedIn export. Maps LinkedIn schema → internal profile schema. |
| `fetch_github_profile` | GitHub API | Fetches public profile: repos, languages, contributions, README, pinned projects. Rate-limited (60 req/hr unauthenticated). |
| `fetch_github_repos` | GitHub API | Fetches repo details: languages, topics, description, stars, activity. Paginated. |
| `infer_skill_proficiency` | LLM | Given skill + context (years used, projects, endorsements), estimates proficiency level (Beginner/Intermediate/Advanced/Expert) with confidence. |
| `deduplicate_entries` | Algorithm + LLM | Merges duplicate work experiences or education entries across sources. Fuzzy matching on company name, title, dates. |
| `embed_profile` | DeepSeek Embedding API | Generates profile embedding for matching. Text is a concatenated summary of the profile. |
| `validate_profile` | Rules + LLM | Checks profile completeness: mandatory fields present, dates consistent, skills tagged. Returns list of warnings and gaps. |
| `enrich_company_names` | Crunchbase API / Web Search | Resolves ambiguous company names, adds industry, size, funding stage. |
| `suggest_professional_summary` | LLM | Generates 3 variants of professional summary at different tones (concise, narrative, achievement-focused). |

#### Memory Requirements

| Memory Type | What Is Stored | Retrieval Trigger |
|-------------|---------------|-------------------|
| **Semantic** | Complete structured profile + embedding | Every agent invocation that needs user context |
| **Episodic** | Profile edit history (what changed, when, why) | Profile version review, undo operations |
| **Procedural** | Best extraction strategies per resume format | Resume parsing pipeline selection |
| **Working** | Current extraction session state (partial results) | During a single profile building session |

#### Failure Handling

| Failure Mode | Detection | Response |
|-------------|-----------|----------|
| Resume parsing fails (corrupted PDF) | `parse_resume` returns error or empty | Ask user to re-upload or paste text manually. Log format for parser improvement. |
| LLM extraction hallucinates (fake company) | Factuality check: cross-reference with known companies DB | Flag entry as `confidence: low`, surface to user for verification with warning icon. |
| GitHub API rate limited | HTTP 403 from GitHub API | Queue for retry with exponential backoff. Notify user: "GitHub import will resume in ~30 minutes." |
| Conflicting data across sources | Deduplication confidence < 0.7 | Surface conflict to user: "We found two versions of your role at Company X. Which is correct?" |
| Profile embedding API fails | API timeout or 5xx | Retry 3× with backoff. Fall back to cached embedding if unchanged. Queue async re-embed. |
| Uploaded file too large | Size check pre-processing | Reject with clear message: "Max 10MB. Please compress or split your document." |

#### Evaluation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Field extraction precision | > 92% | Manual annotation of 200 test resumes |
| Field extraction recall | > 88% | Manual annotation of 200 test resumes |
| Skill extraction F1 | > 0.90 | Comparison with human-labeled skill sets |
| Proficiency accuracy (within 1 level) | > 85% | User self-report verification |
| Profile completion rate (after first session) | > 70% | % of users with all mandatory fields filled |
| Time to complete profile | < 5 min median | Analytics event tracking |
| Enrichment suggestion acceptance rate | > 60% | User accepts suggested enrichment |
| Deduplication false positive rate | < 3% | User corrections of merged entries |

---

### 2.2 Job Discovery Agent

#### Purpose
Continuously discover, ingest, deduplicate, and enrich job listings from 50+ external sources. Maintain a fresh, canonical job database. Trigger matching sweeps when new jobs are discovered.

#### Inputs

| Input | Source | Format | Required |
|-------|--------|--------|----------|
| Source configuration | Database (admin-configured) | `[{name, url, type, schedule, priority}]` | Yes |
| User search preferences | Memory Agent → Supervisor | `{roles[], locations[], remote_policy, companies[]}` | For targeted sweeps |
| Previous sweep cursor | Redis (per source) | `{last_sweep_at, last_job_id, etag}` | For incremental sweeps |

#### Outputs

| Output | Destination | Schema |
|--------|-------------|--------|
| Canonical job listings | PostgreSQL (job_postings) + pgvector (embedding) | Full job schema |
| `job.discovered` event | Redis Stream `stream:jobs` | `{event: "job.discovered", job_id, source, is_new, is_updated}` |
| `sweep.completed` event | Redis Stream `stream:jobs` | `{event: "sweep.completed", source, jobs_found, jobs_new, duration_ms}` |
| Discovery metrics | PostgreSQL (analytics) | `{source, timestamp, count_new, count_updated, count_duplicate, errors}` |
| Job enrichment data | PostgreSQL (job_enrichments) | `{job_id, tech_stack[], salary_range, seniority, remote_policy}` |

#### Tools

| Tool | Type | Description |
|------|------|-------------|
| `scrape_job_board` | Web Scraper | Scrapes a configured job board. Handles pagination, rate limiting, robot.txt compliance. Returns raw job entries. |
| `scrape_company_career_page` | Web Scraper | Scrapes Greenhouse/Lever/Workday/Ashby career pages. Uses public API where available. |
| `fetch_hn_whoishiring` | API Parser | Parses Hacker News "Who's Hiring" monthly thread. Extracts job entries with regex + LLM. |
| `fetch_ycombinator_jobs` | API | Fetches from Y Combinator's job board API. |
| `fetch_community_jobs` | API + Scraper | Fetches from Reddit (r/forhire, r/jobbit), Discord channels, Slack communities. |
| `normalize_job` | LLM + Rules | Converts raw job entry → canonical schema. Extracts: title, company, location, description, requirements. LLM for unstructured text. |
| `deduplicate_job` | Vector + Rules | 3-tier dedup: (1) exact hash match, (2) fuzzy title+company+location, (3) embedding cosine similarity > 0.92 → LLM judge for ambiguous cases. |
| `enrich_job` | LLM | Extracts from JD text: tech stack, seniority level, salary range (if mentioned), remote policy, required years, nice-to-haves, inferred company stage. |
| `embed_job` | DeepSeek Embedding API | Generates job embedding vector (3072d). Embeds title + description + requirements as a single chunk. |
| `detect_stale_jobs` | Rules | Checks last_seen date. Marks jobs as stale (>30 days no refresh), expired (>60 days), or refreshed (re-appeared after being stale). |
| `publish_job_event` | Redis Streams | Publishes `job.discovered` event for each new/updated canonical job. Consumers: Matching Agent, Notification Service. |

#### Memory Requirements

| Memory Type | What Is Stored | Retrieval Trigger |
|-------------|---------------|-------------------|
| **Semantic** | Source health scores (success rate, latency, job volume) | Sweep scheduling decisions |
| **Episodic** | Per-source last sweep cursor, error history | Incremental sweep execution |
| **Procedural** | Scraping patterns per source type (pagination style, rate limit windows) | Scraper execution |
| **Working** | Current sweep batch state (raw → normalized → deduped → enriched → stored) | During a sweep |

#### Failure Handling

| Failure Mode | Detection | Response |
|-------------|-----------|----------|
| Source unreachable (HTTP 5xx) | Scraper timeout or error response | Retry with backoff: 1min → 5min → 15min → 1hr → skip until next scheduled sweep. Alert if 3 consecutive failures. |
| Source changes HTML structure | Normalization returns empty or malformed fields | Log parse failure rate. If > 30% of entries fail, pause source and alert engineering. Use LLM as fallback parser for unstructured text. |
| Rate limit hit | HTTP 429 | Honor Retry-After header. Shift to lower frequency for that source. |
| Dedup false merge (two distinct jobs merged) | User report + manual audit | Unmerge API. Add to dedup training examples. Adjust similarity threshold for that company. |
| LLM enrichment fails | API timeout or error | Store job without enrichment. Queue for async enrichment retry. Job is still discoverable (lower match quality). |
| Embedding API rate limit | API 429 | Batch embeddings. Queue with lower priority. Jobs stored without embeddings temporarily — excluded from vector search until embedded. |
| Duplicate sweep collision | Redis lock already held | Skip sweep. Log collision. This is normal — prevents duplicate work. |

#### Evaluation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Job coverage (jobs found / jobs exist) | > 90% of publicly listed tech jobs | Periodic manual audit of 20 companies across sources |
| Dedup precision (correct merges) | > 98% | Manual review of 500 random dedup decisions |
| Dedup recall (all duplicates caught) | > 95% | Manual review |
| Freshness (new job → indexed) | < 4 hours for priority sources | Timestamp delta monitoring |
| Source uptime | > 99% per source | Health check monitoring |
| Enrichment accuracy (tech stack) | > 85% | Comparison with ground truth from company engineering blogs |
| False positive rate (non-job scraped as job) | < 2% | Manual audit of ingested entries |

---

### 2.3 Job Matching Agent

#### Purpose
Compute explainable match scores between a user profile and job listings. Rank jobs by multi-dimensional relevance. Produce human-readable explanations for why each job matches (or doesn't). Learn from user feedback to continuously improve rankings.

#### Inputs

| Input | Source | Format | Required |
|-------|--------|--------|----------|
| User profile + embedding | Profile Agent / Memory Agent | Full profile + 3072d vector | Yes |
| User preferences | Memory Agent | `{priorities: {comp:0.3, growth:0.25, culture:0.2, ...}, dealbreakers[]}` | Yes |
| Job pool | Job Discovery Agent | List of active canonical jobs with embeddings | Yes |
| User interaction history | Memory Agent | `[{job_id, action: view/save/apply/dismiss, timestamp}]` | For re-ranking |
| Similar user patterns | Memory Agent (anonymized) | Collaborative filtering signals | For collaborative scoring |

#### Outputs

| Output | Destination | Schema |
|--------|-------------|--------|
| Ranked match list | Supervisor → User UI | `[{job_id, overall_score, dimensions{}, explanation[]}]` |
| Match explanation | User UI | Natural language: "Strong match on Python (your #1 skill) and remote preference. Gap: they want 5+ years, you have 3." |
| `match.high_score` event | Redis Stream `stream:matches` | For jobs scoring ≥ 85% |
| Match embedding | pgvector (cached) | For similar-job retrieval |

#### Tools

| Tool | Type | Description |
|------|------|-------------|
| `compute_skill_match` | Vector + Rules | Cosine similarity between user skill vectors and job required skills. Returns per-skill scores + overall skill match %. |
| `compute_experience_match` | LLM | Compares years of experience, title seniority, domain relevance. Returns score + explanation. |
| `compute_tech_stack_overlap` | Set Operations | Jaccard similarity + weighted overlap (exact match > semantic match > adjacent tech). |
| `compute_location_fit` | Rules | Match based on user location prefs vs job location/remote policy. Returns score + flags (relocation needed, etc.). |
| `compute_compensation_alignment` | Rules + Model | Compares user minimum vs job salary range. Uses ML-predicted salary when not listed. Returns alignment + confidence. |
| `compute_culture_fit` | LLM | Analyzes job description language + company data for culture signals. Compares with user-stated culture preferences. Lower confidence — flagged as "signal, not fact." |
| `explain_match` | LLM | Generates natural language explanation: top 3 reasons it matches, top 2 concerns/gaps. Evidence-grounded. |
| `rerank_by_feedback` | ML Model | Adjusts ranking based on user's implicit feedback (dismiss patterns, save patterns, apply history). Real-time weight update. |
| `detect_dealbreakers` | Rules + LLM | Checks job against user's explicit dealbreakers. If found, job is excluded or flagged with reason. |
| `compute_diversity_score` | Rules | If enabled, slightly boosts jobs from companies/industries/roles user hasn't considered but their skills fit. |

#### Memory Requirements

| Memory Type | What Is Stored | Retrieval Trigger |
|-------------|---------------|-------------------|
| **Semantic** | User preference weights (evolving), user embedding | Every match computation |
| **Episodic** | All user-job interactions (view/save/apply/dismiss) | Re-ranking, feedback learning |
| **Procedural** | Learned scoring function weights per user segment | Match computation |
| **Working** | Current batch match computation state | During a match sweep |

#### Failure Handling

| Failure Mode | Detection | Response |
|-------------|-----------|----------|
| Vector search returns empty | Zero results from pgvector | Broaden search: relax location filter, include adjacent roles. Notify user: "No exact matches found. Showing nearby opportunities." |
| LLM explanation fails | API error | Return match scores without explanation. Show "Score breakdown" (numeric) instead of "Why this matches" (NL). Queue async explanation generation. |
| Stale job in results | Job marked expired after matching | Filter post-retrieval. If > 10% of results are stale, trigger re-index. |
| Score computation timeout | > 5 seconds for batch | Return partial results with cached scores for remaining. Flag and retry. |
| Preference model drift | User dismisses > 50% of high-scored matches in a row | Trigger preference re-elicitation: "Your matches don't seem right lately. Have your preferences changed?" |
| Bias detected in scoring | Monitoring alert (demographic disparity in scores) | Halt automated matching for affected segments. Human review. Debiasing prompt injection. |

#### Evaluation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Precision@10 (user saves/applies) | > 65% | Track user action on top-10 results |
| Recall (user's eventual application was in agent's top-50) | > 85% | Retrospective analysis |
| NDCG@20 | > 0.75 | Discounted cumulative gain of ranking vs. user actions |
| Match explanation helpfulness | > 4.0/5 user rating | Post-match feedback prompt |
| Feedback response time (dismiss → ranking change) | < 5 seconds | Latency measurement |
| Dealbreaker violation rate | < 1% | Jobs surfaced that violate explicit dealbreakers |
| Serendipity rate (% of applications to jobs user wouldn't have found) | > 30% | User survey |

---

### 2.4 Resume Agent

#### Purpose
Generate job-tailored resume variants from the user's base profile. Optimize for ATS parsing while maintaining human readability. Every generated bullet point must be traceable to a confirmed profile fact — zero hallucination tolerance.

#### Inputs

| Input | Source | Format | Required |
|-------|--------|--------|----------|
| User profile (canonical) | Profile Agent / Memory Agent | Full structured profile | Yes |
| Target job description | Job Discovery Agent | Full JD with enrichments | Yes |
| Match analysis | Job Matching Agent | Match scores + gaps + explanation | Yes |
| Base resume template | User selection or default | Template ID + styling preferences | Yes |
| Previous tailored resumes | Database | Resume variant history | For consistency |

#### Outputs

| Output | Destination | Schema |
|--------|-------------|--------|
| Tailored resume content | User UI (diff view) + Database | Structured resume (sections with bullets) |
| ATS keyword coverage report | User UI | `{keyword, in_original, in_tailored, density}` |
| Change summary | User UI | "Modified: summary, skills order, 6 bullet points. Added: Docker mention. Removed: nothing." |
| Honest gap disclosure | User UI | "They require Kubernetes — you don't have this. Consider adding 'Learning Kubernetes' or be prepared to discuss in interview." |
| PDF/rendered output | S3/MinIO + User download | Formatted PDF |
| `resume.tailored` event | Redis Stream `stream:documents` | `{user_id, job_id, resume_variant_id, timestamp}` |

#### Tools

| Tool | Type | Description |
|------|------|-------------|
| `analyze_jd_keywords` | LLM + TF-IDF | Extracts critical keywords from JD. Categorizes: must-have (appears 3+ times or in "requirements"), nice-to-have, company-value signals. |
| `map_experience_to_requirements` | LLM + RAG | For each JD requirement, retrieves most relevant experience from user profile (vector search over experience chunks). Returns ranked relevance pairs. |
| `rewrite_bullet` | LLM | Rewrites a single experience bullet to emphasize relevance to a specific JD requirement. Input: original bullet + JD requirement. Output: rewritten bullet. Constraint: NO fabricated metrics or achievements. |
| `quantify_achievement` | LLM | Suggests metric-based rewrites when original bullet implies measurable impact but doesn't state it. Flagged as "suggestion" — user must confirm. |
| `reorder_skills` | Rules | Reorders skills section to prioritize skills mentioned in JD. Preserves proficiency level indicators. |
| `rewrite_summary` | LLM | Generates professional summary tailored to this specific role + company. 3 variants: concise (2 lines), standard (4 lines), narrative (6 lines). |
| `check_ats_compatibility` | Rules + Simulation | Simulates ATS parse: extracts text from generated PDF, checks for common parsing issues (tables, columns, images, weird fonts). Flags issues. |
| `compute_keyword_coverage` | Rules | Calculates % of JD keywords present in tailored resume. Warns if keyword stuffing detected (unnatural density). |
| `identify_honest_gaps` | LLM | Compares JD requirements to user profile. Identifies gaps. For each gap, suggests framing strategy: honest omission, "familiar with," "learning," or "comparable experience in [X]." |
| `render_pdf` | LaTeX / HTML → PDF | Renders final resume to ATS-optimized PDF. Clean, single-column, standard fonts, no images/tables. |

#### Memory Requirements

| Memory Type | What Is Stored | Retrieval Trigger |
|-------------|---------------|-------------------|
| **Semantic** | User profile (ground truth for all generation) | Every resume generation |
| **Episodic** | Previous tailored resumes + which versions got interviews | A/B testing, pattern learning |
| **Procedural** | Best-performing templates and rewrite patterns per industry/role | Template and strategy selection |
| **Working** | Current tailoring session (JD → analysis → map → rewrite → review) | During a tailoring session |

#### Failure Handling

| Failure Mode | Detection | Response |
|-------------|-----------|----------|
| LLM hallucinates achievement | Post-generation factuality check: bullet entities not in profile | Strip the bullet. Replace with "[Your achievement here]" placeholder. Flag for user. Log for model quality tracking. |
| ATS simulation flags formatting issues | `check_ats_compatibility` returns warnings | Show warnings to user. Offer alternative template. Auto-fix simple issues (fonts, columns). |
| JD too long for context window | Token count > context limit | Chunk JD: requirements section only for keyword extraction, full JD for summary. Truncate responsibilities section. |
| User profile too sparse for tailoring | < 2 work experiences or < 5 skills | Generate what's possible. Flag: "Limited profile — tailoring may be less impactful. Consider adding more experiences." |
| Template rendering fails | LaTeX/HTML compilation error | Fall back to simplest template (plain text → PDF). Log error for template debugging. |
| Gap identification flags everything as a gap | > 50% of JD requirements flagged | Suppress low-confidence gaps. Only show critical/high-confidence gaps. Adjust threshold. |

#### Evaluation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Suggestion acceptance rate (% of AI changes kept by user) | > 75% | Diff analysis |
| Hallucination rate (fabricated facts) | < 0.5% | Post-generation factuality check + user reports |
| ATS parse score (predicted) | > 90/100 | ATS simulation tool |
| Keyword coverage improvement (tailored vs base) | +40% relative improvement | Keyword counting |
| Time saved vs manual tailoring | > 80% (user survey: "How long would this have taken manually?") | User survey |
| Interview rate lift (tailored vs base resume) | 2× or higher | A/B experiment |
| User satisfaction | > 4.2/5 | Post-generation rating |

---

### 2.5 Cover Letter Agent

#### Purpose
Generate personalized, evidence-backed cover letters that complement (don't duplicate) the resume. Every claim must be traceable to a profile fact. Tone and structure adapt to company culture signals and user preference.

#### Inputs

| Input | Source | Format | Required |
|-------|--------|--------|----------|
| User profile | Profile Agent / Memory Agent | Full profile | Yes |
| Target job description | Job Discovery Agent | Full JD with enrichments | Yes |
| Match analysis | Job Matching Agent | Match scores + gaps | Yes |
| Company research | Job Discovery Agent (enrichment) | Company info: recent news, tech blog, culture, stage | Yes |
| Tailored resume | Resume Agent | Generated resume (for consistency) | Yes |
| User tone preference | User settings or Memory Agent | `professional / enthusiastic / concise / creative / formal` | No (default: professional) |
| Specific points to emphasize | User input (optional) | Free text | No |

#### Outputs

| Output | Destination | Schema |
|--------|-------------|--------|
| Cover letter text | User UI (editor) + Database | Full text with sections: opening, body (3 para), closing |
| Personalization evidence | User UI | "Referenced: their recent AWS re:Invent talk, Series B funding, Python/Django stack" |
| Tone analysis | User UI | "Tone: Professional-Warm (70% professional, 30% warm)" |
| `cover_letter.generated` event | Redis Stream `stream:documents` | `{user_id, job_id, cover_letter_id, timestamp}` |

#### Tools

| Tool | Type | Description |
|------|------|-------------|
| `research_company` | Web Search + LLM | Searches for recent company news, tech blog posts, product launches, leadership interviews. Returns structured research brief. |
| `generate_opening` | LLM | Generates opening paragraph: genuine interest in this specific company (not generic). References company research. 3 variants. |
| `map_experience_stories` | LLM + RAG | Retrieves top 3 user experiences most relevant to JD requirements. Generates narrative versions (STAR-lite) for letter body. |
| `generate_body` | LLM | Generates 3 body paragraphs: each maps one experience → one JD requirement, with evidence. Constraint: no resume repetition — adds narrative context the resume can't convey. |
| `generate_closing` | LLM | Generates closing: reiterates interest, call to action, professional sign-off. |
| `adapt_tone` | LLM | Rewrites draft in specified tone. Preserves factual content. Adjusts vocabulary, sentence length, enthusiasm level. |
| `verify_factuality` | Rules + LLM | Checks every claim in the letter against user profile. Flags unsupported claims. Returns factuality report. |

#### Memory Requirements

| Memory Type | What Is Stored | Retrieval Trigger |
|-------------|---------------|-------------------|
| **Semantic** | User profile, writing style preferences | Every generation |
| **Episodic** | Previous cover letters, user edits (style learning) | Style adaptation |
| **Procedural** | Best-performing structures per industry | Structure selection |
| **Working** | Current generation session | During generation |

#### Failure Handling

| Failure Mode | Detection | Response |
|-------------|-----------|----------|
| Company research returns nothing | Web search empty | Generate letter without company-specific personalization. Flag: "Company research unavailable — letter is role-specific but not company-specific." |
| Factuality check finds hallucination | `verify_factuality` flags claim | Strip claim. Regenerate paragraph with stricter grounding prompt. |
| Tone adaptation loses key content | Content diff shows > 20% content loss | Revert to original. Apply lighter tone touch. Flag for user review. |
| All user experiences map poorly to JD | `map_experience_stories` returns low relevance | Flag honestly: "Limited direct experience for this role. Letter focuses on transferable skills and enthusiasm." Generate honest framing. |

#### Evaluation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Factuality score (% claims grounded in profile) | > 99% | Automated verification |
| Personalization score (company-specific references) | > 1 unique reference | Automated check |
| User edit distance (% of text user modifies) | < 20% | Diff analysis |
| User satisfaction | > 4.0/5 | Post-generation rating |
| Generation time | < 10 seconds | Latency measurement |

---

### 2.6 Memory Agent

#### Purpose
The Memory Agent is the **strategic moat** of Pathfinder. It manages three tiers of memory (episodic, semantic, procedural), consolidates raw interactions into structured insights, retrieves relevant context for other agents, and maintains the evolving user model. Every other agent depends on it.

#### Inputs

| Input | Source | Format | Required |
|-------|--------|--------|----------|
| User interaction events | All agents + User UI (via Redis Streams) | `{user_id, event_type, payload, timestamp}` | Continuous |
| Agent execution traces | All agents | `{agent_type, input_hash, output_hash, tools_called, latency, success}` | Continuous |
| Explicit user feedback | User UI | `{target_type, target_id, rating, comment}` | On user action |
| Profile changes | Profile Agent | `{field, old_value, new_value, source}` | On change |
| Consolidation trigger | Celery Beat (every 6 hours) | `{user_id}` | Scheduled |

#### Outputs

| Output | Destination | Schema |
|--------|-------------|--------|
| User context package | Supervisor Agent (for any agent invocation) | `{profile, preferences, recent_history, relevant_memories}` |
| Updated preference weights | PostgreSQL (memory_preferences) | `{weights: {comp: 0.32, growth: 0.24, ...}, confidence, last_updated}` |
| Updated career narrative | PostgreSQL + pgvector | Long-form narrative text + embedding |
| Consolidated memory entries | PostgreSQL + pgvector | Structured memory entries with importance scores |
| `memory.consolidated` event | Redis Stream `stream:memory` | `{user_id, memories_added, insights_generated}` |
| `memory.preference_shift` event | Redis Stream `stream:memory` | `{user_id, field, old_weight, new_weight, evidence}` |

#### Tools

| Tool | Type | Description |
|------|------|-------------|
| `store_episodic_memory` | PostgreSQL Insert | Stores raw interaction: `{user_id, session_id, event_type, payload, embedding, timestamp}`. High-throughput append. |
| `retrieve_recent_episodes` | PostgreSQL Query | Returns last N interactions for a user, filtered by relevance or recency. < 10ms. |
| `retrieve_semantic_memories` | pgvector ANN | Vector search over user's memory embeddings. Returns top-K most relevant to current context. |
| `consolidate_memories` | LLM | Batch process: takes last 6 hours of episodic memories → extracts patterns, updates preferences, enriches narrative. The core learning loop. |
| `update_preference_weights` | Algorithm | Bayesian update of preference weights based on observed behavior (what user actually clicks/applies to vs. what they said they wanted). |
| `update_career_narrative` | LLM | Maintains a running ~500-word summary of user's career. Updated incrementally when new experiences or achievements are added. |
| `compute_memory_importance` | LLM | Scores each memory by likely future relevance (0–1). High importance: interview outcomes, preference signals. Low importance: scrolling past a job. |
| `forget_memory` | PostgreSQL Delete / Archive | Implements right-to-erasure: hard delete or archive per user request. GDPR/CCPA compliant. |
| `export_memory` | Serialization | Exports user's entire memory graph in machine-readable format (JSON). Data portability. |
| `detect_preference_drift` | Algorithm | Compares recent behavior distribution to historical. Flags if statistically significant shift detected. |

#### Memory Requirements

| Memory Type | What Is Stored | Retrieval Trigger |
|-------------|---------------|-------------------|
| **Episodic** (own tier) | All raw interactions: views, saves, applies, agent calls, feedback events | Agent context assembly, consolidation |
| **Semantic** (own tier) | User profile, preferences, career narrative, learned facts | Every agent invocation |
| **Procedural** (own tier) | Agent success patterns, best routing decisions, tool effectiveness | Agent routing, strategy selection |
| **Working** | Consolidation batch state | During consolidation run |

#### Failure Handling

| Failure Mode | Detection | Response |
|-------------|-----------|----------|
| Consolidation LLM call fails | API error | Retry with backoff. Skip this cycle — episodic memories accumulate and will be consolidated next cycle (eventual consistency is acceptable). |
| Memory retrieval returns irrelevant results | Agent reports context not useful (feedback loop) | Log retrieval quality. Adjust embedding model or retrieval query. Surface to engineering if systemic. |
| Preference update contradicts explicit user settings | Weighted model diverges > 30% from stated preference | Respect explicit settings. Use learned preferences only where user hasn't explicitly stated. Surface: "I've noticed you tend to prefer X even though you said Y. Want to update?" |
| Memory store reaches capacity | DB approaching partition limit | Archive episodic memories > 90 days. Compress embeddings. Increase partition range. |
| Embedding generation fails for memory entry | API error | Store memory without embedding. Queue for async embedding. Memory is still retrievable by structured query. |
| User deletion request | User action | Hard delete all memory tiers within 30 days. Confirm with user. Log deletion for compliance. |

#### Evaluation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Context relevance (agent rates retrieved memory as useful) | > 85% | Agent feedback signal |
| Preference prediction accuracy (learned vs. stated) | > 80% of implicit preferences match future explicit feedback | Retrospective analysis |
| Consolidation quality (manual audit) | > 4.0/5 | Weekly manual review of 50 consolidated memories |
| Memory retrieval latency (P95) | < 100ms | Latency monitoring |
| Forgetting effectiveness (deleted data truly gone) | 100% | Deletion audit |

---

### 2.7 Interview Agent

#### Purpose
Prepare users for interviews with company-specific guides, role-specific question banks, personalized STAR answers, and (V2) AI-moderated mock interviews with delivery feedback.

#### Inputs

| Input | Source | Format | Required |
|-------|--------|--------|----------|
| User profile | Memory Agent | Full profile | Yes |
| Target job | Application Tracking Agent | Job with company, role, stage | Yes |
| Interview stage | Application Tracking Agent | `phone_screen / tech_interview / onsite / behavioral / system_design / final` | Yes |
| Interview details | User input or Calendar integration | `{date, interviewer_name, interviewer_role, format, duration}` | Optional |
| Previous interview feedback | Memory Agent | User's past interview performance notes | For improvement tracking |

#### Outputs

| Output | Destination | Schema |
|--------|-------------|--------|
| Interview preparation plan | User UI | `{company_info, format_prediction, question_sets, practice_plan}` |
| Behavioral question bank | User UI | `[{question, star_answer_outline, personalized_example}]` |
| Technical question bank | User UI | `[{question, difficulty, topic, solution_approach}]` |
| Company questions to ask | User UI | `[{question, who_to_ask, why_relevant}]` |
| Mock interview transcript + feedback | User UI (V2) | `{transcript[], scores: {clarity, relevance, confidence}, improvements[]}` |

#### Tools

| Tool | Type | Description |
|------|------|-------------|
| `aggregate_interview_data` | Web Search + LLM | Searches Glassdoor, Blind, Reddit for interview experiences at target company. Synthesizes: typical format, common questions, difficulty level. |
| `generate_behavioral_questions` | LLM | Generates 10–15 behavioral questions likely for this role + company. Covers: teamwork, conflict, failure, leadership, technical decision-making. |
| `generate_star_answers` | LLM | For each behavioral question, generates STAR-framework answer outline populated with user's actual experiences. NOT a script — an outline with specific evidence. |
| `generate_technical_questions` | LLM + Problem DB | Generates technical questions calibrated to company's known interview style (LeetCode-style, practical coding, system design, domain-specific). |
| `generate_questions_to_ask` | LLM | Generates smart, researched questions for each interviewer type. Avoids generic questions. References company specifics. |
| `generate_company_brief` | LLM | One-page company research summary: product, tech stack, recent news, culture, interview process, what they look for. |
| `conduct_mock_interview` | LLM + Voice (V2) | AI-moderated mock interview: asks questions, listens to answers, provides feedback on content + delivery. |
| `analyze_answer_quality` | LLM | Scores answer on clarity, relevance, STAR completeness, evidence specificity. Returns score + actionable feedback. |

#### Memory Requirements

| Memory Type | What Is Stored | Retrieval Trigger |
|-------------|---------------|-------------------|
| **Semantic** | User profile, past interview experiences | Question personalization |
| **Episodic** | Past interview outcomes, feedback notes, what worked | Improvement tracking, pattern identification |
| **Procedural** | Best prep strategies per company/role | Prep plan generation |
| **Working** | Current prep session state | During prep session |

#### Failure Handling

| Failure Mode | Detection | Response |
|-------------|-----------|----------|
| No interview data found for company | `aggregate_interview_data` returns empty | Use role-based defaults. Flag: "Limited data for this company. Prep is based on industry standards for this role type." |
| User has no relevant experience for STAR answers | Profile has < 2 work experiences | Use academic projects, volunteer work, coursework. Flag: "Answers draw from academic experience. Consider adding more professional experiences to your profile." |
| Mock interview voice pipeline fails (V2) | STT/TTS API error | Fall back to text-based mock interview. User types answers, agent provides written feedback. |
| Question generation produces duplicates | Exact string match with previous | Deduplicate. Regenerate. Track previously shown questions per user. |

#### Evaluation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Prep plan helpfulness | > 4.2/5 | User rating |
| STAR answer personalization (% with specific user facts) | > 90% | Automated verification |
| Interview pass rate (users who prepped vs. didn't) | +25% relative improvement | A/B or cohort analysis |
| Questions-to-ask relevance | > 4.0/5 | User rating |

---

### 2.8 Career Coach Agent

#### Purpose
Identify skill gaps between user profile and target roles. Generate personalized learning plans with curated resources. Provide long-term career trajectory guidance. This agent is proactive — it can initiate conversations when market shifts or user milestones are detected.

#### Inputs

| Input | Source | Format | Required |
|-------|--------|--------|----------|
| User profile | Memory Agent | Full profile + skills | Yes |
| Target role definition | User input or inferred from application history | `{title, seniority, domain}` | Yes |
| Market demand signals | Job Discovery Agent (aggregate) | Trending skills, salary ranges, demand volume | For gap prioritization |
| User learning history | Memory Agent | Completed courses, certifications, projects | For progress tracking |
| Career goals | User input or Memory Agent | Long-form text or structured goals | Optional |

#### Outputs

| Output | Destination | Schema |
|--------|-------------|--------|
| Skill gap analysis | User UI | `[{skill, current_level, required_level, gap_severity, demand_frequency, priority}]` |
| 90-day learning plan | User UI | `[{week, focus_area, resources[], estimated_hours, milestone}]` |
| Learning resource recommendations | User UI | `[{resource, type, url, cost, duration, rating, why_recommended}]` |
| Career trajectory projection | User UI | "Based on your profile + market trends, here are 3 likely paths for the next 3–5 years." |
| `learning.plan_generated` event | Redis Stream `stream:learning` | `{user_id, plan_id, gaps_identified}` |

#### Tools

| Tool | Type | Description |
|------|------|-------------|
| `analyze_skill_gaps` | Vector + Rules | Compares user skill vectors to target role requirement aggregate. Returns gap list with severity and frequency. |
| `prioritize_gaps` | LLM | Ranks gaps by: market demand, user's stated goals, prerequisite chains, time-to-learn. |
| `curate_learning_resources` | Search + LLM | Searches Coursera, Udemy, edX, YouTube, documentation, books, projects. Curates top 3 per gap. Considers: cost, time commitment, quality, learning style fit. |
| `generate_learning_plan` | LLM | Creates week-by-week plan: what to learn, from where, how to practice, how to demonstrate. Realistic time estimates. |
| `track_learning_progress` | Rules + LLM | Checks course completion, project commits, certification status. Updates skill proficiency estimates. |
| `project_market_trends` | Analytics + LLM | Aggregates job posting data to identify trending skills, declining skills, salary movements. |
| `project_career_trajectory` | LLM | Given current profile + learning plan + market data → projects 3 possible 5-year paths with probabilities and key decision points. |
| `recommend_certifications` | LLM | For each gap, evaluates whether certification is worth it (ROI analysis). Suggests specific certs with cost and time. |

#### Memory Requirements

| Memory Type | What Is Stored | Retrieval Trigger |
|-------------|---------------|-------------------|
| **Semantic** | User skills, career goals, learning history, market knowledge | Every coaching interaction |
| **Episodic** | Past coaching conversations, user's stated aspirations, feedback on previous plans | Personalization |
| **Procedural** | Effective learning plan structures per role transition type | Plan generation |
| **Working** | Current coaching session | During session |

#### Failure Handling

| Failure Mode | Detection | Response |
|-------------|-----------|----------|
| Skill gap analysis finds no gaps | All user skills ≥ target requirements | "Your skills align well with this target. Focus may be on: interview performance, networking, or targeting higher-seniority roles." |
| Learning resource search returns stale/dead links | HTTP check on resource URLs | Periodic link validation. Remove dead resources. Flag in UI if resource is older than 2 years. |
| Market trend data is sparse for niche role | < 100 job postings for analysis | Flag low confidence. Use broader role category as proxy. "Limited data for this specific role — analysis based on the broader [category] market." |
| User doesn't follow plan (no progress after 30 days) | Progress tracking shows no activity | Proactive nudge: "I noticed you haven't started your learning plan. Want me to adjust it — shorter, different resources, different focus?" |

#### Evaluation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Gap analysis accuracy (user agreement) | > 4.0/5 | User rating |
| Learning plan completion rate | > 40% (industry avg for self-paced is ~15%) | Progress tracking |
| Skill improvement (pre/post assessment) | > 1 proficiency level improvement per 90 days for active learners | Profile re-evaluation |
| Resource recommendation CTR | > 25% | Click tracking |

---

### 2.9 Application Tracking Agent

#### Purpose
Track every application through its lifecycle. Provide kanban visualization, deadline management, and document organization. Parse emails to automatically detect status changes. This is the operational backbone of the user's job search.

#### Inputs

| Input | Source | Format | Required |
|-------|--------|--------|----------|
| Application events | User UI + other agents | `{user_id, job_id, action: save/apply/status_change, payload}` | Continuous |
| Email integration | Gmail/Outlook API (user-authorized) | Incoming emails related to applications | For auto-detection |
| Calendar integration | Google/Outlook Calendar (user-authorized) | Interview events | For auto-detection |
| User manual updates | User UI | Status changes, notes, tasks | On user action |

#### Outputs

| Output | Destination | Schema |
|--------|-------------|--------|
| Application pipeline state | User UI (Kanban) + Database | `{user_id, applications[{job, status, stage, documents, tasks, interviews, communications}]}` |
| `app.status_changed` event | Redis Stream `stream:applications` | `{user_id, application_id, old_status, new_status, detected_by}` |
| Deadline alerts | Notification Service | `{user_id, application_id, deadline_type, deadline_at, urgency}` |
| Pipeline analytics | Analytics Service | Aggregated funnel metrics |

#### Tools

| Tool | Type | Description |
|------|------|-------------|
| `update_application_status` | Database | Updates status with audit trail: who/what changed it, timestamp, previous status. |
| `parse_email_for_status` | LLM | Classifies incoming email: interview invitation, rejection, follow-up, offer, assessment, other. Extracts: date, interviewer, next steps. |
| `extract_interview_from_calendar` | Calendar API | Detects interview events: matches calendar event to application by company name. Extracts: date, duration, attendees, location/link. |
| `create_task` | Database | Creates task linked to application: "Follow up on [date]", "Complete assessment by [deadline]", "Send thank-you within 24h of interview". |
| `check_deadlines` | Rules (Celery Beat, every hour) | Scans all active applications for approaching deadlines. Generates alerts for: application deadlines, follow-up windows, assessment expirations, offer expirations. |
| `generate_pipeline_analytics` | Analytics Query | Computes: application volume over time, status distribution, time-in-stage averages, source effectiveness, response rates. |
| `link_document_to_application` | Database | Associates resume variant + cover letter with application. Maintains document → application mapping. |
| `detect_ghosted_applications` | Rules | Flags applications with no response after N days (configurable: 14 days default). Suggests follow-up. |

#### Memory Requirements

| Memory Type | What Is Stored | Retrieval Trigger |
|-------------|---------------|-------------------|
| **Semantic** | Active application states, document associations | Every pipeline view |
| **Episodic** | Full application timeline (every status change with timestamp) | Analytics, user history |
| **Procedural** | Learned patterns: which sources yield responses, which follow-up timing works best | Strategy optimization |
| **Working** | Current pipeline view state | During UI interaction |

#### Failure Handling

| Failure Mode | Detection | Response |
|-------------|-----------|----------|
| Email parsing misclassifies status | User corrects status manually | Log correction. Fine-tune classifier. User correction is the training signal. |
| Calendar event not linked to application | Event company name doesn't fuzzy-match any application | Queue for user review: "We found an event that might be an interview. Confirm?" |
| Duplicate application detection | Same user + same canonical job | Prevent duplicate. Show message: "You've already applied to this role at [Company] on [date]." |
| Email integration disconnected | OAuth token expired or revoked | Notify user: "Email integration needs re-authorization. Your pipeline may miss automatic updates." |

#### Evaluation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Email classification accuracy | > 92% | User corrections as ground truth |
| Auto-detected status changes (vs manual) | > 60% of status changes auto-detected | Ratio tracking |
| Pipeline view load time | < 300ms for 100 applications | P95 latency |
| Deadline alert timeliness | > 99% delivered before deadline | On-time rate |

---

### 2.10 Follow-up Agent

#### Purpose
Generate timely, contextual, personalized follow-up communications: post-application check-ins, post-interview thank-yous, recruiter responses, outreach messages. Schedule and (with user approval) send them at optimal times.

#### Inputs

| Input | Source | Format | Required |
|-------|--------|--------|----------|
| Application context | Application Tracking Agent | `{job, company, status, last_contact_date, contact_person, interview_notes}` | Yes |
| User profile | Memory Agent | Profile summary for signature/personalization | Yes |
| Communication history | Application Tracking Agent | Previous emails/messages in this thread | For context |
| User tone preference | Memory Agent | `professional / warm / concise / persistent` | No (default) |

#### Outputs

| Output | Destination | Schema |
|--------|-------------|--------|
| Draft email/message | User UI (editor) | Full text: subject, body, signature |
| Send recommendation | User UI | "Optimal send time: Tuesday 10:15 AM ET (recipient's timezone). 73% open rate for similar emails." |
| `communication.generated` event | Redis Stream (internal) | `{user_id, application_id, communication_type, timestamp}` |

#### Tools

| Tool | Type | Description |
|------|------|-------------|
| `generate_follow_up` | LLM | Generates post-application follow-up: references role, timeline, reiterates interest. Tone: polite, not pushy. |
| `generate_thank_you` | LLM | Generates post-interview thank-you: references specific discussion points (if interview notes provided), reiterates interest, professional sign-off. |
| `generate_recruiter_response` | LLM | Generates response to common recruiter questions: salary expectations, availability, work authorization, interest level. |
| `generate_outreach` | LLM | Generates networking outreach: connection request, warm introduction, cold outreach. Includes reason for reaching out. |
| `calculate_optimal_send_time` | Algorithm | Based on: recipient timezone, historical email engagement data for similar emails, day-of-week patterns. |
| `schedule_send` | Email API + Celery | Schedules email for future delivery at optimal time. User can override. |
| `check_thread_context` | Email API | Retrieves recent email thread for context. Ensures follow-up references previous communication correctly. |
| `detect_no_response_window` | Rules | Calculates if enough time has passed since last contact to warrant follow-up (configurable per stage). |

#### Memory Requirements

| Memory Type | What Is Stored | Retrieval Trigger |
|-------------|---------------|-------------------|
| **Semantic** | User communication style preferences | Every generation |
| **Episodic** | Communication history per application, which emails got responses | Context + effectiveness tracking |
| **Procedural** | Best-performing templates and send times | Template + timing selection |
| **Working** | Current draft state | During editing |

#### Failure Handling

| Failure Mode | Detection | Response |
|-------------|-----------|----------|
| LLM generates overly aggressive follow-up | Tone classifier flags as "pushy" or "desperate" | Regenerate with tone constraint. Flag for user: "This draft may come across as pushy. Consider this softened version." |
| Thread context unavailable (new thread) | Email API returns no history | Generate as standalone message. Flag: "No prior thread — this will start a new conversation." |
| Optimal send time is during quiet hours | Calculated time is 10PM–6AM recipient local | Adjust to next business hour. Explain to user. |
| User hasn't had contact in 30+ days | `detect_no_response_window` returns "likely ghosted" | Generate honest assessment: "It's been 30 days with no response. A follow-up is still worth sending, but consider focusing on other applications." |

#### Evaluation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Response rate to generated follow-ups | > 25% | Email tracking |
| User edit distance | < 15% of text modified | Diff analysis |
| Optimal send time accuracy (open rate lift) | +15% vs random send time | A/B test |
| Thank-you email timeliness (< 24h post-interview) | > 80% | Timestamp delta |
| User satisfaction | > 4.0/5 | Post-send rating |

---

## 3. Supervisor Agent

### Purpose

The Supervisor Agent is the **central coordinator** of the entire multi-agent system. It is the only agent that directly interacts with the user. It routes intents, plans multi-step tasks, assembles context, delegates to specialized agents, merges results, and enforces quality gates. It is implemented as the **root LangGraph StateGraph** — all other agents are subgraphs or tool-invoked nodes within it.

### Design Philosophy

The Supervisor is intentionally **thin**. It does not do the work — it orchestrates. Its intelligence is in routing, planning, and quality assurance, not in domain execution.

### Supervisor Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SUPERVISOR AGENT INTERNALS                          │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        SUPERVISOR NODES                               │   │
│  │                                                                       │   │
│  │  Node 1: GUARDRAIL                                                   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ - Content safety check (input moderation)                    │    │   │
│  │  │ - Rate limit enforcement                                     │    │   │
│  │  │ - Tier permission check (is user allowed to do this?)        │    │   │
│  │  │ - PII detection (don't send PII to LLM unnecessarily)        │    │   │
│  │  │ - Output: PASS (continue) / BLOCK (return error)             │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                       │   │
│  │  Node 2: CONTEXT BUILDER                                             │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ - Calls Memory Agent: retrieve_recent_episodes +             │    │   │
│  │  │   retrieve_semantic_memories                                 │    │   │
│  │  │ - Assembles context package: profile + preferences +         │    │   │
│  │  │   relevant_history + active_applications                     │    │   │
│  │  │ - Computes context token budget (how much room for agent)    │    │   │
│  │  │ - Output: enriched state with full context                   │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                       │   │
│  │  Node 3: INTENT ROUTER                                               │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ - Classifies user intent from message + context              │    │   │
│  │  │ - Intent taxonomy:                                           │    │   │
│  │  │   discover_jobs | match_me | tailor_resume |                 │    │   │
│  │  │   generate_cover_letter | prep_interview |                   │    │   │
│  │  │   track_applications | follow_up | skill_gap |               │    │   │
│  │  │   career_advice | update_profile | general_question          │    │   │
│  │  │ - Confidence scoring: if confidence < 0.7 → ask clarifying   │    │   │
│  │  │   question instead of routing                                │    │   │
│  │  │ - Output: intent (single or list for multi-step task)        │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                       │   │
│  │  Node 4: TASK PLANNER                                                │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ - Decomposes intent into agent execution plan                │    │   │
│  │  │ - Identifies dependencies: "tailor_resume DEPENDS_ON         │    │   │
│  │  │   match_analysis"                                            │    │   │
│  │  │ - Identifies parallelism: "discover_jobs PARALLEL_WITH       │    │   │
│  │  │   update_profile"                                            │    │   │
│  │  │ - Plans HITL gates: which steps need user approval           │    │   │
│  │  │ - Output: execution_plan [{agent, inputs, depends_on,        │    │   │
│  │  │   needs_approval}]                                           │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                       │   │
│  │  Node 5: AGENT DISPATCHER                                            │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ - Executes plan: invokes specialized agents in order         │    │   │
│  │  │ - Handles dependencies: waits for upstream results           │    │   │
│  │  │ - Parallel execution where specified                         │    │   │
│  │  │ - Timeout management: per-agent timeout, total plan timeout  │    │   │
│  │  │ - Error handling: agent failure → fallback or skip           │    │   │
│  │  │ - Output: agent_results {agent_name: {output, latency,       │    │   │
│  │  │   tokens, success}}                                          │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                       │   │
│  │  Node 6: RESULT SYNTHESIZER                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ - Merges outputs from multiple agents into coherent response │    │   │
│  │  │ - Resolves conflicts: agent A said X, agent B said Y         │    │   │
│  │  │ - Formats for user consumption: text, cards, tables, actions │    │   │
│  │  │ - Adds disclaimers where confidence is low                   │    │   │
│  │  │ - Output: final_response ready for user                      │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                       │   │
│  │  Node 7: QUALITY GATE                                                │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ - Factuality check (spot-check generated content)            │    │   │
│  │  │ - Tone check (appropriate for context)                       │    │   │
│  │  │ - Completeness check (did we answer the user's question?)     │    │   │
│  │  │ - Safety check (output moderation)                           │    │   │
│  │  │ - Output: PASS (send to user) / REVISE (loop back)           │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     SUPERVISOR TOOLS                                   │   │
│  │                                                                       │   │
│  │  Tool                    │ Purpose                                    │   │
│  │  ───────────────────────┼─────────────────────────────────────────── │   │
│  │  route_to_agent          │ Invokes a specialized agent subgraph       │   │
│  │  ask_user                │ Pauses execution for user input/clarification│  │
│  │  request_approval        │ Pauses for HITL approval gate              │   │
│  │  search_memory           │ Queries Memory Agent for context           │   │
│  │  log_audit               │ Logs supervisor decision for audit trail   │   │
│  │  escalate_to_human       │ Escalates to human support (admin)         │   │
│  │  track_metric            │ Emits metric for monitoring                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Supervisor Agent Specifications

#### Purpose
Central coordinator — routes intents, plans tasks, dispatches to specialized agents, synthesizes results, enforces quality.

#### Inputs
- User message + session state
- Full context package from Memory Agent
- Previous agent results (in multi-turn plans)

#### Outputs
- User-facing response (text + structured components)
- Agent execution plan (internal)
- Audit log entries

#### Tools
`route_to_agent`, `ask_user`, `request_approval`, `search_memory`, `log_audit`, `escalate_to_human`, `track_metric`

#### Memory Requirements
- Working memory: current plan execution state, agent results, pending approvals
- No persistent memory of its own — delegates to Memory Agent

#### Failure Handling

| Failure Mode | Response |
|-------------|----------|
| Intent classification confidence < 0.7 | Ask clarifying question. Narrow down with 2–3 suggested intents as buttons. |
| Task planner creates circular dependency | Detect cycle. Simplify to sequential execution. Alert engineering. |
| All specialized agents fail for a task | Graceful degradation: "I wasn't able to complete this request. Here's what I know, and here's what you can try manually." |
| Quality gate fails 3 times | Send best effort response with disclaimer: "This response may not meet our usual quality standards. Our team has been notified." |
| User message violates content policy | Polite refusal. "I can't help with that request. I'm designed to assist with your job search and career growth." |

#### Evaluation Metrics

| Metric | Target |
|--------|--------|
| Intent classification accuracy | > 92% |
| Task plan efficiency (% of agents invoked that were actually needed) | > 85% |
| First-response resolution (% of user intents satisfied without follow-up) | > 70% |
| Quality gate pass rate (first attempt) | > 85% |

---

## 4. Agent Orchestration

### 4.1 LangGraph Graph Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     LANGGRAPH ORCHESTRATION STRUCTURE                         │
│                                                                              │
│  ROOT GRAPH: SupervisorGraph                                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  State: SupervisorState                                                │  │
│  │                                                                        │  │
│  │  Nodes:                                                                │  │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐           │  │
│  │  │guardrail ├──→│ context  ├──→│ intent   ├──→│  task    │           │  │
│  │  │          │   │ builder  │   │ router   │   │ planner  │           │  │
│  │  └──────────┘   └──────────┘   └────┬─────┘   └────┬─────┘           │  │
│  │                                     │               │                 │  │
│  │                          ┌──────────┼───────────────┼───────┐         │  │
│  │                          │          │               │       │         │  │
│  │                          ▼          ▼               ▼       ▼         │  │
│  │                    ┌──────────────────────────────────────────┐       │  │
│  │                    │         AGENT DISPATCHER                 │       │  │
│  │                    │                                          │       │  │
│  │                    │  ┌──────────────────────────────────┐   │       │  │
│  │                    │  │  Conditional routing based on     │   │       │  │
│  │                    │  │  intent + plan:                   │   │       │  │
│  │                    │  │                                   │   │       │  │
│  │                    │  │  discover_jobs → JobDiscoveryAgent │   │       │  │
│  │                    │  │  match_me → JobMatchingAgent      │   │       │  │
│  │                    │  │  tailor_resume → ResumeAgent      │   │       │  │
│  │                    │  │  generate_cover_letter → CLAgen   │   │       │  │
│  │                    │  │  prep_interview → InterviewAgent  │   │       │  │
│  │                    │  │  track_applications → AppTrackAgn │   │       │  │
│  │                    │  │  follow_up → FollowUpAgent        │   │       │  │
│  │                    │  │  skill_gap → CareerCoachAgent     │   │       │  │
│  │                    │  │  career_advice → CareerCoachAgent │   │       │  │
│  │                    │  │  update_profile → ProfileAgent    │   │       │  │
│  │                    │  │  general_question → Supervisor    │   │       │  │
│  │                    │  │    (handles directly)             │   │       │  │
│  │                    │  └──────────────────────────────────┘   │       │  │
│  │                    └────────────────┬─────────────────────────┘       │  │
│  │                                     │                                 │  │
│  │                          ┌──────────┴──────────┐                      │  │
│  │                          ▼                     ▼                      │  │
│  │                    ┌──────────┐          ┌──────────┐                 │  │
│  │                    │ human    │          │ result   │                 │  │
│  │                    │ gate     │          │ synth.   │                 │  │
│  │                    │ (if req) │          │          │                 │  │
│  │                    └────┬─────┘          └────┬─────┘                 │  │
│  │                         │                    │                        │  │
│  │                         └────────┬───────────┘                        │  │
│  │                                  ▼                                    │  │
│  │                           ┌──────────┐                                │  │
│  │                           │ quality  │                                │  │
│  │                           │ gate     │                                │  │
│  │                           └────┬─────┘                                │  │
│  │                                │                                      │  │
│  │                   ┌────────────┼────────────┐                         │  │
│  │                   ▼            ▼            ▼                         │  │
│  │              PASS          REVISE        FAIL                         │  │
│  │              (respond)     (loop to     (graceful                     │  │
│  │                            synth)       degradation)                  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  EDGES (Conditional Routing):                                                │
│                                                                              │
│  guardrail → BLOCK → END                                                     │
│  guardrail → PASS  → context_builder                                         │
│                                                                              │
│  intent_router → confidence < 0.7 → ask_user → END (wait for user)          │
│  intent_router → confidence ≥ 0.7 → task_planner                             │
│                                                                              │
│  task_planner → single_agent → dispatcher → that agent                       │
│  task_planner → multi_step  → dispatcher → agent[0] → ... → agent[N]         │
│  task_planner → parallel    → dispatcher → fan-out → fan-in                   │
│                                                                              │
│  agent → needs_approval → human_gate → approved → result_synthesizer         │
│  agent → needs_approval → human_gate → rejected → agent (revise) or END      │
│  agent → no_approval    → result_synthesizer                                 │
│                                                                              │
│  quality_gate → PASS   → respond_to_user → END                               │
│  quality_gate → REVISE → result_synthesizer (max 3 loops)                    │
│  quality_gate → FAIL   → graceful_degradation → END                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Parallel vs Sequential Execution

```
┌─────────────────────────────────────────────────────────────────────┐
│                   EXECUTION PATTERNS                                 │
│                                                                      │
│  PATTERN 1: SEQUENTIAL (Dependent Agents)                            │
│                                                                      │
│  User: "Find me matching jobs and tailor my resume for the top one"  │
│                                                                      │
│  Plan:                                                               │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                       │
│  │Discovery │───→│ Matching │───→│ Resume   │                       │
│  │Agent     │    │Agent     │    │Agent     │                       │
│  │          │    │          │    │          │                       │
│  │Finds jobs│    │Scores &  │    │Tailors   │                       │
│  │          │    │ranks them│    │for top   │                       │
│  └──────────┘    └──────────┘    └──────────┘                       │
│                                                                      │
│  PATTERN 2: PARALLEL (Independent Agents)                            │
│                                                                      │
│  User: "I just got an interview at Stripe. Prep me."                 │
│                                                                      │
│  Plan:                                                               │
│  ┌──────────┐                                                        │
│  │Discovery │──→ Company research (Stripe)                           │
│  │Agent     │                                                        │
│  └──────────┘                                                        │
│  ┌──────────┐    ┌──────────────────────────────┐                    │
│  │Interview │──→ │Interview Prep Plan           │                    │
│  │Agent     │    │(merged from all three outputs)│                    │
│  └──────────┘    └──────────────────────────────┘                    │
│  ┌──────────┐                                                        │
│  │Matching  │──→ Role comparison (similar roles at Stripe)           │
│  │Agent     │                                                        │
│  └──────────┘                                                        │
│                                                                      │
│  PATTERN 3: FAN-OUT/FAN-IN (Multi-perspective)                       │
│                                                                      │
│  User: "Should I take Job A or Job B?"                               │
│                                                                      │
│  Plan:                                                               │
│                     ┌──────────────┐                                 │
│               ┌────→│Career Coach  │──→ Growth perspective      ───┐│
│               │     └──────────────┘                               ││
│  ┌──────────┐ │     ┌──────────────┐                               ││
│  │Matching  │─┼────→│Matching Agent│──→ Match quality perspective──┼│
│  │Agent     │ │     └──────────────┘                               ││
│  │(score    │ │     ┌──────────────┐                               ││
│  │both jobs)│─┼────→│Interview     │──→ Interview difficulty   ───┼│
│  └──────────┘ │     │Agent         │                               ││
│               │     └──────────────┘                               ││
│               │     ┌──────────────┐                               ││
│               └────→│Memory Agent  │──→ Long-term alignment    ───┘│
│                     └──────────────┘                               │
│                     ┌────────────────────┐                          │
│                     │Result Synthesizer  │                          │
│                     │(comparison table + │                          │
│                     │ recommendation)    │                          │
│                     └────────────────────┘                          │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 Checkpointing & Resumption

```
┌─────────────────────────────────────────────────────────────────────┐
│                   CHECKPOINTING STRATEGY                             │
│                                                                      │
│  MECHANISM: LangGraph PostgresSaver                                   │
│                                                                      │
│  WHAT IS CHECKPOINTED:                                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ - Full SupervisorState after EVERY node execution             │   │
│  │ - Agent subgraph states (nested checkpoint)                   │   │
│  │ - Pending approvals (serialized in state)                     │   │
│  │ - Execution plan progress (which steps completed)             │   │
│  │ - Token usage per step (for cost tracking)                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  WHEN CHECKPOINTS ARE WRITTEN:                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ - After every Supervisor node (guardrail, context, intent...) │   │
│  │ - After every specialized agent invocation completes          │   │
│  │ - Before every HITL gate (so user can resume after hours)     │   │
│  │ - On error (so failed execution can be inspected)             │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  RESUMPTION:                                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ - User returns → load latest checkpoint for session           │   │
│  │ - If checkpoint is at HITL gate → show pending approval       │   │
│  │ - If checkpoint is mid-plan → resume from last completed step │   │
│  │ - If checkpoint is post-error → Supervisor can retry or       │   │
│  │   explain what failed                                         │   │
│  │ - Checkpoints TTL: 30 days for incomplete sessions            │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. Agent Communication

### 5.1 Communication Methods

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMMUNICATION METHODS                                 │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ METHOD 1: DIRECT INVOCATION (LangGraph Subgraph)                      │   │
│  │                                                                       │   │
│  │  Use: Supervisor → Specialized Agent (primary pattern)                │   │
│  │  Mechanism: LangGraph StateGraph composition. Supervisor's             │   │
│  │            dispatcher node calls agent subgraph with state subset.     │   │
│  │  Latency: Synchronous (blocking within graph execution)                │   │
│  │  Context: Passed as state slice (typed, validated)                     │   │
│  │                                                                       │   │
│  │  ┌────────────┐                          ┌──────────────────┐        │   │
│  │  │Supervisor  │──invoke_subgraph(────────→│Specialized Agent │        │   │
│  │  │            │  state_slice,             │(LangGraph)       │        │   │
│  │  │            │  config)                  │                  │        │   │
│  │  │            │←─────result──────────────│                  │        │   │
│  │  └────────────┘                          └──────────────────┘        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ METHOD 2: ASYNC EVENT (Redis Streams)                                 │   │
│  │                                                                       │   │
│  │  Use: Cross-service, background, or fire-and-forget communication     │   │
│  │  Mechanism: Agent publishes event → Redis Stream → consumer picks up  │   │
│  │  Latency: Async (P95 < 1s delivery)                                   │   │
│  │  Context: Event payload (structured, minimal)                          │   │
│  │                                                                       │   │
│  │  Examples:                                                            │   │
│  │  - JobDiscoveryAgent → publishes `job.discovered`                     │   │
│  │    → MatchingAgent consumes → triggers match sweep for affected users │   │
│  │  - ApplicationTrackingAgent → publishes `app.status_changed`          │   │
│  │    → MemoryAgent consumes → stores episodic memory                    │   │
│  │    → NotificationService consumes → sends push notification           │   │
│  │  - MemoryAgent → publishes `memory.preference_shift`                  │   │
│  │    → SupervisorAgent consumes → adjusts future routing                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ METHOD 3: MEMORY-MEDIATED (Shared State via Memory Agent)             │   │
│  │                                                                       │   │
│  │  Use: When agents need persistent shared context without direct call  │   │
│  │  Mechanism: Agent A writes to Memory Agent → Agent B reads from       │   │
│  │            Memory Agent on next invocation                             │   │
│  │  Latency: Eventual consistency (next agent invocation)                 │   │
│  │                                                                       │   │
│  │  Example:                                                             │   │
│  │  - ProfileAgent updates user skills                                   │   │
│  │    → MemoryAgent stores in semantic memory                            │   │
│  │    → Next time MatchingAgent runs, it gets updated skills             │   │
│  │    → No direct ProfileAgent → MatchingAgent communication             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ METHOD 4: HUMAN-IN-THE-LOOP (Supervisor Pause & Resume)               │   │
│  │                                                                       │   │
│  │  Use: When agent needs user input or approval before proceeding       │   │
│  │  Mechanism: LangGraph interrupt() — graph execution pauses,            │   │
│  │            checkpoints state, waits for external resume signal        │   │
│  │  Latency: Indefinite (user controls timing)                           │   │
│  │                                                                       │   │
│  │  ┌────────────┐   interrupt()   ┌──────────────┐    user action      │   │
│  │  │Supervisor  │───────────────→│ Checkpoint    │──────────────────→  │   │
│  │  │            │                │ (PostgreSQL)  │    resume with       │   │
│  │  │            │←───────────────│              │←── approval/input    │   │
│  │  └────────────┘   resume()     └──────────────┘                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Agent Interaction Protocol

Every inter-agent communication follows this contract:

```
┌─────────────────────────────────────────────────────────────────────┐
│                   AGENT INTERACTION PROTOCOL                         │
│                                                                      │
│  REQUEST (Supervisor → Agent):                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ {                                                            │   │
│  │   "call_id": "uuid-v7",           // unique per invocation   │   │
│  │   "parent_call_id": "uuid-v7",    // supervisor call         │   │
│  │   "agent_type": "ResumeAgent",                                 │   │
│  │   "user_id": "uuid",                                           │   │
│  │   "session_id": "uuid",                                        │   │
│  │   "intent": "tailor_resume",                                   │   │
│  │   "context": {                    // minimal, relevant         │   │
│  │     "profile": {...},             // user profile              │   │
│  │     "job": {...},                 // target job                │   │
│  │     "match_analysis": {...},      // from MatchingAgent        │   │
│  │     "template_id": "..."                                       │   │
│  │   },                                                           │   │
│  │   "config": {                                                   │   │
│  │     "needs_approval": true,       // HITL gate required        │   │
│  │     "timeout_ms": 15000,          // max execution time        │   │
│  │     "max_retries": 2,                                          │   │
│  │     "tone": "professional"                                     │   │
│  │   },                                                           │   │
│  │   "trace_context": {              // for distributed tracing   │   │
│  │     "trace_id": "...",                                         │   │
│  │     "span_id": "..."                                           │   │
│  │   }                                                            │   │
│  │ }                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  RESPONSE (Agent → Supervisor):                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ {                                                            │   │
│  │   "call_id": "uuid-v7",           // matches request         │   │
│  │   "status": "success" | "partial" | "failed",                │   │
│  │   "result": {...},                // agent-specific output   │   │
│  │   "artifacts": [{                 // for user display        │   │
│  │     "type": "resume_diff" | "text" | "table" | "chart",     │   │
│  │     "content": {...}                                          │   │
│  │   }],                                                        │   │
│  │   "metadata": {                                               │   │
│  │     "latency_ms": 4200,                                       │   │
│  │     "tokens_used": { "input": 3500, "output": 1200 },        │   │
│  │     "model": "deepseek-chat",                                 │   │
│  │     "tools_called": ["analyze_jd_keywords", "map_experience"],│   │
│  │     "needs_approval": true,                                   │   │
│  │     "confidence": 0.89                                        │   │
│  │   },                                                          │   │
│  │   "error": null | {                                           │   │
│  │     "type": "llm_timeout" | "tool_failure" | "validation",   │   │
│  │     "message": "...",                                         │   │
│  │     "retryable": true | false                                 │   │
│  │   }                                                           │   │
│  │ }                                                             │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. State Management

### 6.1 LangGraph State Definitions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STATE DEFINITIONS                                     │
│                         (TypedDict Schemas)                                   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    SUPERVISOR STATE (Root Graph)                      │   │
│  │                                                                       │   │
│  │  SupervisorState {                                                    │   │
│  │    // ── Session Identity ──                                          │   │
│  │    session_id:       str                    // unique session UUID    │   │
│  │    user_id:          str                    // authenticated user     │   │
│  │    tier:             "free" | "pro" | "premium"                     │   │
│  │    locale:           str                    // "en-US", etc.         │   │
│  │                                                                       │   │
│  │    // ── User Input ──                                                │   │
│  │    user_message:     str | None             // raw user text          │   │
│  │    user_action:      str | None             // button click, etc.     │   │
│  │    user_attachments: list[Attachment] | None // files uploaded        │   │
│  │                                                                       │   │
│  │    // ── Context (Memory Agent output) ──                              │   │
│  │    user_profile:     Profile | None         // full structured profile│   │
│  │    user_preferences: Preferences | None     // preference weights     │   │
│  │    recent_history:   list[Episode]          // last N interactions    │   │
│  │    relevant_memories: list[Memory]          // semantic search results│   │
│  │    active_applications: list[Application]   // current pipeline state │   │
│  │                                                                       │   │
│  │    // ── Routing & Planning ──                                        │   │
│  │    intent:           Intent | None          // classified intent      │   │
│  │    intent_confidence: float                 // 0.0 - 1.0              │   │
│  │    execution_plan:   list[PlanStep]         // task decomposition     │   │
│  │    current_step:     int                    // index into plan        │   │
│  │                                                                       │   │
│  │    // ── Agent Results ──                                             │   │
│  │    agent_results:    dict[str, AgentResult] // agent_name → result    │   │
│  │                                                                       │   │
│  │    // ── Human-in-the-Loop ──                                         │   │
│  │    pending_approval: ApprovalRequest | None // waiting for user       │   │
│  │    approval_history:  list[ApprovalDecision] // audit trail           │   │
│  │                                                                       │   │
│  │    // ── Response ──                                                  │   │
│  │    final_response:   Response | None        // ready for user         │   │
│  │    response_artifacts: list[Artifact]       // structured components  │   │
│  │                                                                       │   │
│  │    // ── Metadata ──                                                  │   │
│  │    call_id:          str                    // this invocation        │   │
│  │    total_tokens:     int                    // aggregate token usage  │   │
│  │    total_latency_ms: int                    // aggregate latency      │   │
│  │    errors:           list[AgentError]       // errors encountered     │   │
│  │    quality_gate_passes: int                 // gate iterations        │   │
│  │    trace_context:    TraceContext           // distributed tracing    │   │
│  │  }                                                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    PROFILE AGENT STATE                                 │   │
│  │                                                                       │   │
│  │  ProfileAgentState {                                                  │   │
│  │    // ── Inputs ──                                                    │   │
│  │    raw_resume:       bytes | None           // uploaded file          │   │
│  │    raw_linkedin:     bytes | None           // LinkedIn export        │   │
│  │    github_username:  str | None                                      │   │
│  │    manual_entries:   dict | None            // user-typed data        │   │
│  │    existing_profile: Profile | None         // for updates            │   │
│  │                                                                       │   │
│  │    // ── Extraction ──                                                │   │
│  │    extracted_sections: dict[str, list]      // raw extraction         │   │
│  │    extraction_confidence: dict[str, float]  // per-field confidence   │   │
│  │    conflicting_entries: list[Conflict]      // needs user resolution  │   │
│  │    missing_fields:    list[str]             // gaps in profile        │   │
│  │                                                                       │   │
│  │    // ── Enrichment ──                                                │   │
│  │    enriched_profile:  Profile | None        // after enrichment       │   │
│  │    skill_extractions: list[Skill]           // inferred skills        │   │
│  │    suggested_enrichments: list[Enrichment]  // for user review        │   │
│  │                                                                       │   │
│  │    // ── Outputs ──                                                   │   │
│  │    final_profile:     Profile | None        // ready to save          │   │
│  │    profile_embedding: list[float] | None    // 3072d vector           │   │
│  │    skill_embeddings:  list[SkillEmbedding]                           │   │
│  │  }                                                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    MATCHING AGENT STATE                                │   │
│  │                                                                       │   │
│  │  MatchingAgentState {                                                 │   │
│  │    // ── Inputs ──                                                    │   │
│  │    user_profile:      Profile                                        │   │
│  │    user_preferences:  Preferences                                    │   │
│  │    job_pool:          list[Job]             // to score               │   │
│  │    user_history:      list[Interaction]    // implicit feedback      │   │
│  │                                                                       │   │
│  │    // ── Scoring ──                                                   │   │
│  │    scored_jobs:       list[ScoredJob]       // jobs with scores       │   │
│  │    dimension_scores:  dict[str, float]      // per-dimension breakdown│   │
│  │    explanations:      dict[str, list[str]]  // job_id → explanations │   │
│  │    dealbreakers_hit:  dict[str, list[str]]  // job_id → dealbreakers │   │
│  │                                                                       │   │
│  │    // ── Ranking ──                                                   │   │
│  │    ranked_jobs:       list[ScoredJob]       // final ranked list      │   │
│  │    ranking_signals:   dict[str, float]      // boosts applied         │   │
│  │                                                                       │   │
│  │    // ── Outputs ──                                                   │   │
│  │    top_matches:       list[ScoredJob]       // top 20                 │   │
│  │    high_score_alerts: list[ScoredJob]       // ≥ 85% matches          │   │
│  │  }                                                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    MEMORY AGENT STATE                                  │   │
│  │                                                                       │   │
│  │  MemoryAgentState {                                                   │   │
│  │    // ── Retrieval ──                                                 │   │
│  │    query_context:     dict                   // what the caller needs │   │
│  │    retrieved_episodes: list[Episode]         // recent interactions   │   │
│  │    retrieved_semantic: list[Memory]          // relevant memories     │   │
│  │    retrieved_procedural: list[ProceduralMemory] // best workflows     │   │
│  │                                                                       │   │
│  │    // ── Storage ──                                                   │   │
│  │    new_episode:       Episode | None         // to store              │   │
│  │    new_semantic:      Memory | None          // to upsert             │   │
│  │    new_procedural:    ProceduralMemory | None                         │   │
│  │                                                                       │   │
│  │    // ── Consolidation ──                                             │   │
│  │    raw_episodes_batch: list[Episode]         // to consolidate        │   │
│  │    extracted_patterns: list[Pattern]         // learned patterns      │   │
│  │    updated_preferences: Preferences | None   // evolved weights       │   │
│  │    updated_narrative:  str | None            // career story          │   │
│  │                                                                       │   │
│  │    // ── Context Package (output) ──                                   │   │
│  │    context_package:   ContextPackage | None                           │   │
│  │  }                                                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    APPLICATION TRACKING AGENT STATE                    │   │
│  │                                                                       │   │
│  │  ApplicationTrackingState {                                           │   │
│  │    // ── Pipeline ──                                                  │   │
│  │    applications:      list[Application]    // all user applications   │   │
│  │    pipeline_summary:  PipelineSummary      // counts per stage        │   │
│  │                                                                       │   │
│  │    // ── Events ──                                                    │   │
│  │    incoming_email:    Email | None         // parsed email            │   │
│  │    calendar_event:    CalendarEvent | None // interview detected      │   │
│  │    status_change:     StatusChange | None  // to apply                │   │
│  │                                                                       │   │
│  │    // ── Tasks & Deadlines ──                                         │   │
│  │    active_tasks:      list[Task]                                      │   │
│  │    approaching_deadlines: list[Deadline]                              │   │
│  │    ghosted_applications: list[Application]                            │   │
│  │  }                                                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 State Transitions

```
┌─────────────────────────────────────────────────────────────────────┐
│                   STATE TRANSITION MAP                                │
│                                                                      │
│  USER_MESSAGE_RECEIVED                                               │
│  ───────────────────                                                 │
│  Trigger: User sends message or clicks action                        │
│  Transition: SupervisorState.user_message ← user text                │
│             SupervisorState.user_action ← action name (if button)    │
│             → guardrail                                               │
│                                                                      │
│  CONTEXT_LOADED                                                      │
│  ──────────────                                                      │
│  Trigger: context_builder completes                                   │
│  Transition: SupervisorState.user_profile ← from MemoryAgent         │
│             SupervisorState.user_preferences ← from MemoryAgent      │
│             SupervisorState.recent_history ← from MemoryAgent        │
│             SupervisorState.active_applications ← from AppTrackAgent │
│             → intent_router                                           │
│                                                                      │
│  INTENT_CLASSIFIED                                                   │
│  ─────────────────                                                   │
│  Trigger: intent_router completes                                     │
│  Transition: SupervisorState.intent ← classified intent               │
│             SupervisorState.intent_confidence ← confidence score      │
│             IF confidence < 0.7 → ask_user (HITL)                    │
│             IF confidence ≥ 0.7 → task_planner                        │
│                                                                      │
│  PLAN_CREATED                                                        │
│  ─────────────                                                       │
│  Trigger: task_planner completes                                      │
│  Transition: SupervisorState.execution_plan ← plan steps              │
│             SupervisorState.current_step ← 0                          │
│             → agent_dispatcher                                         │
│                                                                      │
│  AGENT_COMPLETED                                                     │
│  ────────────────                                                    │
│  Trigger: A specialized agent finishes execution                      │
│  Transition: SupervisorState.agent_results[agent_name] ← result      │
│             SupervisorState.current_step ← current_step + 1           │
│             SupervisorState.errors ← append if failed                 │
│             IF more steps → agent_dispatcher (for next step)          │
│             IF all steps done → result_synthesizer                     │
│                                                                      │
│  APPROVAL_REQUESTED                                                  │
│  ──────────────────                                                  │
│  Trigger: Agent output needs user approval                            │
│  Transition: SupervisorState.pending_approval ← approval request      │
│             → INTERRUPT (LangGraph interrupt)                         │
│             → Wait for user action                                    │
│                                                                      │
│  APPROVAL_RECEIVED                                                   │
│  ─────────────────                                                   │
│  Trigger: User approves/rejects/edits                                 │
│  Transition: SupervisorState.approval_history ← append decision      │
│             SupervisorState.pending_approval ← None                   │
│             IF approved → result_synthesizer                          │
│             IF rejected → agent_dispatcher (revise) or END             │
│             → RESUME (LangGraph resume)                               │
│                                                                      │
│  RESPONSE_SENT                                                       │
│  ─────────────                                                       │
│  Trigger: quality_gate passes                                         │
│  Transition: MemoryAgent ← store episode (this interaction)          │
│             AuditLog ← store full execution trace                     │
│             → END                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Retry Mechanisms

### 7.1 Retry Strategy by Failure Type

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RETRY STRATEGY MATRIX                               │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ FAILURE TYPE         │ RETRY?  │ MAX    │ BACKOFF        │ STRATEGY  │   │
│  │ ────────────────────┼─────────┼────────┼───────────────┼───────────│   │
│  │ LLM API Timeout      │ YES     │ 3      │ 1s, 2s, 4s    │ Retry with│   │
│  │                       │         │        │               │ same input│   │
│  │ LLM API Rate Limit   │ YES     │ 3      │ Retry-After   │ Honor     │   │
│  │ (429)                 │         │        │ header + jitter│ header    │   │
│  │ LLM API Server Error │ YES     │ 3      │ 1s, 3s, 9s    │ Retry with│   │
│  │ (5xx)                 │         │        │               │ same input│   │
│  │ LLM Output Validation │ YES     │ 2      │ 0s (immediate)│ Retry with│   │
│  │ Failed                │         │        │               │ stricter  │   │
│  │                       │         │        │               │ prompt    │   │
│  │ Tool Execution Failed │ YES     │ 2      │ 2s, 8s        │ Retry tool│   │
│  │ (transient)           │         │        │               │ call      │   │
│  │ Tool Execution Failed │ NO      │ -      │ -             │ Report    │   │
│  │ (permanent: bad params)│        │        │               │ error     │   │
│  │ Embedding API Failure │ YES     │ 3      │ 1s, 2s, 4s    │ Retry     │   │
│  │ Database Connection   │ YES     │ 5      │ 100ms, 200ms, │ Retry with│   │
│  │ Error                  │         │        │ 400ms, 800ms, │ jitter    │   │
│  │                       │         │        │ 1.6s           │           │   │
│  │ State Corruption      │ NO      │ -      │ -             │ Load last │   │
│  │ (checkpoint invalid)  │         │        │               │ good ckpt │   │
│  │ Content Safety Flag   │ NO      │ -      │ -             │ Refuse    │   │
│  │                       │         │        │               │ politely  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                   RETRY EXECUTION FLOW                                │   │
│  │                                                                       │   │
│  │  Agent invoked                                                        │   │
│  │     │                                                                 │   │
│  │     ▼                                                                 │   │
│  │  Execute agent node                                                   │   │
│  │     │                                                                 │   │
│  │     ├── SUCCESS → return result                                       │   │
│  │     │                                                                 │   │
│  │     └── FAILURE ─────────────────────────────────────────┐           │   │
│  │         │                                                 │           │   │
│  │         ▼                                                 │           │   │
│  │  ┌─────────────────┐                                      │           │   │
│  │  │ Is it retryable? │                                      │           │   │
│  │  └────┬────────┬───┘                                      │           │   │
│  │       │        │                                           │           │   │
│  │       NO      YES                                          │           │   │
│  │       │        │                                           │           │   │
│  │       ▼        ▼                                           │           │   │
│  │  ┌────────┐ ┌──────────────────┐                           │           │   │
│  │  │Report  │ │Retries < max?    │                           │           │   │
│  │  │error   │ └──┬──────────┬───┘                           │           │   │
│  │  │to Sup. │    │          │                                │           │   │
│  │  └────────┘   YES        NO                               │           │   │
│  │                │          │                                │           │   │
│  │                ▼          ▼                                │           │   │
│  │  ┌──────────────────┐ ┌──────────────────┐                │           │   │
│  │  │Apply backoff +    │ │Report partial    │                │           │   │
│  │  │jitter             │ │failure to Sup.   │                │           │   │
│  │  └────────┬─────────┘ │(Sup. decides:     │                │           │   │
│  │           │           │ skip / fallback / │                │           │   │
│  │           ▼           │ ask user / abort) │                │           │   │
│  │  Retry agent node ────┘──────────────────┘                │           │   │
│  │  (loop back)                                                │           │   │
│  └─────────────────────────────────────────────────────────────┘           │   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Supervisor Retry Orchestration

When a specialized agent exhausts its retries, the Supervisor decides the next action:

| Agent Failure Context | Supervisor Decision |
|----------------------|---------------------|
| ResumeAgent fails, MatchingAgent succeeded | Show match results without tailored resume. Offer manual tailoring or retry button. |
| MatchingAgent fails, user asked "find me jobs" | Fall back: show jobs sorted by recency with basic keyword filter. Explain: "AI matching is temporarily unavailable. Showing recent relevant jobs." |
| Any agent fails during multi-step plan | Complete remaining independent steps. Skip failed step. Explain what was skipped and why. |
| All agents in a plan fail | Graceful degradation message. Escalate to engineering. Offer manual alternatives. |
| MemoryAgent retrieval fails | Proceed with empty context. Quality may degrade — warn user: "I'm having trouble accessing your profile. Responses may be less personalized." |

### 7.3 Circuit Breaker

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CIRCUIT BREAKER CONFIG                            │
│                                                                      │
│  Per-LLM-Provider Circuit Breaker:                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ STATE: CLOSED (normal operation)                              │   │
│  │   → Error rate < 5% → stay CLOSED                             │   │
│  │   → Error rate ≥ 5% in 60s window → OPEN                      │   │
│  │                                                                │   │
│  │ STATE: OPEN (calls blocked)                                    │   │
│  │   → All calls immediately fail with CircuitBreakerOpen         │   │
│  │   → Supervisor routes to fallback model automatically         │   │
│  │   → After 30s → HALF_OPEN                                     │   │
│  │                                                                │   │
│  │ STATE: HALF_OPEN (testing recovery)                            │   │
│  │   → Allow 1 probe request every 10s                            │   │
│  │   → Probe succeeds → CLOSED (resume normal)                    │   │
│  │   → Probe fails → OPEN (wait another 30s)                      │   │
│  │   → 5 consecutive probe failures → double wait time (60s)      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Provider Fallback Chain:                                             │
│  DeepSeek (primary) → OpenAI GPT-4o (secondary) → cached response    │
│  If DeepSeek circuit is OPEN, all calls route to OpenAI automatically.│
└─────────────────────────────────────────────────────────────────────┘
```

---

## 8. Human Approval Workflows

### 8.1 HITL Gate Configuration Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      HUMAN APPROVAL CONFIGURATION                             │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ AGENT          │ PRE-EXECUTION   │ POST-EXECUTION  │ AUTO MODE        │   │
│  │                │ GATE            │ GATE             │ (Premium)        │   │
│  │ ──────────────┼─────────────────┼─────────────────┼────────────────  │   │
│  │ ProfileAgent   │ -               │ Profile changes  │ Profile changes  │   │
│  │                │                 │ must be reviewed │ auto-applied with│   │
│  │                │                 │ before saving    │ undo             │   │
│  │                │                 │                  │                  │   │
│  │ DiscoveryAgent │ -               │ -                │ -                │   │
│  │ (background)   │                 │ (no user-facing  │                  │   │
│  │                │                 │  output)         │                  │   │
│  │                │                 │                  │                  │   │
│  │ MatchingAgent  │ -               │ -                │ -                │   │
│  │                │                 │ (scores are      │                  │   │
│  │                │                 │  informational)  │                  │   │
│  │                │                 │                  │                  │   │
│  │ ResumeAgent    │ User must       │ Diff review      │ Auto-apply for   │   │
│  │                │ confirm "tailor │ required before  │ match ≥ 85%.     │   │
│  │                │ for this job"   │ download/send    │ Diff still shown.│   │
│  │                │                 │                  │                  │   │
│  │ CoverLetterAgt │ Same as Resume  │ Review required  │ Auto-apply for   │   │
│  │                │                 │ before send      │ match ≥ 85%.     │   │
│  │                │                 │                  │                  │   │
│  │ InterviewAgent │ -               │ -                │ -                │   │
│  │                │                 │ (prep materials  │                  │   │
│  │                │                 │  are advisory)   │                  │   │
│  │                │                 │                  │                  │   │
│  │ CareerCoachAgt │ -               │ -                │ Learning plan    │   │
│  │                │                 │ (plans are       │ auto-generated   │   │
│  │                │                 │  advisory)       │                  │   │
│  │                │                 │                  │                  │   │
│  │ AppTrackingAgt │ -               │ -                │ -                │   │
│  │                │                 │ (tracking is     │                  │   │
│  │                │                 │  observational)  │                  │   │
│  │                │                 │                  │                  │   │
│  │ FollowUpAgent  │ User must       │ Review required  │ Auto-send for    │   │
│  │                │ confirm "send   │ before send      │ match ≥ 85% jobs │   │
│  │                │ follow-up"      │                  │ (configurable)   │   │
│  │                │                 │                  │                  │   │
│  │ MemoryAgent    │ -               │ -                │ -                │   │
│  │ (background)   │                 │ (system agent,   │                  │   │
│  │                │                 │  no user-facing) │                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 HITL Workflow States

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       HITL WORKFLOW STATE MACHINE                             │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  ┌──────────┐    agent_completed    ┌──────────────┐                  │   │
│  │  │  AGENT   │──────────────────────→│  APPROVAL    │                  │   │
│  │  │EXECUTING │                       │  REQUIRED    │                  │   │
│  │  │          │                       │              │                  │   │
│  │  └──────────┘                       └──────┬───────┘                  │   │
│  │                                            │                          │   │
│  │                          ┌─────────────────┼─────────────────┐        │   │
│  │                          │                 │                 │        │   │
│  │                          ▼                 ▼                 ▼        │   │
│  │                    ┌──────────┐     ┌──────────┐     ┌──────────┐    │   │
│  │                    │  USER    │     │  USER    │     │  USER    │    │   │
│  │                    │ APPROVES │     │ REJECTS  │     │  EDITS   │    │   │
│  │                    └────┬─────┘     └────┬─────┘     └────┬─────┘    │   │
│  │                         │               │                │           │   │
│  │                         ▼               ▼                ▼           │   │
│  │                    ┌──────────┐     ┌──────────┐    ┌──────────┐     │   │
│  │                    │ EXECUTE  │     │ ASK FOR  │    │MERGE EDIT│     │   │
│  │                    │ ACTION   │     │ FEEDBACK │    │& EXECUTE │     │   │
│  │                    │(send,    │     │(why      │    │          │     │   │
│  │                    │ save,    │     │rejected?)│    │          │     │   │
│  │                    │ apply)   │     └────┬─────┘    └────┬─────┘     │   │
│  │                    └────┬─────┘          │               │           │   │
│  │                         │                ▼               │           │   │
│  │                         │          ┌──────────┐          │           │   │
│  │                         │          │ REGENERATE│         │           │   │
│  │                         │          │ OR ABORT │          │           │   │
│  │                         │          └──────────┘          │           │   │
│  │                         │                                │           │   │
│  │                         ▼                                ▼           │   │
│  │                    ┌──────────────────────────────────────────┐     │   │
│  │                    │              COMPLETED                   │     │   │
│  │                    │  (continue graph execution)              │     │   │
│  │                    └──────────────────────────────────────────┘     │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  APPROVAL REQUEST STRUCTURE:                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ApprovalRequest {                                                     │   │
│  │   approval_id:      str                    // unique                  │   │
│  │   agent_type:       str                    // which agent             │   │
│  │   action_type:      str                    // "send_email", "save",   │   │
│  │                                            // "apply_to_job"          │   │
│  │   action_summary:   str                    // one-line for user       │   │
│  │   action_detail:    str                    // full description        │   │
│  │   diff_view:        DiffView | None        // for resume/CL changes  │   │
│  │   preview:          str | None             // rendered preview        │   │
│  │   risk_level:       "low" | "medium" | "high"                        │   │
│  │   risk_explanation: str | None                                        │   │
│  │   created_at:        datetime                                         │   │
│  │   expires_at:        datetime | None      // auto-expire after 7d    │   │
│  │ }                                                                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  APPROVAL RESPONSE STRUCTURE:                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ApprovalDecision {                                                    │   │
│  │   approval_id:      str                    // matches request         │   │
│  │   decision:         "approved" | "rejected" | "edited"               │   │
│  │   edits:            dict | None            // user modifications      │   │
│  │   rejection_reason: str | None             // why rejected            │   │
│  │   decided_at:       datetime                                          │   │
│  │ }                                                                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.3 Approval UX Modes

| Mode | Description | When Used |
|------|-------------|-----------|
| **Inline Diff** | Side-by-side comparison of original vs. AI-generated. User can accept, reject, or edit individual changes. | Resume tailoring, cover letter drafts |
| **Preview Card** | Rendered preview of the action (e.g., email draft). Single approve/reject/edit button. | Follow-up emails, thank-you notes |
| **Summary Confirm** | Text summary of what will happen. Confirm/Cancel. | Bulk actions, autopilot mode |
| **Silent** | No approval needed. Action executed automatically. | Profile enrichment (low-risk), interview prep materials, match scores |

---

## 9. Agent Evaluation Framework

### 9.1 Per-Agent Evaluation Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     AGENT EVALUATION SUMMARY                                  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ AGENT          │ PRIMARY METRIC          │ TARGET    │ EVAL METHOD    │   │
│  │ ──────────────┼────────────────────────┼───────────┼─────────────── │   │
│  │ ProfileAgent   │ Field extraction F1     │ > 0.90    │ Human-annotated│   │
│  │                │                          │           │ test set (200) │   │
│  │ JobDiscovAgent │ Job coverage            │ > 90%     │ Manual audit   │   │
│  │                │ Dedup precision         │ > 98%     │ of 20 companies│   │
│  │ MatchingAgent  │ Precision@10            │ > 65%     │ User actions   │   │
│  │                │ NDCG@20                │ > 0.75    │ as ground truth│   │
│  │ ResumeAgent    │ Suggestion acceptance   │ > 75%     │ Diff analysis  │   │
│  │                │ Hallucination rate      │ < 0.5%    │ Factuality chk │   │
│  │ CoverLetterAgt │ Factuality score        │ > 99%     │ Automated ver. │   │
│  │                │ User edit distance      │ < 20%     │ Diff analysis  │   │
│  │ MemoryAgent    │ Context relevance       │ > 85%     │ Agent feedback │   │
│  │                │ Preference accuracy     │ > 80%     │ Retrospective  │   │
│  │ InterviewAgent │ Prep helpfulness        │ > 4.2/5   │ User rating    │   │
│  │ CareerCoachAgt │ Gap analysis accuracy   │ > 4.0/5   │ User rating    │   │
│  │ AppTrackingAgt │ Email classification    │ > 92%     │ User correctns │   │
│  │ FollowUpAgent  │ Response rate to FU     │ > 25%     │ Email tracking │   │
│  │ SupervisorAgent│ Intent accuracy         │ > 92%     │ User feedback  │   │
│  │                │ First-response resolve  │ > 70%     │ Session outcome│   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Cross-Agent Evaluation (System-Level)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **End-to-end task success** (% of user requests fulfilled without error or abandonment) | > 85% | Session analysis |
| **Time-to-complete** (from user request to final response) | < 30s for simple, < 90s for complex | Latency tracking |
| **Token efficiency** (tokens used / task complexity score) | Baseline + continuous improvement | Cost tracking |
| **User satisfaction** (post-interaction rating) | > 4.2/5 | In-app rating prompt |
| **Agent utilization** (% of specialized agents that are invoked at least once per day) | > 80% | Usage analytics |
| **Error cascade rate** (% of sessions where one agent failure causes downstream failures) | < 5% | Error trace analysis |

### 9.3 Continuous Evaluation Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                   EVALUATION PIPELINE                                │
│                                                                      │
│  OFFLINE EVAL (runs weekly):                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 1. Golden dataset evaluation:                                  │   │
│  │    - 500 hand-labeled examples per agent                       │   │
│  │    - Run agents against golden set                             │   │
│  │    - Compare outputs to labels                                  │   │
│  │    - Track metric trends over time                             │   │
│  │                                                                │   │
│  │ 2. Adversarial evaluation:                                     │   │
│  │    - Edge cases: empty profiles, non-English resumes,          │   │
│  │      JDs with contradictory requirements                       │   │
│  │    - Injection attempts: prompt injection in resume text       │   │
│  │    - Bias testing: demographic name variations                 │   │
│  │                                                                │   │
│  │ 3. Human eval panel:                                           │   │
│  │    - 100 random outputs per agent per week                     │   │
│  │    - 3 human raters per output                                  │   │
│  │    - Inter-rater reliability tracked                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ONLINE EVAL (continuous):                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 1. User implicit feedback:                                     │   │
│  │    - Do they accept/edit/reject agent output?                  │   │
│  │    - Do they take the recommended action?                      │   │
│  │    - Do they return to the feature?                            │   │
│  │                                                                │   │
│  │ 2. User explicit feedback:                                     │   │
│  │    - Thumbs up/down on agent responses                         │   │
│  │    - Post-task rating prompts (sparse, not annoying)           │   │
│  │    - NPS surveys (quarterly)                                   │   │
│  │                                                                │   │
│  │ 3. Guardrail triggers:                                         │   │
│  │    - Factuality check failures                                 │   │
│  │    - Content safety flags                                      │   │
│  │    - User correction rate spikes                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Appendix: LangGraph State Definitions (Reference)

### SupervisorState (Root Graph)

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `str` | Unique session identifier |
| `user_id` | `str` | Authenticated user ID |
| `tier` | `Literal["free", "pro", "premium"]` | User subscription tier |
| `user_message` | `str \| None` | Raw user text input |
| `user_action` | `str \| None` | Structured action (button click, menu selection) |
| `user_attachments` | `list[Attachment] \| None` | Uploaded files |
| `user_profile` | `Profile \| None` | Full structured user profile from Memory |
| `user_preferences` | `Preferences \| None` | Preference weights from Memory |
| `recent_history` | `list[Episode]` | Last N interactions |
| `relevant_memories` | `list[Memory]` | Vector-retrieved relevant memories |
| `active_applications` | `list[Application]` | Current pipeline state |
| `intent` | `Intent \| None` | Classified user intent |
| `intent_confidence` | `float` | Intent classification confidence (0–1) |
| `execution_plan` | `list[PlanStep]` | Decomposed task steps |
| `current_step` | `int` | Index into execution plan |
| `agent_results` | `dict[str, AgentResult]` | Results keyed by agent name |
| `pending_approval` | `ApprovalRequest \| None` | Awaiting user decision |
| `approval_history` | `list[ApprovalDecision]` | All approval decisions this session |
| `final_response` | `Response \| None` | Ready for user display |
| `response_artifacts` | `list[Artifact]` | Structured UI components |
| `call_id` | `str` | Unique invocation identifier (UUIDv7) |
| `total_tokens` | `int` | Aggregate token consumption |
| `total_latency_ms` | `int` | Aggregate wall-clock latency |
| `errors` | `list[AgentError]` | All errors encountered |
| `quality_gate_passes` | `int` | Number of quality gate iterations |
| `trace_context` | `TraceContext` | Distributed tracing identifiers |

### Intent Taxonomy

| Intent | Description | Routed To |
|--------|-------------|-----------|
| `discover_jobs` | Find new job listings matching user profile | JobDiscoveryAgent |
| `match_me` | Score and rank jobs for user | JobMatchingAgent |
| `tailor_resume` | Generate job-tailored resume variant | ResumeAgent |
| `generate_cover_letter` | Generate personalized cover letter | CoverLetterAgent |
| `prep_interview` | Generate interview preparation materials | InterviewAgent |
| `track_applications` | View/update application pipeline | ApplicationTrackingAgent |
| `follow_up` | Generate follow-up communication | FollowUpAgent |
| `analyze_skill_gap` | Identify and plan skill development | CareerCoachAgent |
| `career_advice` | Get career guidance and coaching | CareerCoachAgent |
| `update_profile` | Modify user profile | ProfileAgent |
| `general_question` | Unclassified or informational query | Supervisor (handles directly) |

### PlanStep

| Field | Type | Description |
|-------|------|-------------|
| `step_id` | `str` | Unique step identifier |
| `agent` | `str` | Agent to invoke |
| `inputs` | `dict` | Input mapping (state field → agent input) |
| `depends_on` | `list[str]` | Step IDs that must complete first |
| `parallel_group` | `str \| None` | Group ID for parallel execution |
| `needs_approval` | `bool` | Whether HITL gate is required |
| `timeout_ms` | `int` | Per-step timeout |
| `on_failure` | `Literal["skip", "abort", "fallback"]` | Failure behavior |

---

> *"A multi-agent system is only as good as its orchestration. The Supervisor is thin, the agents are sharp, and the state is the single source of truth."*

**End of Multi-Agent System Design Document**
