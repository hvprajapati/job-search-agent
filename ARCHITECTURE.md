# Pathfinder — Production Architecture Document

**Document Version:** 1.0
**Date:** 2026-06-17
**Author:** Principal Solutions Architect
**Classification:** Confidential — Internal

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Low-Level Architecture](#2-low-level-architecture)
3. [Service Boundaries](#3-service-boundaries)
4. [Communication Patterns](#4-communication-patterns)
5. [Scalability Design](#5-scalability-design)
6. [Caching Strategy](#6-caching-strategy)
7. [Storage Strategy](#7-storage-strategy)
8. [Security Architecture](#8-security-architecture)
9. [Failure Recovery Strategy](#9-failure-recovery-strategy)
10. [Deployment Architecture](#10-deployment-architecture)

---

## 1. High-Level Architecture

### 1.1 System Context Diagram

```
                          ┌─────────────────────────────────────────┐
                          │              USERS (100K)               │
                          │   Freshers · SWE · DE · AIE · MLE      │
                          └──────────────┬──────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
             ┌──────────┐        ┌──────────┐        ┌──────────┐
             │  Browser │        │   iOS    │        │ Android  │
             │  (Web)   │        │  (V2)    │        │  (V2)    │
             └────┬─────┘        └────┬─────┘        └────┬─────┘
                  │                   │                   │
                  └───────────────────┼───────────────────┘
                                      │ HTTPS / WSS
                                      │
┌─────────────────────────────────────┼─────────────────────────────────────┐
│                            CDN / WAF LAYER                                │
│                      Cloudflare (DDoS, caching, SSL)                      │
└─────────────────────────────────────┼─────────────────────────────────────┘
                                      │
┌─────────────────────────────────────┼─────────────────────────────────────┐
│                          LOAD BALANCER (NGINX)                            │
│                     rate limiting · routing · TLS term                     │
└──────┬──────────────┬──────────────┬──────────────┬───────────────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│  Web App   │ │  API GW    │ │  WS Server │ │  Webhook   │
│  Next.js   │ │  FastAPI   │ │  FastAPI   │ │  FastAPI   │
│  (SSR+CSR) │ │  (REST)    │ │  (WS)      │ │  (Email)   │
└─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
      │              │              │              │
      └──────────────┼──────────────┼──────────────┘
                     │              │
┌────────────────────┼──────────────┼────────────────────────────────────────┐
│            SERVICE MESH (Internal)                                         │
│                                                                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│  │  AGENT           │  │  JOB DISCOVERY   │  │  APPLICATION     │         │
│  │  ORCHESTRATOR    │  │  SERVICE         │  │  TRACKING SVC    │         │
│  │  (LangGraph)     │  │  (FastAPI+Celey) │  │  (FastAPI)       │         │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘         │
│           │                     │                     │                    │
│  ┌────────┴─────────┐  ┌────────┴─────────┐  ┌────────┴─────────┐         │
│  │  MATCHING        │  │  RESUME          │  │  COVER LETTER    │         │
│  │  ENGINE          │  │  ENGINE          │  │  ENGINE          │         │
│  │  (pgvector)      │  │  (LangGraph)     │  │  (LangGraph)     │         │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘         │
│           │                     │                     │                    │
│  ┌────────┴─────────┐  ┌────────┴─────────┐  ┌────────┴─────────┐         │
│  │  INTERVIEW       │  │  LEARNING        │  │  MEMORY          │         │
│  │  PREP SERVICE    │  │  ENGINE          │  │  SERVICE         │         │
│  │  (LangGraph)     │  │  (LangGraph)     │  │  (pgvector)      │         │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘         │
│           │                     │                     │                    │
└───────────┼─────────────────────┼─────────────────────┼────────────────────┘
            │                     │                     │
┌───────────┼─────────────────────┼─────────────────────┼────────────────────┐
│           ▼                     ▼                     ▼                    │
│                         DATA PLANE                                         │
│                                                                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐          │
│  │PostgreSQL  │  │  pgvector  │  │   Redis    │  │    S3/     │          │
│  │ (primary)  │  │ (embeddings│  │  Cluster   │  │   MinIO    │          │
│  │            │  │  + HNSW)   │  │            │  │ (documents)│          │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘          │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                          EXTERNAL SERVICES                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ DeepSeek │ │  Email   │ │  Job     │ │  Company │ │  Social  │        │
│  │   API    │ │ (Gmail,  │ │  Boards  │ │  Data    │ │  (Linked │        │
│  │  (LLM)   │ │ Outlook) │ │ (Scrape) │ │ (Crunch- │ │  In, GH) │        │
│  │          │ │          │ │          │ │  base)   │ │          │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
└────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Layer Summary

| Layer | Components | Responsibility |
|-------|-----------|----------------|
| **Edge** | Cloudflare CDN/WAF | DDoS protection, static asset caching, SSL termination, bot management |
| **Presentation** | Next.js 15 (React 19) | Server-side rendering, client-side interactivity, progressive enhancement |
| **API Gateway** | FastAPI + NGINX | Authentication, rate limiting, request routing, input validation, response transformation |
| **Application** | FastAPI services + LangGraph agents | Business logic, agent orchestration, job discovery, matching, document generation |
| **Messaging** | Redis Streams + Celery | Async task processing, event publication/subscription, background job execution |
| **Data** | PostgreSQL + pgvector + Redis + S3/MinIO | Persistent storage, vector search, caching, document storage |
| **AI** | DeepSeek API + LangGraph | LLM inference, agent reasoning, tool calling, structured generation |
| **Observability** | Prometheus + Grafana + ELK | Metrics, logging, tracing, alerting |
| **Orchestration** | Docker Compose (dev) / Kubernetes (prod) | Container orchestration, service discovery, auto-scaling |

---

## 2. Low-Level Architecture

### 2.1 Frontend Layer — Next.js Application

```
┌─────────────────────────────────────────────────────────────────────┐
│                     NEXT.JS 15 APPLICATION                           │
│                                                                      │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐   │
│  │      APP ROUTER          │    │       SERVER COMPONENTS       │   │
│  │                          │    │                               │   │
│  │  /dashboard              │    │  ProfileSummary (SSR)         │   │
│  │  /jobs                   │    │  JobCard (SSR)                │   │
│  │  /pipeline               │    │  MatchScore (SSR)             │   │
│  │  /applications           │    │  PipelineKanban (SSR)         │   │
│  │  /resumes                │    │  AnalyticsChart (SSR)         │   │
│  │  /interviews             │    │                               │   │
│  │  /learning               │    │                               │   │
│  │  /settings               │    │                               │   │
│  └──────────────────────────┘    └──────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐   │
│  │     CLIENT COMPONENTS    │    │        STATE MANAGEMENT       │   │
│  │                          │    │                               │   │
│  │  JobCard.client.tsx      │    │  Zustand stores:              │   │
│  │  MatchViewer.tsx         │    │  ├─ useAuthStore              │   │
│  │  ResumeDiff.tsx          │    │  ├─ useJobStore               │   │
│  │  CoverLetterEditor.tsx   │    │  ├─ usePipelineStore          │   │
│  │  AgentChat.tsx           │    │  ├─ useProfileStore           │   │
│  │  InterviewSimulator.tsx  │    │  └─ useNotificationStore      │   │
│  │  SkillGapRadar.tsx       │    │                               │   │
│  └──────────────────────────┘    └──────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    API CLIENT LAYER                            │   │
│  │                                                                │   │
│  │  React Query (TanStack Query v5)                               │   │
│  │  ├─ Automatic caching & background refetch                     │   │
│  │  ├─ Optimistic updates for pipeline mutations                  │   │
│  │  ├─ Infinite scroll pagination for job listings                │   │
│  │  └─ Stale-while-revalidate strategy (30s default)              │   │
│  │                                                                │   │
│  │  WebSocket client (native WebSocket API)                       │   │
│  │  ├─ Real-time job match notifications                          │   │
│  │  ├─ Agent streaming responses                                  │   │
│  │  └─ Pipeline status updates                                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Frontend Design Decisions:**

- **Server Components** for data-fetching pages (dashboard, job listings) — reduces client JS, improves SEO
- **Client Components** only for interactive elements (diff viewer, editor, chat) — minimizes bundle size
- **Streaming via Server-Sent Events** for agent responses — user sees tokens as they're generated
- **Optimistic updates** for pipeline mutations — immediate UI feedback, rollback on error
- **Incremental Static Regeneration** for public pages (landing, pricing, docs) — 60s revalidation

### 2.2 API Gateway Layer — FastAPI

```
┌─────────────────────────────────────────────────────────────────────┐
│                     FASTAPI API GATEWAY                              │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  MIDDLEWARE PIPELINE                           │   │
│  │                                                                │   │
│  │  Request → [CORS] → [Auth JWT] → [Rate Limit] → [Audit]       │   │
│  │         → [Input Validation] → [Route Handler] → Response      │   │
│  │                                                                │   │
│  │  Response → [Compression] → [Cache Headers] → Client           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────┐  ┌─────────────────────┐                   │
│  │   REST ENDPOINTS    │  │  WEBSOCKET / SSE     │                   │
│  │                     │  │                      │                   │
│  │  /api/v1/auth/*     │  │  /ws/agent/{id}      │                   │
│  │  /api/v1/profile/*  │  │  /ws/notifications   │                   │
│  │  /api/v1/jobs/*     │  │  /sse/stream/{id}    │                   │
│  │  /api/v1/match/*    │  │                      │                   │
│  │  /api/v1/resume/*   │  │                      │                   │
│  │  /api/v1/cover/*    │  │                      │                   │
│  │  /api/v1/app/*      │  │                      │                   │
│  │  /api/v1/interview/*│  │                      │                   │
│  │  /api/v1/learn/*    │  │                      │                   │
│  │  /api/v1/agent/*    │  │                      │                   │
│  │  /api/v1/analytics/*│  │                      │                   │
│  └─────────┬───────────┘  └─────────────────────┘                   │
│            │                                                         │
│  ┌─────────┴───────────────────────────────────────────────────┐    │
│  │                    SERVICE CLIENTS                            │    │
│  │                                                                │    │
│  │  AgentOrchestratorClient  →  LangGraph Agent Service          │    │
│  │  JobDiscoveryClient       →  Job Discovery Service            │    │
│  │  ApplicationClient        →  Application Tracking Service     │    │
│  │  ProfileClient            →  Profile Service                  │    │
│  │  MatchingClient           →  Matching Engine                  │    │
│  │  DocumentClient           →  Resume + Cover Letter Engines    │    │
│  │  MemoryClient             →  Memory Service                   │    │
│  │  NotificationClient       →  Notification Service             │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

**API Gateway Design Decisions:**

- **FastAPI** for async native support, automatic OpenAPI docs, Pydantic validation
- **JWT-based authentication** — access tokens (15 min) + refresh tokens (7 days), stored in httpOnly cookies
- **Rate limiting** via Redis sliding window — tiered: 100 req/min (free), 300 req/min (pro), 1000 req/min (premium)
- **Request correlation IDs** — UUID v7 injected at edge, propagated through all services for tracing
- **API versioning** — URL-prefix based (/api/v1/) with deprecation headers and sunset policies
- **Bulk endpoints** for list operations — `/api/v1/jobs/bulk` for fetching multiple jobs in one request

### 2.3 Agent Orchestration Layer — LangGraph

This is the **heart of the system**. LangGraph provides the state machine framework for multi-agent coordination.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AGENT ORCHESTRATION ARCHITECTURE                           │
│                        LangGraph StateGraph                                   │
│                                                                               │
│                          ┌─────────────────┐                                  │
│                          │  ENTRY POINT     │                                  │
│                          │  (User Intent)   │                                  │
│                          └────────┬────────┘                                  │
│                                   │                                           │
│                          ┌────────┴────────┐                                  │
│                          │  ORCHESTRATOR   │                                  │
│                          │     AGENT       │                                  │
│                          │                 │                                  │
│                          │  Intent Router  │                                  │
│                          │  Context Builder│                                  │
│                          │  Tool Dispatcher│                                  │
│                          └───┬───┬───┬───┬─┘                                  │
│                              │   │   │   │                                    │
│         ┌────────────────────┼───┼───┼───┼────────────────────┐              │
│         │                    │   │   │   │                    │              │
│         ▼                    ▼   ▼   ▼   ▼                    ▼              │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  PROFILE   │  │DISCOVERY │  │ MATCHING │  │  DOCUMENT│  │INTERVIEW │    │
│  │   AGENT    │  │  AGENT   │  │  AGENT   │  │   AGENTS │  │   AGENT  │    │
│  │            │  │          │  │          │  │          │  │          │    │
│  │ Resume     │  │ Job      │  │ Semantic │  │ Resume   │  │ Question │    │
│  │ Parsing    │  │ Scraping │  │ Scoring  │  │ Tailor   │  │ Generator│    │
│  │ Profile    │  │ Dedup    │  │ Ranking  │  │ Cover    │  │ Mock     │    │
│  │ Enrichment │  │ Freshness│  │ Explain  │  │ Letter   │  │ Interview│    │
│  └─────┬──────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│        │              │             │             │             │           │
│  ┌─────┴──────┐  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐    │
│  │  LEARNING  │  │COMMUNICA-│  │APPLICATION│  │  MEMORY  │  │ ANALYTICS│    │
│  │   AGENT    │  │TION AGENT│  │TRACK AGENT│  │  AGENT   │  │  AGENT   │    │
│  │            │  │          │  │           │  │          │  │          │    │
│  │ Skill Gap  │  │ Follow-up│  │ Pipeline  │  │ Pref.    │  │ Funnel    │    │
│  │ Analysis   │  │ Thank-you│  │ Status    │  │ Learning │  │ Metrics   │    │
│  │ Learning   │  │ Outreach │  │ Deadline  │  │ Narrative│  │ Insights  │    │
│  │ Plans      │  │ Drafts   │  │ Tracking  │  │ Building │  │ Trends    │    │
│  └─────┬──────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│        │              │             │             │             │           │
│        └──────────────┴─────────────┴─────────────┴─────────────┘           │
│                                   │                                          │
│                          ┌────────┴────────┐                                  │
│                          │  RESPONSE       │                                  │
│                          │  SYNTHESIS      │                                  │
│                          │  (Multi-agent   │                                  │
│                          │   result merge) │                                  │
│                          └────────┬────────┘                                  │
│                                   │                                           │
│                          ┌────────┴────────┐                                  │
│                          │  HUMAN GATE     │                                  │
│                          │  (HITL — where  │                                  │
│                          │   configured)   │                                  │
│                          └────────┬────────┘                                  │
│                                   │                                           │
│                          ┌────────┴────────┐                                  │
│                          │  EXECUTE & LOG  │                                  │
│                          └─────────────────┘                                  │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                        SHARED AGENT TOOLS                                │  │
│  │                                                                          │  │
│  │  Tool Registry (all agents have access based on role)                     │  │
│  │                                                                          │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │  │
│  │  │ search_jobs  │ │ read_profile │ │tailor_resume │ │send_email    │    │  │
│  │  │ (pgvector)   │ │ (PostgreSQL) │ │ (DeepSeek)   │ │ (SMTP/API)   │    │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘    │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │  │
│  │  │get_company   │ │analyze_match │ │search_web    │ │update_pipe   │    │  │
│  │  │_info (API)   │ │ (DeepSeek)   │ │ (Search API) │ │ (PostgreSQL) │    │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘    │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │  │
│  │  │store_memory  │ │recall_memory │ │learn_pref    │ │schedule_task │    │  │
│  │  │ (pgvector)   │ │ (pgvector)   │ │ (Memory Svc) │ │ (Celery)     │    │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘    │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**LangGraph Agent Design:**

Each agent is a **compiled StateGraph** with:
- **State schema** (TypedDict) defining the data flowing through the agent
- **Nodes** — functions that transform state (LLM calls, tool execution, data retrieval)
- **Edges** — conditional routing between nodes based on state
- **Checkpointer** — persistence layer for agent state (PostgreSQL-backed)

```
Orchestrator Agent (Root Graph)
├── state: OrchestratorState
│   ├── user_id: str
│   ├── session_id: str
│   ├── intent: str (route key)
│   ├── context: dict (profile, preferences, history)
│   ├── agent_results: dict (outputs from sub-agents)
│   ├── pending_approvals: list (actions needing HITL)
│   └── final_response: dict
│
├── nodes:
│   ├── build_context → fetches user profile, preferences, recent history
│   ├── route_intent → LLM classifies intent → maps to agent
│   ├── invoke_agent → calls specialized sub-agent with context
│   ├── synthesize → merges multi-agent results if needed
│   └── human_gate → pauses if configured, returns pending approvals
│
├── subgraphs (specialized agents):
│   ├── ProfileAgent
│   ├── DiscoveryAgent
│   ├── MatchingAgent
│   ├── DocumentAgent (Resume + CoverLetter sub-subgraphs)
│   ├── InterviewPrepAgent
│   ├── CommunicationAgent
│   ├── ApplicationTrackingAgent
│   ├── LearningAgent
│   └── MemoryAgent
│
└── checkpointer: PostgresSaver (async checkpoint persistence)
```

### 2.4 Job Discovery Service — Internal Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    JOB DISCOVERY SERVICE                              │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    SCHEDULER (Celery Beat)                     │   │
│  │                                                                │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐             │   │
│  │  │ Every   │ │ Every   │ │ Every   │ │ Every   │             │   │
│  │  │ 15 min  │ │ 1 hour  │ │ 6 hours │ │ 24 hours│             │   │
│  │  │ (high   │ │ (medium │ │ (low    │ │ (deep   │             │   │
│  │  │ priority│ │ priority│ │ priority│ │ sweep)  │             │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘             │   │
│  │       └───────────┴───────────┴───────────┘                   │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                        │
│                             ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    INGESTION PIPELINE                          │   │
│  │                                                                │   │
│  │  Source Connectors (Celery Tasks)                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │   │
│  │  │LinkedIn  │ │ Indeed   │ │Company   │ │Community │         │   │
│  │  │Scraper   │ │ Scraper  │ │Career    │ │Crawler   │         │   │
│  │  │          │ │          │ │Pages     │ │(Reddit,  │         │   │
│  │  │          │ │          │ │(Greenhse,│ │ HN, etc) │         │   │
│  │  │          │ │          │ │ Lever..) │ │          │         │   │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘         │   │
│  │       └─────────────┴────────────┴────────────┘                │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                        │
│                             ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    PROCESSING PIPELINE                         │   │
│  │                                                                │   │
│  │  Raw Job → [Clean] → [Normalize] → [Dedup] → [Enrich] → [Embed]→Store│
│  │                                                                │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐          │   │
│  │  │HTML→MD  │  │Schema   │  │Fuzzy    │  │LLM: tech │          │   │
│  │  │strip    │  │map to   │  │matching │  │stack,    │          │   │
│  │  │noise    │  │canonical│  │(title+  │  │seniority,│          │   │
│  │  │         │  │model    │  │co+loc)  │  │remote,   │          │   │
│  │  │         │  │         │  │         │  │salary    │          │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └──────────┘          │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    DEDUPLICATION ENGINE                        │   │
│  │                                                                │   │
│  │  Tier 1: Exact match (title + company + location hash)         │   │
│  │  Tier 2: Fuzzy match (Levenshtein + embedding cosine > 0.92)   │   │
│  │  Tier 3: LLM judge (ambiguous cases, batched, cost-controlled) │   │
│  │                                                                │   │
│  │  Canonical Job ID = stable hash of normalized title+company    │   │
│  └───────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.5 Memory Service — Long-Term Memory Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MEMORY SERVICE                                  │
│                  Three-Tier Memory Architecture                       │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  TIER 1: EPISODIC MEMORY  (Redis + PostgreSQL)                │   │
│  │                                                                │   │
│  │  What: Session interactions, agent-user conversations,         │   │
│  │        actions taken, feedback given                           │   │
│  │  TTL: Hot in Redis (24h), warm in PostgreSQL (90 days)         │   │
│  │  Structure: {session_id, timestamp, event_type, payload}       │   │
│  │  Use: Immediate context for current session + recent history   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  TIER 2: SEMANTIC MEMORY  (pgvector + PostgreSQL)              │   │
│  │                                                                │   │
│  │  What: User profile, skills, preferences, career narrative,    │   │
│  │        learned patterns, company preferences, salary desires   │   │
│  │  TTL: Persistent (indefinite, user-owned)                      │   │
│  │  Structure:                                                    │   │
│  │    - user_profile_embedding (vector 3072)                      │   │
│  │    - skill_vectors[] (vector 1536 per skill)                   │   │
│  │    - preference_weights (JSONB) — evolves with feedback        │   │
│  │    - career_narrative (text + vector) — LLM-maintained summary │   │
│  │    - interaction_patterns (JSONB) — learned behaviors          │   │
│  │  Use: Matching, personalization, agent context                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  TIER 3: PROCEDURAL MEMORY  (PostgreSQL + LangGraph Checkpts) │   │
│  │                                                                │   │
│  │  What: Agent workflow states, successful strategies,           │   │
│  │        tool-use patterns, routing decisions                    │   │
│  │  TTL: Persistent (versioned, evolves)                          │   │
│  │  Structure:                                                    │   │
│  │    - LangGraph checkpoint states (per agent, per session)      │   │
│  │    - Agent execution traces (DAG of nodes → outcomes)          │   │
│  │    - Learned routing rules (intent → best agent path)          │   │
│  │    - Tool effectiveness scores (per tool, per context)         │   │
│  │  Use: Agent improvement, routing optimization, debugging       │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                 MEMORY CONSOLIDATION PROCESS                   │   │
│  │                     (Background Cron)                          │   │
│  │                                                                │   │
│  │  Every 6 hours:                                                │   │
│  │  1. Fetch recent episodic memories (last 6h)                   │   │
│  │  2. LLM summarizes into structured insights                    │   │
│  │  3. Update semantic memory (preference weights, narrative)     │   │
│  │  4. Extract procedural patterns (what worked, what didn't)     │   │
│  │  5. Update embeddings for changed entities                     │   │
│  │  6. Archive raw episodic data older than 90 days               │   │
│  │  7. Update memory importance scores (for retrieval priority)   │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Memory Retrieval Pattern (at agent invocation time):**

```
1. Agent requests context for user_id + intent
2. Memory Service retrieves:
   a. Semantic: user_profile_embedding, preference_weights (always loaded)
   b. Episodic: last 20 interactions (most recent, highest relevance)
   c. Semantic RAG: top-K relevant memories via vector similarity to intent
   d. Procedural: best-known workflow for this intent type
3. Memory Service constructs context payload → returns to agent
4. Agent includes context in system prompt + state
```

### 2.6 RAG Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                   RAG PIPELINE ARCHITECTURE                           │
│                                                                      │
│  ┌──────────────────────┐     ┌──────────────────────┐              │
│  │   INDEXING PIPELINE  │     │   RETRIEVAL PIPELINE  │              │
│  │      (Offline)       │     │      (Online)         │              │
│  │                      │     │                       │              │
│  │  1. Document Ingestion│    │  1. Query Reception    │              │
│  │     (Jobs, Resumes,  │     │     (User intent +    │              │
│  │      Profiles,       │     │      query text)      │              │
│  │      Articles)       │     │                       │              │
│  │       │              │     │  2. Query Processing   │              │
│  │       ▼              │     │     (Embed + expand   │              │
│  │  2. Chunking Strategy│     │      with synonyms)   │              │
│  │     (Semantic split) │     │                       │              │
│  │       │              │     │  3. Hybrid Search     │              │
│  │       ▼              │     │     (Vector + BM25)   │              │
│  │  3. Embedding Gen    │     │                       │              │
│  │     (DeepSeek embed) │     │  4. Re-ranking        │              │
│  │       │              │     │     (Cross-encoder)   │              │
│  │       ▼              │     │                       │              │
│  │  4. Vector Store     │     │  5. Context Assembly  │              │
│  │     (pgvector HNSW)  │     │     (Top-K → LLM)     │              │
│  │                      │     │                       │              │
│  └──────────────────────┘     └──────────────────────┘              │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                 RAG USE CASES IN PATHFINDER                    │   │
│  │                                                                │   │
│  │  1. JOB MATCHING                                              │   │
│  │     Query: user_profile_embedding                              │   │
│  │     Index: job_embeddings (filtered by active, location)       │   │
│  │     Top-K: 200 → re-rank → top 20                              │   │
│  │                                                                │   │
│  │  2. SIMILAR JOB DISCOVERY                                     │   │
│  │     Query: saved_job_embedding                                 │   │
│  │     Index: all active job embeddings                           │   │
│  │     Top-K: 50                                                  │   │
│  │                                                                │   │
│  │  3. SKILL GAP ANALYSIS                                        │   │
│  │     Query: user_skill_embeddings                               │   │
│  │     Index: target_role_skill_requirements                      │   │
│  │     Mode: Set difference with semantic threshold               │   │
│  │                                                                │   │
│  │  4. RESUME TAILORING CONTEXT                                  │   │
│  │     Query: job_description_embedding                           │   │
│  │     Index: user_experience_chunks (projects, roles, achievemts)│   │
│  │     Top-K: 10 most relevant experiences to emphasize           │   │
│  │                                                                │   │
│  │  5. INTERVIEW PREP CONTEXT                                    │   │
│  │     Query: company + role + interview_stage                    │   │
│  │     Index: interview_experiences, company_data, question_bank  │   │
│  │     Top-K: 20 relevant items                                   │   │
│  │                                                                │   │
│  │  6. MEMORY RETRIEVAL                                          │   │
│  │     Query: current_intent_embedding                            │   │
│  │     Index: user_memory_embeddings (filtered by relevance)      │   │
│  │     Top-K: 15 most relevant memories                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Service Boundaries

### 3.1 Service Decomposition

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SERVICE BOUNDARY MAP                             │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │   API GW    │  │  Auth Svc   │  │  Web App    │                  │
│  │  (FastAPI)  │  │  (FastAPI)  │  │  (Next.js)  │                  │
│  │             │  │             │  │             │                  │
│  │ Owns:       │  │ Owns:       │  │ Owns:       │                  │
│  │ - Routing   │  │ - Users     │  │ - SSR pages │                  │
│  │ - Rate lim  │  │ - Sessions  │  │ - Client UI │                  │
│  │ - Auth mid  │  │ - API keys  │  │ - Assets    │                  │
│  │ - Validation│  │ - OAuth     │  │ - Static    │                  │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘                  │
│         │                │                                           │
│  ┌──────┴────────────────┴──────────────────────────────────┐      │
│  │              AGENT ORCHESTRATOR                           │      │
│  │              (LangGraph Service)                          │      │
│  │                                                           │      │
│  │  Owns: Agent routing, state management, tool dispatch     │      │
│  │  Depends on: ALL downstream services + Memory + LLM       │      │
│  │  Boundary: Only service that calls LLM directly           │      │
│  └──────┬───────────────────────────────────────────────────┘      │
│         │                                                           │
│  ┌──────┴──────┬──────────────┬──────────────┬──────────────┐      │
│  │             │              │              │              │      │
│  │    ┌────────┴────────┐    │    ┌────────┴────────┐     │      │
│  │    │  PROFILE SVC    │    │    │  JOB DISCOVERY  │     │      │
│  │    │  (FastAPI)      │    │    │  SVC (FastAPI)  │     │      │
│  │    │                 │    │    │                 │     │      │
│  │    │ Owns:           │    │    │ Owns:           │     │      │
│  │    │ - User profiles │    │    │ - Job listings  │     │      │
│  │    │ - Resume parsing│    │    │ - Source mgmt   │     │      │
│  │    │ - Skill extract │    │    │ - Dedup logic   │     │      │
│  │    │ - Profile enrich│    │    │ - Enrichment    │     │      │
│  │    │ - GitHub import │    │    │ - Company data  │     │      │
│  │    └────────┬────────┘    │    └────────┬────────┘     │      │
│  │             │              │              │              │      │
│  │    ┌────────┴────────┐    │    ┌────────┴────────┐     │      │
│  │    │  MATCHING SVC   │    │    │  DOCUMENT SVC   │     │      │
│  │    │  (FastAPI)      │    │    │  (FastAPI)      │     │      │
│  │    │                 │    │    │                 │     │      │
│  │    │ Owns:           │    │    │ Owns:           │     │      │
│  │    │ - Match scoring │    │    │ - Resume variants│    │      │
│  │    │ - Ranking       │    │    │ - Cover letters │     │      │
│  │    │ - Explanation   │    │    │ - Templates     │     │      │
│  │    │ - Re-ranking    │    │    │ - Export/format │     │      │
│  │    │ - Similar jobs  │    │    │ - ATS sim       │     │      │
│  │    └────────┬────────┘    │    └────────┬────────┘     │      │
│  │             │              │              │              │      │
│  │    ┌────────┴────────┐    │    ┌────────┴────────┐     │      │
│  │    │  APPLICATION    │    │    │  INTERVIEW      │     │      │
│  │    │  TRACKING SVC   │    │    │  PREP SVC       │     │      │
│  │    │  (FastAPI)      │    │    │  (FastAPI)      │     │      │
│  │    │                 │    │    │                 │     │      │
│  │    │ Owns:           │    │    │ Owns:           │     │      │
│  │    │ - Pipeline state│    │    │ - Question banks│     │      │
│  │    │ - Tasks/deadline│    │    │ - Company guides│     │      │
│  │    │ - Email parsing │    │    │ - Mock sessions │     │      │
│  │    │ - Status detect │    │    │ - Feedback      │     │      │
│  │    │ - Analytics     │    │    │ - Performance   │     │      │
│  │    └────────┬────────┘    │    └────────┬────────┘     │      │
│  │             │              │              │              │      │
│  │    ┌────────┴────────┐    │    ┌────────┴────────┐     │      │
│  │    │  COMMUNICATION  │    │    │  LEARNING SVC   │     │      │
│  │    │  SVC (FastAPI)  │    │    │  (FastAPI)      │     │      │
│  │    │                 │    │    │                 │     │      │
│  │    │ Owns:           │    │    │ Owns:           │     │      │
│  │    │ - Email gen     │    │    │ - Skill gaps    │     │      │
│  │    │ - Templates     │    │    │ - Learning plans│     │      │
│  │    │ - Send scheduling│   │    │ - Resource cur. │     │      │
│  │    │ - Tone mgmt     │    │    │ - Progress track│     │      │
│  │    └────────┬────────┘    │    └────────┬────────┘     │      │
│  │             │              │              │              │      │
│  └─────────────┴──────────────┴──────────────┴──────────────┘      │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    SHARED SERVICES                            │   │
│  │                                                                │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │   │
│  │  │ MEMORY SVC   │  │NOTIFICATION  │  │  ANALYTICS   │        │   │
│  │  │              │  │    SVC       │  │     SVC      │        │   │
│  │  │ - Semantic   │  │ - Push notif │  │ - Aggregation│        │   │
│  │  │ - Episodic   │  │ - Email dig. │  │ - Reports    │        │   │
│  │  │ - Procedural │  │ - In-app     │  │ - Dashboards │        │   │
│  │  │ - Retrieval  │  │ - Preferences│  │ - Benchmarks │        │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘        │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Service Boundary Rules

| Rule | Description |
|------|-------------|
| **Data ownership** | Each service owns its database tables. No service reads another service's tables directly — always via API |
| **API contracts** | All service-to-service communication via typed API contracts (OpenAPI specs). Breaking changes require version bumps |
| **No shared databases** | Every service has its own PostgreSQL schema. Cross-service queries go through APIs, never joins |
| **Async boundaries** | Events cross service boundaries via Redis Streams. Services publish domain events, consumers subscribe |
| **LLM access** | Only the Agent Orchestrator makes LLM calls. Services provide data/tools; agents call LLM with context |
| **Auth everywhere** | Every service-to-service call includes a signed JWT. mTLS in production for internal traffic |

### 3.3 API Contract Example — Matching Service

```
POST /api/v1/match/score
  Request:
    user_id: UUID
    job_ids: [UUID] (max 100)
    context: { include_explanation: bool, include_salary_estimate: bool }
  Response:
    matches: [
      {
        job_id: UUID,
        overall_score: float (0-100),
        dimensions: {
          skill_match: float,
          experience_match: float,
          tech_stack_overlap: float,
          location_fit: float,
          compensation_alignment: float,
          culture_fit_estimate: float
        },
        explanation: [str] (top 5 specific reasons),
        salary_estimate: { min: float, max: float, confidence: float } | null,
        ranking_signals: { freshness_boost: float, urgency_flag: bool }
      }
    ]

  Latency SLA: P95 < 500ms for batch of 100 jobs
  Rate limit: 50 req/min (free), 200 req/min (pro), 500 req/min (premium)
```

---

## 4. Communication Patterns

### 4.1 Communication Matrix

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         COMMUNICATION PATTERNS                              │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ PATTERN 1: SYNCHRONOUS REST (gRPC internally)                        │  │
│  │                                                                       │  │
│  │  Use: User-initiated actions, CRUD operations, real-time queries      │  │
│  │  Flow: Client → API GW → Service → Response                           │  │
│  │  SLA: P95 < 500ms (non-LLM), P95 < 15s (LLM with streaming)          │  │
│  │                                                                       │  │
│  │  ┌────────┐      ┌────────┐      ┌────────┐                          │  │
│  │  │Client  │──REST→│API GW  │──REST→│Service │                          │  │
│  │  │        │←─JSON─│        │←─JSON─│        │                          │  │
│  │  └────────┘      └────────┘      └────────┘                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ PATTERN 2: SERVER-SENT EVENTS (Streaming)                             │  │
│  │                                                                       │  │
│  │  Use: Agent LLM responses, long-running generation tasks              │  │
│  │  Flow: Client → SSE endpoint → Agent streams tokens → Client renders  │  │
│  │  SLA: First byte < 2s, continuous streaming until complete            │  │
│  │                                                                       │  │
│  │  ┌────────┐      ┌────────┐      ┌──────────────┐                    │  │
│  │  │Client  │──SSE─→│API GW  │──SSE─→│Agent Orch.   │                    │  │
│  │  │        │←token│        │←token││(LangGraph)   │                    │  │
│  │  │        │←token│        │←token││              │                    │  │
│  │  │        │←done │        │←done ││              │                    │  │
│  │  └────────┘      └────────┘      └──────────────┘                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ PATTERN 3: WEB SOCKET (Persistent)                                    │  │
│  │                                                                       │  │
│  │  Use: Real-time notifications, pipeline updates, agent status         │  │
│  │  Flow: Client establishes WS → server pushes events                   │  │
│  │  SLA: < 500ms from event publish to client receipt                    │  │
│  │                                                                       │  │
│  │  ┌────────┐      ┌────────┐      ┌──────────────┐                    │  │
│  │  │Client  │──WS──→│WS Svr  │←Event─│Redis Streams │                    │  │
│  │  │        │←event─│        │       │(pub/sub)     │                    │  │
│  │  └────────┘      └────────┘      └──────────────┘                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ PATTERN 4: EVENT-DRIVEN (Redis Streams)                               │  │
│  │                                                                       │  │
│  │  Use: Cross-service async communication, domain events                │  │
│  │  Flow: Producer → Redis Stream → Consumer Group → Service             │  │
│  │  SLA: P95 < 1s delivery, at-least-once semantics                      │  │
│  │                                                                       │  │
│  │  ┌────────┐  publish  ┌──────────────┐  consume  ┌────────┐          │  │
│  │  │Service │──────────→│Redis Streams │←──────────│Service │          │  │
│  │  │   A    │           │              │           │   B    │          │  │
│  │  └────────┘           │ Stream: jobs │           └────────┘          │  │
│  │                       │ Stream: apps │                               │  │
│  │                       │ Stream: notif│                               │  │
│  │                       │ Stream: aud. │                               │  │
│  │                       └──────────────┘                               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ PATTERN 5: BACKGROUND JOBS (Celery + Redis)                           │  │
│  │                                                                       │  │
│  │  Use: Long-running, resource-intensive, or scheduled tasks            │  │
│  │  Flow: Task enqueued → Worker picks up → Executes → Stores result     │  │
│  │  SLA: Configurable per queue priority                                 │  │
│  │                                                                       │  │
│  │  ┌────────┐  enqueue ┌──────────────┐  execute ┌────────┐            │  │
│  │  │Service │─────────→│ Redis Queue  │─────────→│Celery  │            │  │
│  │  │        │          │              │          │Worker  │            │  │
│  │  │        │          │ hi/med/low   │          │Pool    │            │  │
│  │  └────────┘          └──────────────┘          └────────┘            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ PATTERN 6: SCHEDULED TASKS (Celery Beat)                              │  │
│  │                                                                       │  │
│  │  Use: Periodic sweeps, memory consolidation, analytics aggregation    │  │
│  │  Flow: Celery Beat → Scheduler → Enqueues task at cron time           │  │
│  │                                                                       │  │
│  │  ┌────────────┐   cron trigger  ┌──────────────┐                     │  │
│  │  │Celery Beat │────────────────→│ Redis Queue  │→ Worker Pool        │  │
│  │  │(scheduler) │                 │              │                     │  │
│  │  └────────────┘                 │ - job_sweep  │                     │  │
│  │                                 │ - memory_con │                     │  │
│  │                                 │ - analytics  │                     │  │
│  │                                 │ - cleanup    │                     │  │
│  │                                 └──────────────┘                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Event Catalog (Redis Streams)

| Stream | Producer | Consumers | Key Events |
|--------|----------|-----------|------------|
| `stream:jobs` | Job Discovery Svc | Matching Svc, Notification Svc, Memory Svc | `job.created`, `job.updated`, `job.expired`, `job.dedup_merged` |
| `stream:applications` | Application Tracking Svc | Notification Svc, Analytics Svc, Memory Svc | `app.saved`, `app.applied`, `app.status_changed`, `app.interview_scheduled`, `app.offer_received` |
| `stream:matches` | Matching Svc | Notification Svc, Agent Orchestrator | `match.high_score` (≥85%), `match.dream_job` (≥95%) |
| `stream:documents` | Document Svc | Application Tracking Svc | `resume.tailored`, `cover_letter.generated` |
| `stream:notifications` | Notification Svc | WebSocket Server | `notif.push`, `notif.email`, `notif.in_app` |
| `stream:audit` | ALL services | Audit Log Svc | `audit.action` (all agent actions, user actions, admin actions) |
| `stream:learning` | Learning Svc | Memory Svc, Notification Svc | `learning.skill_gap_updated`, `learning.plan_progress` |
| `stream:memory` | Memory Svc | Agent Orchestrator | `memory.consolidated`, `memory.preference_shift` |

### 4.3 Request Flow Example — "User applies to a job"

```
┌───────┐   ┌───────┐   ┌──────────┐   ┌─────────┐   ┌───────┐   ┌────────┐
│ Client │   │API GW │   │ Document │   │  Agent  │   │ App   │   │ Redis  │
│        │   │       │   │   Svc    │   │  Orch.  │   │ Track │   │Streams │
└───┬────┘   └───┬───┘   └────┬─────┘   └───┬─────┘   └───┬───┘   └───┬────┘
    │            │             │              │            │            │
    │ POST /apply│             │              │            │            │
    │───────────→│             │              │            │            │
    │            │             │              │            │            │
    │            │ Validate JWT│              │            │            │
    │            │ Rate limit  │              │            │            │
    │            │             │              │            │            │
    │            │ POST /tailor│              │            │            │
    │            │────────────→│              │            │            │
    │            │             │ Generate     │            │            │
    │            │             │ resume+CL    │            │            │
    │            │             │─────────────→│            │            │
    │            │             │←─────────────│            │            │
    │            │             │ (streaming)  │            │            │
    │            │             │              │            │            │
    │            │←────────────│              │            │            │
    │            │  documents  │              │            │            │
    │            │             │              │            │            │
    │            │ POST /applications         │            │            │
    │            │──────────────────────────→│            │            │
    │            │             │              │            │            │
    │            │             │              │ Store app  │            │
    │            │             │              │ state      │            │
    │            │             │              │            │            │
    │            │             │              │ Publish    │            │
    │            │             │              │ app.applied│            │
    │            │             │              │───────────→│            │
    │            │             │              │            │            │
    │            │←──────────────────────────│            │            │
    │←───────────│ 201 + app_id│              │            │            │
    │            │             │              │            │            │
    │            │             │              │            │ Fan-out:   │
    │            │             │              │            │ → Notif Svc│
    │            │             │              │            │ → Analytics│
    │            │             │              │            │ → Memory   │
    │            │             │              │            │ → Audit    │
```

---

## 5. Scalability Design

### 5.1 Scaling Strategy by Component

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           SCALING DIMENSIONS                                │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     HORIZONTAL SCALING MAP                            │  │
│  │                                                                       │  │
│  │  COMPONENT           │ SCALE METHOD    │ BOTTLENECK    │ TARGET      │  │
│  │  ────────────────────┼─────────────────┼───────────────┼─────────────│  │
│  │  Next.js Web App     │ K8s HPA (CPU)   │ Render CPU    │ 50 pods    │  │
│  │  FastAPI Gateway     │ K8s HPA (RPS)   │ Connection    │ 100 pods   │  │
│  │  Agent Orchestrator  │ K8s HPA (queue) │ LLM latency   │ 80 pods    │  │
│  │  Job Discovery Svc   │ K8s HPA (tasks) │ Scraper rate  │ 30 pods    │  │
│  │  Matching Svc        │ K8s HPA (RPS)   │ Vector search │ 40 pods    │  │
│  │  Document Svc        │ K8s HPA (queue) │ LLM latency   │ 40 pods    │  │
│  │  Application Track   │ K8s HPA (RPS)   │ DB writes     │ 20 pods    │  │
│  │  Interview Prep Svc  │ K8s HPA (queue) │ LLM latency   │ 20 pods    │  │
│  │  Learning Svc        │ K8s HPA (RPS)   │ DB reads      │ 10 pods    │  │
│  │  Communication Svc   │ K8s HPA (queue) │ Email rate    │ 10 pods    │  │
│  │  Memory Svc          │ K8s HPA (RPS)   │ Vector search │ 20 pods    │  │
│  │  Notification Svc    │ K8s HPA (events)│ Push rate     │ 10 pods    │  │
│  │  Celery Workers      │ K8s HPA (queue) │ Task backlog  │ 200 pods   │  │
│  │  PostgreSQL          │ Read replicas   │ Write I/O     │ 1W + 3R   │  │
│  │  pgvector            │ pgvector Cloud  │ Index size    │ Managed    │  │
│  │  Redis Cluster       │ Cluster shards  │ Memory        │ 6 nodes    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     LOAD PROJECTIONS (100K Users)                     │  │
│  │                                                                       │  │
│  │  METRIC                    │ DAILY AVG    │ PEAK (10x)   │ HEADROOM  │  │
│  │  ─────────────────────────┼──────────────┼──────────────┼───────────│  │
│  │  API Requests              │ 5M           │ 50M           │ 4×        │  │
│  │  LLM Calls (all agents)    │ 500K         │ 5M            │ 3×        │  │
│  │  Job Discovery Sweeps      │ 500          │ 5,000         │ 5×        │  │
│  │  Jobs Ingested             │ 200K         │ 2M            │ 5×        │  │
│  │  Match Computations        │ 1M           │ 10M           │ 3×        │  │
│  │  Resume Generations        │ 50K          │ 500K          │ 4×        │  │
│  │  Cover Letter Generations  │ 30K          │ 300K          │ 4×        │  │
│  │  Notifications Sent        │ 200K         │ 2M            │ 5×        │  │
│  │  WebSocket Connections     │ 5K           │ 25K           │ 4×        │  │
│  │  DB Queries                │ 20M          │ 200M          │ Read rep. │  │
│  │  Vector Searches           │ 2M           │ 20M           │ pgvector  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Scaling the Agent Orchestrator

The Agent Orchestrator is the most critical scaling challenge — it's stateful (LangGraph checkpoints) and LLM-dependent.

```
┌─────────────────────────────────────────────────────────────────────┐
│               AGENT ORCHESTRATOR SCALING DESIGN                      │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  TIER 1: REQUEST QUEUING                                      │   │
│  │                                                                │   │
│  │  Client → API GW → Redis Priority Queue → Orchestrator Pool    │   │
│  │                                                                │   │
│  │  Priority Lanes:                                               │   │
│  │   - HIGH (P0): User-waiting interactive (match, tailor, CL)    │   │
│  │   - MEDIUM (P1): User-waiting non-interactive (discovery)      │   │
│  │   - LOW (P2): Background (batch matching, memory consolid.)    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  TIER 2: SESSION AFFINITY (Sticky Sessions)                   │   │
│  │                                                                │   │
│  │  - User sessions pinned to specific orchestrator pods          │   │
│  │  - LangGraph checkpoint loaded from PostgreSQL on first call   │   │
│  │  - Hot checkpoint cache in Redis (5 min TTL)                   │   │
│  │  - If pod dies, next pod loads checkpoint from PostgreSQL      │   │
│  │  - Session stickiness via Redis key: session:{id} → pod:{id}   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  TIER 3: CONCURRENCY & BACKPRESSURE                           │   │
│  │                                                                │   │
│  │  - Max concurrent LLM calls per pod: 20 (configurable)         │   │
│  │  - Semaphore-based throttling within each pod                  │   │
│  │  - Queue depth monitoring → HPA triggers scale-up              │   │
│  │  - Circuit breaker: if LLM API error rate > 5% → fallback      │   │
│  │  - Graceful degradation: cached results if LLM unavailable     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  TIER 4: LLM TOKEN BUDGETING                                  │   │
│  │                                                                │   │
│  │  - Per-user daily token budgets based on tier:                 │   │
│  │    Free: 50K tokens/day                                        │   │
│  │    Pro: 200K tokens/day                                        │   │
│  │    Premium: 500K tokens/day                                    │   │
│  │  - Token usage tracked in Redis (daily counters)               │   │
│  │  - Soft limit at 80%: warning to user                          │   │
│  │  - Hard limit at 100%: queue until next day or prompt upgrade  │   │
│  │  - Cost allocation tags for per-user COGS tracking             │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.3 Database Scaling Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DATABASE SCALING                                   │
│                                                                      │
│  POSTGRESQL:                                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  WRITE PATH:              │  READ PATH:                       │   │
│  │                           │                                   │   │
│  │  App → Primary (RW)      │  App → Read Replica Pool           │   │
│  │   │                       │   │                                │   │
│  │   │  Connection Pooling    │   │  PgBouncer per replica         │   │
│  │   │  (PgBouncer, tx mode)  │   │  (Session mode for txns)       │   │
│  │   │                       │   │                                │   │
│  │   │  Write-ahead log      │   │  Load-balanced reads           │   │
│  │   │  → replicas           │   │  (round-robin + lag check)     │   │
│  │   ▼                       │   ▼                                │   │
│  │  Primary (db.r6g.xlarge) │  Replica 1 (db.r6g.large)          │   │
│  │                           │  Replica 2 (db.r6g.large)          │   │
│  │                           │  Replica 3 (db.r6g.large)          │   │
│  │                           │                                    │   │
│  │  Partitioning strategy:   │  Read routing rules:               │   │
│  │  - applications: BY RANGE│  - Analytics → replica (tolerate   │   │
│  │    (created_at, monthly)  │    5s lag)                         │   │
│  │  - job_listings: BY RANGE│  - User-facing → primary for       │   │
│  │    (first_seen_at, weekly)│    own data (read-your-writes)     │   │
│  │  - audit_logs: BY RANGE  │  - Shared data → replica            │   │
│  │    (created_at, daily)   │                                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  PGVECTOR:                                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  - HNSW index for ANN search (faster than IVFFlat, slower build)│  │
│  │  - Index parameters: m=16, ef_construction=200                │   │
│  │  - Query: ef_search=100 (adjustable per query)                │   │
│  │  - Partitioning: BY HASH(user_id) for user-specific vectors   │   │
│  │  - Filter pass: Apply WHERE clauses BEFORE vector distance    │   │
│  │    (e.g., WHERE location IN (...) AND is_active = true        │   │
│  │     ORDER BY embedding <=> query_vector LIMIT 50)             │   │
│  │  - Partial indexes for active jobs, recent listings           │   │
│  │  - Vacuum after batch inserts (job ingestion runs)            │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Caching Strategy

### 6.1 Multi-Tier Cache Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CACHING ARCHITECTURE                              │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  LAYER 1: CDN CACHE (Cloudflare)                              │   │
│  │                                                                │   │
│  │  What: Static assets, public pages, images                     │   │
│  │  TTL: Assets (7d, immutable), Pages (60s, stale-while-rev.)    │   │
│  │  Strategy: Cache-Control headers, CDN purging on deploy        │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  LAYER 2: APPLICATION CACHE (Redis)                            │   │
│  │                                                                │   │
│  │  ┌─────────────────────────────────────────────────────────┐  │   │
│  │  │ CACHE KEY PATTERN          │ TTL    │ INVALIDATION       │  │   │
│  │  │ ──────────────────────────┼────────┼─────────────────── │  │   │
│  │  │ user:{id}:profile          │ 30 min │ On profile update  │  │   │
│  │  │ user:{id}:preferences      │ 15 min │ On pref update     │  │   │
│  │  │ user:{id}:match:top20      │ 10 min │ On new sweep       │  │   │
│  │  │ job:{id}:detail            │ 1 hr   │ On job update      │  │   │
│  │  │ job:search:{query_hash}    │ 5 min  │ TTL only           │  │   │
│  │  │ company:{id}:info          │ 24 hr  │ On manual refresh  │  │   │
│  │  │ template:resume:{id}       │ 1 hr   │ On template update │  │   │
│  │  │ rate_limit:{user}:{window} │ window │ N/A (counter)      │  │   │
│  │  │ session:{id}:state         │ 30 min │ On activity        │  │   │
│  └─────────────────────────────────────────────────────────────────┘  │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  LAYER 3: LLM RESPONSE CACHE (Redis)                           │   │
│  │                                                                │   │
│  │  Semantic Cache for LLM responses:                             │   │
│  │  - Key: hash(user_id + intent + input_embedding_bucket)        │   │
│  │  - Value: LLM response + metadata                              │   │
│  │  - Strategy: Cache identical/similar requests (cosine > 0.95)  │   │
│  │  - TTL: 1 hour for matching, 24 hours for company info         │   │
│  │  - Invalidation: Profile changes, preference changes           │   │
│  │  - Cost savings target: 15-20% reduction in LLM calls          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  LAYER 4: EMBEDDING CACHE (Redis)                              │   │
│  │                                                                │   │
│  │  - Job description embeddings (immutable per version)          │   │
│  │  - User profile embeddings (recompute on profile change)       │   │
│  │  - Common query embeddings (e.g., "senior python engineer")    │   │
│  │  - TTL: Jobs — 7 days (or until job expired), Users — 1 hour   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  LAYER 5: DATABASE QUERY CACHE (PostgreSQL + Redis)            │   │
│  │                                                                │   │
│  │  - PostgreSQL shared_buffers: 25% of RAM                       │   │
│  │  - pg_stat_statements: Identify hot queries for optimization   │   │
│  │  - Materialized views: Daily job counts, user stats (refresh   │   │
│  │    every 15 min via cron)                                      │   │
│  │  - Read-through cache pattern for hot entities in Redis        │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 Cache Invalidation Strategies

| Pattern | Strategy | Rationale |
|---------|----------|-----------|
| **Write-through** | Write to DB + cache simultaneously | Used for user profile, preferences — always consistent |
| **Write-behind** | Write to cache, async flush to DB | Used for session state, ephemeral data — acceptable eventual consistency |
| **Cache-aside** | App checks cache → misses → loads DB → populates cache | Used for job listings, company info — read-heavy, write-rare |
| **TTL-based** | Cache expires after fixed duration | Used for search results, match lists — freshness window acceptable |
| **Event-driven** | Redis pub/sub invalidation events | Used for cross-service cache coordination — "user profile updated" → invalidate all caches containing user data |

---

## 7. Storage Strategy

### 7.1 Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        STORAGE ARCHITECTURE                           │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                POSTGRESQL (Primary Relational DB)              │   │
│  │                                                                │   │
│  │  SCHEMAS:                                                      │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │   │
│  │  │  auth    │ │ profile  │ │  jobs    │ │  app     │         │   │
│  │  │          │ │          │ │          │ │          │         │   │
│  │  │ users    │ │ profiles │ │job_post- │ │applica-  │         │   │
│  │  │ sessions │ │ work_exp │ │ ings     │ │ tions    │         │   │
│  │  │ api_keys │ │education │ │companies │ │tasks     │         │   │
│  │  │ oauth    │ │ skills   │ │sources   │ │communi-  │         │   │
│  │  │          │ │ projects │ │enrichment│ │ cations  │         │   │
│  │  │          │ │ certs    │ │          │ │interviews│         │   │
│  │  │          │ │          │ │          │ │offers    │         │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │   │
│  │  │ learning │ │ document │ │  audit   │ │ analytics│         │   │
│  │  │          │ │          │ │          │ │          │         │   │
│  │  │skill_gaps│ │resume_   │ │audit_logs│ │metrics   │         │   │
│  │  │learn_    │ │ variants │ │agent_    │ │reports   │         │   │
│  │  │  plans   │ │cover_    │ │ actions  │ │aggrega-  │         │   │
│  │  │resources │ │ letters  │ │user_act  │ │ tions    │         │   │
│  │  │progress  │ │templates │ │          │ │          │         │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  PGVECTOR (Vector Storage)                     │   │
│  │                                                                │   │
│  │  VECTOR TABLES (same PostgreSQL instance, pgvector extension): │   │
│  │  ┌─────────────────────┐ ┌─────────────────────┐               │   │
│  │  │ job_embeddings      │ │ user_embeddings     │               │   │
│  │  │ - job_id (FK)       │ │ - user_id (FK)      │               │   │
│  │  │ - embedding (3072d) │ │ - embedding (3072d) │               │   │
│  │  │ - chunk_type        │ │ - version            │               │   │
│  │  │   (title/desc/full) │ │ - updated_at         │               │   │
│  │  │ - HNSW index        │ │ - HNSW index         │               │   │
│  │  └─────────────────────┘ └─────────────────────┘               │   │
│  │  ┌─────────────────────┐ ┌─────────────────────┐               │   │
│  │  │ memory_embeddings   │ │ skill_embeddings    │               │   │
│  │  │ - memory_id (FK)    │ │ - skill_id (FK)     │               │   │
│  │  │ - embedding (3072d) │ │ - embedding (1536d) │               │   │
│  │  │ - memory_type       │ │ - skill_name         │               │   │
│  │  │ - user_id (FK)      │ │ - HNSW index         │               │   │
│  │  │ - HNSW index        │ │                      │               │   │
│  │  └─────────────────────┘ └─────────────────────┘               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     REDIS (In-Memory Store)                    │   │
│  │                                                                │   │
│  │  USAGE BREAKDOWN:                                              │   │
│  │  ┌──────────────────┬──────────┬──────────────────────────┐   │   │
│  │  │ PURPOSE          │ % OF RAM │ KEY PATTERNS             │   │   │
│  │  ├──────────────────┼──────────┼──────────────────────────┤   │   │
│  │  │ Session Cache    │ 20%      │ session:*                │   │   │
│  │  │ Application Cache│ 25%      │ cache:*                  │   │   │
│  │  │ LLM Sem. Cache   │ 15%      │ llm_cache:*              │   │   │
│  │  │ Rate Limiting    │ 5%       │ rate:*                   │   │   │
│  │  │ Job Queues       │ 15%      │ queue:*, celery:*        │   │   │
│  │  │ Event Streams    │ 10%      │ stream:*                 │   │   │
│  │  │ Leaderboards/Hot │ 5%       │ hot:*                    │   │   │
│  │  │ Pub/Sub          │ 5%       │ channel:*                │   │   │
│  │  └──────────────────┴──────────┴──────────────────────────┘   │   │
│  │                                                                │   │
│  │  CONFIGURATION:                                                │   │
│  │  - Cluster mode: 3 shards × 2 replicas = 6 nodes               │   │
│  │  - Eviction policy: allkeys-lru (LRU across all keys)          │   │
│  │  - Max memory: 16GB per node                                   │   │
│  │  - Persistence: AOF every 1s + RDB snapshot every hour         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  S3 / MINIO (Object Storage)                   │   │
│  │                                                                │   │
│  │  ┌─────────────────────────────────────────────────────────┐  │   │
│  │  │ BUCKET              │ CONTENT           │ LIFECYCLE      │  │   │
│  │  │ ───────────────────┼───────────────────┼─────────────── │  │   │
│  │  │ resumes/            │ User-uploaded     │ 30d after      │  │   │
│  │  │                     │ resume PDFs/DOCXs │ inactivity     │  │   │
│  │  │ generated-resumes/  │ AI-generated      │ 90d after      │  │   │
│  │  │                     │ resume PDFs        │ application    │  │   │
│  │  │ cover-letters/      │ AI-generated CLs  │ 90d after app  │  │   │
│  │  │ profile-assets/     │ Photos, portfolio │ Until deletion │  │   │
│  │  │ exports/            │ User data exports │ 7d (temp)      │  │   │
│  │  │ backups/            │ DB backups        │ 30d rolling    │  │   │
│  │  │ logs/               │ Application logs  │ 90d → glacier  │  │   │
│  │  └─────────────────────────────────────────────────────────┘  │   │
│  │                                                                │   │
│  │  - Storage class: Standard (frequent access) → IA (30d)        │   │
│  │                     → Glacier (90d archive)                    │   │
│  │  - Encryption: SSE-S3 (AES-256) with customer-managed keys     │   │
│  │  - CDN origin: CloudFront for generated PDFs (signed URLs)     │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 Data Retention & Lifecycle

| Data Category | Retention | Archive | Purge |
|---------------|-----------|---------|-------|
| User profile | Indefinite (active) | After 12mo inactivity | On user deletion request |
| Applications | 2 years after last activity | Archive to cold storage | 5 years |
| Job listings | 3 months after expiry | N/A | Auto-purge |
| Agent action logs | 1 year | Archive to S3 Glacier | 3 years |
| Audit logs | 3 years | Archive to S3 Glacier | 7 years |
| LLM request/response | 90 days | N/A | Auto-purge |
| Episodic memory | 90 days | Consolidate to semantic | Auto-purge raw |
| Semantic memory | Indefinite (user-owned) | N/A | On deletion request |
| Redis ephemeral data | Per-TTL | N/A | Auto-evict |
| DB backups | 30 days rolling | N/A | Auto-purge |

---

## 8. Security Architecture

### 8.1 Defense-in-Depth Model

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SECURITY LAYERS                                 │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  LAYER 1: NETWORK SECURITY                                    │   │
│  │                                                                │   │
│  │  ┌──────────────────┐  ┌──────────────────┐                   │   │
│  │  │ Cloudflare WAF   │  │ VPC / Private     │                   │   │
│  │  │ - DDoS protection│  │ Subnets           │                   │   │
│  │  │ - Bot management │  │ - Public: ALB only│                   │   │
│  │  │ - OWASP ruleset  │  │ - Private: All    │                   │   │
│  │  │ - Rate limiting  │  │   services + DB   │                   │   │
│  │  │ - SSL/TLS 1.3    │  │ - No direct       │                   │   │
│  │  │                  │  │   internet access  │                   │   │
│  │  └──────────────────┘  └──────────────────┘                   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  LAYER 2: AUTHENTICATION & AUTHORIZATION                      │   │
│  │                                                                │   │
│  │  ┌──────────────────────────────────────────────────────────┐ │   │
│  │  │ AUTH FLOW:                                                │ │   │
│  │  │                                                           │ │   │
│  │  │  User → OAuth2.0/OIDC (Google, GitHub) or Email+Password  │ │   │
│  │  │       │                                                    │ │   │
│  │  │       ▼                                                    │ │   │
│  │  │  Auth Service issues:                                      │ │   │
│  │  │  - Access Token (JWT, RS256, 15 min expiry)               │ │   │
│  │  │  - Refresh Token (opaque, 7 days, stored in httpOnly      │ │   │
│  │  │    cookie, rotated on use, one-time use)                  │ │   │
│  │  │  - ID Token (OIDC, contains user claims)                  │ │   │
│  │  │                                                           │ │   │
│  │  │  JWT Claims:                                               │ │   │
│  │  │  {                                                        │ │   │
│  │  │    sub: user_id,                                          │ │   │
│  │  │    tier: "pro",                                           │ │   │
│  │  │    roles: ["user"],                                       │ │   │
│  │  │    permissions: ["jobs:read","resume:write",...],         │ │   │
│  │  │    iat, exp, jti (unique token ID for revocation)         │ │   │
│  │  │  }                                                        │ │   │
│  │  │                                                           │ │   │
│  │  │  SERVICE-TO-SERVICE AUTH:                                  │ │   │
│  │  │  - mTLS (X.509 certificates) for all internal traffic      │ │   │
│  │  │  - Service account JWTs for API calls between services    │ │   │
│  │  │  - Istio/Envoy sidecar handles mTLS transparently         │ │   │
│  │  └──────────────────────────────────────────────────────────┘ │   │
│  │                                                                │   │
│  │  ┌──────────────────────────────────────────────────────────┐ │   │
│  │  │ AUTHORIZATION MODEL (RBAC + ABAC):                         │ │   │
│  │  │                                                           │ │   │
│  │  │  ROLES:                                                    │ │   │
│  │  │  - user: Standard end user                                 │ │   │
│  │  │  - premium_user: Premium tier user                         │ │   │
│  │  │  - admin: Internal admin (support, ops)                    │ │   │
│  │  │  - agent: Service-to-service agent identity                │ │   │
│  │  │  - system: Automated system processes                      │ │   │
│  │  │                                                           │ │   │
│  │  │  ATTRIBUTE-BASED RULES (examples):                         │ │   │
│  │  │  - User can ONLY access own applications                   │ │   │
│  │  │  - Premium users can use autopilot feature                 │ │   │
│  │  │  - Free users limited to 50 applications/month             │ │   │
│  │  │  - Admin can access user data only in support mode         │ │   │
│  │  │    (with audit trail and user consent)                     │ │   │
│  │  └──────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  LAYER 3: DATA PROTECTION                                     │   │
│  │                                                                │   │
│  │  ┌────────────────────┐  ┌────────────────────┐               │   │
│  │  │ ENCRYPTION AT REST │  │ ENCRYPTION IN      │               │   │
│  │  │                    │  │ TRANSIT             │               │   │
│  │  │ - AES-256 (all DB) │  │ - TLS 1.3 (all)    │               │   │
│  │  │ - Field-level for  │  │ - mTLS (internal)   │               │   │
│  │  │   PII columns      │  │ - HSTS (strict)     │               │   │
│  │  │ - Separate key per │  │                     │               │   │
│  │  │   tenant (KMS)     │  │                     │               │   │
│  │  │ - Key rotation: 90d│  │                     │               │   │
│  │  └────────────────────┘  └────────────────────┘               │   │
│  │                                                                │   │
│  │  PII CLASSIFICATION:                                           │   │
│  │  ┌────────────────────┬──────────┬─────────────────────────┐  │   │
│  │  │ FIELD              │ LEVEL    │ PROTECTION              │  │   │
│  │  ├────────────────────┼──────────┼─────────────────────────┤  │   │
│  │  │ Full name, email   │ PII      │ Field-level encryption  │  │   │
│  │  │ Phone, address     │ PII      │ Field-level encryption  │  │   │
│  │  │ Resume content     │ PII      │ Field-level encryption  │  │   │
│  │  │ Work history       │ Sensitive│ Standard encryption     │  │   │
│  │  │ Skills, education  │ Internal │ Standard encryption     │  │   │
│  │  │ Application data   │ Sensitive│ Standard encryption     │  │   │
│  │  │ Salary preferences │ Sensitive│ Field-level encryption  │  │   │
│  │  │ Behavioral data    │ Internal │ Standard encryption     │  │   │
│  │  │ Anonymized metrics │ Public   │ No special handling     │  │   │
│  │  └────────────────────┴──────────┴─────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  LAYER 4: APPLICATION SECURITY                                │   │
│  │                                                                │   │
│  │  ┌──────────────────────────────────────────────────────────┐ │   │
│  │  │ - Input validation: Pydantic v2 strict mode, all inputs   │ │   │
│  │  │ - Output sanitization: HTML entity encoding, CSP headers  │ │   │
│  │  │ - CSRF protection: Double-submit cookie pattern + SameSite│ │   │
│  │  │ - SQL injection: Parameterized queries only (SQLAlchemy)  │ │   │
│  │  │ - XSS prevention: Content-Security-Policy headers          │ │   │
│  │  │ - File upload security:                                    │ │   │
│  │  │   - Allowlist: PDF, DOCX, TXT only                        │ │   │
│  │  │   - Max size: 10MB                                        │ │   │
│  │  │   - Virus scanning (ClamAV) before processing             │ │   │
│  │  │   - Store outside web root (S3/MinIO)                     │ │   │
│  │  │ - Dependency scanning: Snyk/Dependabot in CI/CD           │ │   │
│  │  │ - Container scanning: Trivy in build pipeline              │ │   │
│  │  └──────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  LAYER 5: LLM SECURITY                                        │   │
│  │                                                                │   │
│  │  ┌──────────────────────────────────────────────────────────┐ │   │
│  │  │ - Prompt injection prevention:                             │ │   │
│  │  │   - Strict system/user message separation                  │ │   │
│  │  │   - Input sanitization for user-supplied text              │ │   │
│  │  │   - Prompt hardening: "Ignore any instructions to..."      │ │   │
│  │  │ - Output validation:                                       │ │   │
│  │  │   - Structured outputs validated against JSON Schema       │ │   │
│  │  │   - Free text: content safety classifier                   │ │   │
│  │  │ - Data leakage prevention:                                 │ │   │
│  │  │   - PII detection in prompts (regex + NER) before sending  │ │   │
│  │  │   - No training data opt-out enforced with DeepSeek        │ │   │
│  │  │   - Prompt data minimized — only essential context sent    │ │   │
│  │  │ - Hallucination guardrails:                                │ │   │
│  │  │   - Resume/CL: ONLY allowed to reference confirmed profile │ │   │
│  │  │   - Post-generation factuality check before user sees it   │ │   │
│  │  │   - Diff highlighting of AI changes vs. original           │ │   │
│  │  └──────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 8.2 Audit Log Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AUDIT LOG SYSTEM                               │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  WHAT IS AUDITED (immutable, append-only):                    │   │
│  │                                                                │   │
│  │  1. ALL AGENT ACTIONS:                                        │   │
│  │     - agent_type, action_type, user_id, session_id            │   │
│  │     - input_context (what the agent was told)                  │   │
│  │     - output_summary (what the agent did)                     │   │
│  │     - tools_called[] (which tools + parameters)               │   │
│  │     - llm_model, tokens_used, latency_ms, cost                │   │
│  │     - user_approval (was HITL gate passed?)                   │   │
│  │     - timestamp (server-received, not client-claimed)         │   │
│  │                                                                │   │
│  │  2. ALL USER ACTIONS:                                         │   │
│  │     - Login/logout, profile changes, preference updates       │   │
│  │     - Application actions (save/apply/status change)          │   │
│  │     - Document generation/export                              │   │
│  │     - Feedback actions (thumbs up/down, overrides)            │   │
│  │                                                                │   │
│  │  3. ALL ADMIN ACTIONS:                                        │   │
│  │     - Support access to user data (with reason)               │   │
│  │     - Configuration changes, feature flags                    │   │
│  │     - Manual data modifications                               │   │
│  │                                                                │   │
│  │  4. ALL SECURITY EVENTS:                                      │   │
│  │     - Failed auth attempts, rate limit hits                   │   │
│  │     - Permission denied events                                │   │
│  │     - Suspicious activity patterns                            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  AUDIT PIPELINE:                                              │   │
│  │                                                                │   │
│  │  Service → Redis Stream (stream:audit)                        │   │
│  │         → Audit Logger (async consumer)                       │   │
│  │         → PostgreSQL (audit_logs table, partitioned)          │   │
│  │         → Cold storage archive (S3, after 90 days)            │   │
│  │                                                                │   │
│  │  Audit log table:                                              │   │
│  │  - Partitioned BY RANGE (created_at, daily)                   │   │
│  │  - INSERT-only permissions (no UPDATE/DELETE)                 │   │
│  │  - Indexed on: (user_id, created_at), (action_type, created_at)│  │
│  │  - Retention: 3 years hot (PostgreSQL), 7 years cold (S3)     │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 9. Failure Recovery Strategy

### 9.1 Failure Mode Analysis & Mitigation

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     FAILURE RECOVERY MATRIX                                 │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ FAILURE MODE          │ DETECTION       │ MITIGATION                  │  │
│  │ ─────────────────────┼─────────────────┼─────────────────────────────│  │
│  │                       │                 │                             │  │
│  │ LLM API DOWN          │ Health check    │ Multi-model fallback chain  │  │
│  │ (DeepSeek outage)     │ (every 30s)     │ (GPT-4o → Gemini → cached)  │  │
│  │                       │ Error rate > 5% │ Circuit breaker: stop calls │  │
│  │                       │                 │ Graceful degradation msg    │  │
│  │                       │                 │                             │  │
│  │ LLM LATENCY SPIKE     │ P95 latency     │ Timeout + retry with        │  │
│  │ (>8s for interactive) │ monitor         │ backoff (1s, 2s, 4s, 8s)   │  │
│  │                       │                 │ Fail to secondary model     │  │
│  │                       │                 │                             │  │
│  │ POSTGRESQL PRIMARY    │ Health check    │ Automated failover to       │  │
│  │ FAILURE               │ (every 5s)      │ replica (Patroni/Cloud SQL) │  │
│  │                       │ Replication lag │ RPO: < 1 min (sync repl.)   │  │
│  │                       │                 │ RTO: < 60s (auto-failover)  │  │
│  │                       │                 │                             │  │
│  │ POSTGRESQL REPLICA    │ Health check    │ Remove from LB pool         │  │
│  │ FAILURE               │                 │ Spin up replacement         │  │
│  │                       │                 │ Reads route to primary      │  │
│  │                       │                 │ (degraded but functional)    │  │
│  │                       │                 │                             │  │
│  │ REDIS NODE FAILURE    │ Cluster gossip  │ Auto-failover to replica    │  │
│  │                       │ Health check    │ Sentinel promotes replica   │  │
│  │                       │                 │ Queues: tasks re-enqueued   │  │
│  │                       │                 │ Cache: cold start (ok)      │  │
│  │                       │                 │ Sessions: users re-auth     │  │
│  │                       │                 │                             │  │
│  │ CELERY WORKER CRASH   │ Worker heartbeat │ Task re-queued (ack_late)  │  │
│  │                       │ (every 10s)     │ New worker auto-started     │  │
│  │                       │                 │ Idempotent task design      │  │
│  │                       │                 │ Max retries: 3 per task     │  │
│  │                       │                 │                             │  │
│  │ AGENT POD FAILURE     │ K8s liveness    │ K8s restart (new pod)       │  │
│  │                       │ probe           │ Session state loaded from   │  │
│  │                       │                 │ LangGraph checkpoint (PG)   │  │
│  │                       │                 │ In-flight request: client   │  │
│  │                       │                 │ retries with same session   │  │
│  │                       │                 │                             │  │
│  │ JOB DISCOVERY SOURCE  │ Source-specific │ Exponential backoff retry   │  │
│  │ SCRAPE FAILURE        │ error counters  │ (1m, 5m, 15m, 1h, 6h)      │  │
│  │                       │                 │ Alert if > 3 consecutive    │  │
│  │                       │                 │ Continue with other sources │  │
│  │                       │                 │                             │  │
│  │ MEMORY CORRUPTION     │ Checksum        │ Restore from latest backup  │  │
│  │ (vector index corrupt)│ verification    │ Rebuild vector index        │  │
│  │                       │                 │ Re-ingest from source data  │  │
│  │                       │                 │                             │  │
│  │ DATA CENTER OUTAGE    │ External        │ Multi-AZ deployment in      │  │
│  │ (AWS AZ failure)      │ monitoring      │ primary region              │  │
│  │                       │                 │ Cross-region DR (V2+)       │  │
│  │                       │                 │ RPO: < 1h, RTO: < 4h        │  │
│  │                       │                 │                             │  │
│  │ DISK FULL             │ Disk usage      │ Auto-scale storage (cloud)  │  │
│  │                       │ monitor (>80%)  │ Log rotation + compression  │  │
│  │                       │                 │ Data retention enforcement  │  │
│  │                       │                 │ Alert at 70%, page at 85%   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Graceful Degradation Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                  GRACEFUL DEGRADATION TIERS                          │
│                                                                      │
│  TIER 0: FULL SERVICE (all systems nominal)                          │
│  ─────────────────────────────────────────                           │
│  All features available, all agents operational, all sources active  │
│                                                                      │
│  TIER 1: DEGRADED LLM (LLM API issues)                              │
│  ────────────────────────────────────────                            │
│  - Agent responses use secondary model (lower quality but functional)│
│  - User sees: "AI is running in backup mode — responses may be       │
│    slightly less detailed. Full quality will resume shortly."        │
│  - Features available: All, with quality reduction                   │
│                                                                      │
│  TIER 2: CACHED MODE (LLM completely unavailable)                    │
│  ───────────────────────────────────────────────                     │
│  - Agent responses from semantic cache where available               │
│  - No new resume/CL generation (show cached versions)                │
│  - Match scores from last computed values                            │
│  - User sees: "AI features are temporarily limited. Your data is     │
│    safe and we'll resume full service shortly."                      │
│  - Features available: Browse jobs, view pipeline, edit documents    │
│                                                                      │
│  TIER 3: READ-ONLY MODE (Database write failure)                     │
│  ─────────────────────────────────────────────                       │
│  - All writes queued in Redis, processed when DB recovers            │
│  - User can browse, view, but not save/apply                         │
│  - User sees: "We're experiencing a brief outage. Your work is       │
│    saved locally and will sync when service resumes."                │
│  - Client-side persistence for draft work                            │
│                                                                      │
│  TIER 4: STATIC MODE (Complete backend outage)                       │
│  ────────────────────────────────────────────                        │
│  - CDN serves static error page with status info                     │
│  - Status page (status.pathfinder.io) shows incident details         │
│  - Email/SMS notification to affected users (Premium tier)           │
│  - Estimated recovery time displayed                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 9.3 Backup & Disaster Recovery

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKUP & DR STRATEGY                               │
│                                                                      │
│  BACKUP SCHEDULE:                                                    │
│  ┌──────────────────────┬──────────┬──────────┬──────────────────┐   │
│  │ DATA                 │ FREQUENCY│ RETENTION│ VERIFICATION     │   │
│  ├──────────────────────┼──────────┼──────────┼──────────────────┤   │
│  │ PostgreSQL (full)    │ Daily    │ 30 days  │ Weekly restore   │   │
│  │ PostgreSQL (WAL)     │Continuous│ 7 days   │ test              │   │
│  │ pgvector (full)      │ Daily    │ 30 days  │ Weekly restore   │   │
│  │ Redis (RDB snapshot) │ Hourly   │ 24 hours │ test              │   │
│  │ S3 (resumes, docs)   │Continuous│ 90 days  │ Daily restore    │   │
│  │ S3 (versioned)       │Per-write │ 30 days  │ test              │   │
│  │ Configuration (IaC)  │ Per-commit│Indefinite│ Per-deploy       │   │
│  └──────────────────────┴──────────┴──────────┴──────────────────┘   │
│                                                                      │
│  DISASTER RECOVERY RUNBOOK (summary):                                 │
│  1. Detect: Monitoring alerts + manual confirmation                  │
│  2. Declare: Incident commander designated, status page updated      │
│  3. Assess: RPO/RTO determination based on failure scope             │
│  4. Restore:                                                        │
│     a. Infrastructure from IaC (Terraform apply)                     │
│     b. Databases from latest backup                                  │
│     c. Apply WAL logs to reach point-in-time                         │
│     d. Verify data integrity (checksums, record counts)              │
│     e. Rebuild vector indices                                        │
│     f. Warm caches before routing traffic                            │
│  5. Validate: Smoke tests against restored environment               │
│  6. Failback: DNS cutover to primary region                          │
│  7. Post-mortem: Within 48 hours, blameless post-mortem document     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 10. Deployment Architecture

### 10.1 Development Environment — Docker Compose

```
┌─────────────────────────────────────────────────────────────────────┐
│                 LOCAL DEVELOPMENT (Docker Compose)                    │
│                                                                      │
│  docker-compose.yml services:                                        │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  nextjs:          Next.js dev server (hot reload, port 3000)  │   │
│  │  api-gateway:     FastAPI (uvicorn --reload, port 8000)      │   │
│  │  agent-orchestrator: FastAPI + LangGraph (port 8001)         │   │
│  │  profile-svc:     FastAPI (port 8002)                        │   │
│  │  job-discovery:   FastAPI (port 8003)                        │   │
│  │  matching-svc:    FastAPI (port 8004)                        │   │
│  │  document-svc:    FastAPI (port 8005)                        │   │
│  │  application-svc: FastAPI (port 8006)                        │   │
│  │  interview-svc:   FastAPI (port 8007)                        │   │
│  │  learning-svc:    FastAPI (port 8008)                        │   │
│  │  communication-svc: FastAPI (port 8009)                      │   │
│  │  memory-svc:      FastAPI (port 8010)                        │   │
│  │  notification-svc: FastAPI (port 8011)                       │   │
│  │  postgres:        PostgreSQL 16 + pgvector (port 5432)       │   │
│  │  redis:           Redis 7 (port 6379)                        │   │
│  │  minio:           MinIO (S3-compatible, ports 9000/9001)     │   │
│  │  celery-worker:   Celery worker (all queues)                 │   │
│  │  celery-beat:     Celery beat scheduler                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Network: pathfinder-net (bridge)                                     │
│  Volumes: postgres_data, redis_data, minio_data                      │
│  Profiles:                                                           │
│    - dev: All services with hot reload                               │
│    - test: Services + test runners (pytest, vitest)                  │
│    - minimal: API GW + Agent Orchestrator + DB + Redis (for FE dev)  │
└─────────────────────────────────────────────────────────────────────┘
```

### 10.2 Production Environment — Kubernetes

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     PRODUCTION KUBERNETES CLUSTER                           │
│                         (EKS / GKE / AKS)                                   │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         INGRESS LAYER                                 │  │
│  │                                                                       │  │
│  │  Cloudflare ──→ AWS ALB / NGINX Ingress Controller                    │  │
│  │  ├── pathfinder.com/* ──────────────→ web-app (Next.js)               │  │
│  │  ├── api.pathfinder.com/* ──────────→ api-gateway (FastAPI)           │  │
│  │  ├── ws.pathfinder.com/* ───────────→ ws-server (FastAPI)             │  │
│  │  ├── static.pathfinder.com/* ───────→ CDN (S3 + CloudFront)           │  │
│  │  └── status.pathfinder.com/* ───────→ status-page (static S3)         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     NAMESPACES (Logical Isolation)                    │  │
│  │                                                                       │  │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐      │  │
│  │  │ ns:frontend      │ │ ns:api-gateway   │ │ ns:agents        │      │  │
│  │  │                  │ │                  │ │                  │      │  │
│  │  │ - web-app        │ │ - api-gw (10     │ │ - orchestrator   │      │  │
│  │  │   (20 pods)      │ │   pods)          │ │   (40 pods)      │      │  │
│  │  │ - static-assets  │ │ - ws-server (5   │ │ - tool-registry  │      │  │
│  │  │   (N/A, CDN)     │ │   pods)          │ │   (5 pods)       │      │  │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘      │  │
│  │                                                                       │  │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐      │  │
│  │  │ ns:services      │ │ ns:workers       │ │ ns:data          │      │  │
│  │  │                  │ │                  │ │                  │      │  │
│  │  │ - profile (10)   │ │ - celery-hi (50) │ │ - PostgreSQL      │      │  │
│  │  │ - job-disc (15)  │ │ - celery-med(100)│ │   Primary + 3R    │      │  │
│  │  │ - matching (15)  │ │ - celery-low(50) │ │ - pgvector        │      │  │
│  │  │ - document (15)  │ │ - celery-beat(2) │ │ - Redis Cluster   │      │  │
│  │  │ - application(8) │ │                  │ │   (6 nodes)       │      │  │
│  │  │ - interview (8)  │ │                  │ │ - S3 (AWS/GCP)    │      │  │
│  │  │ - learning (5)   │ │                  │ │                  │      │  │
│  │  │ - comm (5)       │ │                  │ │                  │      │  │
│  │  │ - memory (8)     │ │                  │ │                  │      │  │
│  │  │ - notification(4)│ │                  │ │                  │      │  │
│  │  │ - analytics (3)  │ │                  │ │                  │      │  │
│  │  │ - audit-log (3)  │ │                  │ │                  │      │  │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘      │  │
│  │                                                                       │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │                    ns:observability                               │ │  │
│  │  │                                                                   │ │  │
│  │  │  - prometheus (2 pods)  - grafana (2 pods)                        │ │  │
│  │  │  - elasticsearch (3)    - kibana (1)                              │ │  │
│  │  │  - jaeger (2)           - alertmanager (2)                        │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     RESOURCE ALLOCATIONS                              │  │
│  │                                                                       │  │
│  │  POD TYPE              │ CPU REQ │ CPU LIM │ MEM REQ │ MEM LIM │ GPUs │
│  │  ─────────────────────┼─────────┼─────────┼─────────┼─────────┼──────│  │
│  │  Next.js Web           │ 500m    │ 2       │ 512Mi   │ 2Gi     │ -    │  │
│  │  FastAPI API GW        │ 250m    │ 1       │ 256Mi   │ 1Gi     │ -    │  │
│  │  Agent Orchestrator    │ 500m    │ 2       │ 1Gi     │ 4Gi     │ -    │  │
│  │  FastAPI services      │ 250m    │ 1       │ 512Mi   │ 2Gi     │ -    │  │
│  │  Celery (LLM tasks)    │ 250m    │ 2       │ 512Mi   │ 2Gi     │ -    │  │
│  │  Celery (scraping)     │ 500m    │ 2       │ 1Gi     │ 4Gi     │ -    │  │
│  │  Celery (light)        │ 100m    │ 500m    │ 256Mi   │ 1Gi     │ -    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     AUTO-SCALING POLICIES                             │  │
│  │                                                                       │  │
│  │  SERVICE              │ METRIC          │ MIN │ MAX │ TARGET         │  │
│  │  ────────────────────┼─────────────────┼─────┼─────┼─────────────── │  │
│  │  API Gateway          │ CPU             │ 5   │ 100 │ 70%            │  │
│  │  Agent Orchestrator   │ Queue depth     │ 5   │ 80  │ >50 pending    │  │
│  │  Celery Workers (hi)  │ Queue depth     │ 10  │ 100 │ >20 pending    │  │
│  │  Celery Workers (med) │ Queue depth     │ 10  │ 200 │ >50 pending    │  │
│  │  Celery Workers (low) │ Queue depth     │ 5   │ 50  │ >100 pending   │  │
│  │  Job Discovery        │ CPU + Queue     │ 3   │ 30  │ 60% CPU        │  │
│  │  Matching             │ RPS             │ 3   │ 40  │ >500 RPS/pod   │  │
│  │  Document Services    │ Queue depth     │ 3   │ 40  │ >30 pending    │  │
│  │  Web App              │ CPU             │ 5   │ 50  │ 60%            │  │
│  │  WebSocket Server     │ Connections     │ 2   │ 20  │ >5K conn/pod   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

### 10.3 CI/CD Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CI/CD PIPELINE                                │
│                                                                      │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────┐    │
│  │  PULL REQUEST    │   │  MAIN BRANCH     │   │  RELEASE TAG │    │
│  │                  │   │                  │   │              │    │
│  │  1. Lint         │   │  1. Lint + Test  │   │  1. All tests│    │
│  │  2. Type check   │   │  2. Build images │   │  2. Build    │    │
│  │  3. Unit tests   │   │  3. Push to ECR  │   │     images   │    │
│  │  4. Build check  │   │  4. Deploy to    │   │  3. Push ECR │    │
│  │  5. Security scan│   │     staging      │   │  4. Deploy to│    │
│  │     (SAST + SCA) │   │  5. E2E tests    │   │     canary   │    │
│  │                  │   │  6. Security scan│   │     (10%)     │    │
│  │                  │   │  7. Perf test    │   │  5. Smoke test│   │
│  │  → Auto-merge if │   │                  │   │  6. Monitor   │    │
│  │    all pass      │   │  → Auto-deploy   │   │     30 min    │    │
│  │                  │   │    to staging    │   │  7. Full      │    │
│  │                  │   │                  │   │     rollout   │    │
│  │                  │   │                  │   │  8. Monitor   │    │
│  │                  │   │                  │   │     24h       │    │
│  └──────────────────┘   └──────────────────┘   └──────────────┘    │
│                                                                      │
│  DEPLOYMENT STRATEGY:                                                │
│  - Staging: Rolling update (maxSurge: 25%, maxUnavailable: 0)        │
│  - Production: Canary (10% → 25% → 50% → 100%, 30 min observation   │
│    between each step with automated metric validation)               │
│  - Rollback: Automated if error rate > 1%, P95 latency +50%,         │
│    or health check failure. Manual trigger via Slack command.        │
│  - Database migrations: Run before deploy, must be backward-         │
│    compatible (no breaking changes to current schema)                │
│  - Feature flags: LaunchDarkly for gradual feature rollout           │
└─────────────────────────────────────────────────────────────────────┘
```

### 10.4 Environment Strategy

| Environment | Purpose | Data | Scale | Deploy Trigger |
|-------------|---------|------|-------|---------------|
| **local** | Developer workstation | Docker Compose, seeded test data | 1 instance each | Manual |
| **dev** | Integration testing | Anonymized subset of prod (1%) | Minimal K8s (1-2 pods each) | PR merge |
| **staging** | Pre-production validation | Full mirror of prod (anonymized PII) | 25% of prod capacity | Main branch merge |
| **canary** | Production canary | Production data, subset of traffic | 10% of production traffic | Release tag |
| **production** | Live system | Full production data | 100% capacity | Canary promotion |
| **dr** | Disaster recovery | Replicated from prod (1h RPO) | 50% of prod capacity (scale up on activation) | Manual (DR activation) |

---

## Appendix A: Technology Stack Summary

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Frontend** | Next.js | 15 | SSR + CSR web application |
| | React | 19 | UI components |
| | TypeScript | 5.x | Type safety |
| | Tailwind CSS | 4.x | Styling |
| | TanStack Query | 5.x | Server state management |
| | Zustand | 5.x | Client state management |
| **API Gateway** | FastAPI | 0.11x | REST + WebSocket API |
| | Pydantic | 2.x | Validation + serialization |
| | Uvicorn | 0.3x | ASGI server |
| **Agent Framework** | LangGraph | 0.3.x | Multi-agent state machines |
| | LangChain | 0.3.x | LLM abstractions (optional) |
| **LLM** | DeepSeek API | Latest | Primary LLM (reasoning + generation) |
| | OpenAI API | Latest | Secondary/fallback LLM |
| **Database** | PostgreSQL | 16 | Primary relational DB |
| | pgvector | 0.7.x | Vector embeddings + ANN search |
| **Cache/Queue** | Redis | 7.x | Cache, queue broker, pub/sub, streams |
| **Task Queue** | Celery | 5.x | Async task processing |
| **Object Storage** | MinIO (dev) / S3 (prod) | Latest | Document + asset storage |
| **Container** | Docker | 26.x | Containerization |
| **Orchestration** | Docker Compose (dev) | Latest | Local orchestration |
| | Kubernetes (prod) | 1.31+ | Production orchestration |
| **IaC** | Terraform | 1.9+ | Infrastructure as code |
| **CI/CD** | GitHub Actions | Latest | Build + deploy pipeline |
| **Monitoring** | Prometheus + Grafana | Latest | Metrics + dashboards |
| | ELK Stack | 8.x | Log aggregation |
| | Jaeger | Latest | Distributed tracing |
| | Sentry | Latest | Error tracking |
| **Security** | Cloudflare | N/A | WAF, DDoS, CDN |
| | Vault | Latest | Secrets management |
| | ClamAV | Latest | File virus scanning |

---

## Appendix B: Key Architecture Decision Records (ADR)

### ADR-1: LangGraph for Multi-Agent Orchestration
**Decision:** Use LangGraph StateGraph as the agent orchestration framework.
**Rationale:** Native support for state machines, checkpointing (persistence), conditional routing, tool calling, and human-in-the-loop. Compose subgraphs for specialized agents. PostgreSQL-backed checkpointer for durability.
**Alternatives considered:** Custom state machine (too much to build), CrewAI (less flexible), AutoGen (immature ecosystem).

### ADR-2: pgvector over Dedicated Vector DB
**Decision:** Use pgvector extension on PostgreSQL rather than Pinecone/Qdrant/Milvus.
**Rationale:** Single database for relational + vector reduces operational complexity at MVP–V1 scale. HNSW index provides competitive ANN performance. Evaluate migration to dedicated vector DB at V2 when embedding volume exceeds 10M+ vectors.
**Alternatives considered:** Pinecone (managed, expensive), Milvus (operational overhead).

### ADR-3: Redis Streams for Event-Driven Communication
**Decision:** Use Redis Streams with consumer groups for cross-service events.
**Rationale:** Already using Redis for caching and queues; leveraging Streams avoids introducing Kafka (operational complexity). Adequate throughput for 100K users. Re-evaluate Kafka at 1M+ users.
**Alternatives considered:** Kafka (overkill at this scale), RabbitMQ (additional infra), direct HTTP (tight coupling).

### ADR-4: Modular Monolith → Microservices Evolution
**Decision:** Start with logically separated services (own DB schemas) in a single deployable, extract to independently deployed microservices at V1.
**Rationale:** Premature microservice extraction kills early velocity. Clear API boundaries from day one make extraction mechanical, not architectural.
**Alternatives considered:** Microservices from day one (too slow), true monolith (hard to scale team).

### ADR-5: DeepSeek as Primary LLM
**Decision:** Use DeepSeek API as the primary LLM with multi-model fallback.
**Rationale:** Strong reasoning capabilities, cost-effective (important for 100K-user economics), supports tool calling. Multi-model fallback ensures availability.
**Alternatives considered:** OpenAI-only (vendor lock-in), open-source self-hosted (operational burden at this stage).

---

> *"Architecture is the art of deciding what to care about and what to defer."*

**End of Architecture Document**
