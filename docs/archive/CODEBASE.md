# Pathfinder — Production Codebase Architecture

**Document Version:** 1.0
**Date:** 2026-06-17
**Role:** Principal Software Architect
**Stack:** Python 3.12+ / FastAPI / LangGraph / PostgreSQL / Redis
**Classification:** Confidential — Internal

---

## Table of Contents

1. [Architecture Philosophy](#1-architecture-philosophy)
2. [Top-Level Folder Structure](#2-top-level-folder-structure)
3. [Layer Architecture](#3-layer-architecture)
4. [Domain Design](#4-domain-design)
5. [Module Boundaries](#5-module-boundaries)
6. [Naming Conventions](#6-naming-conventions)
7. [Design Patterns](#7-design-patterns)
8. [Dependency Injection](#8-dependency-injection)
9. [Coding Standards](#9-coding-standards)
10. [Test Architecture](#10-test-architecture)
11. [Configuration Management](#11-configuration-management)
12. [Package & Import Rules](#12-package--import-rules)

---

## 1. Architecture Philosophy

### 1.1 Core Principles

| Principle | Rule |
|-----------|------|
| **Domain over Framework** | Business logic never imports FastAPI, LangGraph, or database drivers. Domain is pure Python. |
| **Ports & Adapters** | Every external dependency (DB, LLM, email, file storage) sits behind an interface defined by the domain. |
| **Dependency Inversion** | High-level modules (domain) never depend on low-level modules (infrastructure). Both depend on abstractions. |
| **Explicit over Implicit** | Dependencies are constructor-injected. No global state. No service locators. No magic imports. |
| **Testability First** | Every component can be unit-tested with mocks for its dependencies. Integration tests verify adapter implementations. |
| **One Domain, One Module** | Each bounded context is a top-level package. Contexts communicate through well-defined interfaces, never through shared database tables. |

### 1.2 Dependency Rule

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DEPENDENCY DIRECTION                                │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        DEPENDS ON ▼                                  │    │
│  │                                                                      │    │
│  │  ┌──────────────────────────────────────────────────────────────┐   │    │
│  │  │                   PRESENTATION LAYER                          │   │    │
│  │  │  (FastAPI routes, middleware, WebSocket handlers, SSE)        │   │    │
│  │  │  Knows about: Application layer only                          │   │    │
│  │  └──────────────────────────┬───────────────────────────────────┘   │    │
│  │                             │                                       │    │
│  │                             ▼                                       │    │
│  │  ┌──────────────────────────────────────────────────────────────┐   │    │
│  │  │                   APPLICATION LAYER                           │   │    │
│  │  │  (Use cases, orchestration, DTOs, command/query handlers)     │   │    │
│  │  │  Knows about: Domain layer + Port interfaces                  │   │    │
│  │  └──────────────────────────┬───────────────────────────────────┘   │    │
│  │                             │                                       │    │
│  │                             ▼                                       │    │
│  │  ┌──────────────────────────────────────────────────────────────┐   │    │
│  │  │                      DOMAIN LAYER                             │   │    │
│  │  │  (Entities, value objects, aggregates, domain services,       │   │    │
│  │  │   repository interfaces, port interfaces, domain events)      │   │    │
│  │  │  Knows about: NOTHING external. Pure Python.                  │   │    │
│  │  └──────────────────────────┬───────────────────────────────────┘   │    │
│  │                             │                                       │    │
│  │                             ▼                                       │    │
│  │  ┌──────────────────────────────────────────────────────────────┐   │    │
│  │  │                  INFRASTRUCTURE LAYER                         │   │    │
│  │  │  (Repository implementations, DB adapters, LLM adapters,      │   │    │
│  │  │   Redis adapters, S3 adapters, email adapters, external APIs) │   │    │
│  │  │  Knows about: Domain interfaces + External libraries          │   │    │
│  │  └──────────────────────────────────────────────────────────────┘   │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  CRITICAL RULE: The DOMAIN LAYER has zero imports from:                      │
│  · FastAPI / starlette                                                       │
│  · SQLAlchemy / asyncpg / psycopg                                            │
│  · Redis / aioredis                                                          │
│  · LangGraph / LangChain                                                     │
│  · boto3 / botocore                                                          │
│  · Any HTTP or network library                                               │
│  · Any file I/O beyond standard library                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Top-Level Folder Structure

```
pathfinder/
│
├── pyproject.toml                     # Project metadata, dependencies, tool config
├── poetry.lock                        # Locked dependencies
├── Dockerfile                         # Production container
├── Dockerfile.dev                     # Development container with hot-reload
├── docker-compose.yml                 # Local development stack
├── docker-compose.test.yml            # CI test stack
├── Makefile                           # Common commands (lint, test, migrate, etc.)
├── .env.example                       # Environment variable template
├── .env.test                          # Test environment variables
├── alembic.ini                        # Migration config
├── .editorconfig                      # Editor consistency
├── .gitignore
│
├── alembic/                           # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/                      # Migration files
│       ├── 001_initial_tenants.py
│       ├── 002_users_and_auth.py
│       ├── 003_profiles_and_resumes.py
│       └── ...
│
├── scripts/                           # Operational scripts
│   ├── seed_dev_data.py               # Development seed data
│   ├── run_consolidation.py           # Manual memory consolidation trigger
│   └── export_user_data.py            # GDPR data export tool
│
├── tests/                             # ALL tests (mirrors src/ structure)
│   ├── conftest.py                    # Root fixtures: DB, Redis, HTTP client
│   ├── unit/                          # Domain logic, use cases, entities
│   │   ├── domain/
│   │   │   ├── identity/
│   │   │   ├── profile/
│   │   │   ├── jobs/
│   │   │   ├── applications/
│   │   │   ├── documents/
│   │   │   ├── interviews/
│   │   │   ├── matching/
│   │   │   ├── agent_orchestration/
│   │   │   └── memory/
│   │   └── application/
│   ├── integration/                   # Repository implementations, adapters
│   │   ├── infrastructure/
│   │   │   ├── persistence/
│   │   │   ├── llm/
│   │   │   ├── cache/
│   │   │   └── storage/
│   │   └── api/
│   ├── e2e/                           # Full API flow tests
│   │   ├── test_auth_flow.py
│   │   ├── test_job_search_flow.py
│   │   ├── test_application_flow.py
│   │   └── test_agent_execution_flow.py
│   └── fixtures/                      # Test data factories, seed data
│       ├── user_fixtures.py
│       ├── job_fixtures.py
│       └── agent_fixtures.py
│
└── src/                               # APPLICATION SOURCE
    ├── __init__.py
    │
    ├── shared/                        # Cross-cutting, domain-agnostic
    │   ├── __init__.py
    │   ├── domain/                    # Shared domain primitives
    │   │   ├── __init__.py
    │   │   ├── base_entity.py         # Abstract Entity base class
    │   │   ├── base_value_object.py   # Immutable ValueObject base
    │   │   ├── base_aggregate.py      # AggregateRoot base
    │   │   ├── base_domain_event.py   # DomainEvent base
    │   │   ├── base_repository.py     # Abstract Repository [T] generic
    │   │   ├── base_specification.py  # Specification pattern base
    │   │   ├── identifiers.py         # UUID, Slug, TenantId, UserId
    │   │   ├── money.py               # Money value object (amount + currency)
    │   │   ├── date_range.py          # DateRange value object
    │   │   ├── location.py            # Location value object
    │   │   ├── proficiency.py         # Proficiency enum + value object
    │   │   ├── result.py              # Result[T] monad (success/failure)
    │   │   └── exceptions.py          # DomainError, ValidationError, NotFoundError
    │   │
    │   ├── application/              # Shared application concerns
    │   │   ├── __init__.py
    │   │   ├── ports/                 # Interfaces defined by application layer
    │   │   │   ├── __init__.py
    │   │   │   ├── logger_port.py     # Abstract Logger
    │   │   │   ├── event_bus_port.py  # Abstract EventBus
    │   │   │   ├── unit_of_work.py    # Abstract UnitOfWork
    │   │   │   └── clock_port.py      # Abstract Clock (for testability)
    │   │   ├── dto.py                 # Base DTO
    │   │   └── pagination.py          # Cursor, Page, PaginationParams
    │   │
    │   └── infrastructure/           # Shared infrastructure
    │       ├── __init__.py
    │       ├── database.py            # AsyncEngine, session factory
    │       ├── redis.py               # Redis connection pool
    │       ├── logging_config.py      # Structlog configuration
    │       ├── clock.py               # SystemClock (implements ClockPort)
    │       └── event_bus.py           # RedisStreamEventBus
    │
    ├── identity/                      # DOMAIN: Authentication & Users
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py            # User, Tenant, ApiKey
    │   │   ├── value_objects.py       # Email, HashedPassword, AuthToken
    │   │   ├── repositories.py        # UserRepository (abstract), TenantRepository (abstract)
    │   │   ├── services.py            # PasswordHasher, TokenService (abstracts)
    │   │   ├── events.py              # UserRegistered, UserLoggedIn, SessionRevoked
    │   │   └── exceptions.py          # InvalidCredentialsError, EmailAlreadyExistsError
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/                 # Identity-specific ports
    │   │   │   ├── __init__.py
    │   │   │   ├── auth_port.py       # Abstract AuthService
    │   │   │   └── oauth_port.py      # Abstract OAuthProvider
    │   │   ├── commands.py            # RegisterUser, LoginUser, RefreshToken, RevokeSession
    │   │   ├── queries.py             # GetUserById, GetUserByEmail
    │   │   └── handlers.py            # Command/Query handlers
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   ├── user_repository.py # SQLAlchemy implementation
    │   │   │   ├── tenant_repository.py
    │   │   │   └── models.py          # SQLAlchemy ORM models
    │   │   ├── auth/
    │   │   │   ├── __init__.py
    │   │   │   ├── jwt_service.py     # JWT creation + validation
    │   │   │   ├── password_hasher.py # Argon2 implementation
    │   │   │   └── oauth_google.py    # Google OAuth adapter
    │   │   └── middleware.py          # AuthMiddleware (FastAPI dependency)
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py              # /v1/auth/* routes
    │       ├── schemas.py             # Pydantic request/response models
    │       └── dependencies.py        # FastAPI Depends() wiring
    │
    ├── profile/                       # DOMAIN: User Profiles & Skills
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py            # Profile, WorkExperience, Education, Skill
    │   │   ├── value_objects.py       # SkillProficiency, EmploymentDate, JobTitle
    │   │   ├── repositories.py        # ProfileRepository (abstract)
    │   │   ├── services.py            # SkillExtractor, ResumeParser (abstracts)
    │   │   ├── events.py              # ProfileCreated, ProfileUpdated, SkillAdded
    │   │   └── exceptions.py          # ProfileNotFoundError, ResumeParsingError
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   ├── __init__.py
    │   │   │   ├── resume_parser_port.py    # Abstract ResumeParser
    │   │   │   ├── linkedin_import_port.py  # Abstract LinkedInImporter
    │   │   │   ├── github_import_port.py    # Abstract GitHubImporter
    │   │   │   └── embedding_port.py        # Abstract EmbeddingService
    │   │   ├── commands.py            # CreateProfile, UpdateProfile, ImportResume, ImportLinkedIn
    │   │   ├── queries.py             # GetProfile, GetProfileVersion
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   ├── profile_repository.py
    │   │   │   └── models.py
    │   │   ├── parsing/
    │   │   │   ├── __init__.py
    │   │   │   ├── resume_parser.py   # LLM-based resume parsing
    │   │   │   ├── linkedin_parser.py
    │   │   │   └── github_fetcher.py
    │   │   └── embedding/
    │   │       ├── __init__.py
    │   │       └── deepseek_embedder.py
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py              # /v1/profile/* routes
    │       ├── schemas.py
    │       └── dependencies.py
    │
    ├── jobs/                          # DOMAIN: Job Listings & Companies
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py            # JobPosting, Company, JobSource
    │   │   ├── value_objects.py       # SalaryRange, JobLocation, RemotePolicy
    │   │   ├── repositories.py        # JobRepository, CompanyRepository (abstract)
    │   │   ├── services.py            # JobDeduplicationService, JobEnrichmentService
    │   │   ├── events.py              # JobDiscovered, JobExpired, JobDedupMerged
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   ├── __init__.py
    │   │   │   ├── job_scraper_port.py      # Abstract JobScraper
    │   │   │   └── company_enrichment_port.py
    │   │   ├── commands.py            # IngestJob, EnrichJob, MarkJobExpired
    │   │   ├── queries.py             # SearchJobs, GetJobById, GetCompanyById, SearchCompanies
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   ├── job_repository.py
    │   │   │   ├── company_repository.py
    │   │   │   └── models.py
    │   │   ├── scraping/
    │   │   │   ├── __init__.py
    │   │   │   ├── base_scraper.py
    │   │   │   ├── linkedin_scraper.py
    │   │   │   ├── indeed_scraper.py
    │   │   │   ├── greenhouse_scraper.py
    │   │   │   ├── lever_scraper.py
    │   │   │   ├── workday_scraper.py
    │   │   │   ├── hn_scraper.py
    │   │   │   └── scraper_registry.py
    │   │   └── enrichment/
    │   │       ├── __init__.py
    │   │       ├── llm_enricher.py
    │   │       └── crunchbase_client.py
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py              # /v1/jobs/*, /v1/companies/*
    │       ├── schemas.py
    │       └── dependencies.py
    │
    ├── matching/                      # DOMAIN: Job-User Matching
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py            # MatchResult
    │   │   ├── value_objects.py       # MatchScore, MatchDimension, MatchExplanation
    │   │   ├── repositories.py        # MatchRepository (abstract)
    │   │   ├── services.py            # MatchingEngine, ScoringStrategy (abstracts)
    │   │   ├── events.py              # MatchComputed, HighScoreMatchFound
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   ├── __init__.py
    │   │   │   ├── profile_port.py    # Abstract ProfileReader (cross-domain)
    │   │   │   └── embedding_port.py
    │   │   ├── commands.py            # ComputeMatch, SubmitFeedback
    │   │   ├── queries.py             # GetMatches, GetMatchDetail
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   ├── match_repository.py
    │   │   │   └── models.py
    │   │   └── engine/
    │   │       ├── __init__.py
    │   │       ├── vector_matcher.py  # pgvector ANN search
    │   │       ├── skill_matcher.py
    │   │       ├── experience_matcher.py
    │   │       ├── compensation_matcher.py
    │   │       ├── culture_matcher.py
    │   │       ├── scoring_weights.py
    │   │       └── explainer.py       # LLM match explanation
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py              # /v1/match/*
    │       ├── schemas.py
    │       └── dependencies.py
    │
    ├── applications/                  # DOMAIN: Application Tracking
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py            # Application, Interview, Offer
    │   │   ├── value_objects.py       # ApplicationStatus, InterviewStage, OfferDetails
    │   │   ├── repositories.py        # ApplicationRepository (abstract)
    │   │   ├── services.py            # PipelineService, StatusTransitionValidator
    │   │   ├── events.py              # ApplicationSubmitted, StatusChanged, InterviewScheduled, OfferReceived
    │   │   └── exceptions.py          # InvalidTransitionError, DuplicateApplicationError
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   ├── __init__.py
    │   │   │   ├── email_integration_port.py  # Abstract EmailParser
    │   │   │   └── calendar_integration_port.py
    │   │   ├── commands.py            # CreateApplication, UpdateStatus, ScheduleInterview, RecordOffer
    │   │   ├── queries.py             # GetApplications, GetPipelineSummary, GetApplicationDetail
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   ├── application_repository.py
    │   │   │   └── models.py
    │   │   └── integrations/
    │   │       ├── __init__.py
    │   │       ├── gmail_parser.py
    │   │       ├── outlook_parser.py
    │   │       └── calendar_sync.py
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py              # /v1/applications/*
    │       ├── schemas.py
    │       └── dependencies.py
    │
    ├── documents/                     # DOMAIN: Resumes & Cover Letters
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py            # Resume, CoverLetter, ResumeTemplate
    │   │   ├── value_objects.py       # ResumeSection, BulletPoint, CoverLetterTone
    │   │   ├── repositories.py        # ResumeRepository, CoverLetterRepository (abstract)
    │   │   ├── services.py            # ResumeTailoringService, CoverLetterService (abstracts)
    │   │   ├── events.py              # ResumeCreated, ResumeTailored, CoverLetterGenerated
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   ├── __init__.py
    │   │   │   ├── llm_port.py         # Abstract LLMService
    │   │   │   ├── pdf_renderer_port.py # Abstract PdfRenderer
    │   │   │   └── ats_simulator_port.py
    │   │   ├── commands.py            # CreateResume, TailorResume, GenerateCoverLetter
    │   │   ├── queries.py             # GetResume, GetCoverLetter, ListTemplates
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   ├── resume_repository.py
    │   │   │   ├── cover_letter_repository.py
    │   │   │   └── models.py
    │   │   ├── llm/
    │   │   │   ├── __init__.py
    │   │   │   ├── deepseek_llm.py    # DeepSeek LLM adapter
    │   │   │   ├── openai_llm.py      # OpenAI fallback adapter
    │   │   │   ├── llm_factory.py     # Factory with circuit breaker + fallback
    │   │   │   └── prompt_templates/  # Versioned prompt templates
    │   │   │       ├── resume_tailoring/
    │   │   │       ├── cover_letter/
    │   │   │       └── factuality_check/
    │   │   └── rendering/
    │   │       ├── __init__.py
    │   │       ├── pdf_renderer.py
    │   │       └── ats_simulator.py
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py              # /v1/documents/*, /v1/resumes/*
    │       ├── schemas.py
    │       └── dependencies.py
    │
    ├── interviews/                    # DOMAIN: Interview Preparation
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py            # InterviewPrep, Question, MockSession
    │   │   ├── value_objects.py       # QuestionDifficulty, StarFramework, FeedbackScore
    │   │   ├── repositories.py        # InterviewPrepRepository (abstract)
    │   │   ├── services.py            # QuestionGenerator, CompanyBriefGenerator
    │   │   ├── events.py              # PrepGenerated, MockInterviewCompleted
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   ├── __init__.py
    │   │   │   └── llm_port.py
    │   │   ├── commands.py            # GeneratePrep, RecordMockInterview, SubmitFeedback
    │   │   ├── queries.py             # GetPrepForInterview, GetPrepHistory
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   ├── interview_prep_repository.py
    │   │   │   └── models.py
    │   │   └── generation/
    │   │       ├── __init__.py
    │   │       ├── question_generator.py
    │   │       ├── company_briefer.py
    │   │       └── mock_interviewer.py
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py              # /v1/interviews/*/prep
    │       ├── schemas.py
    │       └── dependencies.py
    │
    ├── agent_orchestration/           # DOMAIN: LangGraph Agent System
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py            # AgentExecution, AgentAction, ApprovalRequest
    │   │   ├── value_objects.py       # Intent, AgentType, ExecutionStatus, ConfidenceScore
    │   │   ├── repositories.py        # AgentExecutionRepository (abstract)
    │   │   ├── services.py            # IntentRouter, TaskPlanner, ResultSynthesizer (abstracts)
    │   │   ├── events.py              # AgentInvoked, AgentCompleted, ApprovalRequested, ApprovalResolved
    │   │   └── exceptions.py          # IntentNotRecognizedError, AgentExecutionError, CircuitBreakerOpenError
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   ├── __init__.py
    │   │   │   ├── agent_port.py       # Abstract Agent interface
    │   │   │   ├── tool_port.py        # Abstract Tool interface
    │   │   │   └── llm_port.py
    │   │   ├── commands.py            # ExecuteIntent, RespondToApproval, CancelExecution
    │   │   ├── queries.py             # GetExecutionHistory, GetPendingApprovals, GetAgentStats
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   ├── agent_execution_repository.py
    │   │   │   └── models.py
    │   │   ├── langgraph/
    │   │   │   ├── __init__.py
    │   │   │   ├── supervisor_graph.py      # Root StateGraph
    │   │   │   ├── nodes/                    # Graph nodes (one file per node)
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── guardrail_node.py
    │   │   │   │   ├── context_builder_node.py
    │   │   │   │   ├── intent_router_node.py
    │   │   │   │   ├── task_planner_node.py
    │   │   │   │   ├── agent_dispatcher_node.py
    │   │   │   │   ├── result_synthesizer_node.py
    │   │   │   │   └── quality_gate_node.py
    │   │   │   ├── subgraphs/               # Specialized agent subgraphs
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── profile_agent.py
    │   │   │   │   ├── job_discovery_agent.py
    │   │   │   │   ├── job_matching_agent.py
    │   │   │   │   ├── resume_agent.py
    │   │   │   │   ├── cover_letter_agent.py
    │   │   │   │   ├── interview_agent.py
    │   │   │   │   ├── career_coach_agent.py
    │   │   │   │   ├── application_tracking_agent.py
    │   │   │   │   ├── follow_up_agent.py
    │   │   │   │   └── memory_agent.py
    │   │   │   ├── state.py                  # TypedDict state schemas
    │   │   │   ├── checkpointer.py           # PostgresSaver setup
    │   │   │   └── tools/                    # Agent tool implementations
    │   │   │       ├── __init__.py
    │   │   │       ├── tool_registry.py
    │   │   │       ├── search_tools.py
    │   │   │       ├── profile_tools.py
    │   │   │       ├── document_tools.py
    │   │   │       ├── application_tools.py
    │   │   │       ├── memory_tools.py
    │   │   │       └── communication_tools.py
    │   │   └── circuit_breaker.py
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py              # /v1/agent/*
    │       ├── schemas.py
    │       ├── sse_handler.py         # Server-Sent Events streaming
    │       └── dependencies.py
    │
    ├── memory/                        # DOMAIN: Memory System
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py            # EpisodicMemory, SemanticMemory, ProceduralMemory, Preference
    │   │   ├── value_objects.py       # MemoryImportance, MemoryType, ConsolidationRun
    │   │   ├── repositories.py        # MemoryRepository (abstract)
    │   │   ├── services.py            # MemoryConsolidationService, MemoryRetrievalService, PreferenceLearner
    │   │   ├── events.py              # MemoryStored, MemoryConsolidated, PreferenceShifted, NarrativeUpdated
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   ├── __init__.py
    │   │   │   ├── llm_port.py
    │   │   │   └── embedding_port.py
    │   │   ├── commands.py            # StoreEpisode, ConsolidateMemories, UpdatePreferences, RecalibrateImportance
    │   │   ├── queries.py             # RetrieveContext, SearchSemanticMemories, GetCareerNarrative, GetPreferenceHistory
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   ├── memory_repository.py
    │   │   │   └── models.py
    │   │   ├── consolidation/
    │   │   │   ├── __init__.py
    │   │   │   ├── consolidator.py     # 5-step consolidation pipeline
    │   │   │   ├── pattern_extractor.py
    │   │   │   ├── preference_updater.py
    │   │   │   └── narrative_updater.py
    │   │   └── retrieval/
    │   │       ├── __init__.py
    │   │       ├── context_assembler.py
    │   │       ├── vector_retriever.py
    │   │       └── ranking.py
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py              # (memory is mostly internal — minimal API)
    │       ├── schemas.py
    │       └── dependencies.py
    │
    ├── career/                        # DOMAIN: Career Goals & Learning
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py            # CareerGoal, LearningPlan, LearningItem
    │   │   ├── value_objects.py       # GoalType, PlanStatus, SkillGap
    │   │   ├── repositories.py        # CareerGoalRepository, LearningPlanRepository (abstract)
    │   │   ├── services.py            # SkillGapAnalyzer, LearningResourceCurator
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   └── llm_port.py
    │   │   ├── commands.py            # CreateGoal, GenerateLearningPlan, UpdateProgress
    │   │   ├── queries.py             # GetGoals, GetLearningPlans, AnalyzeSkillGaps
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   ├── career_goal_repository.py
    │   │   │   └── models.py
    │   │   └── coaching/
    │   │       ├── __init__.py
    │   │       ├── skill_gap_analyzer.py
    │   │       └── resource_curator.py
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py              # /v1/goals/*, /v1/learning-plans/*
    │       ├── schemas.py
    │       └── dependencies.py
    │
    ├── communications/                # DOMAIN: Follow-ups & Outreach
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py            # Communication
    │   │   ├── value_objects.py       # CommunicationType, SendTiming, Tone
    │   │   ├── repositories.py        # CommunicationRepository (abstract)
    │   │   ├── services.py            # CommunicationGenerator, SendTimeOptimizer
    │   │   └── exceptions.py
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   ├── __init__.py
    │   │   │   ├── email_port.py      # Abstract EmailSender
    │   │   │   └── llm_port.py
    │   │   ├── commands.py            # GenerateFollowUp, GenerateThankYou, ScheduleSend, SendNow
    │   │   ├── queries.py             # GetCommunicationHistory
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   ├── communication_repository.py
    │   │   │   └── models.py
    │   │   └── email/
    │   │       ├── __init__.py
    │   │       ├── email_sender.py     # AWS SES / Resend adapter
    │   │       └── send_time_optimizer.py
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py
    │       ├── schemas.py
    │       └── dependencies.py
    │
    ├── analytics/                     # DOMAIN: Analytics & Reporting
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py            # PipelineAnalytics, AgentUsageReport
    │   │   ├── repositories.py        # AnalyticsRepository (abstract)
    │   │   └── services.py            # ReportGenerator
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── queries.py             # GetPipelineAnalytics, GetAgentUsage, GetMarketInsights
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   ├── analytics_repository.py
    │   │   │   └── models.py          # Materialized views
    │   │   └── reporting/
    │   │       └── report_generator.py
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py              # /v1/analytics/*
    │       ├── schemas.py
    │       └── dependencies.py
    │
    ├── notifications/                 # DOMAIN: Notifications & Alerts
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py            # Notification, NotificationPreference
    │   │   ├── value_objects.py       # NotificationChannel, NotificationPriority
    │   │   ├── repositories.py        # NotificationRepository (abstract)
    │   │   └── services.py            # NotificationRouter, DigestCompiler
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── ports/
    │   │   │   ├── __init__.py
    │   │   │   ├── push_port.py       # Abstract PushNotifier
    │   │   │   └── email_port.py
    │   │   ├── commands.py            # SendNotification, CompileDigest, UpdatePreferences
    │   │   └── handlers.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── persistence/
    │   │   │   ├── __init__.py
    │   │   │   ├── notification_repository.py
    │   │   │   └── models.py
    │   │   └── channels/
    │   │       ├── __init__.py
    │   │       ├── push_notifier.py    # Firebase / APNs adapter
    │   │       ├── email_notifier.py
    │   │       └── in_app_notifier.py
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py
    │       ├── ws_handler.py          # WebSocket for real-time push
    │       └── schemas.py
    │
    └── webhooks/                      # DOMAIN: Webhook Management
        ├── __init__.py
        ├── domain/
        │   ├── __init__.py
        │   ├── entities.py            # WebhookEndpoint, WebhookDelivery
        │   └── repositories.py
        ├── application/
        │   ├── commands.py
        │   ├── queries.py
        │   └── handlers.py
        ├── infrastructure/
        │   ├── persistence/
        │   └── delivery/
        │       └── webhook_sender.py
        └── presentation/
            ├── router.py              # /v1/webhooks/*
            └── schemas.py
```

---

## 3. Layer Architecture

### 3.1 The Four Layers — Strict Rules

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LAYER RESPONSIBILITIES                                │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER              │ RESPONSIBILITY              │ ALLOWED IMPORTS   │   │
│  │  ──────────────────┼────────────────────────────┼────────────────── │   │
│  │  PRESENTATION       │ HTTP concerns: routing,    │ Application layer │   │
│  │  (presentation/)    │ request parsing, response  │ Shared DTOs       │   │
│  │                     │ serialization, auth        │ FastAPI/Pydantic  │   │
│  │                     │ middleware, SSE/WS, error  │                   │   │
│  │                     │ formatting, status codes   │                   │   │
│  │                     │                            │                   │   │
│  │  APPLICATION        │ Use case orchestration:    │ Domain layer      │   │
│  │  (application/)     │ command/query handlers,    │ Application ports │   │
│  │                     │ DTOs, transaction          │ Shared types      │   │
│  │                     │ boundaries, cross-domain   │ (never infra)     │   │
│  │                     │ coordination, input        │                   │   │
│  │                     │ validation against domain  │                   │   │
│  │                     │ rules                      │                   │   │
│  │                     │                            │                   │   │
│  │  DOMAIN             │ Business logic: entities,  │ Shared domain     │   │
│  │  (domain/)          │ value objects, aggregates, │ primitives ONLY   │   │
│  │                     │ domain services, domain    │ Python stdlib     │   │
│  │                     │ events, repository         │ (NEVER external   │   │
│  │                     │ interfaces (abstract),     │  libraries)       │   │
│  │                     │ port interfaces (abstract) │                   │   │
│  │                     │                            │                   │   │
│  │  INFRASTRUCTURE     │ Technical implementations: │ Domain interfaces │   │
│  │  (infrastructure/)  │ DB repositories, LLM       │ External libs     │   │
│  │                     │ adapters, Redis adapters,  │ (SQLAlchemy,      │   │
│  │                     │ file storage, external     │  Redis, boto3,    │   │
│  │                     │ API clients, email sending │  LangGraph, etc.) │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Cross-Layer Communication Rules

| Rule | Detail |
|------|--------|
| **Presentation → Domain** | NEVER. Presentation calls Application handlers only. |
| **Application → Infrastructure** | NEVER directly. Application depends on Port interfaces (defined in application/ports/). Infrastructure implements those ports. |
| **Domain → Infrastructure** | NEVER. Domain defines interfaces. Infrastructure implements them. |
| **Domain → Domain** | Allowed through domain services and domain events. Cross-domain via interfaces (e.g., MatchingDomain depends on abstract ProfileReader, not on ProfileDomain). |
| **Infrastructure → Domain** | Allowed. Infrastructure implements domain repository interfaces. |


## 4. Domain Design

### 4.1 Bounded Context Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BOUNDED CONTEXT MAP                                  │
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                 │
│  │   IDENTITY   │     │   PROFILE    │     │     JOBS     │                 │
│  │              │     │              │     │              │                 │
│  │ Users        │────►│ Profile      │     │ JobPosting   │                 │
│  │ Tenants      │     │ Skills       │     │ Company      │                 │
│  │ Auth         │     │ Work History │     │ JobSource    │                 │
│  │ Sessions     │     │ Education    │     │ Enrichment   │                 │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘                 │
│         │                    │                    │                          │
│         │         ┌──────────┼────────────────────┼──────────┐              │
│         │         │          │                    │          │              │
│         ▼         ▼          ▼                    ▼          ▼              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                 │
│  │  APPLICATIONS│     │   MATCHING   │     │  AGENT ORCH. │                 │
│  │              │     │              │     │              │                 │
│  │ Application  │◄────│ MatchResult  │────►│ Execution    │                 │
│  │ Interview    │     │ MatchScore   │     │ Intent       │                 │
│  │ Offer        │     │ Explanation  │     │ Approval     │                 │
│  │ Task         │     │              │     │ CircuitBrkr  │                 │
│  └──────┬───────┘     └──────────────┘     └──────┬───────┘                 │
│         │                                         │                          │
│         │         ┌───────────────────────────────┼──────────┐              │
│         │         │                               │          │              │
│         ▼         ▼                               ▼          ▼              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                 │
│  │  DOCUMENTS   │     │   MEMORY     │     │  INTERVIEWS  │                 │
│  │              │     │              │     │              │                 │
│  │ Resume       │     │ Episodic     │     │ PrepPlan     │                 │
│  │ CoverLetter  │     │ Semantic     │     │ Question     │                 │
│  │ Template     │     │ Procedural   │     │ MockSession  │                 │
│  │              │     │ Preference   │     │ Feedback     │                 │
│  └──────────────┘     └──────┬───────┘     └──────────────┘                 │
│                              │                                               │
│                              ▼                                               │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                 │
│  │   CAREER     │     │COMMUNICATION │     │ NOTIFICATION │                 │
│  │              │     │              │     │              │                 │
│  │ CareerGoal   │     │ FollowUp     │     │ Notification │                 │
│  │ LearningPlan │     │ ThankYou     │     │ Digest       │                 │
│  │ SkillGap     │     │ Outreach     │     │ PushToken    │                 │
│  └──────────────┘     └──────────────┘     └──────────────┘                 │
│                                                                              │
│  RELATIONSHIP TYPES:                                                         │
│  ────►  Upstream (supplier) — downstream depends on upstream's interface     │
│  ◄────  Downstream (consumer) — consumes upstream's published events         │
│                                                                              │
│  SHARED KERNEL: shared/domain/ (identifiers, money, result monad, etc.)      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Domain Module Internal Structure

Every domain module follows this exact internal structure:

```
{domain_name}/
├── domain/                    # Inner sanctum — pure business logic
│   ├── entities.py            # Entities with identity (User, Job, Application)
│   ├── value_objects.py       # Immutable values (Email, Money, SkillLevel)
│   ├── repositories.py        # Abstract repository interfaces (ABC)
│   ├── services.py            # Domain services (stateless business logic)
│   ├── events.py              # Domain events (UserRegistered, JobApplied)
│   └── exceptions.py          # Domain-specific errors
│
├── application/               # Use case orchestration
│   ├── ports/                 # Interfaces this domain needs from outside
│   │   └── *_port.py          # Abstract ports (LLMPort, EmailPort, etc.)
│   ├── commands.py            # Command DTOs (imperative: DoSomething)
│   ├── queries.py             # Query DTOs (interrogative: GetSomething)
│   └── handlers.py            # Command/Query handlers (orchestrate domain)
│
├── infrastructure/            # Technical implementations
│   ├── persistence/           # Database adapters
│   │   ├── *_repository.py    # Concrete repository implementations
│   │   └── models.py          # SQLAlchemy ORM models
│   └── {adapter_name}/        # Other adapters (llm/, email/, etc.)
│
└── presentation/              # HTTP layer
    ├── router.py              # FastAPI APIRouter
    ├── schemas.py             # Pydantic request/response models
    └── dependencies.py        # FastAPI dependency injection wiring
```

### 4.3 Entity Design Rules

| Rule | Example |
|------|---------|
| Entities have identity (UUID) | `class User(BaseEntity): id: UserId` |
| Entities are mutable over time | `user.update_email(new_email)` |
| Value objects are immutable | `class Email(BaseValueObject): value: str` (frozen) |
| Aggregates enforce consistency boundaries | `Application` is root of `Application → Interview → Offer` |
| Repository per aggregate root only | `ApplicationRepository`, no `InterviewRepository` |
| Domain events are raised by aggregates | `application.add_event(ApplicationSubmitted(...))` |
| Entities never know about persistence | No `user.save()`. Always `repository.save(user)` |

### 4.4 Cross-Domain Communication

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CROSS-DOMAIN COMMUNICATION PATTERNS                       │
│                                                                              │
│  PATTERN 1: SHARED INTERFACE (same process, synchronous)                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Matching domain needs user profile data.                            │   │
│  │                                                                       │   │
│  │  In matching/application/ports/profile_port.py:                       │   │
│  │    class ProfileReader(ABC):                                          │   │
│  │        @abstractmethod                                                │   │
│  │        async def get_profile(self, user_id: UserId) -> Profile: ...   │   │
│  │                                                                       │   │
│  │  In profile/infrastructure/profile_reader_adapter.py:                 │   │
│  │    class ProfileReaderAdapter(ProfileReader):                         │   │
│  │        """Adapter wraps ProfileRepository for external consumers."""  │   │
│  │                                                                       │   │
│  │  DI container wires: ProfileReaderAdapter → ProfileReader             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  PATTERN 2: DOMAIN EVENTS (async, via EventBus)                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Applications domain emits ApplicationSubmitted event.               │   │
│  │  Memory domain subscribes → stores episodic memory.                  │   │
│  │  Notifications domain subscribes → sends push notification.          │   │
│  │                                                                       │   │
│  │  Event flow:                                                          │   │
│  │  1. Domain raises: entity.add_event(ApplicationSubmitted(...))        │   │
│  │  2. Application handler publishes: event_bus.publish(events)          │   │
│  │  3. Subscribers react asynchronously (Redis Streams consumer groups) │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Module Boundaries

### 5.1 Boundary Enforcement

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     IMPORT BOUNDARY RULES                                      │
│                                                                              │
│  ALLOWED (within a domain module):                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ presentation → application         ✅                                  │   │
│  │ application → domain              ✅                                  │   │
│  │ infrastructure → domain           ✅ (implements interfaces)          │   │
│  │ domain → domain (same module)     ✅                                  │   │
│  │ domain → shared/domain            ✅                                  │   │
│  │ application → shared/application  ✅                                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  FORBIDDEN:                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ domain → application               ❌ (domain never depends on app)   │   │
│  │ domain → infrastructure            ❌ (domain never depends on infra) │   │
│  │ domain → presentation              ❌                                 │   │
│  │ application → infrastructure       ❌ (application depends on ports)  │   │
│  │ application → presentation         ❌                                 │   │
│  │ infrastructure → application       ❌ (infra implements, doesn't call)│   │
│  │ infrastructure → presentation      ❌                                 │   │
│  │ presentation → domain              ❌                                 │   │
│  │ presentation → infrastructure      ❌                                 │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  CROSS-DOMAIN (allowed with restrictions):                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ domain_A → domain_B (via interface) ✅ — interface defined in B       │   │
│  │ application_A → application_B       ❌ — use ports or events          │   │
│  │ infrastructure_A → domain_B         ✅ — for adapter implementations  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ENFORCEMENT: Use `import-linter` or `pytest-arch` in CI to validate rules.  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 API for Each Module

Every domain module exposes a minimal public API through its `__init__.py`:

```python
# src/profile/__init__.py
from src.profile.domain.entities import Profile
from src.profile.domain.repositories import ProfileRepository
from src.profile.domain.exceptions import ProfileNotFoundError
from src.profile.application.commands import CreateProfileCommand
from src.profile.application.handlers import ProfileCommandHandler
from src.profile.presentation.router import router as profile_router

__all__ = [
    "Profile",
    "ProfileRepository",
    "ProfileNotFoundError",
    "CreateProfileCommand",
    "ProfileCommandHandler",
    "profile_router",
]
```

Every other module imports only from this public surface — never from internal files.

---

## 6. Naming Conventions

### 6.1 File Naming

| Component | Convention | Example |
|-----------|-----------|---------|
| Entity files | `entities.py` (plural) | `domain/entities.py` |
| Value object files | `value_objects.py` (plural) | `domain/value_objects.py` |
| Repository interfaces | `repositories.py` (plural) | `domain/repositories.py` |
| Repository implementations | `{name}_repository.py` | `infrastructure/persistence/user_repository.py` |
| Domain services | `services.py` (plural) | `domain/services.py` |
| Port interfaces | `{name}_port.py` | `application/ports/llm_port.py` |
| Command DTOs | `commands.py` | `application/commands.py` |
| Query DTOs | `queries.py` | `application/queries.py` |
| Command/Query handlers | `handlers.py` | `application/handlers.py` |
| FastAPI routers | `router.py` | `presentation/router.py` |
| Pydantic schemas | `schemas.py` | `presentation/schemas.py` |
| DI wiring | `dependencies.py` | `presentation/dependencies.py` |
| ORM models | `models.py` | `infrastructure/persistence/models.py` |
| Domain events | `events.py` | `domain/events.py` |
| Exceptions | `exceptions.py` | `domain/exceptions.py` |
| LangGraph nodes | `{name}_node.py` | `nodes/guardrail_node.py` |
| LangGraph agent subgraphs | `{name}_agent.py` | `subgraphs/resume_agent.py` |
| Tool implementations | `{name}_tools.py` | `tools/search_tools.py` |
| Test files | `test_{what}.py` | `test_user_entity.py` |

### 6.2 Class & Function Naming

| Component | Convention | Example |
|-----------|-----------|---------|
| Entity classes | `Noun` (no suffix) | `User`, `Application`, `JobPosting` |
| Value objects | `Noun` (no suffix) | `Email`, `Money`, `SkillProficiency` |
| Aggregate roots | `Noun` (no suffix) | `Application` (root of Application aggregate) |
| Domain services | `{Verb}Service` or `{Noun}{Verb}` | `MatchingEngine`, `ResumeTailoringService` |
| Repository interfaces | `{Entity}Repository` (abstract ABC) | `UserRepository` |
| Repository implementations | `Sql{Entity}Repository` or `{Entity}RepositoryImpl` | `SqlUserRepository` |
| Port interfaces | `{Capability}Port` (abstract ABC) | `LLMPort`, `EmailSenderPort` |
| Port implementations | `{Technology}{Port}` | `DeepSeekLLMAdapter`, `SesEmailSender` |
| Command DTOs | `{Verb}{Noun}Command` | `CreateApplicationCommand` |
| Query DTOs | `Get{Noun}Query` or `{Noun}Query` | `GetUserByEmailQuery` |
| Command handlers | `{Noun}CommandHandler` | `ApplicationCommandHandler` |
| Query handlers | `{Noun}QueryHandler` | `UserQueryHandler` |
| Domain events | `{Noun}{PastTenseVerb}` | `ApplicationSubmitted`, `UserRegistered` |
| FastAPI dependencies | `get_{resource}` | `get_user_repository`, `get_current_user` |
| Private methods | `_{verb}_{noun}` | `_validate_status_transition` |
| Factory methods | `create_{what}` | `User.create(email, password)` |

### 6.3 Variable Naming

| Context | Convention | Example |
|---------|-----------|---------|
| Repository variable | `{entity}_repo` | `user_repo`, `job_repo` |
| Unit of work variable | `uow` | `uow` |
| DTO variable | `dto` or `{specific}` | `dto`, `command` |
| Database session | `session` | `session` |
| Redis client | `redis` | `redis` |
| LLM client | `llm` | `llm` |
| Event bus | `event_bus` | `event_bus` |
| Logger | `logger` or `log` | `logger` |
| List variables | Plural noun | `users`, `applications`, `job_ids` |
| Boolean variables | `is_`, `has_`, `can_`, `should_` prefix | `is_active`, `has_profile` |

---

## 7. Design Patterns

### 7.1 Pattern Catalog

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DESIGN PATTERNS IN USE                               │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ PATTERN            │ WHERE USED                │ PURPOSE              │   │
│  │ ──────────────────┼──────────────────────────┼───────────────────── │   │
│  │                    │                           │                      │   │
│  │ Repository         │ domain/repositories.py    │ Abstract data access │   │
│  │                    │ infra/persistence/*.py    │ behind an interface  │   │
│  │                    │                           │                      │   │
│  │ Unit of Work       │ shared/application/ports/ │ Transaction boundary │   │
│  │                    │   unit_of_work.py         │ across repositories  │   │
│  │                    │                           │                      │   │
│  │ Specification      │ shared/domain/base_       │ Composable query     │   │
│  │                    │   specification.py        │ filters for repos    │   │
│  │                    │                           │                      │   │
│  │ Result Monad       │ shared/domain/result.py   │ Railway-oriented     │   │
│  │                    │                           │ error handling       │   │
│  │                    │                           │                      │   │
│  │ Command/Query      │ application/commands.py   │ CQRS: separate read  │   │
│  │ Separation (CQRS)  │ application/queries.py    │ from write models    │   │
│  │                    │                           │                      │   │
│  │ Domain Events      │ domain/events.py          │ Decoupled cross-     │   │
│  │                    │                           │ domain communication │   │
│  │                    │                           │                      │   │
│  │ Ports & Adapters   │ application/ports/        │ Invert dependencies  │   │
│  │ (Hexagonal)        │ infrastructure/           │ on external systems  │   │
│  │                    │                           │                      │   │
│  │ Factory Method     │ domain/entities.py        │ Entity creation with │   │
│  │                    │ (create_* classmethods)   │ invariant validation │   │
│  │                    │                           │                      │   │
│  │ Strategy           │ matching/domain/services/ │ Pluggable scoring    │   │
│  │                    │   scoring_strategy.py     │ algorithms           │   │
│  │                    │                           │                      │   │
│  │ Observer           │ EventBus implementation   │ Decoupled event      │   │
│  │ (Pub/Sub)          │ (Redis Streams)           │ handling             │   │
│  │                    │                           │                      │   │
│  │ Circuit Breaker    │ agent_orchestration/      │ Fail fast when LLM   │   │
│  │                    │   infra/circuit_breaker.py│ is degraded          │   │
│  │                    │                           │                      │   │
│  │ Chain of           │ presentation/middleware/  │ Auth → Rate Limit →  │   │
│  │ Responsibility     │                           │ Validation → Handler │   │
│  │                    │                           │                      │   │
│  │ Template Method    │ agent_orchestration/      │ Standard agent       │   │
│  │                    │   langgraph/nodes/        │ execution lifecycle  │   │
│  │                    │                           │                      │   │
│  │ State Machine      │ applications/domain/      │ Application status   │   │
│  │                    │   services/status_valid.  │ transitions          │   │
│  │                    │   py                      │                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Key Pattern Details

#### Repository Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│  DOMAIN (abstract):                                                  │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ class ApplicationRepository(ABC):                            │    │
│  │     async def get_by_id(self, id: ApplicationId)            │    │
│  │         -> Application | None: ...                          │    │
│  │     async def save(self, application: Application) -> None  │    │
│  │     async def list_by_user(                                 │    │
│  │         self, user_id: UserId,                              │    │
│  │         specification: Specification | None                 │    │
│  │     ) -> Paginated[Application]: ...                        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  INFRASTRUCTURE (concrete):                                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ class SqlApplicationRepository(ApplicationRepository):       │    │
│  │     def __init__(self, session: AsyncSession): ...          │    │
│  │     async def get_by_id(...) -> Application | None:         │    │
│  │         orm_model = await session.get(ApplicationModel, id) │    │
│  │         return orm_model.to_domain() if orm_model else None │    │
│  │     async def save(self, application: Application) -> None: │    │
│  │         orm_model = ApplicationModel.from_domain(application)│   │
│  │         await session.merge(orm_model)                       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  KEY: Repository deals in DOMAIN objects, not ORM objects.           │
│  Mapping (to_domain / from_domain) happens at the repository edge.   │
└─────────────────────────────────────────────────────────────────────┘
```

#### Result Monad

```
┌─────────────────────────────────────────────────────────────────────┐
│  Instead of exceptions for expected failures, use Result[T]:         │
│                                                                      │
│  def validate_status_transition(                                     │
│      current: ApplicationStatus,                                    │
│      target: ApplicationStatus                                      │
│  ) -> Result[None]:                                                  │
│      if not is_valid_transition(current, target):                    │
│          return Result.failure(                                      │
│              InvalidTransitionError(current, target)                 │
│          )                                                           │
│      return Result.success(None)                                     │
│                                                                      │
│  Usage in handler:                                                   │
│  result = validate_status_transition(app.status, command.new_status) │
│  if result.is_failure:                                               │
│      return result.error                                             │
│  app.change_status(command.new_status)                               │
│                                                                      │
│  Exceptions are ONLY for truly exceptional cases (DB down, etc.)     │
└─────────────────────────────────────────────────────────────────────┘
```

#### Specification Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│  Composable query filters without leaking persistence details:       │
│                                                                      │
│  class ActiveApplicationsSpec(Specification):                        │
│      def is_satisfied_by(self, app: Application) -> bool:            │
│          return app.status not in TERMINAL_STATUSES                  │
│                                                                      │
│  class ByStatusSpec(Specification):                                  │
│      def __init__(self, status: ApplicationStatus): ...              │
│      def is_satisfied_by(self, app: Application) -> bool:            │
│          return app.status == self.status                            │
│                                                                      │
│  composed = ActiveApplicationsSpec() & ByStatusSpec(INTERVIEW)       │
│  results = await application_repo.list_by_user(user_id, composed)    │
│                                                                      │
│  Repository translates Specification → SQL WHERE clause.             │
│  Domain code never sees SQL.                                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 8. Dependency Injection

### 8.1 Wiring Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DEPENDENCY INJECTION ARCHITECTURE                         │
│                                                                              │
│  PRINCIPLE: Constructor injection everywhere. No service locator.            │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  CONTAINER (per domain module): presentation/dependencies.py          │   │
│  │                                                                       │   │
│  │  # FastAPI's Depends() wires the container                            │   │
│  │                                                                       │   │
│  │  async def get_application_repository(                                 │   │
│  │      session: AsyncSession = Depends(get_db_session)                  │   │
│  │  ) -> ApplicationRepository:                                          │   │
│  │      return SqlApplicationRepository(session)                         │   │
│  │                                                                       │   │
│  │  async def get_application_command_handler(                           │   │
│  │      app_repo: ApplicationRepository = Depends(                       │   │
│  │          get_application_repository                                   │   │
│  │      ),                                                               │   │
│  │      event_bus: EventBus = Depends(get_event_bus),                    │   │
│  │      uow: UnitOfWork = Depends(get_unit_of_work),                     │   │
│  │  ) -> ApplicationCommandHandler:                                      │   │
│  │      return ApplicationCommandHandler(app_repo, event_bus, uow)       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  ROUTER: presentation/router.py                                       │   │
│  │                                                                       │   │
│  │  router = APIRouter(prefix="/v1/applications", tags=["Applications"]) │   │
│  │                                                                       │   │
│  │  @router.post("/", response_model=ApplicationResponse, status_code=201)│  │
│  │  async def create_application(                                        │   │
│  │      body: CreateApplicationRequest,                                  │   │
│  │      handler: ApplicationCommandHandler = Depends(                    │   │
│  │          get_application_command_handler                              │   │
│  │      ),                                                               │   │
│  │      current_user: User = Depends(get_current_user),                  │   │
│  │  ):                                                                    │   │
│  │      command = CreateApplicationCommand(                              │   │
│  │          user_id=current_user.id,                                     │   │
│  │          job_id=body.job_id,                                          │   │
│  │          ...                                                          │   │
│  │      )                                                                │   │
│  │      result = await handler.handle_create(command)                    │   │
│  │      return ApplicationResponse.from_domain(result)                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Singleton vs Scoped vs Transient

| Lifetime | For | Example |
|----------|-----|---------|
| **Singleton** (app lifespan) | Stateless, thread-safe clients | Redis connection pool, LLM client, HTTP client |
| **Scoped** (per request) | Stateful resources tied to a request | DB session, Unit of Work, repositories |
| **Transient** (per injection) | Lightweight, no state | Command handlers, query handlers, domain services |

### 8.3 Testing with DI

```
┌─────────────────────────────────────────────────────────────────────┐
│  Test overrides (in conftest.py):                                    │
│                                                                      │
│  @pytest.fixture                                                     │
│  def mock_application_repository():                                  │
│      return Mock(spec=ApplicationRepository)                         │
│                                                                      │
│  @pytest.fixture                                                     │
│  def command_handler(mock_application_repository, fake_event_bus):   │
│      return ApplicationCommandHandler(                               │
│          app_repo=mock_application_repository,                       │
│          event_bus=fake_event_bus,                                   │
│          uow=FakeUnitOfWork()                                        │
│      )                                                               │
│                                                                      │
│  async def test_create_application(command_handler, ...):            │
│      command = CreateApplicationCommand(...)                         │
│      result = await command_handler.handle_create(command)           │
│      assert result.is_success                                        │
│      mock_application_repository.save.assert_called_once()           │
│                                                                      │
│  No DI container needed in tests. Just construct with mocks.         │
│  No database. No Redis. Pure unit test. Fast.                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 9. Coding Standards

### 9.1 Python Standards

| Rule | Detail |
|------|--------|
| **Python version** | 3.12+ |
| **Type hints** | Mandatory on ALL public functions and methods. `disallow_untyped_defs = true` in mypy. |
| **Line length** | 100 characters (black default) |
| **Formatter** | `black` with `--line-length 100` |
| **Linter** | `ruff` (replaces flake8, isort, pylint) |
| **Type checker** | `mypy` with `strict = true` |
| **Import sorting** | `ruff` with `isort` rules. Order: stdlib → third-party → first-party → relative |
| **Docstrings** | Google-style for all public functions/classes. One-line summary, then Args/Returns/Raises. |
| **Async/await** | Use throughout. No sync wrappers around async code. No `asyncio.run()` in library code. |
| **String quoting** | Double quotes `"` for user-facing strings. Single quotes `'` for internal identifiers. |

### 9.2 Docstring Convention

```python
async def tailor_resume(
    self,
    user_profile: Profile,
    job: JobPosting,
    match_analysis: MatchResult,
    *,
    template_id: str = "modern_professional",
    emphasis: list[str] | None = None,
) -> TailoredResume:
    """Generate a job-tailored resume variant.

    Analyzes the job description against the user profile, identifies
    the most relevant experiences, and rewrites content to maximize
    both ATS keyword coverage and human readability.

    Args:
        user_profile: The user's canonical profile with all experiences.
        job: The target job posting with enrichments.
        match_analysis: Pre-computed match scores and gaps.
        template_id: Resume template to use for rendering.
        emphasis: Specific areas to emphasize in tailoring.
            Options: "skills", "achievements", "culture_fit".

    Returns:
        A tailored resume with diff from base, ATS coverage report,
        and honest gap disclosures.

    Raises:
        ProfileTooThinError: If profile has fewer than 2 work experiences.
        TailoringFailedError: If LLM generation fails after all retries.
    """
```

### 9.3 Async Conventions

| Rule | Detail |
|------|--------|
| All I/O is async | DB queries, Redis operations, HTTP calls, LLM calls — all `async def` / `await` |
| No sync I/O in async context | Never `time.sleep()`, `requests.get()`, or sync DB drivers in async code |
| Async session pattern | `async with session.begin(): ...` for transaction boundaries |
| Background tasks | Celery for heavy work. Async for event handlers. |
| Cancellation | All long-running operations accept optional `CancellationToken` |

### 9.4 Error Handling Convention

```
┌───────────────────────────────────────────────────────────────────┐
│  LAYER           │ HOW ERRORS ARE HANDLED                         │
│  ───────────────┼─────────────────────────────────────────────── │
│  Domain          │ Return Result[T] for expected failures         │
│                  │ Raise DomainError subclasses for invariants    │
│  Application     │ Catch domain errors, map to Result or re-raise│
│                  │ Never catch generic Exception                  │
│  Infrastructure  │ Wrap external errors in domain exceptions     │
│                  │ (e.g., DB connection error → PersistenceError) │
│  Presentation    │ Catch all → map to HTTP status codes          │
│                  │ via exception handlers (FastAPI middleware)    │
│                  │ Log full traceback, return safe error to user  │
└───────────────────────────────────────────────────────────────────┘
```

### 9.5 Commit & PR Standards

| Rule | Detail |
|------|--------|
| **Branch naming** | `feature/domain-brief-description`, `fix/issue-number-description` |
| **Commit messages** | Conventional commits: `feat(matching): add vector-based skill scoring` |
| **PR size** | Max 400 lines changed. Break large features into stacked PRs. |
| **PR template** | Description, testing notes, screenshots (if UI), migration notes (if DB change) |
| **Review requirements** | 1 approval minimum. All CI checks (lint, type, test) must pass. |

---

## 10. Test Architecture

### 10.1 Test Pyramid

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TEST PYRAMID                                     │
│                                                                              │
│                        ┌─────────────┐                                       │
│                        │     E2E     │   5%   — Full API flows, real DB/Redis│
│                        │   (slow)    │                                       │
│                        └──────┬──────┘                                       │
│                               │                                              │
│                      ┌────────┴────────┐                                     │
│                      │   INTEGRATION   │  20%  — Repository impls, adapters  │
│                      │   (medium)      │         Real DB/Redis in Docker     │
│                      └───────┬─────────┘                                     │
│                              │                                               │
│                     ┌────────┴────────┐                                      │
│                     │      UNIT       │  75%  — Domain logic, entities,      │
│                     │     (fast)      │         value objects, handlers      │
│                     │                 │         Pure Python, mocked deps     │
│                     └─────────────────┘                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Test File Organization

```
tests/
├── unit/
│   ├── domain/
│   │   ├── identity/
│   │   │   ├── test_user_entity.py         # User creation, invariants
│   │   │   ├── test_email_value_object.py  # Email validation
│   │   │   └── test_auth_service.py        # Password hashing, token logic
│   │   ├── applications/
│   │   │   ├── test_application_entity.py
│   │   │   ├── test_status_transitions.py  # State machine validation
│   │   │   └── test_pipeline_service.py
│   │   ├── matching/
│   │   │   ├── test_match_score.py
│   │   │   └── test_scoring_weights.py
│   │   └── ...
│   └── application/
│       ├── identity/
│       │   └── test_register_user_handler.py  # Handler with mocked deps
│       └── ...
│
├── integration/
│   ├── infrastructure/
│   │   ├── persistence/
│   │   │   ├── test_user_repository.py     # Real PostgreSQL via testcontainers
│   │   │   ├── test_job_repository.py
│   │   │   └── test_memory_repository.py
│   │   ├── llm/
│   │   │   └── test_deepseek_adapter.py    # Real LLM calls (sandbox)
│   │   └── cache/
│   │       └── test_redis_adapter.py
│   └── api/
│       ├── test_auth_api.py                # HTTP client + real DB
│       └── test_job_search_api.py
│
└── e2e/
    ├── test_full_application_flow.py       # Register → Profile → Match → Apply → Track
    ├── test_agent_tailoring_flow.py        # Full agent orchestration test
    └── test_memory_consolidation.py        # End-to-end memory pipeline
```

### 10.3 Test Naming Convention

```
test_{method_or_scenario}_{expected_outcome}

Examples:
  test_register_user_with_valid_email_creates_user
  test_apply_to_same_job_twice_raises_duplicate_error
  test_status_transition_from_applied_to_offer_is_invalid
  test_search_jobs_by_salary_range_returns_filtered_results
  test_consolidation_with_50_episodes_produces_3_insights
```

### 10.4 Fixtures & Factories

```
┌─────────────────────────────────────────────────────────────────────┐
│  FACTORY PATTERN: tests/fixtures/                                    │
│                                                                      │
│  class UserFactory:                                                  │
│      """Builds User entities for tests with sensible defaults."""    │
│                                                                      │
│      @staticmethod                                                    │
│      def build(**overrides) -> User:                                 │
│          defaults = {                                                │
│              "id": UserId(uuid4()),                                  │
│              "email": Email("test@example.com"),                     │
│              "full_name": "Test User",                               │
│              "tier": Tier.FREE,                                      │
│          }                                                           │
│          return User(**{**defaults, **overrides})                    │
│                                                                      │
│      @staticmethod                                                    │
│      def with_profile(**overrides) -> User:                          │
│          user = UserFactory.build(**overrides)                       │
│          profile = ProfileFactory.build(user_id=user.id)             │
│          user._profile = profile                                     │
│          return user                                                 │
│                                                                      │
│  Usage in tests:                                                     │
│  user = UserFactory.build(tier=Tier.PRO)                             │
│  job = JobFactory.with_enrichment(seniority="senior")                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 11. Configuration Management

### 11.1 Configuration Hierarchy

```
┌─────────────────────────────────────────────────────────────────────┐
│  CONFIG SOURCES (loaded in order; later overrides earlier):          │
│                                                                      │
│  1. src/shared/config/defaults.py       # Hardcoded safe defaults    │
│  2. .env file                            # Local development         │
│  3. Environment variables                # Production (K8s secrets)  │
│  4. AWS Parameter Store / Vault          # Secrets (prod only)       │
│                                                                      │
│  CONFIG CLASS:                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ class Settings(BaseSettings):                                │    │
│  │     model_config = SettingsConfigDict(                       │    │
│  │         env_file=".env",                                     │    │
│  │         env_file_encoding="utf-8",                           │    │
│  │         extra="forbid"   # Reject unknown env vars           │    │
│  │     )                                                        │    │
│  │                                                               │    │
│  │     # Database                                                │    │
│  │     database_url: PostgresDsn                                 │    │
│  │     database_pool_size: int = 20                              │    │
│  │     database_pool_overflow: int = 10                          │    │
│  │                                                               │    │
│  │     # Redis                                                   │    │
│  │     redis_url: RedisDsn                                       │    │
│  │     redis_max_connections: int = 50                           │    │
│  │                                                               │    │
│  │     # DeepSeek                                                │    │
│  │     deepseek_api_key: SecretStr                               │    │
│  │     deepseek_base_url: HttpUrl                                │    │
│  │     deepseek_model: str = "deepseek-chat"                     │    │
│  │     deepseek_timeout_seconds: int = 30                        │    │
│  │     deepseek_max_retries: int = 3                             │    │
│  │                                                               │    │
│  │     # OpenAI (fallback)                                       │    │
│  │     openai_api_key: SecretStr | None = None                   │    │
│  │                                                               │    │
│  │     # Application                                              │    │
│  │     app_env: Literal["local", "dev", "staging", "prod"]       │    │
│  │     app_debug: bool = False                                   │    │
│  │     app_cors_origins: list[str] = ["http://localhost:3000"]   │    │
│  │                                                               │    │
│  │     # Security                                                 │    │
│  │     jwt_public_key: str                                       │    │
│  │     jwt_private_key: SecretStr                                │    │
│  │     jwt_algorithm: str = "RS256"                              │    │
│  │     jwt_access_token_ttl: int = 900                           │    │
│  │     jwt_refresh_token_ttl: int = 604800                       │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### 11.2 Environment-Specific Configuration

```
┌─────────────────────────────────────────────────────────────────────┐
│  SETTING              │ LOCAL        │ STAGING      │ PRODUCTION    │
│  ────────────────────┼─────────────┼─────────────┼────────────── │
│  database_pool_size   │ 5            │ 10           │ 20            │
│  database_url         │ localhost    │ RDS staging   │ RDS prod      │
│  redis_url            │ localhost    │ ElastiCache   │ ElastiCache   │
│  deepseek_timeout     │ 60s          │ 30s           │ 30s           │
│  app_debug            │ true         │ false         │ false         │
│  log_level            │ DEBUG        │ INFO          │ WARNING       │
│  sentry_dsn           │ (unset)      │ (set)         │ (set)         │
│  circuit_breaker_max  │ 10           │ 5             │ 5             │
│  _failures            │              │               │               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 12. Package & Import Rules

### 12.1 `pyproject.toml` Structure

```toml
[project]
name = "pathfinder"
version = "0.1.0"
requires-python = ">=3.12"

[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.115"
uvicorn = {extras = ["standard"], version = "^0.32"}
sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
asyncpg = "^0.29"
pgvector = "^0.3"
redis = {extras = ["hiredis"], version = "^5.2"}
langgraph = "^0.3"
langgraph-checkpoint-postgres = "^0.1"
pydantic = "^2.9"
pydantic-settings = "^2.6"
httpx = "^0.28"
structlog = "^24.4"
tenacity = "^9.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3"
pytest-asyncio = "^0.24"
pytest-cov = "^6.0"
black = "^24.10"
ruff = "^0.8"
mypy = "^1.13"
faker = "^33.0"
testcontainers = "^4.9"

[tool.black]
line-length = 100
target-version = ["py312"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "B", "C4", "SIM", "UP", "ARG"]

[tool.mypy]
strict = true
disallow_untyped_defs = true
warn_unused_ignores = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### 12.2 Import Style

```python
# CORRECT — clear origin of every name
from src.profile.domain.entities import Profile
from src.profile.domain.value_objects import SkillProficiency
from src.profile.domain.exceptions import ProfileNotFoundError

# WRONG — wildcard imports
from src.profile.domain.entities import *

# WRONG — importing from internal implementation
from src.profile.infrastructure.persistence.models import ProfileModel

# CORRECT — importing the public API
from src.profile import Profile, ProfileRepository, profile_router

# CORRECT — relative imports within a module (domain layer only)
from .entities import Profile
from .exceptions import ProfileNotFoundError

# WRONG — relative imports that cross layer boundaries
# In application/handlers.py:
from ..infrastructure.persistence.user_repository import SqlUserRepository  # NO
from ..domain.repositories import UserRepository  # YES (interface only)
```

### 12.3 Module Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MODULE DEPENDENCIES (→ means "depends on")                                   │
│                                                                              │
│  identity       → shared/domain, shared/application                          │
│  profile        → shared/domain, shared/application                          │
│  jobs           → shared/domain, shared/application                          │
│  matching       → shared/domain, profile (interface), jobs (interface)       │
│  applications   → shared/domain, profile (interface), jobs (interface)       │
│  documents      → shared/domain, profile (interface), jobs (interface)       │
│  interviews     → shared/domain, applications (interface)                    │
│  agent_orch.    → shared/domain, ALL domains (interfaces)                    │
│  memory         → shared/domain, ALL domains (events)                        │
│  career         → shared/domain, profile (interface)                         │
│  communications → shared/domain, applications (interface)                    │
│  notifications  → shared/domain                                              │
│  analytics      → shared/domain, applications (interface)                    │
│  webhooks       → shared/domain                                              │
│                                                                              │
│  CRITICAL: No circular dependencies. The dependency graph is a DAG.          │
│  agent_orchestration and memory sit at the top (depend on everything).       │
│  shared sits at the bottom (depends on nothing external).                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

> *"Code is read far more often than it is written. Optimize for the reader — your future self six months from now."*

**End of Codebase Architecture Document**
