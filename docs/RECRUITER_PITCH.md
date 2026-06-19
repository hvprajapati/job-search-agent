# Pathfinder — Recruiter Pitch

## 30-Second Pitch

"Pathfinder is an Autonomous AI Career Agent I built from scratch — a production-grade multi-agent system that automates the entire job search pipeline. It uses a LangGraph agent with 7 tools, a 6-dimension matching engine, hybrid RAG knowledge retrieval, and a 3-tier memory system that learns user preferences over time. 36 API endpoints, 98 source files, 84 tests. Built with FastAPI, PostgreSQL+pgvector, Redis, and DeepSeek over 12 weeks as a solo engineer."

## 1-Minute Pitch

"I built Pathfinder — a production-grade Autonomous AI Career Agent. The problem: job seekers spend 11-25 hours a week across 15+ disconnected tools while employers have AI-powered screening. Pathfinder closes this gap.

Architecture-wise, it's a modular monolith with 9 bounded contexts following Clean Architecture and Domain-Driven Design. The core is a LangGraph Supervisor Agent — a 7-node state graph that routes user intents, plans multi-step tasks, executes tools, and validates outputs. It has 7 tools wrapping real services — search, match, profile, recommendations.

The agent is backed by a 3-tier memory system that learns user preferences over months — episodic raw events, semantic structured facts with vector search, and procedural behavioral patterns. Daily LLM consolidation extracts insights from raw interactions.

For reliability, I implemented a circuit breaker that opens after 5 LLM failures and falls back to deterministic plans. Every one of the 36 API endpoints degrades gracefully without the LLM. Zero endpoints crash.

The matching engine runs 6 concurrent scorers via asyncio.gather — skills, experience, education, location, preferences, culture. The resume tailoring engine has a post-generation factuality guard that verifies every AI-written claim against the user's actual profile.

I built this solo in 12 weeks. 98 source files, 84 tests, production Docker Compose deployment, Prometheus metrics, structured logging. It's a complete, deployable system."

## 3-Minute Project Walkthrough

### The Problem
Job seekers spend 11-25 hours per week across job boards, company career pages, resume builders, cover letter editors, spreadsheets, and interview prep platforms. Meanwhile, employers deploy AI-powered ATS systems that screen candidates automatically. The asymmetry is staggering — recruiters have AI, candidates don't.

### The Solution
Pathfinder is an Autonomous AI Career Agent. It's not a chatbot. It's a persistent, proactive AI system that operates 24/7 on behalf of job seekers. It discovers jobs from multiple sources, matches candidates using multi-dimensional scoring, tailors resumes with zero-hallucination guarantees, tracks applications through a kanban pipeline, and learns user preferences through long-term memory.

### The Architecture (1 min)
I chose a modular monolith — FastAPI serving 36 REST endpoints, a LangGraph Supervisor Agent with 7 nodes and 7 tools, PostgreSQL with pgvector for hybrid vector+keyword search, Redis for caching and task queuing, and DeepSeek API for LLM capabilities.

The agent graph: guardrail (safety check) → context builder (loads profile, preferences, memories) → intent router (classifies user intent from 11 types) → task planner (generates multi-step execution plan) → tool executor (runs tools) → result synthesizer (formats response) → quality gate (validates output).

### The Resilience Story (30 sec)
I designed for LLM failure from day one. A circuit breaker opens after 5 consecutive API failures. Every intent has a deterministic fallback plan. Regex-based keyword extraction works without the LLM. The skills reorder in resume tailoring is deterministic. Keyword search in RAG works without embeddings. Users experience reduced intelligence but never a crash.

### The Memory System (30 sec)
This is the strategic moat. Every agent execution, every user feedback, every profile change is stored as an episodic memory. Daily, a Celery job runs consolidation — the LLM extracts structured facts ("User prefers remote fintech roles with 3.7× apply rate") and upserts them into semantic memory with evidence tracking and confidence scoring. On each subsequent agent invocation, the context builder loads relevant memories via vector search and injects them into every LLM prompt. After 6 months, the agent knows the user's career narrative better than any human mentor.

### The Matching Engine (30 sec)
Not keyword matching. Six concurrent scorers evaluate skills (semantic + proficiency-weighted), experience (years × title relevance), education, location compatibility, preference alignment, and culture signals. Scores are human-readable — the user sees "Strong Python match (your #1 skill, 8 years)" and "Gap: No Kubernetes experience (consider adding as 'learning')".

### The Results
98 source files. 84 tests. 36 functional endpoints. Zero crashes. Graceful degradation. Docker Compose deployable. Production-ready for private alpha. Built solo in 12 weeks.
