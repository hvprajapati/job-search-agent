# Pathfinder — Production-Grade Memory Architecture

**Document Version:** 1.0
**Date:** 2026-06-17
**Role:** Staff AI Engineer — Memory Systems
**Storage:** PostgreSQL 16 + pgvector 0.7+
**Classification:** Confidential — Internal

---

## Table of Contents

1. [Memory Architecture Overview](#1-memory-architecture-overview)
2. [Memory Types & Schemas](#2-memory-types--schemas)
3. [Memory Lifecycle](#3-memory-lifecycle)
4. [Memory Retrieval](#4-memory-retrieval)
5. [Memory Ranking](#5-memory-ranking)
6. [Memory Compression](#6-memory-compression)
7. [Memory Summarization](#7-memory-summarization)
8. [Memory Deletion](#8-memory-deletion)
9. [Memory Versioning](#9-memory-versioning)
10. [Agent-Memory Interaction](#10-agent-memory-interaction)
11. [Database Design](#11-database-design)
12. [Retrieval Algorithms](#12-retrieval-algorithms)

---

## 1. Memory Architecture Overview

### 1.1 The Memory Moat

Memory is Pathfinder's **primary strategic moat**. After 6 months of use, the system knows a user's career narrative, preferences, failures, successes, and patterns better than any human mentor. This accumulated context cannot be replicated by a competitor — it is fundamentally non-portable at depth. Every architectural decision below serves this moat.

### 1.2 Seven Memory Types

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MEMORY TYPE TAXONOMY                                   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                      │    │
│  │  ┌──────────────────────┐    ┌──────────────────────┐               │    │
│  │  │                      │    │                      │               │    │
│  │  │   SHORT-TERM         │    │   LONG-TERM           │               │    │
│  │  │   MEMORY             │    │   MEMORY              │               │    │
│  │  │                      │    │                      │               │    │
│  │  │  Scope: Session      │    │  Scope: Persistent    │               │    │
│  │  │  TTL: 24 hours       │    │  TTL: Indefinite      │               │    │
│  │  │  Storage: Redis      │    │  Storage: PostgreSQL  │               │    │
│  │  │                      │    │                      │               │    │
│  │  │  Contains:           │    │  Contains:            │               │    │
│  │  │  · Current session   │    │  · Episodic memories  │               │    │
│  │  │    conversation      │    │  · Semantic memories  │               │    │
│  │  │  · In-flight agent   │    │  · Procedural memories│               │    │
│  │  │    state             │    │  · Preferences        │               │    │
│  │  │  · Pending approvals │    │  · Career history     │               │    │
│  │  │  · Recent context    │    │  · Consolidated       │               │    │
│  │  │    window            │    │    insights           │               │    │
│  │  └──────────┬───────────┘    └──────────┬───────────┘               │    │
│  │             │                           │                            │    │
│  │             │    ┌──────────────────────┼──────────────────────┐     │    │
│  │             │    │                      │                      │     │    │
│  │             └────┼──► EPISODIC     ◄────┼──────◄──────────────┘     │    │
│  │                  │    MEMORY            │                            │    │
│  │                  │                      │                            │    │
│  │                  │  What happened       │                            │    │
│  │                  │  · User interactions │                            │    │
│  │                  │  · Agent actions     │                            │    │
│  │                  │  · Application events│                            │    │
│  │                  │  · Feedback signals  │                            │    │
│  │                  │  · Interview outcomes│                            │    │
│  │                  │                      │                            │    │
│  │                  │  ────────────────────│                            │    │
│  │                  │  SEMANTIC MEMORY     │                            │    │
│  │                  │                      │                            │    │
│  │                  │  What it means       │                            │    │
│  │                  │  · User profile      │                            │    │
│  │                  │  · Skills ontology   │                            │    │
│  │                  │  · Career narrative  │                            │    │
│  │                  │  · Company knowledge │                            │    │
│  │                  │  · Market facts      │                            │    │
│  │                  │  · Learned facts     │                            │    │
│  │                  │  · Inferred traits   │                            │    │
│  │                  │                      │                            │    │
│  │                  │  ────────────────────│                            │    │
│  │                  │  PROCEDURAL MEMORY   │                            │    │
│  │                  │                      │                            │    │
│  │                  │  How to act          │                            │    │
│  │                  │  · Agent workflows   │                            │    │
│  │                  │  · Best strategies   │                            │    │
│  │                  │  · Tool effectiveness│                            │    │
│  │                  │  · Routing patterns  │                            │    │
│  │                  │  · User habits       │                            │    │
│  │                  │                      │                            │    │
│  │                  │  ────────────────────│                            │    │
│  │                  │  PREFERENCE MEMORY   │                            │    │
│  │                  │                      │                            │    │
│  │                  │  What user wants     │                            │    │
│  │                  │  · Explicit prefs    │                            │    │
│  │                  │  · Implicit prefs    │                            │    │
│  │                  │  · Weight vectors    │                            │    │
│  │                  │  · Dealbreakers      │                            │    │
│  │                  │  · Communication     │                            │    │
│  │                  │    style             │                            │    │
│  │                  │                      │                            │    │
│  │                  │  ────────────────────│                            │    │
│  │                  │  CAREER HISTORY      │                            │    │
│  │                  │                      │                            │    │
│  │                  │  The full story      │                            │    │
│  │                  │  · Work timeline     │                            │    │
│  │                  │  · Education path    │                            │    │
│  │                  │  · Skill evolution   │                            │    │
│  │                  │  · Compensation hist │                            │    │
│  │                  │  · Application hist  │                            │    │
│  │                  │  · Interview hist    │                            │    │
│  │                  │  · Career decisions  │                            │    │
│  │                  └──────────────────────┘                            │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Memory Tier Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MEMORY TIER ARCHITECTURE                              │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     TIER 0: HOT MEMORY                                │   │
│  │                     ────────────────                                   │   │
│  │  Storage:    Redis (in-memory)                                        │   │
│  │  Latency:    < 1ms                                                     │   │
│  │  Capacity:   Per-user: ~2MB (session + working context)                │   │
│  │  Contents:   Current session state, active context window,             │   │
│  │              pending approvals, in-flight agent state,                  │   │
│  │              hot cache of frequently accessed memories                 │   │
│  │  Eviction:   TTL-based (5min–24h depending on key)                     │   │
│  │  Persistence: AOF every 1 second + RDB snapshot every hour             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     TIER 1: WARM MEMORY                               │   │
│  │                     ────────────────                                   │   │
│  │  Storage:    PostgreSQL (indexed, optimized)                           │   │
│  │  Latency:    < 10ms (indexed queries), < 100ms (vector search)         │   │
│  │  Capacity:   Per-user: ~50MB (recent episodic + all semantic/pref)     │   │
│  │  Contents:   Last 90 days of episodic memories, all semantic,          │   │
│  │              all preferences, current career history,                  │   │
│  │              active procedural memories, embeddings                    │   │
│  │  Indexing:   B-tree (time, type), GIN (JSONB), HNSW (vectors)         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     TIER 2: COLD MEMORY                               │   │
│  │                     ────────────────                                   │   │
│  │  Storage:    PostgreSQL (partitioned, compressed) + S3/MinIO          │   │
│  │  Latency:    < 100ms (indexed), < 2s (full scan)                       │   │
│  │  Capacity:   Per-user: ~500MB (full historical archive)                │   │
│  │  Contents:   Episodic memories 90–730 days, old versions,              │   │
│  │              archived procedural patterns, full audit trail            │   │
│  │  Compression: TOAST + pg_column_compression for JSONB columns          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     TIER 3: ARCHIVE MEMORY                             │   │
│  │                     ──────────────────                                  │   │
│  │  Storage:    S3 Glacier (object storage)                               │   │
│  │  Latency:    Minutes to hours (restore required)                       │   │
│  │  Capacity:   Unlimited, per-user ~2GB over lifetime                    │   │
│  │  Contents:   Memories > 2 years, deleted user data (pre-purge),        │   │
│  │              raw episodic data that was consolidated                   │   │
│  │  Access:     Restore to Tier 1 on demand (user data export,            │   │
│  │              legal hold, compliance)                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Memory Types & Schemas

### 2.1 Short-Term Memory

**Purpose:** Hold the current session's working context — conversation history, in-flight agent state, pending decisions. Ephemeral by design.

**Storage:** Redis exclusively. Nothing in short-term memory is written to PostgreSQL until the session ends and consolidation runs.

```
┌─────────────────────────────────────────────────────────────────────┐
│ SHORT-TERM MEMORY SCHEMA (Redis)                                     │
│                                                                      │
│ Key Pattern: stm:{user_id}:{session_id}:{component}                  │
│                                                                      │
│ ┌────────────────────────────────────────────────────────────────┐  │
│ │ KEY                          │ TYPE   │ TTL    │ CONTENT        │  │
│ │ ────────────────────────────┼────────┼────────┼─────────────── │  │
│ │ stm:{uid}:{sid}:messages    │ LIST   │ 24h    │ Conversation    │  │
│ │                              │        │        │ turn objects    │  │
│ │ stm:{uid}:{sid}:context     │ HASH   │ 24h    │ Current context │  │
│ │                              │        │        │ window (profile,│  │
│ │                              │        │        │ prefs, jobs)    │  │
│ │ stm:{uid}:{sid}:agent_state │ STRING │ 24h    │ Serialized      │  │
│ │                              │        │        │ LangGraph state │  │
│ │ stm:{uid}:{sid}:pending     │ HASH   │ 24h    │ Pending HITL    │  │
│ │   _approval                 │        │        │ approvals       │  │
│ │ stm:{uid}:{sid}:tool_calls  │ LIST   │ 24h    │ Tool call log   │  │
│ │ stm:{uid}:{sid}:token_count │ STRING │ 24h    │ Running token   │  │
│ │                              │        │        │ counter         │  │
│ │ stm:{uid}:{sid}:plan_stack  │ LIST   │ 24h    │ Remaining plan  │  │
│ │                              │        │        │ steps (LIFO)    │  │
│ └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│ MESSAGE FORMAT (JSON, stored in Redis LIST):                         │
│ ┌────────────────────────────────────────────────────────────────┐  │
│ │ {                                                               │  │
│ │   "turn_id": "uuid-v7",                                        │  │
│ │   "role": "user" | "agent" | "system",                         │  │
│ │   "content": "text or structured block",                        │  │
│ │   "agent_invocations": ["ProfileAgent", "MatchingAgent"],       │  │
│ │   "artifacts": ["resume_diff", "job_card"],                     │  │
│ │   "tokens": {"in": 3500, "out": 1200},                         │  │
│ │   "timestamp": "2026-06-17T14:30:00Z",                          │  │
│ │   "latency_ms": 4200                                           │  │
│ │ }                                                               │  │
│ └────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Episodic Memory

**Purpose:** The raw log of everything that happened — user actions, agent decisions, system events, feedback signals. This is the **source of truth** from which all other memory types are derived. Immutable. Append-only.

**Storage:** PostgreSQL (hot: 90 days, cold: 2 years, archive: beyond). Partitioned by day.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ EPISODIC MEMORY SCHEMA (PostgreSQL)                                           │
│                                                                              │
│ TABLE: episodic_memories                                                      │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ COLUMN                  │ TYPE                │ DESCRIPTION              │  │
│ │ ───────────────────────┼────────────────────┼───────────────────────── │  │
│ │ id                      │ UUID (PK)          │ Unique episode ID         │  │
│ │ user_id                 │ UUID (FK, NOT NULL) │ Owning user              │  │
│ │ session_id              │ UUID (NOT NULL)    │ Session this belongs to   │  │
│ │ episode_type            │ EPISODE_TYPE (ENUM)│ Category (see below)      │  │
│ │ actor                   │ ACTOR_TYPE (ENUM)  │ Who caused this           │  │
│ │ action                  │ TEXT (NOT NULL)    │ Human-readable description │  │
│ │ payload                 │ JSONB (NOT NULL)   │ Full event data           │  │
│ │ importance_score        │ REAL [0.0-1.0]    │ Computed future relevance  │  │
│ │ emotion_signal          │ REAL [-1.0-1.0]   │ Negative↔positive sentiment│  │
│ │ embedding               │ VECTOR(1536)       │ Semantic embedding         │  │
│ │ context_summary         │ TEXT               │ 1-line LLM summary         │  │
│ │ parent_episode_id       │ UUID (FK, NULL)    │ Links to causing episode   │  │
│ │ consolidation_id        │ UUID (FK, NULL)    │ Which consolidation run    │  │
│ │ created_at              │ TIMESTAMPTZ (PK)   │ When it happened (server)  │  │
│ │ recorded_at             │ TIMESTAMPTZ        │ When we stored it          │  │
│ │ expires_at              │ TIMESTAMPTZ        │ Auto-delete after this     │  │
│ │                         │                    │                            │  │
│ │ PRIMARY KEY: (id, created_at)  -- composite for partitioning             │  │
│ │ PARTITION BY: RANGE (created_at) — daily partitions                      │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ EPISODE_TYPE ENUM:                                                            │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ VALUE                    │ DESCRIPTION                 │ EXAMPLE         │ │
│ │ ────────────────────────┼────────────────────────────┼──────────────── │ │
│ │ user_message             │ User sent text              │ "Find me remote │ │
│ │                          │                             │  Python jobs"   │ │
│ │ user_action              │ User clicked/performed      │ Saved job #42,  │ │
│ │                          │                             │  approved resume │ │
│ │ agent_invocation         │ Agent was called            │ ResumeAgent     │ │
│ │                          │                             │  tailored for   │ │
│ │                          │                             │  job #42        │ │
│ │ agent_result             │ Agent returned output       │ Generated       │ │
│ │                          │                             │  resume_v3.pdf  │ │
│ │ tool_execution           │ Tool was called             │ parse_resume()  │ │
│ │                          │                             │  returned 15    │ │
│ │                          │                             │  skills         │ │
│ │ system_event             │ Automated system action     │ Job sweep       │ │
│ │                          │                             │  completed, 234 │ │
│ │                          │                             │  new jobs found │ │
│ │ feedback_explicit        │ User gave explicit rating   │ Thumbs up on    │ │
│ │                          │                             │  match #42      │ │
│ │ feedback_implicit        │ Inferred from behavior      │ Dismissed 5     │ │
│ │                          │                             │  jobs in a row  │ │
│ │ application_event        │ Application status change   │ Moved to        │ │
│ │                          │                             │  "Interview"    │ │
│ │ interview_event          │ Interview-related           │ Phone screen    │ │
│ │                          │                             │  scheduled for  │ │
│ │                          │                             │  Thursday       │ │
│ │ preference_signal        │ Explicit/implicit pref      │ Clicked "growth"│ │
│ │                          │                             │  as priority    │ │
│ │ error_event              │ Something failed            │ LLM timeout on  │ │
│ │                          │                             │  cover letter   │ │
│ │ consolidation_event      │ Memory was consolidated     │ 6hr cycle: 45   │ │
│ │                          │                             │  episodes → 3   │ │
│ │                          │                             │  insights       │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ ACTOR_TYPE ENUM:                                                              │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ user | profile_agent | discovery_agent | matching_agent | resume_agent   │ │
│ │ cover_letter_agent | interview_agent | career_coach_agent |              │ │
│ │ application_tracking_agent | follow_up_agent | memory_agent |            │ │
│ │ supervisor_agent | system_scheduler | email_integration |                │ │
│ │ calendar_integration | admin                                              │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Semantic Memory

**Purpose:** Structured, factual knowledge about the user and the world they operate in. This is what the system *knows* — not what happened, but what it means. Continuously updated via consolidation. Used directly by agents for reasoning.

**Storage:** PostgreSQL with pgvector. Indefinite retention.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SEMANTIC MEMORY SCHEMA (PostgreSQL)                                           │
│                                                                              │
│ TABLE: semantic_memories                                                      │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ COLUMN                  │ TYPE                │ DESCRIPTION              │  │
│ │ ───────────────────────┼────────────────────┼───────────────────────── │  │
│ │ id                      │ UUID (PK)          │ Unique memory ID          │  │
│ │ user_id                 │ UUID (FK, NOT NULL) │ Owning user              │  │
│ │ memory_type             │ SEMANTIC_TYPE (ENUM)│ Category (see below)      │  │
│ │ subject                 │ TEXT (NOT NULL)    │ What this memory is about │  │
│ │ content                 │ JSONB (NOT NULL)   │ Structured memory body    │  │
│ │ content_text            │ TEXT               │ Searchable text version   │  │
│ │ embedding               │ VECTOR(3072)       │ Semantic embedding         │  │
│ │ confidence              │ REAL [0.0-1.0]    │ How certain we are         │  │
│ │ evidence_episodes        │ UUID[]             │ Source episode IDs         │  │
│ │ evidence_count          │ INTEGER            │ How many episodes support  │  │
│ │ importance_score        │ REAL [0.0-1.0]    │ Future relevance estimate   │  │
│ │ access_count            │ INTEGER            │ Times retrieved by agents   │  │
│ │ last_accessed_at        │ TIMESTAMPTZ        │ Last retrieval timestamp   │  │
│ │ last_updated_at         │ TIMESTAMPTZ        │ Last modification          │  │
│ │ consolidation_run_id    │ UUID (FK, NULL)    │ Which consolidation created│  │
│ │ version                 │ INTEGER            │ Revision number            │  │
│ │ is_active               │ BOOLEAN            │ Soft delete flag           │  │
│ │ created_at              │ TIMESTAMPTZ        │ When first created         │  │
│ │                         │                    │                            │  │
│ │ INDEX: idx_semantic_user_type (user_id, memory_type)                     │  │
│ │ INDEX: idx_semantic_embedding USING hnsw (embedding vector_cosine_ops)   │  │
│ │ INDEX: idx_semantic_importance (user_id, importance_score DESC)          │  │
│ │ INDEX: idx_semantic_text USING gin (to_tsvector('english', content_text))│  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ SEMANTIC_TYPE ENUM:                                                           │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ VALUE              │ DESCRIPTION                │ EXAMPLE                 │ │
│ │ ──────────────────┼───────────────────────────┼─────────────────────────│ │
│ │ profile_fact       │ Verified fact about user   │ "Works at Stripe since  │ │
│ │                    │                            │  2024 as Senior SWE"    │ │
│ │ skill_knowledge    │ Skill + proficiency        │ "Python: Expert (8y),   │ │
│ │                    │                            │  confirmed by 3 roles"  │ │
│ │ career_narrative   │ Long-form career story     │ 500-word narrative of   │ │
│ │                    │                            │  user's progression     │ │
│ │ company_knowledge  │ Information about company  │ "Stripe: payments infra,│ │
│ │                    │                            │  8000+ employees"       │ │
│ │ market_knowledge   │ Job market facts           │ "ML Engineers in SF:    │ │
│ │                    │                            │  $200K–$350K TC"        │ │
│ │ learned_insight    │ Pattern derived from data  │ "User performs better   │ │
│ │                    │                            │  in startup interviews" │ │
│ │ inferred_trait     │ Derived personality/behavior│ "Prefers async comms    │ │
│ │                    │                            │  over meetings"         │ │
│ │ role_requirement   │ Synthesized target role req│ "Staff SWE typically    │ │
│ │                    │                            │  needs: sys design,     │ │
│ │                    │                            │  mentorship, 8+ YOE"    │ │
│ │ learning_resource  │ Curated learning content   │ "Grokking Algorithms:   │ │
│ │                    │                            │  book, 4.5★, 8 weeks"   │ │
│ │ interview_knowledge│ Interview experience data  │ "Stripe onsite: 2 coding│ │
│ │                    │                            │  + 1 design + 1 behavioral"│
│ │ application_fact   │ Outcome of an application  │ "Applied to Meta 2025:  │ │
│ │                    │                            │  rejected after onsite" │ │
│ │ general_knowledge  │ Uncategorized fact         │ Fallback type           │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ JSONB CONTENT EXAMPLES:                                                       │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                           │ │
│ │ profile_fact:                                                             │ │
│ │ {                                                                         │ │
│ │   "subject_entity": "work_experience",                                    │ │
│ │   "company": "Stripe",                                                    │ │
│ │   "title": "Senior Software Engineer",                                    │ │
│ │   "start_date": "2024-03",                                                │ │
│ │   "end_date": null,                                                       │ │
│ │   "key_achievements": ["Led payment API redesign", "Mentored 4 engineers"],│ │
│ │   "tech_stack": ["Ruby", "Java", "AWS"],                                  │ │
│ │   "verified": true                                                        │ │
│ │ }                                                                         │ │
│ │                                                                           │ │
│ │ skill_knowledge:                                                          │ │
│ │ {                                                                         │ │
│ │   "skill_name": "Python",                                                 │ │
│ │   "proficiency": "expert",                                                │ │
│ │   "years_experience": 8,                                                  │ │
│ │   "last_used": "2026-06",                                                 │ │
│ │   "evidence": [                                                           │ │
│ │     {"source": "work_experience", "company": "Stripe", "years": 2},       │ │
│ │     {"source": "project", "name": "ml-pipeline", "url": "github.com/..."},│ │
│ │     {"source": "certification", "name": "Python Professional"}            │ │
│ │   ],                                                                      │ │
│ │   "sub_skills": ["FastAPI", "pandas", "pytest", "async/await"]            │ │
│ │ }                                                                         │ │
│ │                                                                           │ │
│ │ learned_insight:                                                          │ │
│ │ {                                                                         │ │
│ │   "insight": "User's callback rate is 3× higher for fintech companies",   │ │
│ │   "confidence": 0.82,                                                     │ │
│ │   "derived_from": "analysis of 47 applications over 6 months",            │ │
│ │   "actionable": true,                                                     │ │
│ │   "suggested_action": "Prioritize fintech roles in matching"              │ │
│ │ }                                                                         │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.4 Procedural Memory

**Purpose:** Knowledge about *how* to act — which agent workflows succeed, which tools work best in which contexts, how the user prefers the system to behave. This is the system's "muscle memory."

**Storage:** PostgreSQL. Continuously updated from agent execution traces.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PROCEDURAL MEMORY SCHEMA (PostgreSQL)                                         │
│                                                                              │
│ TABLE: procedural_memories                                                    │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ COLUMN                  │ TYPE                │ DESCRIPTION              │  │
│ │ ───────────────────────┼────────────────────┼───────────────────────── │  │
│ │ id                      │ UUID (PK)          │ Unique memory ID          │  │
│ │ user_id                 │ UUID (FK, NOT NULL) │ Owning user (NULL for     │  │
│ │                         │                    │  global patterns)         │  │
│ │ scope                   │ SCOPE_TYPE (ENUM)  │ user | role | global      │  │
│ │ pattern_type            │ PATTERN_TYPE (ENUM)│ What kind of pattern      │  │
│ │ context_signature       │ TEXT (NOT NULL)    │ When this pattern applies │  │
│ │ context_embedding       │ VECTOR(1536)       │ Embedding of the context  │  │
│ │ action_sequence         │ JSONB (NOT NULL)   │ What to do                │  │
│ │ expected_outcome        │ TEXT               │ What should happen         │  │
│ │ success_rate            │ REAL [0.0-1.0]    │ Historical effectiveness   │  │
│ │ execution_count         │ INTEGER            │ Times this pattern used    │  │
│ │ avg_latency_ms          │ INTEGER            │ Average execution time     │  │
│ │ avg_token_cost          │ INTEGER            │ Average token consumption  │  │
│ │ last_executed_at        │ TIMESTAMPTZ        │ Last use timestamp         │  │
│ │ is_active               │ BOOLEAN            │ Currently recommended      │  │
│ │ created_at              │ TIMESTAMPTZ        │ When discovered            │  │
│ │ updated_at              │ TIMESTAMPTZ        │ Last success rate update   │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ SCOPE_TYPE: user | role_type | global                                         │
│ PATTERN_TYPE:                                                                 │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ VALUE                    │ DESCRIPTION               │ EXAMPLE            │ │
│ │ ────────────────────────┼──────────────────────────┼─────────────────── │ │
│ │ agent_routing            │ Which agent to invoke     │ "intent=tailor +   │ │
│ │                          │                           │  job_type=startup  │ │
│ │                          │                           │  → use concise     │ │
│ │                          │                           │  template"         │ │
│ │ tool_selection           │ Which tool works best     │ "For company       │ │
│ │                          │                           │  research → use    │ │
│ │                          │                           │  Crunchbase API    │ │
│ │                          │                           │  first, then web   │ │
│ │                          │                           │  search"           │ │
│ │ prompt_strategy          │ Which prompt template     │ "User responds     │ │
│ │                          │                           │  better to 3-bullet│ │
│ │                          │                           │  summaries than    │ │
│ │                          │                           │  paragraphs"       │ │
│ │ communication_pattern    │ How to present to user    │ "Show diff before  │ │
│ │                          │                           │  download for this │ │
│ │                          │                           │  user"             │ │
│ │ follow_up_strategy       │ When/how to follow up     │ "This user checks  │ │
│ │                          │                           │  on Tuesdays —     │ │
│ │                          │                           │  send digest then" │ │
│ │ search_strategy          │ How to search most        │ "Prioritize HN and │ │
│ │                          │  effectively              │  YC jobs for this  │ │
│ │                          │                           │  user — highest    │ │
│ │                          │                           │  response rate"    │ │
│ │ error_recovery           │ What to do on failure     │ "If resume gen     │ │
│ │                          │                           │  fails twice →     │ │
│ │                          │                           │  offer manual      │ │
│ │                          │                           │  template"         │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.5 User Preference Memory

**Purpose:** What the user wants — both what they told us (explicit) and what their behavior reveals (implicit). This is a **continuously learning Bayesian model** that gets more accurate over time.

**Storage:** PostgreSQL (current weights) + Redis (hot for agent access). Versioned on every update.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ USER PREFERENCE SCHEMA (PostgreSQL)                                           │
│                                                                              │
│ TABLE: user_preferences                                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ COLUMN                  │ TYPE                │ DESCRIPTION              │  │
│ │ ───────────────────────┼────────────────────┼───────────────────────── │  │
│ │ id                      │ UUID (PK)          │ Unique version ID         │  │
│ │ user_id                 │ UUID (FK, NOT NULL) │ Owning user              │  │
│ │ version                 │ INTEGER            │ Monotonic revision number │  │
│ │ is_current              │ BOOLEAN            │ True for latest version   │  │
│ │ preference_data         │ JSONB (NOT NULL)   │ Full preference tree      │  │
│ │ source_breakdown        │ JSONB              │ explicit vs implicit %     │  │
│ │ confidence_scores       │ JSONB              │ Per-preference confidence │  │
│ │ evidence_episodes        │ UUID[]             │ Source episodes           │  │
│ │ change_summary          │ TEXT               │ What changed from prev    │  │
│ │ created_at              │ TIMESTAMPTZ        │ When this version created │  │
│ │                         │                    │                            │  │
│ │ INDEX: idx_prefs_current (user_id, is_current) WHERE is_current = true   │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ PREFERENCE_DATA JSONB STRUCTURE:                                              │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ {                                                                         │ │
│ │   "role_preferences": {                                                   │ │
│ │     "target_titles": ["Senior Software Engineer", "Staff Engineer"],       │ │
│ │     "title_weights": {"Senior Software Engineer": 0.6, ...},              │ │
│ │     "excluded_titles": ["Principal Engineer"]                             │ │
│ │   },                                                                      │ │
│ │   "compensation": {                                                       │ │
│ │     "minimum_base": 180000,                                               │ │
│ │     "target_total": 250000,                                               │ │
│ │     "currency": "USD",                                                    │ │
│ │     "equity_preference": "options_preferred",                             │ │
│ │     "salary_flexibility": 0.15   // willing to go 15% below target       │ │
│ │   },                                                                      │ │
│ │   "location": {                                                           │ │
│ │     "regions": ["San Francisco Bay Area", "Seattle", "Remote US"],        │ │
│ │     "remote_policy": "remote_first",                                      │ │
│ │     "relocation_willingness": "west_coast_only",                          │ │
│ │     "office_policy_weights": {"remote": 1.0, "hybrid": 0.6, "onsite": 0.0}││
│ │   },                                                                      │ │
│ │   "company_preferences": {                                                │ │
│ │     "size": {"min": 50, "max": 5000},                                    │ │
│ │     "stage": ["Series B", "Series C", "Public"],                          │ │
│ │     "industry_weights": {"fintech": 0.9, "devtools": 0.85, "adtech": 0.1},││
│ │     "dream_companies": ["Stripe", "Figma", "Vercel"],                     │ │
│ │     "excluded_companies": ["Meta", "Amazon"]                              │ │
│ │   },                                                                      │ │
│ │   "culture_priorities": {                                                 │ │
│ │     "engineering_driven": 0.9,                                            │ │
│ │     "work_life_balance": 0.7,                                             │ │
│ │     "mission_alignment": 0.5,                                             │ │
│ │     "fast_paced": 0.3                                                     │ │
│ │   },                                                                      │ │
│ │   "priority_weights": {           // ranked-choice derived                │ │
│ │     "compensation": 0.30,                                                 │ │
│ │     "growth_potential": 0.25,                                             │ │
│ │     "tech_stack": 0.20,                                                   │ │
│ │     "culture": 0.15,                                                      │ │
│ │     "location": 0.10                                                      │ │
│ │   },                                                                      │ │
│ │   "dealbreakers": [                                                       │ │
│ │     {"field": "requires_relocation_to", "value": ["New York"]},           │ │
│ │     {"field": "industry", "value": ["defense", "crypto"]}                 │ │
│ │   ],                                                                      │ │
│ │   "communication_style": {                                                │ │
│ │     "tone": "professional",                                               │ │
│ │     "verbosity": "concise",                                               │ │
│ │     "notification_frequency": "daily_digest",                             │ │
│ │     "preferred_contact_time": "08:00 PT"                                  │ │
│ │   },                                                                      │ │
│ │   "search_behavior": {                                                    │ │
│ │     "mode": "active",                                                     │ │
│ │     "auto_apply_threshold": 0.85,                                         │ │
│ │     "sweep_frequency": "daily",                                           │ │
│ │     "requires_approval_for": ["apply", "send_email"]                      │ │
│ │   }                                                                       │ │
│ │ }                                                                         │ │
│ │                                                                           │ │
│ │ SOURCE_BREAKDOWN:                                                         │ │
│ │ {                                                                         │ │
│ │   "compensation.minimum_base": {"explicit": 1.0, "implicit": 0.0},        │ │
│ │   "company_preferences.industry_weights": {"explicit": 0.4, "implicit": 0.6}││
│ │ }                                                                         │ │
│ │                                                                           │ │
│ │ CONFIDENCE_SCORES:                                                        │ │
│ │ {                                                                         │ │
│ │   "company_preferences.industry_weights.fintech": 0.95,  // 47 data points│ │
│ │   "company_preferences.industry_weights.devops": 0.45    // 3 data points │ │
│ │ }                                                                         │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.6 Career History Memory

**Purpose:** The complete, versioned, structured timeline of the user's professional life. This is an **append-only chronicle** — the biographical source of truth. Every job application, interview, offer, and career decision is recorded here.

**Storage:** PostgreSQL. Indefinite retention. This is the user's most valuable data.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CAREER HISTORY SCHEMA (PostgreSQL)                                            │
│                                                                              │
│ TABLE: career_timeline                                                        │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ COLUMN                  │ TYPE                │ DESCRIPTION              │  │
│ │ ───────────────────────┼────────────────────┼───────────────────────── │  │
│ │ id                      │ UUID (PK)          │ Unique entry ID           │  │
│ │ user_id                 │ UUID (FK, NOT NULL) │ Owning user              │  │
│ │ entry_type              │ CAREER_TYPE (ENUM) │ Category of event         │  │
│ │ title                   │ TEXT (NOT NULL)    │ Human-readable label      │  │
│ │ description             │ TEXT               │ Detailed description      │  │
│ │ structured_data         │ JSONB (NOT NULL)   │ Type-specific data        │  │
│ │ start_date              │ DATE               │ When this started         │  │
│ │ end_date                │ DATE               │ When this ended (null=now)│  │
│ │ is_current              │ BOOLEAN            │ True for active entries   │  │
│ │ importance              │ IMPORTANCE (ENUM)  │ major | minor | milestone │  │
│ │ source                  │ TEXT               │ How we learned this       │  │
│ │ verified                │ BOOLEAN            │ User-confirmed            │  │
│ │ embedding               │ VECTOR(3072)       │ For similarity queries    │  │
│ │ version                 │ INTEGER            │ Edit revision             │  │
│ │ created_at              │ TIMESTAMPTZ        │ First recorded            │  │
│ │ updated_at              │ TIMESTAMPTZ        │ Last modified             │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ CAREER_TYPE ENUM:                                                             │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ work_experience | education | certification | project | publication       │ │
│ │ patent | award | speaking_engagement | open_source_contribution           │ │
│ │ job_application | interview | job_offer | promotion | career_break        │ │
│ │ skill_acquired | skill_deprecated | career_decision | networking_event    │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ TABLE: compensation_history                                                   │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ COLUMN                  │ TYPE                │ DESCRIPTION              │  │
│ │ ───────────────────────┼────────────────────┼───────────────────────── │  │
│ │ id                      │ UUID (PK)          │                          │  │
│ │ user_id                 │ UUID (FK)          │                          │  │
│ │ career_entry_id         │ UUID (FK)          │ Links to work_experience  │  │
│ │ base_salary             │ NUMERIC(12,2)      │ Annual base               │  │
│ │ currency                │ CHAR(3)            │ ISO 4217                  │  │
│ │ bonus_target            │ NUMERIC(5,2)       │ Percentage                │  │
│ │ equity_grant            │ JSONB              │ {type, shares, strike,    │  │
│ │                         │                    │  vesting_schedule}        │  │
│ │ total_comp_estimated    │ NUMERIC(12,2)      │ Annualized estimate       │  │
│ │ benefits_summary        │ JSONB              │ {health, 401k, pto, ...}   │  │
│ │ offer_letter_url        │ TEXT               │ S3 link (encrypted)       │  │
│ │ effective_date          │ DATE               │ When comp took effect     │  │
│ │ created_at              │ TIMESTAMPTZ        │                          │  │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ TABLE: skill_evolution                                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ COLUMN                  │ TYPE                │ DESCRIPTION              │  │
│ │ ───────────────────────┼────────────────────┼───────────────────────── │  │
│ │ id                      │ UUID (PK)          │                          │  │
│ │ user_id                 │ UUID (FK)          │                          │  │
│ │ skill_name              │ TEXT (NOT NULL)    │ Canonical skill name      │  │
│ │ proficiency             │ PROFICIENCY (ENUM) │ beginner|intermediate|    │  │
│ │                         │                    │  advanced|expert          │  │
│ │ assessed_at             │ DATE               │ When this was measured    │  │
│ │ assessment_method       │ ASSESS_METHOD (ENUM)│ self_report|job_usage|   │  │
│ │                         │                    │  project|cert|inferred    │  │
│ │ evidence                │ JSONB              │ Supporting evidence       │  │
│ │ embedding               │ VECTOR(1536)       │ Skill embedding            │  │
│ │ created_at              │ TIMESTAMPTZ        │                          │  │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Memory Lifecycle

### 3.1 Full Lifecycle State Machine

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MEMORY LIFECYCLE FSM                                  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                      │    │
│  │  ┌──────────┐                                                        │    │
│  │  │  BIRTH   │                                                        │    │
│  │  │  (Event  │                                                        │    │
│  │  │  occurs) │                                                        │    │
│  │  └────┬─────┘                                                        │    │
│  │       │                                                              │    │
│  │       ▼                                                              │    │
│  │  ┌──────────┐     ┌──────────┐                                       │    │
│  │  │ CAPTURE  │────→│ FAILED   │──→ Dead letter queue (manual review)  │    │
│  │  │ (Write   │     │ CAPTURE  │                                       │    │
│  │  │ episode) │     └──────────┘                                       │    │
│  │  └────┬─────┘                                                        │    │
│  │       │                                                              │    │
│  │       ▼                                                              │    │
│  │  ┌──────────┐                                                        │    │
│  │  │  RAW     │  Episode stored in PostgreSQL. Immutable.              │    │
│  │  │ EPISODE  │  importance_score assigned (initial estimate).         │    │
│  │  │          │  embedding generated.                                  │    │
│  │  └────┬─────┘                                                        │    │
│  │       │                                                              │    │
│  │       │  ┌────────────────────────┐                                  │    │
│  │       ├──┤ IMPORTANCE > 0.8?      │── YES ──→ RUSH CONSOLIDATE       │    │
│  │       │  │ (e.g., offer received, │   (immediate)                    │    │
│  │       │  │  explicit preference)  │                                  │    │
│  │       │  └────────────────────────┘                                  │    │
│  │       │                                                              │    │
│  │       ▼ (normal path: waits for batch consolidation)                  │    │
│  │  ┌──────────┐                                                        │    │
│  │  │ QUEUED   │  Episode in consolidation queue.                       │    │
│  │  │ FOR      │  Batched with other episodes from same 6-hour window.  │    │
│  │  │ CONSOL   │                                                        │    │
│  │  └────┬─────┘                                                        │    │
│  │       │                                                              │    │
│  │       │  Every 6 hours (or on high-importance trigger):              │    │
│  │       ▼                                                              │    │
│  │  ┌──────────┐                                                        │    │
│  │  │CONSOLID- │  LLM processes batch of raw episodes:                  │    │
│  │  │ ATING    │  · Extracts patterns & insights                        │    │
│  │  │          │  · Updates semantic memories                           │    │
│  │  │          │  · Updates preference weights                          │    │
│  │  │          │  · Updates career narrative                            │    │
│  │  │          │  · Discovers procedural patterns                       │    │
│  │  │          │  · Recalculates importance scores                      │    │
│  │  └────┬─────┘                                                        │    │
│  │       │                                                              │    │
│  │       ▼                                                              │    │
│  │  ┌──────────┐                                                        │    │
│  │  │ ACTIVE   │  Memory is contributing to agent context.              │    │
│  │  │ MEMORY   │  Regularly retrieved. Access count incrementing.       │    │
│  │  │          │  importance_score updated based on retrieval patterns. │    │
│  │  └────┬─────┘                                                        │    │
│  │       │                                                              │    │
│  │       │  ┌──────────────────────────────┐                            │    │
│  │       ├──┤ access_count == 0 for 30d?   │── YES ──┐                 │    │
│  │       │  │ AND importance < 0.3?        │         │                 │    │
│  │       │  └──────────────────────────────┘         │                 │    │
│  │       │                                           ▼                 │    │
│  │       │  (no: stay active)              ┌──────────────┐            │    │
│  │       │                                 │   DORMANT    │            │    │
│  │       │                                 │   (Cold DB)  │            │    │
│  │       │                                 │              │            │    │
│  │       │                                 │ Moved to cold │            │    │
│  │       │                                 │ storage. Still│            │    │
│  │       │                                 │ retrievable  │            │    │
│  │       │                                 │ but slower.  │            │    │
│  │       │                                 └──────┬───────┘            │    │
│  │       │                                        │                    │    │
│  │       │   ┌────────────────────────────────────┼──────┐             │    │
│  │       │   │                                    │      │             │    │
│  │       │   ▼                                    ▼      ▼             │    │
│  │       │ ┌─────────┐                    ┌─────────┐ ┌─────────┐      │    │
│  │       │ │REACTIV- │                    │ EXPIRED │ │ DELETED │      │    │
│  │       │ │ ATED    │                    │ (past   │ │ (user   │      │    │
│  │       │ │         │                    │  TTL)   │ │ request)│      │    │
│  │       │ │ User or │                    │         │ │         │      │    │
│  │       │ │ agent   │                    │ Auto-   │ │ Hard    │      │    │
│  │       │ │ re-     │                    │ archived│ │ delete  │      │    │
│  │       │ │ accesses│                    │ to S3   │ │ after   │      │    │
│  │       │ │ dormant │                    │ Glacier │ │ 30-day  │      │    │
│  │       │ │ memory  │                    │         │ │ grace   │      │    │
│  │       │ └────┬────┘                    └─────────┘ └─────────┘      │    │
│  │       │      │                                                       │    │
│  │       │      └──→ Back to ACTIVE                                    │    │
│  │       │                                                              │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Lifecycle Timings

| Stage | Trigger | Timing | Notes |
|-------|---------|--------|-------|
| **Capture** | Any system or user event | Real-time (< 100ms) | Async write via Redis Stream → batch insert |
| **Initial importance scoring** | On capture | Real-time | Fast heuristic: offer received = 1.0, scroll = 0.1 |
| **Embedding generation** | On capture | Async, < 5s | Batched in groups of 50 for efficiency |
| **Consolidation (normal)** | Celery Beat cron | Every 6 hours | Processes last 6h of episodes per user |
| **Consolidation (rush)** | High-importance event | < 60 seconds | Only for importance ≥ 0.8 events |
| **Dormancy check** | Celery Beat cron | Daily at 03:00 UTC | Moves cold memories to cold storage |
| **Expiration** | Celery Beat cron | Daily at 04:00 UTC | Episodic > 730 days → S3 Glacier |
| **Hard delete** | User request or compliance | Within 30 days of request | Full purge from all tiers |

### 3.3 Consolidation Detail

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONSOLIDATION PROCESS (6-Hour Cycle)                     │
│                                                                              │
│  INPUT: Raw episodes from last 6 hours (typically 50–500 per active user)    │
│  MODEL: DeepSeek (cheaper model sufficient for consolidation)                │
│  COST: ~$0.002 per active user per cycle                                     │
│                                                                              │
│  STEP 1: GROUP & FILTER                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ · Group episodes by user_id                                           │   │
│  │ · Filter out noise: episodes with importance < 0.1, duplicates        │   │
│  │ · Sort by timestamp, group by type                                     │   │
│  │ · For each user: assemble batch context (profile summary + episodes)  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  STEP 2: PATTERN EXTRACTION (LLM)                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ · Extract preference signals from behavior                            │   │
│  │   "User said they want big companies but applied to 3 startups"       │   │
│  │ · Identify emerging patterns                                          │   │
│  │   "User keeps searching for Rust roles despite Python profile"        │   │
│  │ · Detect anomalies                                                    │   │
│  │   "User dismissed 5 high-match jobs in 2 minutes — fatigue?"          │   │
│  │ · Surface decisions                                                   │   │
│  │   "User accepted offer from Stripe — major career event"              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  STEP 3: MEMORY UPDATES                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ For each extracted pattern/insight:                                    │   │
│  │                                                                        │   │
│  │ a. SEMANTIC MEMORY UPDATE:                                             │   │
│  │    · UPSERT if similar memory exists (match on subject + user_id)      │   │
│  │    · Increment evidence_count                                          │   │
│  │    · Update confidence (more evidence → higher confidence)             │   │
│  │    · Add new evidence_episodes[]                                       │   │
│  │    · Bump version                                                      │   │
│  │    · Regenerate embedding if content changed significantly             │   │
│  │                                                                        │   │
│  │ b. PREFERENCE UPDATE:                                                  │   │
│  │    · Bayesian update of preference weights                             │   │
│  │    · weight_new = (weight_old × n_old + signal × signal_strength)      │   │
│  │                    / (n_old + signal_strength)                         │   │
│  │    · Update confidence: confidence += 0.02 per supporting episode      │   │
│  │    · Create new preference version if any weight changed > 5%          │   │
│  │                                                                        │   │
│  │ c. PROCEDURAL MEMORY UPDATE:                                           │   │
│  │    · If agent workflow succeeded → increment success_rate              │   │
│  │    · If agent workflow failed → decrement, add failure signature       │   │
│  │    · If new pattern discovered → INSERT new procedural memory          │   │
│  │                                                                        │   │
│  │ d. CAREER HISTORY UPDATE:                                              │   │
│  │    · Job applications → INSERT career_timeline entries                 │   │
│  │    · Interview outcomes → INSERT/UPDATE                                │   │
│  │    · Offers → INSERT with importance=major                             │   │
│  │    · Skill changes → INSERT skill_evolution                            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  STEP 4: NARRATIVE UPDATE                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ · LLM generates incremental update to career_narrative                 │   │
│  │ · "Since last update: applied to 12 roles, interviewed at 3 companies, │   │
│  │    received 1 offer. Python skills confirmed at Expert level through   │   │
│  │    technical interviews. Preference signal: fintech companies are      │   │
│  │    responding at 3× the rate of big tech."                             │   │
│  │ · Narrative append, not replace (version history maintained)           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  STEP 5: CLEANUP                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ · Mark source episodes as consolidated (consolidation_id = this run)  │   │
│  │ · Update user memory_stats: total_episodes, last_consolidation_at      │   │
│  │ · Emit memory.consolidated event                                       │   │
│  │ · Log consolidation metrics: episodes_processed, insights_generated,   │   │
│  │   preferences_updated, duration_ms, tokens_used                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Memory Retrieval

### 4.1 Retrieval Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MEMORY RETRIEVAL FLOW                                 │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  CALLER: Supervisor Agent (building context for specialized agent)    │   │
│  │  INPUT:  user_id, intent, current_query_embedding                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    RETRIEVAL ORCHESTRATOR                              │   │
│  │                                                                       │   │
│  │  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐     │   │
│  │  │ ROUTE 1:        │   │ ROUTE 2:        │   │ ROUTE 3:        │     │   │
│  │  │ FULL PROFILE    │   │ RELEVANT        │   │ PROCEDURAL      │     │   │
│  │  │ LOAD            │   │ MEMORIES        │   │ PATTERNS        │     │   │
│  │  │                 │   │                 │   │                 │     │   │
│  │  │ Always loaded:  │   │ Vector search:  │   │ Pattern match:  │     │   │
│  │  │ · User profile  │   │ · Episodic      │   │ · Context       │     │   │
│  │  │ · Preferences   │   │   (recent)      │   │   signature     │     │   │
│  │  │ · Career summary│   │ · Semantic      │   │   match         │     │   │
│  │  │ · Active apps   │   │   (facts)       │   │ · Best workflow │     │   │
│  │  │                 │   │                 │   │   for intent    │     │   │
│  │  │ Latency: <10ms  │   │ Latency: <50ms  │   │ Latency: <30ms  │     │   │
│  │  └────────┬────────┘   └────────┬────────┘   └────────┬────────┘     │   │
│  │           │                     │                     │               │   │
│  │           └─────────────────────┼─────────────────────┘               │   │
│  │                                 │                                     │   │
│  │                                 ▼                                     │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │   │
│  │  │                    CONTEXT ASSEMBLER                               │ │   │
│  │  │                                                                   │ │   │
│  │  │  1. Deduplicate: remove redundant info across memory types        │ │   │
│  │  │  2. Rank: sort by relevance × importance (see §5)                 │ │   │
│  │  │  3. Truncate: fit within token budget (8K tokens for context)     │ │   │
│  │  │  4. Format: structured context package for agent consumption      │ │   │
│  │  │  5. Log: record retrieval_stats for future optimization           │ │   │
│  │  └──────────────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  OUTPUT: ContextPackage                                                │   │
│  │  {                                                                    │   │
│  │    "profile": {...},                  // always included              │   │
│  │    "preferences": {...},              // always included              │   │
│  │    "career_summary": "...",           // always included              │   │
│  │    "recent_episodes": [...],          // last 20 interactions         │   │
│  │    "relevant_semantic": [...],        // top 10 vector matches        │   │
│  │    "relevant_procedural": [...],      // top 3 matching patterns      │   │
│  │    "active_applications": [...],      // current pipeline             │   │
│  │    "retrieval_metadata": {            // for logging/debugging        │   │
│  │      "total_tokens": 7200,                                            │   │
│  │      "budget_remaining": 800,                                         │   │
│  │      "routes_used": ["full_profile", "vector_semantic"],              │   │
│  │      "latency_ms": 87                                                 │   │
│  │    }                                                                  │   │
│  │  }                                                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Retrieval Routes Detail

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RETRIEVAL ROUTES                                      │
│                                                                              │
│  ROUTE A: DIRECT KEY LOOKUP (Latency: < 5ms)                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Use: When caller knows exactly what they need                        │   │
│  │  Query:                                                               │   │
│  │    SELECT * FROM semantic_memories                                    │   │
│  │    WHERE user_id = $1 AND memory_type = 'profile_fact'                │   │
│  │    AND is_active = true;                                              │   │
│  │  Index: idx_semantic_user_type (covers this perfectly)                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ROUTE B: VECTOR SIMILARITY SEARCH (Latency: < 50ms for top-20)              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Use: Find memories semantically related to current context           │   │
│  │  Query (semantic):                                                    │   │
│  │    SELECT id, memory_type, subject, content_text,                     │   │
│  │           1 - (embedding <=> $query_vector) AS similarity             │   │
│  │    FROM semantic_memories                                             │   │
│  │    WHERE user_id = $1                                                 │   │
│  │      AND is_active = true                                             │   │
│  │      AND importance_score > 0.2                                       │   │
│  │    ORDER BY embedding <=> $query_vector                               │   │
│  │    LIMIT 10;                                                          │   │
│  │                                                                       │   │
│  │  Query (episodic):                                                    │   │
│  │    SELECT id, episode_type, action, payload, context_summary,         │   │
│  │           1 - (embedding <=> $query_vector) AS similarity             │   │
│  │    FROM episodic_memories                                             │   │
│  │    WHERE user_id = $1                                                 │   │
│  │      AND created_at > NOW() - INTERVAL '90 days'                      │   │
│  │    ORDER BY embedding <=> $query_vector                               │   │
│  │    LIMIT 20;                                                          │   │
│  │                                                                       │   │
│  │  Index: HNSW on embedding column (ef_search=100 at query time)        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ROUTE C: HYBRID SEARCH (Vector + Keyword) (Latency: < 80ms)                 │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Use: When both semantic meaning and exact keyword matching matter    │   │
│  │  Query:                                                               │   │
│  │    WITH semantic_hits AS (                                            │   │
│  │      SELECT id, 1 - (embedding <=> $query_vector) AS score            │   │
│  │      FROM semantic_memories WHERE user_id = $1 AND is_active = true   │   │
│  │      ORDER BY embedding <=> $query_vector LIMIT 50                    │   │
│  │    ),                                                                 │   │
│  │    keyword_hits AS (                                                  │   │
│  │      SELECT id, ts_rank(to_tsvector('english', content_text),         │   │
│  │             plainto_tsquery('english', $keyword_query)) AS score      │   │
│  │      FROM semantic_memories WHERE user_id = $1 AND is_active = true   │   │
│  │      AND to_tsvector('english', content_text) @@                       │   │
│  │          plainto_tsquery('english', $keyword_query)                    │   │
│  │      LIMIT 50                                                        │   │
│  │    )                                                                  │   │
│  │    SELECT m.*,                                                        │   │
│  │           COALESCE(s.score, 0) * 0.7 + COALESCE(k.score, 0) * 0.3    │   │
│  │           AS hybrid_score                                             │   │
│  │    FROM semantic_memories m                                           │   │
│  │    LEFT JOIN semantic_hits s ON m.id = s.id                           │   │
│  │    LEFT JOIN keyword_hits k ON m.id = k.id                            │   │
│  │    WHERE s.id IS NOT NULL OR k.id IS NOT NULL                         │   │
│  │    ORDER BY hybrid_score DESC                                         │   │
│  │    LIMIT 10;                                                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ROUTE D: RECENCY-WEIGHTED RETRIEVAL (Latency: < 30ms)                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Use: Get recent history with optional type filter                    │   │
│  │  Query:                                                               │   │
│  │    SELECT * FROM episodic_memories                                    │   │
│  │    WHERE user_id = $1                                                 │   │
│  │      AND created_at > NOW() - INTERVAL '7 days'                       │   │
│  │      AND episode_type = ANY($2)  -- optional filter                   │   │
│  │    ORDER BY created_at DESC                                           │   │
│  │    LIMIT 50;                                                          │   │
│  │                                                                       │   │
│  │  Index: (user_id, created_at DESC) — lightning fast                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ROUTE E: PROCEDURAL PATTERN MATCH (Latency: < 30ms)                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Use: Find best workflow for current intent + context                 │   │
│  │  Query:                                                               │   │
│  │    SELECT * FROM procedural_memories                                  │   │
│  │    WHERE (user_id = $1 OR scope = 'role_type' OR scope = 'global')   │   │
│  │      AND is_active = true                                             │   │
│  │      AND success_rate > 0.6                                           │   │
│  │    ORDER BY                                                           │   │
│  │      CASE scope                                                       │   │
│  │        WHEN 'user' THEN 0                                             │   │
│  │        WHEN 'role_type' THEN 1                                        │   │
│  │        WHEN 'global' THEN 2                                           │   │
│  │      END,                                                             │   │
│  │      success_rate DESC                                                │   │
│  │    LIMIT 5;                                                           │   │
│  │                                                                       │   │
│  │  Then re-rank by context_embedding cosine similarity to current query │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Memory Ranking

### 5.1 Ranking Formula

Memories are ranked by a composite score. The formula balances relevance (how well it matches the current query), importance (how valuable this memory is long-term), recency (fresher is usually more relevant), and access frequency (frequently used memories are probably useful).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MEMORY RANKING FORMULA                              │
│                                                                              │
│  SCORE = α · RELEVANCE + β · IMPORTANCE + γ · RECENCY + δ · ACCESS_FREQ     │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ COMPONENT      │ WEIGHT  │ COMPUTATION                                │   │
│  │ ──────────────┼─────────┼─────────────────────────────────────────── │   │
│  │ RELEVANCE      │ α = 0.40│ cosine_similarity(query_embedding,         │   │
│  │                │         │   memory_embedding)                         │   │
│  │                │         │ OR hybrid score from Route C                │   │
│  │                │         │ OR 0.0 for non-vector routes                │   │
│  │                │         │                                             │   │
│  │ IMPORTANCE     │ β = 0.30│ importance_score (from memory table)        │   │
│  │                │         │ · Explicit: offer_received = 1.00           │   │
│  │                │         │ · Explicit: page_scroll = 0.05              │   │
│  │                │         │ · Learned: boosted by consolidation         │   │
│  │                │         │   if memory contributed to insights         │   │
│  │                │         │                                             │   │
│  │ RECENCY        │ γ = 0.20│ exp(-λ · days_since_creation)              │   │
│  │                │         │ λ = 0.05 (half-life ≈ 14 days)              │   │
│  │                │         │ Higher λ for episodic (0.10, half-life ~7d) │   │
│  │                │         │ Lower λ for semantic (0.01, half-life ~69d) │   │
│  │                │         │                                             │   │
│  │ ACCESS_FREQ    │ δ = 0.10│ min(access_count / 100, 1.0)               │   │
│  │                │         │ Capped at 100 accesses (diminishing returns)│   │
│  │                │         │ Recent accesses weighted more heavily       │   │
│  │                │         │ (recency-weighted access count)             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DYNAMIC WEIGHT ADJUSTMENT:                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ · For interview prep intent: α = 0.50, β = 0.20 (relevance matters    │   │
│  │   more than long-term importance)                                      │   │
│  │ · For career coaching: β = 0.40, γ = 0.10 (importance over recency)   │   │
│  │ · For real-time matching: α = 0.55, γ = 0.25 (relevance + freshness)  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Importance Scoring Heuristic

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      IMPORTANCE SCORE ASSIGNMENT                              │
│                                                                              │
│  ON CAPTURE (initial heuristic, fast):                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ EVENT TYPE                    │ INITIAL IMPORTANCE │ RATIONALE       │   │
│  │ ─────────────────────────────┼───────────────────┼────────────────  │   │
│  │ offer_received                │ 1.00               │ Career-defining │   │
│  │ offer_accepted                │ 1.00               │ Career-defining │   │
│  │ explicit_preference_stated    │ 0.90               │ Direct signal   │   │
│  │ interview_scheduled           │ 0.80               │ Major milestone │   │
│  │ interview_completed           │ 0.75               │ Valuable signal │   │
│  │ application_submitted         │ 0.60               │ Important event │   │
│  │ resume_tailored               │ 0.50               │ Effort signal   │   │
│  │ job_saved                    │ 0.40               │ Interest signal │   │
│  │ feedback_explicit (rating)   │ 0.70               │ Direct feedback │   │
│  │ feedback_implicit (dismiss)  │ 0.30               │ Weak signal     │   │
│  │ job_viewed                   │ 0.15               │ Browsing        │   │
│  │ page_scroll                  │ 0.05               │ Noise           │   │
│  │ error_event                  │ 0.20               │ Debug value     │   │
│  │ system_event (job sweep)     │ 0.10               │ Operational     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  POST-CONSOLIDATION (refined by LLM):                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ · Memory that contributed to an insight → +0.15 boost                 │   │
│  │ · Memory that contradicted a previous belief → +0.20 (learning)       │   │
│  │ · Memory that is the sole evidence for a fact → +0.10 (unique)        │   │
│  │ · Memory that duplicates others → -0.10 (redundancy penalty)          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  DECAY OVER TIME:                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ · Episodic memories: importance decays by 0.01 per month              │   │
│  │   (an interview from 2 years ago is less important than one yesterday)│   │
│  │ · Semantic memories: importance is stable (facts don't decay)         │   │
│  │ · Preferences: importance of implicit signals decays slower           │   │
│  │   (recent behavior > old behavior, but old patterns still matter)     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Memory Compression

### 6.1 Compression Strategies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MEMORY COMPRESSION                                   │
│                                                                              │
│  STRATEGY 1: EPISODIC → SEMANTIC EXTRACTION (Lossy, High Ratio)              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Input:  50 raw episodes about user's job search behavior            │   │
│  │  Output: 3 semantic memories + 2 preference updates                  │   │
│  │  Ratio:  ~15:1 compression                                            │   │
│  │                                                                       │   │
│  │  Example:                                                             │   │
│  │  INPUT (50 episodes):                                                 │   │
│  │   · Viewed 12 fintech jobs                                            │   │
│  │   · Saved 5 fintech jobs                                              │   │
│  │   · Applied to 3 fintech jobs                                         │   │
│  │   · Dismissed 15 big-tech jobs                                        │   │
│  │   · Viewed and dismissed 10 adtech jobs                               │   │
│  │                                                                       │   │
│  │  OUTPUT (compressed):                                                 │   │
│  │   · Semantic: "User strongly prefers fintech (3.7× apply rate vs      │   │
│  │     other industries)" confidence: 0.85                                │   │
│  │   · Preference update: fintech_weight 0.4 → 0.7                       │   │
│  │   · Preference update: big_tech_weight 0.5 → 0.3                      │   │
│  │   · Procedural: "For this user, filter out adtech entirely"           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  STRATEGY 2: EMBEDDING COMPRESSION (Lossy, Configurable)                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  · Episodic memories: 3072d → 1536d (reduce dimensionality for        │   │
│  │    older memories where approximate retrieval is sufficient)          │   │
│  │  · Embedding quantization: float32 → int8 (4× compression,            │   │
│  │    < 1% recall loss for memories > 90 days)                           │   │
│  │  · Trigger: When memory moves from Tier 1 (warm) to Tier 2 (cold)     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  STRATEGY 3: PAYLOAD SUMMARIZATION (Lossy, Moderate Ratio)                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  · Episodic payload JSONB → summarized context_summary (TEXT)         │   │
│  │  · Original payload moved to S3, summary kept in PostgreSQL           │   │
│  │  · Trigger: Episodic memories older than 90 days                      │   │
│  │  · Ratio: ~8:1 (500B JSONB → 60B summary)                            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  STRATEGY 4: DEDUPLICATION MERGE (Near-Lossless, Low Ratio)                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  · Identical or near-identical episodic memories merged               │   │
│  │  · Example: 5 "user viewed job #42" episodes → 1 episode with         │   │
│  │    view_count=5 and first_viewed_at + last_viewed_at                  │   │
│  │  · Detection: Same (user_id, episode_type, target_id) within 24h      │   │
│  │  · Trigger: During consolidation                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  STRATEGY 5: TOAST + COLUMN COMPRESSION (Lossless, Low Ratio)                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  · PostgreSQL TOAST: automatic compression for large TEXT/JSONB       │   │
│  │  · pg_column_compression (PG16+): LZ4 compression on JSONB columns    │   │
│  │  · Ratio: ~2.5:1 for typical JSONB payloads                          │   │
│  │  · Applied at storage engine level, transparent to application        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Memory Summarization

### 7.1 Summarization Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MEMORY SUMMARIZATION                                   │
│                                                                              │
│  LEVEL 1: EPISODE SUMMARIZATION (On Capture)                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  When: Every episodic memory on creation                              │   │
│  │  Model: DeepSeek (cheap/fast model)                                   │   │
│  │  Input: Full episode payload (JSONB)                                  │   │
│  │  Output: context_summary (one sentence, max 100 chars)                │   │
│  │                                                                       │   │
│  │  Examples:                                                            │   │
│  │  "Applied to Senior SWE at Stripe with tailored resume v3"            │   │
│  │  "Dismissed 5 fintech jobs with match scores above 85%"               │   │
│  │  "Completed technical phone screen at Notion — felt confident"        │   │
│  │  "Explicitly stated preference for remote-only roles"                 │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  LEVEL 2: WINDOW SUMMARIZATION (On Consolidation, Every 6 Hours)             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  When: During consolidation cycle                                     │   │
│  │  Model: DeepSeek (reasoning model)                                    │   │
│  │  Input: Last 6 hours of context_summaries + extracted patterns        │   │
│  │  Output: Window summary (3–5 sentences)                               │   │
│  │                                                                       │   │
│  │  Example:                                                             │   │
│  │  "In the last 6 hours, David was highly active: viewed 42 jobs,       │   │
│  │   saved 8, applied to 4 using tailored resumes. Strong fintech        │   │
│  │   preference confirmed (all 4 applications were fintech). Two new     │   │
│  │   dealbreakers detected: defense and crypto industries. Interview      │   │
│  │   scheduled at Ramp for Thursday. Overall sentiment: motivated."      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  LEVEL 3: CAREER NARRATIVE (On Consolidation, Incremental)                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  When: During consolidation, if significant events occurred           │   │
│  │  Model: DeepSeek (best reasoning model)                                │   │
│  │  Input: Current career narrative + new window summary                 │   │
│  │  Output: Updated career narrative (~500 words)                        │   │
│  │                                                                       │   │
│  │  Structure:                                                           │   │
│  │  · Current status (role, company, compensation)                       │   │
│  │  · Recent activity (last 30 days of job search)                       │   │
│  │  · Key insights (preferences, patterns, strengths)                    │   │
│  │  · Active goals (what user is working toward)                         │   │
│  │  · Market context (how user compares to market)                       │   │
│  │  · Next milestones (upcoming interviews, deadlines)                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  LEVEL 4: AGENT-SPECIFIC SUMMARIZATION (On Retrieval, On-Demand)             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  When: When an agent needs context about a specific topic              │   │
│  │  Model: DeepSeek (reasoning model)                                    │   │
│  │  Input: All episodic + semantic memories matching a topic filter      │   │
│  │  Output: Topic summary                                               │   │
│  │                                                                       │   │
│  │  Example (ResumeAgent requests "interview history at Stripe"):        │   │
│  │  "David interviewed at Stripe twice: once in 2024 (rejected at        │   │
│  │   onsite — feedback cited system design weakness) and again in 2026   │   │
│  │   (phone screen passed, onsite scheduled). Since 2024, he completed   │   │
│  │   Grokking the System Design Interview and led a major architecture    │   │
│  │   project at his current company. He's better prepared this time."    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Memory Deletion

### 8.1 Deletion Policies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MEMORY DELETION MATRIX                               │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ DELETION TYPE    │ TRIGGER            │ TIMING    │ SCOPE             │   │
│  │ ────────────────┼───────────────────┼──────────┼──────────────────  │   │
│  │ TTL Expiry       │ Automatic (cron)   │ Daily     │ Episodic > 730d  │   │
│  │ User Hard Delete │ User request       │ Within    │ All memory types │   │
│  │                  │ (Settings → Delete │ 30 days   │ for that user    │   │
│  │                  │  My Data)          │           │                  │   │
│  │ User Soft Delete │ Account deactiv-   │ Immediate │ Episodic purged, │   │
│  │                  │ ation              │           │ semantic kept    │   │
│  │                  │                    │           │ (recoverable)    │   │
│  │ Selective Delete │ "Forget this       │ Immediate │ Single memory    │   │
│  │                  │  interaction"      │           │ entry + derived  │   │
│  │ GDPR/CCPA        │ Legal request      │ 30 days   │ All user data    │   │
│  │ Compliance       │                    │           │                  │   │
│  │ Admin Purge      │ Court order,       │ As needed │ Specific scope   │   │
│  │                  │ security incident  │           │                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  HARD DELETE CASCADE:                                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  When a memory is hard-deleted:                                       │   │
│  │                                                                       │   │
│  │  1. Mark memory as is_active = false (immediate, reversible for 30d)  │   │
│  │  2. Remove from all vector indices (immediate)                        │   │
│  │  3. If semantic memory:                                               │   │
│  │     a. Check if it's the only evidence for any derived memory         │   │
│  │     b. If yes → mark derived memory confidence as "degraded"          │   │
│  │     c. If other evidence exists → remove this evidence link           │   │
│  │  4. If episodic memory:                                               │   │
│  │     a. Check for derived semantic memories that used this as evidence  │   │
│  │     b. Decrement evidence_count on those semantic memories            │   │
│  │     c. If evidence_count reaches 0 and no other source → flag         │   │
│  │  5. After 30-day grace period:                                        │   │
│  │     a. Physically DELETE FROM episodic_memories                       │   │
│  │     b. Remove from S3/MinIO if payload was archived                   │   │
│  │     c. Log deletion audit record (what was deleted, when, why)        │   │
│  │     d. Confirm deletion in deletion_log table                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Memory Versioning

### 9.1 Versioning Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MEMORY VERSIONING                                     │
│                                                                              │
│  ENTITIES VERSIONED:                                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ · Semantic memories (every content update)                            │   │
│  │ · User preferences (every weight change > 5%)                         │   │
│  │ · Career timeline entries (every edit)                                │   │
│  │ · Career narrative (every consolidation update)                       │   │
│  │ · Skill proficiency (every reassessment)                              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ENTITIES NOT VERSIONED (immutable or append-only):                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ · Episodic memories (immutable — never updated, only appended)        │   │
│  │ · Procedural memories (success_rate and execution_count updated       │   │
│  │   in-place — these are statistics, not content)                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  VERSIONING MECHANISM:                                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  Table: semantic_memory_versions                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │ COLUMN              │ TYPE          │ DESCRIPTION            │     │   │
│  │  │ ───────────────────┼──────────────┼─────────────────────── │     │   │
│  │  │ id                  │ UUID (PK)     │ Version ID             │     │   │
│  │  │ memory_id           │ UUID (FK)     │ Parent semantic memory │     │   │
│  │  │ version             │ INTEGER       │ Monotonic counter      │     │   │
│  │  │ content             │ JSONB         │ Full snapshot          │     │   │
│  │  │ content_text        │ TEXT          │ Snapshot text          │     │   │
│  │  │ embedding           │ VECTOR(3072)  │ Snapshot embedding     │     │   │
│  │  │ change_description  │ TEXT          │ What changed + why     │     │   │
│  │  │ consolidation_run_id│ UUID          │ Which run created this │     │   │
│  │  │ created_by          │ ACTOR_TYPE    │ user | agent | system  │     │   │
│  │  │ created_at          │ TIMESTAMPTZ   │ When created           │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                       │   │
│  │  The main semantic_memories table always has the LATEST version.      │   │
│  │  Historical versions are in semantic_memory_versions.                  │   │
│  │                                                                       │   │
│  │  SEMANTIC UPDATE = INSERT INTO semantic_memory_versions               │   │
│  │                     + UPDATE semantic_memories SET content = $new     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  PREFERENCE VERSIONING:                                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ · Every preference update creates a new row in user_preferences       │   │
│  │ · Previous version: is_current = false                                │   │
│  │ · New version: is_current = true, version = prev.version + 1          │   │
│  │ · change_summary = "fintech_weight: 0.4→0.7 (evidence: 12 fintech     │   │
│  │   applications vs 2 big-tech in last 30 days)"                        │   │
│  │ · Previous versions retained indefinitely for audit + rollback        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Agent-Memory Interaction

### 10.1 Agent Memory Access Patterns

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     AGENT-MEMORY INTERACTION MAP                              │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  AGENT              │ READS FROM              │ WRITES TO             │   │
│  │  ──────────────────┼────────────────────────┼────────────────────── │   │
│  │  SupervisorAgent    │· STM (session state)   │· Episodic (invocation │   │
│  │                     │· Semantic (profile,    │  logs)                 │   │
│  │                     │  preferences)          │· STM (state updates)   │   │
│  │                     │· Procedural (routing)  │                         │   │
│  │                     │                        │                         │   │
│  │  ProfileAgent       │· Career history        │· Semantic (profile     │   │
│  │                     │  (existing profile)    │  facts, skills)         │   │
│  │                     │· Semantic (company     │· Career timeline       │   │
│  │                     │  knowledge)            │· Episodic (parse log)  │   │
│  │                     │                        │                         │   │
│  │  JobDiscoveryAgent  │· Procedural (scraping  │· Episodic (sweep log)  │   │
│  │                     │  patterns)             │· Semantic (company     │   │
│  │                     │· Semantic (market      │  knowledge, market)    │   │
│  │                     │  knowledge)            │                         │   │
│  │                     │                        │                         │   │
│  │  JobMatchingAgent   │· Semantic (profile,    │· Episodic (match log)  │   │
│  │                     │  skills, preferences)  │· Procedural (scoring   │   │
│  │                     │· Career history        │  weights update)       │   │
│  │                     │  (application history) │                         │   │
│  │                     │· Procedural (scoring   │                         │   │
│  │                     │  weights)              │                         │   │
│  │                     │                        │                         │   │
│  │  ResumeAgent        │· Semantic (profile,    │· Episodic (gen log)    │   │
│  │                     │  skills, career facts) │                         │   │
│  │                     │· Career history        │                         │   │
│  │                     │                        │                         │   │
│  │  CoverLetterAgent   │· Semantic (profile,    │· Episodic (gen log)    │   │
│  │                     │  career narrative)     │                         │   │
│  │                     │· Career history        │                         │   │
│  │                     │                        │                         │   │
│  │  InterviewAgent     │· Career history        │· Episodic (prep log,   │   │
│  │                     │  (interview history)   │  interview outcomes)    │   │
│  │                     │· Semantic (interview   │· Career timeline       │   │
│  │                     │  knowledge, company    │  (interview events)    │   │
│  │                     │  knowledge)            │                         │   │
│  │                     │                        │                         │   │
│  │  CareerCoachAgent   │· Semantic (skills,     │· Episodic (coaching    │   │
│  │                     │  career narrative)     │  log)                   │   │
│  │                     │· Career history (full) │· Semantic (skill       │   │
│  │                     │· Procedural (learning  │  knowledge, role       │   │
│  │                     │  patterns)             │  requirements)         │   │
│  │                     │                        │· Career timeline       │   │
│  │                     │                        │  (learning events)     │   │
│  │                     │                        │                         │   │
│  │  ApplicationTrackAgt│· Career history        │· Episodic (status      │   │
│  │                     │  (applications)        │  change log)            │   │
│  │                     │· Episodic (recent      │· Career timeline       │   │
│  │                     │  application events)   │  (application events)  │   │
│  │                     │                        │                         │   │
│  │  FollowUpAgent      │· Career history        │· Episodic (comm log)   │   │
│  │                     │  (application context) │                         │   │
│  │                     │· Episodic (comm hist)  │                         │   │
│  │                     │· Semantic (preferences │                         │   │
│  │                     │  for comm style)       │                         │   │
│  │                     │                        │                         │   │
│  │  MemoryAgent        │· ALL memory types      │· ALL memory types      │   │
│  │  (itself)           │  (it owns them)        │  (it owns them)        │   │
│  │                     │                        │                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  KEY PRINCIPLES:                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 1. All writes go through MemoryAgent (direct DB writes from other     │   │
│  │    agents are forbidden — agents call MemoryAgent.store_episodic())   │   │
│  │ 2. All reads go through MemoryAgent (agents don't query DB directly)  │   │
│  │ 3. Supervisor pre-fetches context package for specialized agents      │   │
│  │ 4. Specialized agents receive context, not raw memory                 │   │
│  │ 5. STM is the exception — Supervisor reads/writes STM directly        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Context Assembly Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CONTEXT ASSEMBLY FOR AGENT INVOCATION                     │
│                                                                              │
│  STEP 1: SUPERVISOR CALLS MEMORY AGENT                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Request:                                                             │   │
│  │  {                                                                    │   │
│  │    "user_id": "...",                                                  │   │
│  │    "intent": "tailor_resume",                                         │   │
│  │    "intent_context": {                                                │   │
│  │      "job_id": "...",                                                 │   │
│  │      "match_analysis": {...}                                          │   │
│  │    },                                                                 │   │
│  │    "context_budget_tokens": 8000,                                     │   │
│  │    "required_routes": ["full_profile", "relevant_semantic"],          │   │
│  │    "optional_routes": ["procedural_patterns"]                         │   │
│  │  }                                                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  STEP 2: MEMORY AGENT RETRIEVES (parallel routes)                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │   │
│  │  │ Route A:        │  │ Route B:        │  │ Route C:        │       │   │
│  │  │ Full Profile    │  │ Vector Search   │  │ Procedural      │       │   │
│  │  │ (10ms)          │  │ (50ms)          │  │ Match (30ms)    │       │   │
│  │  │                 │  │                 │  │                 │       │   │
│  │  │ Profile         │  │ Top-10 semantic │  │ Top-3 patterns  │       │   │
│  │  │ Preferences     │  │ memories        │  │ for intent      │       │   │
│  │  │ Career summary  │  │ Top-20 episodic │  │                 │       │   │
│  │  │ Active pipeline │  │                 │  │                 │       │   │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘       │   │
│  │           │                    │                    │                │   │
│  │           └────────────────────┼────────────────────┘                │   │
│  │                                ▼                                     │   │
│  │                    ┌──────────────────────┐                           │   │
│  │                    │   RANK & TRUNCATE    │                           │   │
│  │                    │   (see §5 formula)   │                           │   │
│  │                    │   Fit token budget   │                           │   │
│  │                    └──────────┬───────────┘                           │   │
│  │                               │                                       │   │
│  │                               ▼                                       │   │
│  │                    ┌──────────────────────┐                           │   │
│  │                    │   ContextPackage     │                           │   │
│  │                    │   (ready for agent)  │                           │   │
│  │                    └──────────────────────┘                           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  STEP 3: SUPERVISOR INVOKES SPECIALIZED AGENT                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  The specialized agent receives:                                      │   │
│  │  {                                                                    │   │
│  │    "call_id": "...",                                                  │   │
│  │    "user_id": "...",                                                  │   │
│  │    "intent": "tailor_resume",                                         │   │
│  │    "context": <ContextPackage>,  // from MemoryAgent                  │   │
│  │    "task_specific_input": {     // from Supervisor's plan            │   │
│  │      "job_id": "...",                                                 │   │
│  │      "match_analysis": {...}                                          │   │
│  │    }                                                                  │   │
│  │  }                                                                    │   │
│  │                                                                       │   │
│  │  The agent does NOT query memory again. It uses what it was given.    │   │
│  │  Exception: agent can call MemoryAgent.store_episodic() to log.       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  STEP 4: POST-EXECUTION WRITE-BACK                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  After agent completes:                                               │   │
│  │  1. Supervisor logs agent_invocation episode                          │   │
│  │  2. Supervisor logs agent_result episode                              │   │
│  │  3. If agent generated artifacts → tool_execution episodes            │   │
│  │  4. MemoryAgent queues consolidation for this user (next 6hr cycle)   │   │
│  │  5. STM updated with new conversation turn                            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Database Design

### 11.1 Complete Schema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     COMPLETE POSTGRESQL SCHEMA                                │
│                     ─────────────────────────                                │
│                     DATABASE: pathfinder_memory                               │
│                     EXTENSIONS: pgvector, pg_partman, pg_stat_statements     │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                           CORE TABLES                                 │   │
│  │                                                                       │   │
│  │  ┌────────────────────────────┐  ┌────────────────────────────┐      │   │
│  │  │ episodic_memories          │  │ semantic_memories           │      │   │
│  │  │ ───────────────────────── │  │ ─────────────────────────── │      │   │
│  │  │ PK: (id, created_at)       │  │ PK: id                      │      │   │
│  │  │ PARTITION: RANGE(created   │  │                             │      │   │
│  │  │   _at) — daily             │  │ INDEXES:                    │      │   │
│  │  │                            │  │ · (user_id, memory_type)    │      │   │
│  │  │ INDEXES:                   │  │ · HNSW(embedding)           │      │   │
│  │  │ · (user_id, created_at     │  │ · GIN(content_text tsvector)│      │   │
│  │  │   DESC)                    │  │ · (user_id, importance      │      │   │
│  │  │ · (user_id, episode_type,  │  │   DESC)                     │      │   │
│  │  │   created_at DESC)         │  │ · (user_id, is_active)      │      │   │
│  │  │ · HNSW(embedding)          │  │   WHERE is_active = true    │      │   │
│  │  │ · (consolidation_id)       │  │                             │      │   │
│  │  │ · (created_at) — partition │  │ FK: user_id → users(id)     │      │   │
│  │  │   key                      │  │                             │      │   │
│  │  │                            │  │                             │      │   │
│  │  │ FK: user_id → users(id)    │  │                             │      │   │
│  │  └────────────────────────────┘  └────────────────────────────┘      │   │
│  │                                                                       │   │
│  │  ┌────────────────────────────┐  ┌────────────────────────────┐      │   │
│  │  │ semantic_memory_versions   │  │ procedural_memories         │      │   │
│  │  │ ───────────────────────── │  │ ─────────────────────────── │      │   │
│  │  │ PK: id                     │  │ PK: id                      │      │   │
│  │  │                            │  │                             │      │   │
│  │  │ INDEXES:                   │  │ INDEXES:                    │      │   │
│  │  │ · (memory_id, version)     │  │ · (user_id, is_active)      │      │   │
│  │  │ · (created_at)             │  │ · HNSW(context_embedding)   │      │   │
│  │  │                            │  │ · (scope, pattern_type,     │      │   │
│  │  │ FK: memory_id →            │  │   success_rate DESC)        │      │   │
│  │  │   semantic_memories(id)    │  │                             │      │   │
│  │  └────────────────────────────┘  │ FK: user_id → users(id)     │      │   │
│  │                                   └────────────────────────────┘      │   │
│  │                                                                       │   │
│  │  ┌────────────────────────────┐  ┌────────────────────────────┐      │   │
│  │  │ user_preferences           │  │ career_timeline             │      │   │
│  │  │ ───────────────────────── │  │ ─────────────────────────── │      │   │
│  │  │ PK: id                     │  │ PK: id                      │      │   │
│  │  │                            │  │                             │      │   │
│  │  │ INDEXES:                   │  │ INDEXES:                    │      │   │
│  │  │ · (user_id, is_current)    │  │ · (user_id, entry_type)     │      │   │
│  │  │   WHERE is_current = true  │  │ · (user_id, start_date      │      │   │
│  │  │ · (user_id, version)       │  │   DESC)                     │      │   │
│  │  │                            │  │ · HNSW(embedding)           │      │   │
│  │  │ FK: user_id → users(id)    │  │ · (user_id, is_current)     │      │   │
│  │  └────────────────────────────┘  │                             │      │   │
│  │                                   │ FK: user_id → users(id)     │      │   │
│  │                                   └────────────────────────────┘      │   │
│  │                                                                       │   │
│  │  ┌────────────────────────────┐  ┌────────────────────────────┐      │   │
│  │  │ compensation_history       │  │ skill_evolution             │      │   │
│  │  │ ───────────────────────── │  │ ─────────────────────────── │      │   │
│  │  │ PK: id                     │  │ PK: id                      │      │   │
│  │  │                            │  │                             │      │   │
│  │  │ INDEXES:                   │  │ INDEXES:                    │      │   │
│  │  │ · (user_id, effective_date │  │ · (user_id, skill_name)     │      │   │
│  │  │   DESC)                    │  │ · (user_id, assessed_at     │      │   │
│  │  │ · (career_entry_id)        │  │   DESC)                     │      │   │
│  │  │                            │  │ · HNSW(embedding)           │      │   │
│  │  │ FK: user_id → users(id)    │  │                             │      │   │
│  │  │ FK: career_entry_id →      │  │ FK: user_id → users(id)     │      │   │
│  │  │   career_timeline(id)      │  └────────────────────────────┘      │   │
│  │  └────────────────────────────┘                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        SUPPORTING TABLES                              │   │
│  │                                                                       │   │
│  │  ┌────────────────────────────┐  ┌────────────────────────────┐      │   │
│  │  │ consolidation_runs         │  │ memory_stats                │      │   │
│  │  │ ───────────────────────── │  │ ─────────────────────────── │      │   │
│  │  │ PK: id                     │  │ PK: user_id                 │      │   │
│  │  │                            │  │                             │      │   │
│  │  │ · user_id (FK)             │  │ · total_episodes (BIGINT)   │      │   │
│  │  │ · started_at               │  │ · total_semantic (INT)      │      │   │
│  │  │ · completed_at             │  │ · total_procedural (INT)    │      │   │
│  │  │ · episodes_processed (INT) │  │ · last_consolidation_at     │      │   │
│  │  │ · insights_generated (INT) │  │ · total_tokens_used (BIGINT)│      │   │
│  │  │ · preferences_updated (INT)│  │ · storage_bytes (BIGINT)    │      │   │
│  │  │ · status (ENUM)            │  │ · updated_at                │      │   │
│  │  │ · error_message (TEXT)     │  │                             │      │   │
│  │  │ · tokens_used (INT)        │  │                             │      │   │
│  │  │ · duration_ms (INT)        │  │                             │      │   │
│  │  └────────────────────────────┘  └────────────────────────────┘      │   │
│  │                                                                       │   │
│  │  ┌────────────────────────────┐  ┌────────────────────────────┐      │   │
│  │  │ deletion_log               │  │ memory_access_log           │      │   │
│  │  │ ───────────────────────── │  │ ─────────────────────────── │      │   │
│  │  │ PK: id                     │  │ PK: id                      │      │   │
│  │  │                            │  │                             │      │   │
│  │  │ · user_id                  │  │ · user_id                   │      │   │
│  │  │ · deletion_type (ENUM)     │  │ · agent_type                │      │   │
│  │  │ · memory_type_deleted      │  │ · retrieval_route            │      │   │
│  │  │ · memory_ids (UUID[])      │  │ · memories_returned (INT)   │      │   │
│  │  │ · requested_by (ACTOR)     │  │ · latency_ms (INT)          │      │   │
│  │  │ · request_reason (TEXT)    │  │ · context_tokens (INT)      │      │   │
│  │  │ · completed_at             │  │ · created_at                │      │   │
│  │  │ · verified_by (UUID)       │  │                             │      │   │
│  │  └────────────────────────────┘  └────────────────────────────┘      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Index Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INDEX STRATEGY                                       │
│                                                                              │
│  CRITICAL INDICES (affect query performance for every agent invocation):     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ TABLE              │ INDEX                      │ JUSTIFICATION       │   │
│  │ ──────────────────┼───────────────────────────┼─────────────────────│   │
│  │ episodic_memories  │ (user_id, created_at DESC) │ Every agent reads   │   │
│  │                    │                           │ recent episodes      │   │
│  │ episodic_memories  │ HNSW on embedding         │ Vector retrieval     │   │
│  │                    │ (m=16, ef_construction=200)│ route B             │   │
│  │ semantic_memories  │ (user_id, memory_type)    │ Profile/pref lookup  │   │
│  │ semantic_memories  │ HNSW on embedding         │ Most common route    │   │
│  │                    │ (m=16, ef_construction=200)│                     │   │
│  │ semantic_memories  │ GIN on content_text       │ Hybrid keyword      │   │
│  │                    │ (tsvector)                │ search              │   │
│  │ user_preferences   │ (user_id, is_current)     │ Every agent reads   │   │
│  │                    │ WHERE is_current = true   │ preferences         │   │
│  │ procedural_memories│ (user_id, is_active)      │ Routing lookup      │   │
│  │ career_timeline    │ (user_id, entry_type)     │ Agent-specific      │   │
│  │                    │                           │ queries             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  HNSW CONFIGURATION:                                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ PARAMETER             │ VALUE     │ JUSTIFICATION                     │   │
│  │ ─────────────────────┼──────────┼────────────────────────────────── │   │
│  │ m (connections/layer) │ 16        │ Standard. Good recall/speed       │   │
│  │                       │           │ tradeoff.                         │   │
│  │ ef_construction       │ 200       │ Higher = better recall, slower    │   │
│  │                       │           │ build. Acceptable for batch.      │   │
│  │ ef_search (query)     │ 100       │ Configurable per query. Higher    │   │
│  │                       │           │ for interview prep (needs recall) │   │
│  │                       │           │ Lower for browsing (needs speed)  │   │
│  │                       │           │ Default: 100.                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  PARTITIONING:                                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ TABLE              │ PARTITION KEY    │ STRATEGY    │ RETENTION       │   │
│  │ ──────────────────┼─────────────────┼────────────┼────────────────  │   │
│  │ episodic_memories  │ created_at       │ RANGE, daily│ Hot: 90 days    │   │
│  │                    │                  │             │ Cold: 730 days  │   │
│  │                    │                  │             │ Archive: beyond │   │
│  │ semantic_memories  │ HASH(user_id)    │ HASH, 64    │ Indefinite      │   │
│  │                    │ (at > 10M rows)  │ partitions  │                 │   │
│  │ audit_logs         │ created_at       │ RANGE, daily│ 90 days hot     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Retrieval Algorithms

### 12.1 Algorithm Catalog

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     RETRIEVAL ALGORITHM CATALOG                               │
│                                                                              │
│  ALGORITHM 1: CONTEXT-WINDOW ASSEMBLY                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ NAME: assemble_context_window(user_id, intent, budget_tokens)         │   │
│  │ PURPOSE: Build the optimal context package for an agent invocation    │   │
│  │                                                                       │   │
│  │ ALGORITHM:                                                            │   │
│  │ 1. ALWAYS_LOAD = [profile, preferences, career_summary,               │   │
│  │                   active_applications]                                │   │
│  │    → tokens_used = sum(token_count(ALWAYS_LOAD))                      │   │
│  │                                                                       │   │
│  │ 2. REMAINING_BUDGET = budget_tokens - tokens_used                     │   │
│  │                                                                       │   │
│  │ 3. CANDIDATE_POOL = []                                                │   │
│  │    a. RECENT_EPISODES = query_recent_episodes(user_id, limit=50)      │   │
│  │       → scored by recency (exponential decay, λ=0.10)                 │   │
│  │    b. RELEVANT_SEMANTIC = vector_search(                              │   │
│  │         query_embedding=intent_to_embedding(intent),                  │   │
│  │         user_id=user_id, limit=30)                                    │   │
│  │       → scored by cosine_similarity × importance                      │   │
│  │    c. PROCEDURAL_PATTERNS = match_procedural(                         │   │
│  │         intent=intent, user_id=user_id, limit=5)                      │   │
│  │       → scored by success_rate × context_match                        │   │
│  │                                                                       │   │
│  │    Merge all into CANDIDATE_POOL with unified score                    │   │
│  │                                                                       │   │
│  │ 4. SORT CANDIDATE_POOL by unified_score DESC                          │   │
│  │                                                                       │   │
│  │ 5. SELECTED = []                                                      │   │
│  │    FOR candidate IN CANDIDATE_POOL:                                   │   │
│  │      IF tokens(candidate) + current_tokens <= REMAINING_BUDGET:       │   │
│  │        SELECTED.append(candidate)                                     │   │
│  │        current_tokens += tokens(candidate)                            │   │
│  │      ELSE:                                                            │   │
│  │        IF candidate.importance > 0.8:  // would displace something    │   │
│  │          try_displace_lowest_scored(SELECTED, candidate)              │   │
│  │                                                                       │   │
│  │ 6. Format SELECTED into ContextPackage                                │   │
│  │ 7. Log memory_access_log with stats                                    │   │
│  │ 8. Return ContextPackage                                              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ALGORITHM 2: PREFERENCE WEIGHT UPDATE (Bayesian)                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ NAME: update_preference_weight(user_id, field, signal, strength)      │   │
│  │ PURPOSE: Update a preference weight based on new evidence             │   │
│  │                                                                       │   │
│  │ ALGORITHM:                                                            │   │
│  │ 1. current = SELECT preference_data → field FROM user_preferences     │   │
│  │    WHERE user_id = $1 AND is_current = true                           │   │
│  │                                                                       │   │
│  │ 2. evidence_count = get_evidence_count_for_field(user_id, field)      │   │
│  │                                                                       │   │
│  │ 3. // Bayesian update with prior weight                               │   │
│  │    α = evidence_count  // strength of prior belief                    │   │
│  │    β = signal_strength // strength of new evidence                    │   │
│  │    new_weight = (current * α + signal * β) / (α + β)                  │   │
│  │    new_confidence = min(1.0, confidence + 0.02 * β)                   │   │
│  │                                                                       │   │
│  │ 4. IF |new_weight - current| / current > 0.05:  // 5% threshold       │   │
│  │      INSERT new version into user_preferences                         │   │
│  │      UPDATE is_current = false on previous version                    │   │
│  │      EMIT memory.preference_shift event                                │   │
│  │                                                                       │   │
│  │ 5. Return {new_weight, new_confidence, did_change}                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ALGORITHM 3: IMPORTANCE RECALIBRATION                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ NAME: recalibrate_importance(memory_id)                               │   │
│  │ PURPOSE: Update importance score based on actual usage patterns       │   │
│  │                                                                       │   │
│  │ ALGORITHM:                                                            │   │
│  │ 1. memory = SELECT importance_score, access_count,                    │   │
│  │              last_accessed_at, evidence_count, created_at             │   │
│  │           FROM semantic_memories WHERE id = $1                        │   │
│  │                                                                       │   │
│  │ 2. usage_score = min(1.0,                                           │   │
│  │      (memory.access_count * 0.02) +  // base usage                   │   │
│  │      (days_since_last_access < 7 ? 0.3 : 0)  // recency bonus       │   │
│  │    )                                                                  │   │
│  │                                                                       │   │
│  │ 3. evidence_score = min(1.0, memory.evidence_count * 0.1)            │   │
│  │                                                                       │   │
│  │ 4. age_factor = max(0.3, 1.0 - (days_since_creation / 730) * 0.7)    │   │
│  │    // 0–2 years: 1.0→0.3 linear decay                                 │   │
│  │                                                                       │   │
│  │ 5. new_importance = (                                                   │   │
│  │      memory.importance_score * 0.4 +  // prior belief                │   │
│  │      usage_score * 0.35 +              // actual usage               │   │
│  │      evidence_score * 0.15 +           // evidentiary strength       │   │
│  │      age_factor * 0.10                 // age adjustment             │   │
│  │    )                                                                  │   │
│  │                                                                       │   │
│  │ 6. UPDATE semantic_memories SET importance_score = new_importance     │   │
│  │    WHERE id = $1                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ALGORITHM 4: MEMORY DEDUPLICATION ON RETRIEVAL                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ NAME: deduplicate_retrieved(memories, threshold=0.85)                 │   │
│  │ PURPOSE: Remove near-duplicate memories from context to save tokens   │   │
│  │                                                                       │   │
│  │ ALGORITHM:                                                            │   │
│  │ 1. Sort memories by importance_score DESC (keep more important)       │   │
│  │                                                                       │   │
│  │ 2. KEPT = []                                                          │   │
│  │    FOR memory IN memories:                                            │   │
│  │      is_duplicate = FALSE                                             │   │
│  │      FOR kept IN KEPT:                                                │   │
│  │        IF cosine_similarity(memory.embedding, kept.embedding)         │   │
│  │           > threshold:                                                │   │
│  │          is_duplicate = TRUE                                          │   │
│  │          BREAK                                                        │   │
│  │      IF NOT is_duplicate:                                             │   │
│  │        KEPT.append(memory)                                            │   │
│  │                                                                       │   │
│  │ 3. Return KEPT                                                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ALGORITHM 5: CROSS-TIER RETRIEVAL                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ NAME: cross_tier_search(user_id, query_embedding, limit=20)           │   │
│  │ PURPOSE: Search across warm + cold tiers transparently                │   │
│  │                                                                       │   │
│  │ ALGORITHM:                                                            │   │
│  │ 1. results_warm = vector_search(semantic_memories,                    │   │
│  │      WHERE is_active=true AND tier='warm', limit=limit)               │   │
│  │                                                                       │   │
│  │ 2. IF len(results_warm) >= limit:                                     │   │
│  │      RETURN results_warm  // warm tier had enough                    │   │
│  │                                                                       │   │
│  │ 3. remaining = limit - len(results_warm)                              │   │
│  │    results_cold = vector_search(semantic_memories,                    │   │
│  │      WHERE is_active=true AND tier='cold', limit=remaining)           │   │
│  │    // Cold tier is same table, different partition — slower but       │   │
│  │    // transparent to caller                                           │   │
│  │                                                                       │   │
│  │ 4. RETURN results_warm + results_cold                                 │   │
│  │    WITH metadata: {tiers_searched: ["warm", "cold"],                  │   │
│  │                    warm_count: len(results_warm),                     │   │
│  │                    cold_count: len(results_cold)}                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

> *"Memory is not a feature. Memory is the product. Everything else — matching, tailoring, coaching — is just a retrieval query over well-structured memory."*

**End of Memory Architecture Document**
