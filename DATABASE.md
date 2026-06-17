# Pathfinder — Production Database Schema Design

**Document Version:** 1.0
**Date:** 2026-06-17
**Role:** Principal Database Architect
**Technology:** PostgreSQL 16 + pgvector 0.7+
**Classification:** Confidential — Internal

---

## Table of Contents

1. [Entity-Relationship Diagram](#1-entity-relationship-diagram)
2. [Multi-Tenancy Strategy](#2-multi-tenancy-strategy)
3. [Schema Definitions](#3-schema-definitions)
4. [Relationships & Foreign Keys](#4-relationships--foreign-keys)
5. [Indexing Strategy](#5-indexing-strategy)
6. [Partitioning Strategy](#6-partitioning-strategy)
7. [Query Optimization](#7-query-optimization)
8. [Backup Strategy](#8-backup-strategy)
9. [Migration Strategy](#9-migration-strategy)
10. [Connection & Pooling](#10-connection--pooling)

---

## 1. Entity-Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              PATHFINDER DATABASE — ENTITY-RELATIONSHIP DIAGRAM                         │
│                                                                                                         │
│  ┌──────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐               │
│  │  tenants │     │      users       │     │    sessions      │     │   api_keys       │               │
│  │          │     │                  │     │                  │     │                  │               │
│  │ id (PK)  │◄──┐ │ id (PK)          │     │ id (PK)          │     │ id (PK)          │               │
│  │ name     │   ├─│ tenant_id (FK)   │──┐  │ user_id (FK)     │     │ user_id (FK)     │               │
│  │ plan     │   │ │ email            │  │  │ token_hash       │     │ key_hash         │               │
│  │ status   │   │ │ full_name        │  │  │ expires_at       │     │ name             │               │
│  │ settings │   │ │ avatar_url       │  │  │ created_at       │     │ permissions      │               │
│  └──────────┘   │ │ tier             │  │  └──────────────────┘     │ last_used_at     │               │
│                 │ │ status           │  │                            │ expires_at       │               │
│                 │ │ created_at       │  │                            └──────────────────┘               │
│                 │ └────────┬─────────┘  │                                                                 │
│                 │          │            │                                                                 │
│                 │          │ 1:N        │ 1:N                                                             │
│                 │          │            │                                                                 │
│                 │          ▼            ▼                                                                 │
│                 │ ┌──────────────────────────────┐    ┌──────────────────┐                                │
│                 │ │         profiles             │    │ user_preferences │                                │
│                 │ │                              │    │                  │                                │
│                 │ │ id (PK)                      │    │ id (PK)          │                                │
│                 │ │ user_id (FK, UNIQUE)         │    │ user_id (FK)     │                                │
│                 │ │ structured_data (JSONB)      │    │ version (INT)    │                                │
│                 │ │ embedding (VECTOR(3072))     │    │ is_current (BOOL)│                                │
│                 │ │ version (INT)                │    │ preference_data  │                                │
│                 │ │ is_active (BOOL)             │    │   (JSONB)        │                                │
│                 │ │ created_at                   │    │ confidence_      │                                │
│                 │ │ updated_at                   │    │   scores (JSONB) │                                │
│                 │ └──────────────┬───────────────┘    │ created_at       │                                │
│                 │                │                    └──────────────────┘                                │
│                 │                │ 1:N                                                                     │
│                 │                ▼                                                                         │
│                 │ ┌──────────────────────────────┐    ┌──────────────────┐                                │
│                 │ │        resumes               │    │ cover_letters    │                                │
│                 │ │                              │    │                  │                                │
│                 │ │ id (PK)                      │    │ id (PK)          │                                │
│                 │ │ user_id (FK)                 │    │ user_id (FK)     │                                │
│                 │ │ name                         │    │ application_id   │                                │
│                 │ │ template_id                  │    │   (FK, nullable) │                                │
│                 │ │ content (JSONB)              │    │ content (TEXT)   │                                │
│                 │ │ tailored_for_job_id (FK)     │    │ tone             │                                │
│                 │ │ file_url                     │    │ company_research │                                │
│                 │ │ performance_metrics (JSONB)  │    │   (JSONB)        │                                │
│                 │ │ is_base (BOOL)               │    │ created_at       │                                │
│                 │ │ created_at                   │    └──────────────────┘                                │
│                 │ └──────────────┬───────────────┘                                                         │
│                 │                │                                                                         │
│                 │                │ 1:N                                                                     │
│                 │                ▼                                                                         │
│                 │ ┌──────────────────────────────┐    ┌──────────────────┐    ┌──────────────────┐        │
│                 │ │        applications          │    │    interviews    │    │   offers         │        │
│                 │ │                              │    │                  │    │                  │        │
│                 │ │ id (PK)                      │    │ id (PK)          │    │ id (PK)          │        │
│                 │ │ user_id (FK)                 │◄───│ application_id   │    │ application_id   │        │
│                 │ │ job_id (FK)                  │    │   (FK)           │    │   (FK)           │        │
│                 │ │ resume_id (FK, nullable)     │    │ stage            │    │ compensation     │        │
│                 │ │ cover_letter_id (FK)         │    │ scheduled_at     │    │   (JSONB)        │        │
│                 │ │ status (ENUM)                │    │ interviewer_name │    │ status           │        │
│                 │ │ source_channel               │    │ notes (TEXT)     │    │ expires_at       │        │
│                 │ │ applied_at                   │    │ feedback (JSONB) │    │ created_at       │        │
│                 │ │ last_updated_at              │    │ created_at       │    └──────────────────┘        │
│                 │ └──────────────┬───────────────┘    └──────────────────┘                                │
│                 │                │                                                                         │
│                 │                │ 1:N                                                                     │
│                 │                ▼                                                                         │
│                 │ ┌──────────────────────────────┐    ┌──────────────────┐    ┌──────────────────┐        │
│                 │ │    application_tasks         │    │ application_     │    │ application_     │        │
│                 │ │                              │    │ communications  │    │ documents        │        │
│                 │ │ id (PK)                      │    │                  │    │                  │        │
│                 │ │ application_id (FK)          │    │ id (PK)          │    │ id (PK)          │        │
│                 │ │ task_type                    │    │ application_id   │    │ application_id   │        │
│                 │ │ title                        │    │   (FK)           │    │   (FK)           │        │
│                 │ │ due_at                       │    │ comm_type (ENUM) │    │ document_type    │        │
│                 │ │ is_completed                 │    │ subject          │    │ document_id (FK) │        │
│                 │ │ completed_at                 │    │ content (TEXT)   │    │ created_at       │        │
│                 │ │ created_at                   │    │ sent_at          │    └──────────────────┘        │
│                 │ └──────────────────────────────┘    │ created_at       │                                │
│                 │                                    └──────────────────┘                                │
│                 │                                                                                         │
│  ┌──────────────┴───────────────────────────────────────────────────────────────────────────────────┐    │
│  │                                         JOB DOMAIN                                                │    │
│  │                                                                                                   │    │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │    │
│  │  │  job_postings    │    │   companies      │    │  job_sources     │    │  job_enrichments │     │    │
│  │  │                  │    │                  │    │                  │    │                  │     │    │
│  │  │ id (PK)          │    │ id (PK)          │    │ id (PK)          │    │ id (PK)          │     │    │
│  │  │ canonical_job_id │◄───│ name             │    │ name             │    │ job_id (FK)      │     │    │
│  │  │ company_id (FK)  │    │ website          │    │ type             │    │ tech_stack       │     │    │
│  │  │ title            │    │ industry         │    │ base_url         │    │   (JSONB)        │     │    │
│  │  │ location         │    │ size_range       │    │ scraper_config   │    │ salary_range     │     │    │
│  │  │ description_raw  │    │ funding_stage    │    │   (JSONB)        │    │   (JSONB)        │     │    │
│  │  │ description_clean│    │ founded_year     │    │ health_status    │    │ seniority        │     │    │
│  │  │ remote_policy    │    │ headquarters     │    │ last_sweep_at    │    │ remote_policy    │     │    │
│  │  │ source_url       │    │ crunchbase_id    │    │ success_rate     │    │ required_skills  │     │    │
│  │  │ source_type      │    │ glassdoor_id     │    │ created_at       │    │   (JSONB)        │     │    │
│  │  │ job_embedding    │    │ tech_stack (JSONB)│   └──────────────────┘    │ nice_to_have     │     │    │
│  │  │   (VECTOR(3072)) │    │ culture_tags     │                            │   (JSONB)        │     │    │
│  │  │ is_active (BOOL) │    │   (JSONB)        │                            │ created_at       │     │    │
│  │  │ first_seen_at    │    │ created_at       │                            └──────────────────┘     │    │
│  │  │ last_seen_at     │    │ updated_at       │                                                     │    │
│  │  │ expires_at       │    └──────────────────┘                                                     │    │
│  │  │ created_at       │                                                                              │    │
│  │  └──────────────────┘                                                                              │    │
│  └───────────────────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                                         │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐    │
│  │                                      MEMORY DOMAIN                                                │    │
│  │                                                                                                   │    │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │    │
│  │  │ episodic_memories│    │semantic_memories │    │procedural_memory │    │semantic_memory  │     │    │
│  │  │                  │    │                  │    │                  │    │_versions         │     │    │
│  │  │ id (PK)          │    │ id (PK)          │    │ id (PK)          │    │ id (PK)          │     │    │
│  │  │ user_id (FK)     │    │ user_id (FK)     │    │ user_id (FK)     │    │ memory_id (FK)   │     │    │
│  │  │ session_id       │    │ memory_type      │    │ scope (ENUM)     │    │ version (INT)    │     │    │
│  │  │ episode_type     │    │   (ENUM)         │    │ pattern_type     │    │ content (JSONB)  │     │    │
│  │  │ actor (ENUM)     │    │ subject          │    │   (ENUM)         │    │ embedding        │     │    │
│  │  │ action (TEXT)    │    │ content (JSONB)  │    │ context_signature│    │   (VECTOR(3072)) │     │    │
│  │  │ payload (JSONB)  │    │ content_text     │    │ context_embedding│    │ change_desc      │     │    │
│  │  │ importance_score │    │ embedding        │    │   (VECTOR(1536)) │    │ created_at       │     │    │
│  │  │ embedding        │    │   (VECTOR(3072)) │    │ action_sequence  │    └──────────────────┘     │    │
│  │  │   (VECTOR(1536)) │    │ confidence       │    │   (JSONB)        │                               │    │
│  │  │ parent_episode   │    │ importance_score │    │ success_rate     │                               │    │
│  │  │   _id (FK)       │    │ evidence_count   │    │ execution_count  │                               │    │
│  │  │ consolidation_id │    │ evidence_episodes│    │ is_active (BOOL) │                               │    │
│  │  │ created_at (PK)  │    │ version (INT)    │    │ created_at       │                               │    │
│  │  │ PARTITION BY     │    │ is_active (BOOL) │    └──────────────────┘                               │    │
│  │  │   RANGE(created) │    │ created_at       │                                                       │    │
│  │  └──────────────────┘    └──────────────────┘                                                       │    │
│  │                                                                                                     │    │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │    │
│  │  │user_preferences  │    │ career_timeline  │    │skill_evolution   │    │compensation_     │     │    │
│  │  │                  │    │                  │    │                  │    │history           │     │    │
│  │  │ id (PK)          │    │ id (PK)          │    │ id (PK)          │    │ id (PK)          │     │    │
│  │  │ user_id (FK)     │    │ user_id (FK)     │    │ user_id (FK)     │    │ user_id (FK)     │     │    │
│  │  │ version (INT)    │    │ entry_type (ENUM)│    │ skill_name       │    │ career_entry_id  │     │    │
│  │  │ is_current (BOOL)│    │ title            │    │ proficiency (ENUM)│   │   (FK)           │     │    │
│  │  │ preference_data  │    │ description      │    │ assessed_at      │    │ base_salary      │     │    │
│  │  │   (JSONB)        │    │ structured_data  │    │ assessment_method│    │ currency         │     │    │
│  │  │ source_breakdown │    │   (JSONB)        │    │   (ENUM)         │    │ bonus_target     │     │    │
│  │  │   (JSONB)        │    │ start_date       │    │ evidence (JSONB) │    │ equity_grant     │     │    │
│  │  │ confidence_      │    │ end_date         │    │ embedding        │    │   (JSONB)        │     │    │
│  │  │   scores (JSONB) │    │ is_current (BOOL)│    │   (VECTOR(1536)) │    │ total_comp_est   │     │    │
│  │  │ change_summary   │    │ importance (ENUM)│    │ created_at       │    │ effective_date   │     │    │
│  │  │ created_at       │    │ verified (BOOL)  │    └──────────────────┘    │ created_at       │     │    │
│  │  └──────────────────┘    │ embedding        │                            └──────────────────┘     │    │
│  │                          │   (VECTOR(3072)) │                                                     │    │
│  │                          │ created_at       │                                                     │    │
│  │                          └──────────────────┘                                                     │    │
│  └──────────────────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                                         │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐    │
│  │                                   ANALYTICS & AUDIT DOMAIN                                         │    │
│  │                                                                                                   │    │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │    │
│  │  │  agent_executions│    │   audit_logs     │    │  learning_plans  │    │ career_goals     │     │    │
│  │  │                  │    │                  │    │                  │    │                  │     │    │
│  │  │ id (PK)          │    │ id (PK)          │    │ id (PK)          │    │ id (PK)          │     │    │
│  │  │ user_id (FK)     │    │ user_id (FK,     │    │ user_id (FK)     │    │ user_id (FK)     │     │    │
│  │  │ session_id       │    │   nullable)      │    │ title            │    │ goal_type (ENUM) │     │    │
│  │  │ agent_type (ENUM)│    │ actor_type (ENUM)│    │ description      │    │ title            │     │    │
│  │  │ action_type      │    │ action (TEXT)    │    │ target_role      │    │ description      │     │    │
│  │  │ input_context    │    │ resource_type    │    │ target_timeline  │    │ target_date      │     │    │
│  │  │   (JSONB)        │    │   (ENUM)         │    │ skill_gaps       │    │ status (ENUM)    │     │    │
│  │  │ output_summary   │    │ resource_id      │    │   (JSONB)        │    │ progress_pct     │     │    │
│  │  │   (JSONB)        │    │ changes (JSONB)  │    │ learning_items   │    │ created_at       │     │    │
│  │  │ tools_called     │    │ ip_address       │    │   (JSONB)        │    │ updated_at       │     │    │
│  │  │   (JSONB)        │    │ user_agent       │    │ status (ENUM)    │    └──────────────────┘     │    │
│  │  │ llm_model        │    │ created_at (PK)  │    │ created_at       │                               │    │
│  │  │ tokens_used      │    │ PARTITION BY     │    │ updated_at       │                               │    │
│  │  │   (JSONB)        │    │   RANGE(created) │    └──────────────────┘                               │    │
│  │  │ latency_ms       │    └──────────────────┘                                                       │    │
│  │  │ cost_estimate    │                                                                                │    │
│  │  │ is_success (BOOL)│                                                                                │    │
│  │  │ error_message    │                                                                                │    │
│  │  │ created_at       │                                                                                │    │
│  │  └──────────────────┘                                                                                │    │
│  └──────────────────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                                         │
│  LEGEND:                                                                                                 │
│  ──── 1:N relationship                                                                                   │
│  ◄──  Foreign key reference                                                                              │
│  (PK) Primary Key                                                                                        │
│  (FK) Foreign Key                                                                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Multi-Tenancy Strategy

### 2.1 Approach: Shared Database, Row-Level Isolation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MULTI-TENANCY ARCHITECTURE                                │
│                                                                              │
│  APPROACH: SHARED DATABASE WITH tenant_id SEGMENTATION                       │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │                SINGLE POSTGRESQL CLUSTER                       │    │   │
│  │  │                                                                │    │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │    │   │
│  │  │  │ Tenant A │  │ Tenant B │  │ Tenant C │  │  Tenant  │     │    │   │
│  │  │  │  Data    │  │  Data    │  │  Data    │  │   Data   │     │    │   │
│  │  │  │          │  │          │  │          │  │          │     │    │   │
│  │  │  │ All rows │  │ All rows │  │ All rows │  │ All rows │     │    │   │
│  │  │  │ tenant_id│  │ tenant_id│  │ tenant_id│  │ tenant_id│     │    │   │
│  │  │  │ = 'A'    │  │ = 'B'    │  │ = 'C'    │  │ = '...'  │     │    │   │
│  │  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  │                                                                       │   │
│  │  ISOLATION LAYER:                                                     │   │
│  │  ┌────────────────────────────────────────────────────────────────┐  │   │
│  │  │  ROW-LEVEL SECURITY (RLS)                                       │  │   │
│  │  │  ┌──────────────────────────────────────────────────────────┐  │  │   │
│  │  │  │  ALTER TABLE users ENABLE ROW LEVEL SECURITY;             │  │  │   │
│  │  │  │  CREATE POLICY tenant_isolation ON users                  │  │  │   │
│  │  │  │    USING (tenant_id = current_setting('app.tenant_id'));  │  │  │   │
│  │  │  └──────────────────────────────────────────────────────────┘  │  │   │
│  │  │                                                                │  │   │
│  │  │  APPLICATION LAYER                                             │  │   │
│  │  │  ┌──────────────────────────────────────────────────────────┐  │  │   │
│  │  │  │  · API Gateway injects tenant_id into every request       │  │  │   │
│  │  │  │  · Connection pooler sets app.tenant_id per session       │  │  │   │
│  │  │  │  · Every query filtered by WHERE tenant_id = $tenant_id   │  │  │   │
│  │  │  │  · RLS as defense-in-depth (catches missing WHERE clause) │  │  │   │
│  │  │  └──────────────────────────────────────────────────────────┘  │  │   │
│  │  └────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  TENANT TYPES:                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ TYPE              │ DESCRIPTION                  │ tenant_id FORMAT  │   │
│  │ ─────────────────┼─────────────────────────────┼──────────────────  │   │
│  │ individual_user   │ Standard end-user account    │ Direct UUID       │   │
│  │ enterprise        │ University, bootcamp,        │ Separate tenant    │   │
│  │                   │ outplacement firm            │ record UUID       │   │
│  │ marketplace       │ Employer/recruiter (V3)      │ Separate tenant    │   │
│  │                   │                              │ record UUID       │   │
│  │ internal          │ Pathfinder internal ops      │ System reserved   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  TENANT-SCOPED TABLES (all queries include WHERE tenant_id = $1):            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ users, profiles, resumes, cover_letters, applications, interviews    │   │
│  │ offers, application_tasks, application_communications,               │   │
│  │ episodic_memories, semantic_memories, procedural_memories,           │   │
│  │ user_preferences, career_timeline, skill_evolution,                  │   │
│  │ compensation_history, learning_plans, career_goals,                  │   │
│  │ agent_executions, api_keys, sessions                                 │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  SHARED TABLES (cross-tenant, read-only for tenants):                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ job_postings, companies, job_sources, job_enrichments                │   │
│  │ (these are shared reference data, not user-owned)                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 RLS Implementation Strategy

| Layer | Mechanism | Purpose |
|-------|-----------|---------|
| **Application** | Every query builder injects `WHERE tenant_id = $current_tenant` | Primary isolation — catch at code review |
| **Connection** | `SET app.tenant_id = $tenant_id` on every pooled connection acquisition | Session-level variable for RLS |
| **Database** | Row-Level Security policies on all tenant-scoped tables | Defense-in-depth — catches missing WHERE clauses |
| **Audit** | All queries logged with tenant_id for forensic analysis | Breach detection |

### 2.3 tenant_id Column Convention

- Every tenant-scoped table includes `tenant_id UUID NOT NULL` as the first column after the primary key
- `tenant_id` is always part of composite indexes where it makes sense
- Partitioned tables include `tenant_id` in the partition pruning path where possible

---

## 3. Schema Definitions

### 3.1 Tenant & User Management

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TABLE: tenants                                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK, DEFAULT gen_random() │  │
│  │ name                │ VARCHAR(255)            │ NOT NULL                 │  │
│  │ slug                │ VARCHAR(100)            │ NOT NULL, UNIQUE         │  │
│  │ plan                │ PLAN_ENUM               │ NOT NULL                 │  │
│  │ status              │ TENANT_STATUS_ENUM      │ NOT NULL, DEFAULT active │  │
│  │ billing_email       │ VARCHAR(320)            │                          │  │
│  │ settings            │ JSONB                   │ DEFAULT '{}'             │  │
│  │ max_users           │ INTEGER                 │                          │  │
│  │ storage_limit_bytes │ BIGINT                  │                          │  │
│  │ created_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  │ updated_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  │ deleted_at          │ TIMESTAMPTZ             │ Soft delete              │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ENUM: PLAN_ENUM = 'free' | 'pro' | 'premium' | 'enterprise' | 'internal'    │
│  ENUM: TENANT_STATUS_ENUM = 'active' | 'suspended' | 'deleted' | 'trial'     │
│                                                                              │
│  TABLE: users                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK, DEFAULT gen_random() │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ email               │ VARCHAR(320)            │ NOT NULL                 │  │
│  │ email_verified      │ BOOLEAN                 │ NOT NULL, DEFAULT FALSE  │  │
│  │ full_name           │ VARCHAR(255)            │ NOT NULL                 │  │
│  │ avatar_url          │ TEXT                    │                          │  │
│  │ hashed_password     │ VARCHAR(255)            │ NULL (for OAuth users)   │  │
│  │ oauth_provider      │ VARCHAR(50)             │ 'google','github',NULL   │  │
│  │ oauth_subject       │ VARCHAR(255)            │ OAuth ID from provider   │  │
│  │ tier                │ TIER_ENUM               │ NOT NULL, DEFAULT 'free' │  │
│  │ status              │ USER_STATUS_ENUM        │ NOT NULL, DEFAULT active │  │
│  │ role                │ USER_ROLE_ENUM          │ NOT NULL, DEFAULT 'user' │  │
│  │ locale              │ VARCHAR(10)             │ DEFAULT 'en-US'          │  │
│  │ timezone            │ VARCHAR(50)             │ DEFAULT 'UTC'            │  │
│  │ last_login_at       │ TIMESTAMPTZ             │                          │  │
│  │ created_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  │ updated_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  │ deleted_at          │ TIMESTAMPTZ             │ Soft delete              │  │
│  │                      │                        │                          │  │
│  │ UNIQUE: (tenant_id, email)                    │ One email per tenant     │  │
│  │ UNIQUE: (oauth_provider, oauth_subject)       │ One OAuth link           │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ENUM: TIER_ENUM = 'free' | 'pro' | 'premium'                                │
│  ENUM: USER_STATUS_ENUM = 'active' | 'inactive' | 'suspended' | 'deleted'    │
│  ENUM: USER_ROLE_ENUM = 'user' | 'admin' | 'support'                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Authentication & Sessions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TABLE: sessions                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK, DEFAULT gen_random() │  │
│  │ user_id             │ UUID                    │ FK→users, NOT NULL      │  │
│  │ token_hash          │ VARCHAR(255)            │ NOT NULL, UNIQUE         │  │
│  │ refresh_token_hash  │ VARCHAR(255)            │ NOT NULL                 │  │
│  │ ip_address          │ INET                    │                          │  │
│  │ user_agent          │ TEXT                    │                          │  │
│  │ is_revoked          │ BOOLEAN                 │ NOT NULL, DEFAULT FALSE  │  │
│  │ expires_at          │ TIMESTAMPTZ             │ NOT NULL                 │  │
│  │ last_activity_at    │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  │ created_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  │                      │                        │                          │  │
│  │ INDEX: idx_sessions_user (user_id, is_revoked)│                          │  │
│  │ INDEX: idx_sessions_expires (expires_at) WHERE is_revoked = false        │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: api_keys                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ user_id             │ UUID                    │ FK→users, NOT NULL      │  │
│  │ key_prefix          │ VARCHAR(8)              │ NOT NULL (for UI display) │  │
│  │ key_hash            │ VARCHAR(255)            │ NOT NULL, UNIQUE         │  │
│  │ name                │ VARCHAR(255)            │ NOT NULL                 │  │
│  │ permissions         │ JSONB                   │ DEFAULT '[]'             │  │
│  │ last_used_at        │ TIMESTAMPTZ             │                          │  │
│  │ expires_at          │ TIMESTAMPTZ             │                          │  │
│  │ is_revoked          │ BOOLEAN                 │ DEFAULT FALSE            │  │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Profiles & Resumes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TABLE: profiles                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ user_id             │ UUID                    │ FK→users, UNIQUE, NOT NULL│ │
│  │ version             │ INTEGER                 │ NOT NULL, DEFAULT 1      │  │
│  │ is_active           │ BOOLEAN                 │ NOT NULL, DEFAULT TRUE   │  │
│  │ structured_data     │ JSONB                   │ NOT NULL                 │  │
│  │ embedding           │ VECTOR(3072)            │                          │  │
│  │ summary             │ TEXT                    │ LLM-generated summary    │  │
│  │ parsing_confidence  │ JSONB                   │ Per-field confidence     │  │
│  │ enrichment_data     │ JSONB                   │ GitHub, LinkedIn enrich  │  │
│  │ source              │ TEXT[]                  │ 'resume','linkedin',etc. │  │
│  │ created_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  │ updated_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  structured_data JSONB structure:                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ {                                                                        │  │
│  │   "full_name": "David Chen",                                             │  │
│  │   "headline": "Senior Full-Stack Engineer",                              │  │
│  │   "email": "david@example.com",                                          │  │
│  │   "phone": "+1-555-0123",                                                │  │
│  │   "location": {"city": "San Francisco", "state": "CA", "country": "US"}, │  │
│  │   "work_experiences": [{                                                 │  │
│  │     "id": "we_001",                                                      │  │
│  │     "company": "Stripe",                                                 │  │
│  │     "title": "Senior Software Engineer",                                 │  │
│  │     "start_date": "2024-03",                                             │  │
│  │     "end_date": null,                                                    │  │
│  │     "is_current": true,                                                  │  │
│  │     "description": "Led payment API redesign...",                        │  │
│  │     "achievements": ["Reduced latency 40%", "Mentored 4 engineers"],     │  │
│  │     "tech_stack": ["Ruby", "Java", "AWS", "PostgreSQL"],                 │  │
│  │     "verified": true                                                     │  │
│  │   }],                                                                    │  │
│  │   "education": [{                                                        │  │
│  │     "id": "edu_001",                                                     │  │
│  │     "institution": "UCLA",                                               │  │
│  │     "degree": "Bachelor of Science",                                     │  │
│  │     "field": "Computer Science",                                         │  │
│  │     "graduation_year": 2018                                              │  │
│  │   }],                                                                    │  │
│  │   "skills": [{                                                           │  │
│  │     "name": "Python",                                                    │  │
│  │     "proficiency": "expert",                                             │  │
│  │     "years": 8,                                                          │  │
│  │     "last_used": "2026-06",                                              │  │
│  │     "category": "programming_language",                                  │  │
│  │     "sub_skills": ["FastAPI", "pandas", "pytest"],                       │  │
│  │     "verified": true                                                     │  │
│  │   }],                                                                    │  │
│  │   "projects": [...],                                                     │  │
│  │   "certifications": [...],                                               │  │
│  │   "publications": [...],                                                 │  │
│  │   "languages": [...],                                                    │  │
│  │   "links": {                                                             │  │
│  │     "linkedin": "https://linkedin.com/in/davidchen",                     │  │
│  │     "github": "https://github.com/davidchen",                            │  │
│  │     "portfolio": "https://davidchen.dev"                                 │  │
│  │   }                                                                      │  │
│  │ }                                                                        │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: resumes                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ user_id             │ UUID                    │ FK→users, NOT NULL       │  │
│  │ name                │ VARCHAR(255)            │ NOT NULL                 │  │
│  │ description         │ TEXT                    │                          │  │
│  │ template_id         │ VARCHAR(50)             │ NOT NULL, DEFAULT 'base' │  │
│  │ content             │ JSONB                   │ NOT NULL                 │  │
│  │ file_url            │ TEXT                    │ S3/MinIO path to PDF     │  │
│  │ file_format         │ VARCHAR(10)             │ 'pdf','docx','tex','txt' │  │
│  │ is_base             │ BOOLEAN                 │ DEFAULT FALSE            │  │
│  │ tailored_for_job_id │ UUID                    │ FK→job_postings, NULL    │  │
│  │ tailored_for_role   │ VARCHAR(255)            │ Generic role type        │  │
│  │ performance_metrics │ JSONB                   │ callback_rate, views     │  │
│  │ ats_parse_score     │ SMALLINT                │ 0-100 prediction         │  │
│  │ created_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  │ updated_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: cover_letters                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ user_id             │ UUID                    │ FK→users, NOT NULL       │  │
│  │ application_id      │ UUID                    │ FK→applications, NULL    │  │
│  │ content             │ TEXT                    │ NOT NULL                 │  │
│  │ tone                │ VARCHAR(50)             │ DEFAULT 'professional'   │  │
│  │ company_research    │ JSONB                   │ Research used in letter  │  │
│  │ factuality_score    │ REAL                    │ 0.0-1.0                  │  │
│  │ version             │ INTEGER                 │ DEFAULT 1                │  │
│  │ created_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Jobs Domain

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TABLE: companies                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ name                │ VARCHAR(255)            │ NOT NULL                 │  │
│  │ canonical_name      │ VARCHAR(255)            │ NOT NULL, UNIQUE         │  │
│  │ website             │ TEXT                    │                          │  │
│  │ industry            │ VARCHAR(100)            │                          │  │
│  │ industry_tags       │ TEXT[]                  │                          │  │
│  │ size_range          │ VARCHAR(20)             │ '1-10','11-50',...       │  │
│  │ employee_count      │ INTEGER                 │                          │  │
│  │ funding_stage       │ VARCHAR(50)             │ 'seed','series_a',...    │  │
│  │ total_funding       │ BIGINT                  │ In USD                   │  │
│  │ founded_year        │ SMALLINT                │                          │  │
│  │ headquarters        │ JSONB                   │ {city,state,country}     │  │
│  │ locations           │ JSONB[]                 │ Other offices            │  │
│  │ tech_stack          │ JSONB                   │ Known technology         │  │
│  │ culture_tags        │ JSONB                   │ Extracted signals        │  │
│  │ crunchbase_id       │ VARCHAR(100)            │                          │  │
│  │ glassdoor_rating    │ REAL                    │                          │  │
│  │ career_page_url     │ TEXT                    │                          │  │
│  │ created_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  │ updated_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: job_postings                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ canonical_job_id    │ VARCHAR(64)             │ NOT NULL (dedup key)     │  │
│  │ company_id          │ UUID                    │ FK→companies             │  │
│  │ title               │ VARCHAR(255)            │ NOT NULL                 │  │
│  │ normalized_title    │ VARCHAR(255)            │ Standardized title       │  │
│  │ location            │ JSONB                   │ {city,state,country}     │  │
│  │ remote_policy       │ VARCHAR(20)             │ 'onsite','hybrid','remote'│ │
│  │ description_raw     │ TEXT                    │ Original HTML/MD         │  │
│  │ description_clean   │ TEXT                    │ Cleaned text             │  │
│  │ description_summary │ TEXT                    │ LLM 3-sentence summary   │  │
│  │ source_url          │ TEXT                    │ NOT NULL                 │  │
│  │ source_type         │ VARCHAR(50)             │ 'linkedin','indeed',...  │  │
│  │ application_url     │ TEXT                    │ Direct apply URL         │  │
│  │ job_embedding       │ VECTOR(3072)            │                          │  │
│  │ is_active           │ BOOLEAN                 │ NOT NULL, DEFAULT TRUE   │  │
│  │ is_verified         │ BOOLEAN                 │ DEFAULT FALSE            │  │
│  │ first_seen_at       │ TIMESTAMPTZ             │ NOT NULL                 │  │
│  │ last_seen_at        │ TIMESTAMPTZ             │ NOT NULL                 │  │
│  │ refreshed_at        │ TIMESTAMPTZ             │ When re-encountered      │  │
│  │ expires_at          │ TIMESTAMPTZ             │ Estimated expiry         │  │
│  │ created_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  │ updated_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  │                      │                        │                          │  │
│  │ UNIQUE: (canonical_job_id)                    │                          │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: job_sources                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ name                │ VARCHAR(100)            │ NOT NULL, UNIQUE         │  │
│  │ type                │ VARCHAR(50)             │ 'job_board','career_page'│  │
│  │ base_url            │ TEXT                    │                          │  │
│  │ scraper_config      │ JSONB                   │ NOT NULL                 │  │
│  │ priority            │ SMALLINT                │ 1-10, 1=highest          │  │
│  │ sweep_interval_min  │ INTEGER                 │ Minutes between sweeps   │  │
│  │ health_status       │ VARCHAR(20)             │ 'healthy','degraded',... │  │
│  │ last_sweep_at       │ TIMESTAMPTZ             │                          │  │
│  │ last_sweep_status   │ VARCHAR(20)             │ 'success','partial',...  │  │
│  │ success_rate        │ REAL                    │ Rolling 24h              │  │
│  │ jobs_per_sweep_avg  │ REAL                    │ Rolling 7d               │  │
│  │ consecutive_fails   │ SMALLINT                │ Alert threshold          │  │
│  │ is_enabled          │ BOOLEAN                 │ DEFAULT TRUE             │  │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: job_enrichments                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ job_id              │ UUID                    │ FK→job_postings, UNIQUE  │  │
│  │ tech_stack          │ JSONB                   │ Inferred technologies    │  │
│  │ salary_range        │ JSONB                   │ {min,max,currency,src}   │  │
│  │ seniority           │ VARCHAR(30)             │ 'junior','mid',...       │  │
│  │ required_skills     │ JSONB                   │ [{name,importance}]      │  │
│  │ nice_to_have_skills │ JSONB                   │ [{name,importance}]      │  │
│  │ required_years_min  │ SMALLINT                │                          │  │
│  │ education_required  │ VARCHAR(100)            │                          │  │
│  │ interview_process   │ JSONB                   │ Known process details    │  │
│  │ benefits_inferred   │ JSONB                   │ Extracted from JD        │  │
│  │ urgency_flag        │ BOOLEAN                 │ "Urgently hiring" signal │  │
│  │ enrichment_version  │ INTEGER                 │ DEFAULT 1                │  │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  │ updated_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.5 Applications Domain

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TABLE: applications                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ user_id             │ UUID                    │ FK→users, NOT NULL       │  │
│  │ job_id              │ UUID                    │ FK→job_postings          │  │
│  │ resume_id           │ UUID                    │ FK→resumes, NULL         │  │
│  │ cover_letter_id     │ UUID                    │ FK→cover_letters, NULL   │  │
│  │ status              │ APP_STATUS_ENUM         │ NOT NULL                 │  │
│  │ status_history      │ JSONB                   │ Array of status changes  │  │
│  │ source_channel      │ VARCHAR(50)             │ How user found this job  │  │
│  │ match_score_at_apply│ REAL                    │ Snapshot of match score  │  │
│  │ notes               │ TEXT                    │ User notes               │  │
│  │ applied_at          │ TIMESTAMPTZ             │ When submitted           │  │
│  │ last_updated_at     │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  │ next_follow_up_at   │ TIMESTAMPTZ             │ Suggested follow-up      │  │
│  │ is_archived         │ BOOLEAN                 │ DEFAULT FALSE            │  │
│  │ created_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  │                      │                        │                          │  │
│  │ UNIQUE: (user_id, job_id) — prevent duplicates│                          │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ENUM: APP_STATUS_ENUM = 'saved' | 'applied' | 'phone_screen' |              │
│        'technical_interview' | 'onsite' | 'take_home' | 'offer' |            │
│        'accepted' | 'rejected' | 'withdrawn' | 'ghosted'                     │
│                                                                              │
│  TABLE: interviews                                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ application_id      │ UUID                    │ FK→applications, NOT NULL│  │
│  │ stage               │ VARCHAR(50)             │ NOT NULL                 │  │
│  │ scheduled_at        │ TIMESTAMPTZ             │                          │  │
│  │ duration_minutes    │ SMALLINT                │                          │  │
│  │ interviewer_name    │ VARCHAR(255)            │                          │  │
│  │ interviewer_role    │ VARCHAR(100)            │                          │  │
│  │ location            │ VARCHAR(50)             │ 'zoom','phone','onsite'  │  │
│  │ meeting_link        │ TEXT                    │                          │  │
│  │ status              │ VARCHAR(30)             │ 'scheduled','completed', │  │
│  │                     │                        │  'cancelled','no_show'   │  │
│  │ notes               │ TEXT                    │ User's notes             │  │
│  │ feedback            │ JSONB                   │ Structured feedback      │  │
│  │ outcome             │ VARCHAR(30)             │ 'passed','failed','pending'│ │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  │ updated_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: offers                                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ application_id      │ UUID                    │ FK→applications, UNIQUE  │  │
│  │ compensation        │ JSONB                   │ Full comp breakdown      │  │
│  │ status              │ VARCHAR(20)             │ 'pending','accepted',    │  │
│  │                     │                        │  'declined','expired'    │  │
│  │ expires_at          │ TIMESTAMPTZ             │                          │  │
│  │ negotiated          │ BOOLEAN                 │ DEFAULT FALSE            │  │
│  │ negotiation_history │ JSONB                   │ Round-by-round changes   │  │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: application_tasks                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ application_id      │ UUID                    │ FK→applications, NOT NULL│  │
│  │ task_type           │ VARCHAR(50)             │ NOT NULL                 │  │
│  │ title               │ TEXT                    │ NOT NULL                 │  │
│  │ description         │ TEXT                    │                          │  │
│  │ due_at              │ TIMESTAMPTZ             │                          │  │
│  │ is_completed        │ BOOLEAN                 │ DEFAULT FALSE            │  │
│  │ completed_at        │ TIMESTAMPTZ             │                          │  │
│  │ created_by          │ VARCHAR(50)             │ 'user','agent','system'  │  │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: application_communications                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ application_id      │ UUID                    │ FK→applications, NOT NULL│  │
│  │ comm_type           │ COMM_TYPE_ENUM          │ NOT NULL                 │  │
│  │ subject             │ TEXT                    │                          │  │
│  │ content             │ TEXT                    │ NOT NULL                 │  │
│  │ sent_at             │ TIMESTAMPTZ             │                          │  │
│  │ sent_via            │ VARCHAR(50)             │ 'email','linkedin',...   │  │
│  │ generated_by        │ VARCHAR(50)             │ 'agent','user','template'│  │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ENUM: COMM_TYPE_ENUM = 'follow_up' | 'thank_you' | 'outreach' |              │
│        'recruiter_response' | 'offer_acceptance' | 'offer_decline' |         │
│        'networking' | 'other'                                                  │
│                                                                              │
│  TABLE: application_documents                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ application_id      │ UUID                    │ FK→applications, NOT NULL│  │
│  │ document_type       │ VARCHAR(30)             │ 'resume','cover_letter', │  │
│  │                     │                        │  'portfolio','assessment' │  │
│  │ document_id         │ UUID                    │ FK to resumes/cover etc  │  │
│  │ file_url            │ TEXT                    │ Direct S3 URL            │  │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.6 Memory Domain (Complete)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TABLE: episodic_memories                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │                         │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ user_id             │ UUID                    │ FK→users, NOT NULL       │  │
│  │ session_id          │ UUID                    │ NOT NULL                 │  │
│  │ episode_type        │ EPISODE_ENUM            │ NOT NULL                 │  │
│  │ actor               │ ACTOR_ENUM              │ NOT NULL                 │  │
│  │ action              │ TEXT                    │ NOT NULL                 │  │
│  │ payload             │ JSONB                   │ NOT NULL                 │  │
│  │ importance_score    │ REAL                    │ DEFAULT 0.5               │  │
│  │ emotion_signal      │ REAL                    │ -1.0 to 1.0              │  │
│  │ embedding           │ VECTOR(1536)            │                          │  │
│  │ context_summary     │ TEXT                    │ 1-line LLM summary        │  │
│  │ parent_episode_id   │ UUID                    │ FK→episodic_memories     │  │
│  │ consolidation_id    │ UUID                    │ FK→consolidation_runs    │  │
│  │ created_at          │ TIMESTAMPTZ             │ NOT NULL                 │  │
│  │ recorded_at         │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  │ expires_at          │ TIMESTAMPTZ             │ TTL-based                │  │
│  │                      │                        │                          │  │
│  │ PRIMARY KEY: (id, created_at)                                              │  │
│  │ PARTITION BY: RANGE (created_at) — daily partitions                      │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: semantic_memories                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ user_id             │ UUID                    │ FK→users, NOT NULL       │  │
│  │ memory_type         │ SEMANTIC_ENUM           │ NOT NULL                 │  │
│  │ subject             │ TEXT                    │ NOT NULL                 │  │
│  │ content             │ JSONB                   │ NOT NULL                 │  │
│  │ content_text        │ TEXT                    │ Searchable text          │  │
│  │ embedding           │ VECTOR(3072)            │                          │  │
│  │ confidence          │ REAL                    │ DEFAULT 0.5              │  │
│  │ evidence_episodes   │ UUID[]                  │ Source episode IDs       │  │
│  │ evidence_count      │ INTEGER                 │ DEFAULT 1                │  │
│  │ importance_score    │ REAL                    │ DEFAULT 0.5              │  │
│  │ access_count        │ INTEGER                 │ DEFAULT 0                │  │
│  │ last_accessed_at    │ TIMESTAMPTZ             │                          │  │
│  │ last_updated_at     │ TIMESTAMPTZ             │                          │  │
│  │ consolidation_run_id│ UUID                    │ FK→consolidation_runs    │  │
│  │ version             │ INTEGER                 │ DEFAULT 1                │  │
│  │ is_active           │ BOOLEAN                 │ DEFAULT TRUE             │  │
│  │ created_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: semantic_memory_versions                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ memory_id           │ UUID                    │ FK→semantic_memories     │  │
│  │ version             │ INTEGER                 │ NOT NULL                 │  │
│  │ content             │ JSONB                   │ NOT NULL                 │  │
│  │ content_text        │ TEXT                    │                          │  │
│  │ embedding           │ VECTOR(3072)            │                          │  │
│  │ change_description  │ TEXT                    │                          │  │
│  │ created_by          │ ACTOR_ENUM              │                          │  │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  │                      │                        │                          │  │
│  │ UNIQUE: (memory_id, version)                  │                          │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: procedural_memories                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ user_id             │ UUID                    │ FK→users, NULL           │  │
│  │ scope               │ SCOPE_ENUM              │ NOT NULL                 │  │
│  │ pattern_type        │ PATTERN_ENUM            │ NOT NULL                 │  │
│  │ context_signature   │ TEXT                    │ NOT NULL                 │  │
│  │ context_embedding   │ VECTOR(1536)            │                          │  │
│  │ action_sequence     │ JSONB                   │ NOT NULL                 │  │
│  │ expected_outcome    │ TEXT                    │                          │  │
│  │ success_rate        │ REAL                    │ DEFAULT 0.0              │  │
│  │ execution_count     │ INTEGER                 │ DEFAULT 0                │  │
│  │ avg_latency_ms      │ INTEGER                 │                          │  │
│  │ avg_token_cost      │ INTEGER                 │                          │  │
│  │ last_executed_at    │ TIMESTAMPTZ             │                          │  │
│  │ is_active           │ BOOLEAN                 │ DEFAULT TRUE             │  │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  │ updated_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: user_preferences                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ user_id             │ UUID                    │ FK→users, NOT NULL       │  │
│  │ version             │ INTEGER                 │ NOT NULL                 │  │
│  │ is_current          │ BOOLEAN                 │ NOT NULL, DEFAULT TRUE   │  │
│  │ preference_data     │ JSONB                   │ NOT NULL                 │  │
│  │ source_breakdown    │ JSONB                   │ Explicit vs implicit     │  │
│  │ confidence_scores   │ JSONB                   │ Per-field confidence     │  │
│  │ evidence_episodes   │ UUID[]                  │ Supporting episodes      │  │
│  │ change_summary      │ TEXT                    │ What changed from prev   │  │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: career_timeline                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ user_id             │ UUID                    │ FK→users, NOT NULL       │  │
│  │ entry_type          │ CAREER_ENUM             │ NOT NULL                 │  │
│  │ title               │ TEXT                    │ NOT NULL                 │  │
│  │ description         │ TEXT                    │                          │  │
│  │ structured_data     │ JSONB                   │ NOT NULL                 │  │
│  │ start_date          │ DATE                    │                          │  │
│  │ end_date            │ DATE                    │ NULL = current           │  │
│  │ is_current          │ BOOLEAN                 │ DEFAULT FALSE            │  │
│  │ importance          │ IMPORTANCE_ENUM         │ DEFAULT 'minor'          │  │
│  │ source              │ TEXT                    │ How we learned this      │  │
│  │ verified            │ BOOLEAN                 │ DEFAULT FALSE            │  │
│  │ embedding           │ VECTOR(3072)            │                          │  │
│  │ version             │ INTEGER                 │ DEFAULT 1                │  │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  │ updated_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: compensation_history                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ user_id             │ UUID                    │ FK→users, NOT NULL       │  │
│  │ career_entry_id     │ UUID                    │ FK→career_timeline       │  │
│  │ base_salary         │ NUMERIC(12,2)           │                          │  │
│  │ currency            │ CHAR(3)                 │ ISO 4217                 │  │
│  │ bonus_target        │ NUMERIC(5,2)            │ Percentage               │  │
│  │ equity_grant        │ JSONB                   │ Type, shares, vesting    │  │
│  │ total_comp_estimated│ NUMERIC(12,2)           │                          │  │
│  │ benefits_summary    │ JSONB                   │ Health, 401k, PTO        │  │
│  │ effective_date      │ DATE                    │                          │  │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  TABLE: skill_evolution                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ user_id             │ UUID                    │ FK→users, NOT NULL       │  │
│  │ skill_name          │ VARCHAR(100)            │ NOT NULL                 │  │
│  │ proficiency         │ PROFICIENCY_ENUM        │ NOT NULL                 │  │
│  │ assessed_at         │ DATE                    │ NOT NULL                 │  │
│  │ assessment_method   │ ASSESS_ENUM             │ NOT NULL                 │  │
│  │ evidence            │ JSONB                   │                          │  │
│  │ embedding           │ VECTOR(1536)            │                          │  │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.7 Career Goals & Learning

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TABLE: career_goals                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ user_id             │ UUID                    │ FK→users, NOT NULL       │  │
│  │ goal_type           │ GOAL_ENUM               │ NOT NULL                 │  │
│  │ title               │ VARCHAR(255)            │ NOT NULL                 │  │
│  │ description         │ TEXT                    │                          │  │
│  │ target_date         │ DATE                    │                          │  │
│  │ status              │ GOAL_STATUS_ENUM        │ DEFAULT 'active'         │  │
│  │ progress_pct        │ REAL                    │ DEFAULT 0.0              │  │
│  │ parent_goal_id      │ UUID                    │ FK→career_goals, NULL    │  │
│  │ priority            │ SMALLINT                │ DEFAULT 3                │  │
│  │ metadata            │ JSONB                   │ Extra context            │  │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  │ updated_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  │ completed_at        │ TIMESTAMPTZ             │                          │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ENUM: GOAL_ENUM = 'role_transition' | 'skill_acquisition' |                  │
│        'compensation_target' | 'promotion' | 'company_target' |               │
│        'relocation' | 'certification' | 'project_completion' | 'other'        │
│  ENUM: GOAL_STATUS_ENUM = 'active' | 'in_progress' | 'completed' |            │
│        'abandoned' | 'on_hold'                                                 │
│                                                                              │
│  TABLE: learning_plans                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ user_id             │ UUID                    │ FK→users, NOT NULL       │  │
│  │ career_goal_id      │ UUID                    │ FK→career_goals, NULL    │  │
│  │ title               │ VARCHAR(255)            │ NOT NULL                 │  │
│  │ description         │ TEXT                    │                          │  │
│  │ target_role         │ VARCHAR(255)            │                          │  │
│  │ target_timeline     │ VARCHAR(50)             │ '30d','90d','6m','1y'    │  │
│  │ skill_gaps          │ JSONB                   │ [{skill,current,target}] │  │
│  │ learning_items      │ JSONB                   │ Array of learning items  │  │
│  │ status              │ PLAN_STATUS_ENUM        │ DEFAULT 'active'         │  │
│  │ started_at          │ TIMESTAMPTZ             │                          │  │
│  │ completed_at        │ TIMESTAMPTZ             │                          │  │
│  │ created_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  │ updated_at          │ TIMESTAMPTZ             │ DEFAULT NOW()            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  learning_items JSONB structure:                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ [                                                                        │  │
│  │   {                                                                      │  │
│  │     "week": 1,                                                           │  │
│  │     "focus_area": "Data Structures",                                     │  │
│  │     "resources": [                                                       │  │
│  │       {                                                                  │  │
│  │         "title": "Grokking Algorithms",                                  │  │
│  │         "type": "book",                                                  │  │
│  │         "url": "https://...",                                            │  │
│  │         "cost": 39.99,                                                   │  │
│  │         "estimated_hours": 20,                                           │  │
│  │         "priority": "critical"                                           │  │
│  │       }                                                                  │  │
│  │     ],                                                                   │  │
│  │     "milestone": "Complete 40 LeetCode Easy problems",                   │  │
│  │     "estimated_hours": 15,                                               │  │
│  │     "status": "not_started"                                              │  │
│  │   }                                                                      │  │
│  │ ]                                                                        │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.8 Agent Executions & Audit

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TABLE: agent_executions                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │ PK                       │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NOT NULL     │  │
│  │ user_id             │ UUID                    │ FK→users, NOT NULL       │  │
│  │ session_id          │ UUID                    │ NOT NULL                 │  │
│  │ call_id             │ UUID                    │ NOT NULL, UNIQUE         │  │
│  │ parent_call_id      │ UUID                    │ FK→agent_executions      │  │
│  │ agent_type          │ AGENT_ENUM              │ NOT NULL                 │  │
│  │ action_type         │ VARCHAR(100)            │ NOT NULL                 │  │
│  │ input_context       │ JSONB                   │ Context sent to agent    │  │
│  │ output_summary      │ JSONB                   │ Structured output        │  │
│  │ tools_called        │ JSONB                   │ [{tool, params_hash, ...}]│ │
│  │ llm_model           │ VARCHAR(50)             │ NOT NULL                 │  │
│  │ llm_provider        │ VARCHAR(20)             │ 'deepseek','openai',...  │  │
│  │ tokens_used         │ JSONB                   │ {input, output, total}   │  │
│  │ latency_ms          │ INTEGER                 │ Wall clock               │  │
│  │ cost_estimate       │ NUMERIC(10,6)           │ In USD                   │  │
│  │ is_success          │ BOOLEAN                 │ NOT NULL                 │  │
│  │ error_message       │ TEXT                    │                          │  │
│  │ error_type          │ VARCHAR(50)             │ 'llm_timeout','tool_fail'│  │
│  │ retry_count         │ SMALLINT                │ DEFAULT 0                │  │
│  │ user_approved       │ BOOLEAN                 │ For HITL gates           │  │
│  │ user_modified       │ BOOLEAN                 │ User edited output       │  │
│  │ created_at          │ TIMESTAMPTZ             │ NOT NULL, DEFAULT NOW()  │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ENUM: AGENT_ENUM = 'supervisor' | 'profile' | 'job_discovery' |              │
│        'job_matching' | 'resume' | 'cover_letter' | 'interview' |             │
│        'career_coach' | 'application_tracking' | 'follow_up' | 'memory'       │
│                                                                              │
│  TABLE: audit_logs                                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ COLUMN              │ TYPE                    │ CONSTRAINTS             │  │
│  │ ───────────────────┼────────────────────────┼─────────────────────────│  │
│  │ id                  │ UUID                    │                         │  │
│  │ tenant_id           │ UUID                    │ FK→tenants, NULL         │  │
│  │ user_id             │ UUID                    │ FK→users, NULL           │  │
│  │ actor_type          │ ACTOR_ENUM              │ NOT NULL                 │  │
│  │ actor_id            │ UUID                    │ Who performed action     │  │
│  │ action              │ TEXT                    │ NOT NULL                 │  │
│  │ action_category     │ VARCHAR(50)             │ 'auth','data','agent',...│  │
│  │ resource_type       │ VARCHAR(50)             │ What was affected        │  │
│  │ resource_id         │ UUID                    │ Affected entity ID       │  │
│  │ changes             │ JSONB                   │ Before/after diff        │  │
│  │ ip_address          │ INET                    │                          │  │
│  │ user_agent          │ TEXT                    │                          │  │
│  │ request_id          │ UUID                    │ For correlation          │  │
│  │ metadata            │ JSONB                   │ Extra context            │  │
│  │ created_at          │ TIMESTAMPTZ             │ NOT NULL                 │  │
│  │                      │                        │                          │  │
│  │ PRIMARY KEY: (id, created_at)                                              │  │
│  │ PARTITION BY: RANGE (created_at) — daily partitions                      │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.9 ENUM Catalog

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COMPLETE ENUM CATALOG                                │
│                                                                              │
│  ┌──────────────┬──────────────────────────────────────────────────────────┐│
│  │ ENUM NAME    │ VALUES                                                   ││
│  │ ────────────┼───────────────────────────────────────────────────────── ││
│  │ plan_enum    │ free, pro, premium, enterprise, internal                 ││
│  │ tenant_      │ active, suspended, deleted, trial                        ││
│  │   status     │                                                          ││
│  │ tier_enum    │ free, pro, premium                                       ││
│  │ user_status  │ active, inactive, suspended, deleted                     ││
│  │ user_role    │ user, admin, support                                     ││
│  │ episode_enum │ user_message, user_action, agent_invocation,              ││
│  │              │ agent_result, tool_execution, system_event,               ││
│  │              │ feedback_explicit, feedback_implicit,                     ││
│  │              │ application_event, interview_event,                       ││
│  │              │ preference_signal, error_event,                           ││
│  │              │ consolidation_event                                      ││
│  │ actor_enum   │ user, profile_agent, discovery_agent, matching_agent,     ││
│  │              │ resume_agent, cover_letter_agent, interview_agent,        ││
│  │              │ career_coach_agent, application_tracking_agent,           ││
│  │              │ follow_up_agent, memory_agent, supervisor_agent,          ││
│  │              │ system_scheduler, email_integration, admin               ││
│  │ semantic_enum│ profile_fact, skill_knowledge, career_narrative,           ││
│  │              │ company_knowledge, market_knowledge, learned_insight,     ││
│  │              │ inferred_trait, role_requirement, learning_resource,       ││
│  │              │ interview_knowledge, application_fact, general_knowledge  ││
│  │ scope_enum   │ user, role_type, global                                  ││
│  │ pattern_enum │ agent_routing, tool_selection, prompt_strategy,            ││
│  │              │ communication_pattern, follow_up_strategy,                 ││
│  │              │ search_strategy, error_recovery                          ││
│  │ career_enum  │ work_experience, education, certification, project,        ││
│  │              │ publication, patent, award, speaking_engagement,           ││
│  │              │ open_source_contribution, job_application, interview,      ││
│  │              │ job_offer, promotion, career_break, skill_acquired,        ││
│  │              │ skill_deprecated, career_decision, networking_event       ││
│  │ proficiency  │ beginner, intermediate, advanced, expert                  ││
│  │ assess_enum  │ self_report, job_usage, project, certification, inferred   ││
│  │ app_status   │ saved, applied, phone_screen, technical_interview,         ││
│  │              │ onsite, take_home, offer, accepted, rejected,              ││
│  │              │ withdrawn, ghosted                                       ││
│  │ comm_type    │ follow_up, thank_you, outreach, recruiter_response,        ││
│  │              │ offer_acceptance, offer_decline, networking, other        ││
│  │ goal_enum    │ role_transition, skill_acquisition, compensation_target,   ││
│  │              │ promotion, company_target, relocation, certification,      ││
│  │              │ project_completion, other                                ││
│  │ plan_status  │ active, completed, paused, abandoned                      ││
│  │ importance   │ major, minor, milestone                                   ││
│  │ agent_enum   │ supervisor, profile, job_discovery, job_matching,          ││
│  │              │ resume, cover_letter, interview, career_coach,             ││
│  │              │ application_tracking, follow_up, memory                   ││
│  └──────────────┴──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Relationships & Foreign Keys

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMPLETE FOREIGN KEY MAP                              │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │ CHILD TABLE                │ COLUMN              │ PARENT TABLE          ││
│  │ ─────────────────────────┼────────────────────┼────────────────────── ││
│  │ users                     │ tenant_id           │ tenants(id)            ││
│  │ sessions                  │ user_id             │ users(id)              ││
│  │ api_keys                  │ user_id             │ users(id)              ││
│  │ profiles                  │ tenant_id           │ tenants(id)            ││
│  │ profiles                  │ user_id             │ users(id)              ││
│  │ resumes                   │ tenant_id           │ tenants(id)            ││
│  │ resumes                   │ user_id             │ users(id)              ││
│  │ resumes                   │ tailored_for_job_id │ job_postings(id)       ││
│  │ cover_letters             │ tenant_id           │ tenants(id)            ││
│  │ cover_letters             │ user_id             │ users(id)              ││
│  │ cover_letters             │ application_id      │ applications(id)       ││
│  │ job_postings              │ company_id          │ companies(id)          ││
│  │ job_enrichments           │ job_id              │ job_postings(id)       ││
│  │ applications              │ tenant_id           │ tenants(id)            ││
│  │ applications              │ user_id             │ users(id)              ││
│  │ applications              │ job_id              │ job_postings(id)       ││
│  │ applications              │ resume_id           │ resumes(id)            ││
│  │ applications              │ cover_letter_id     │ cover_letters(id)      ││
│  │ interviews                │ tenant_id           │ tenants(id)            ││
│  │ interviews                │ application_id      │ applications(id)       ││
│  │ offers                    │ tenant_id           │ tenants(id)            ││
│  │ offers                    │ application_id      │ applications(id)       ││
│  │ application_tasks         │ tenant_id           │ tenants(id)            ││
│  │ application_tasks         │ application_id      │ applications(id)       ││
│  │ application_comm          │ tenant_id           │ tenants(id)            ││
│  │ application_comm          │ application_id      │ applications(id)       ││
│  │ application_docs          │ application_id      │ applications(id)       ││
│  │ episodic_memories         │ tenant_id           │ tenants(id)            ││
│  │ episodic_memories         │ user_id             │ users(id)              ││
│  │ episodic_memories         │ parent_episode_id   │ episodic_memories(id)  ││
│  │ episodic_memories         │ consolidation_id    │ consolidation_runs(id) ││
│  │ semantic_memories         │ tenant_id           │ tenants(id)            ││
│  │ semantic_memories         │ user_id             │ users(id)              ││
│  │ semantic_memory_versions  │ memory_id           │ semantic_memories(id)  ││
│  │ procedural_memories       │ tenant_id           │ tenants(id)            ││
│  │ procedural_memories       │ user_id             │ users(id)              ││
│  │ user_preferences          │ tenant_id           │ tenants(id)            ││
│  │ user_preferences          │ user_id             │ users(id)              ││
│  │ career_timeline           │ tenant_id           │ tenants(id)            ││
│  │ career_timeline           │ user_id             │ users(id)              ││
│  │ compensation_history      │ tenant_id           │ tenants(id)            ││
│  │ compensation_history      │ user_id             │ users(id)              ││
│  │ compensation_history      │ career_entry_id     │ career_timeline(id)    ││
│  │ skill_evolution           │ tenant_id           │ tenants(id)            ││
│  │ skill_evolution           │ user_id             │ users(id)              ││
│  │ career_goals              │ tenant_id           │ tenants(id)            ││
│  │ career_goals              │ user_id             │ users(id)              ││
│  │ career_goals              │ parent_goal_id      │ career_goals(id)       ││
│  │ learning_plans            │ tenant_id           │ tenants(id)            ││
│  │ learning_plans            │ user_id             │ users(id)              ││
│  │ learning_plans            │ career_goal_id      │ career_goals(id)       ││
│  │ agent_executions          │ tenant_id           │ tenants(id)            ││
│  │ agent_executions          │ user_id             │ users(id)              ││
│  │ agent_executions          │ parent_call_id      │ agent_executions(id)   ││
│  │ audit_logs                │ tenant_id           │ tenants(id)            ││
│  │ audit_logs                │ user_id             │ users(id)              ││
│  └──────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  CASCADE RULES:                                                               │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │ · sessions: ON DELETE CASCADE (delete sessions when user deleted)        ││
│  │ · api_keys: ON DELETE CASCADE (delete keys when user deleted)            ││
│  │ · profiles: ON DELETE CASCADE (delete profile when user deleted)         ││
│  │ · episodic_memories: ON DELETE CASCADE (user deleted → memories purged)  ││
│  │ · semantic_memories: ON DELETE CASCADE                                   ││
│  │ · Most application sub-tables: ON DELETE CASCADE                         ││
│  │                                                                          ││
│  │ RESTRICT (NO CASCADE) RULES:                                             ││
│  │ · applications: job_id → SET NULL on job delete (keep app history)       ││
│  │ · agent_executions: ON DELETE SET NULL for parent_call_id                ││
│  │ · career_timeline: NO CASCADE (career history must survive everything)   ││
│  └──────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Indexing Strategy

### 5.1 Index Inventory

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INDEXING STRATEGY                                    │
│                                                                              │
│  CRITICAL PATH INDEXES (every agent invocation hits these):                   │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │ #  │ TABLE               │ INDEX NAME              │ COLUMNS / TYPE      ││
│  │ ──┼────────────────────┼────────────────────────┼─────────────────── ││
│  │ 1  │ users              │ idx_users_tenant_email  │ (tenant_id, email)   ││
│  │ 2  │ users              │ idx_users_oauth         │ (oauth_provider,     ││
│  │    │                    │                         │  oauth_subject)      ││
│  │ 3  │ sessions           │ idx_sessions_user       │ (user_id, is_revoked)││
│  │ 4  │ sessions           │ idx_sessions_expiry     │ (expires_at) WHERE   ││
│  │    │                    │                         │  is_revoked = false  ││
│  │ 5  │ profiles           │ idx_profiles_user       │ (user_id)            ││
│  │ 6  │ job_postings       │ idx_jobs_canonical      │ (canonical_job_id)   ││
│  │    │                    │                         │  UNIQUE              ││
│  │ 7  │ job_postings       │ idx_jobs_active_fresh   │ (is_active,          ││
│  │    │                    │                         │  first_seen_at DESC) ││
│  │ 8  │ job_postings       │ idx_jobs_company        │ (company_id)         ││
│  │ 9  │ job_postings       │ idx_jobs_embedding      │ HNSW(job_embedding  ││
│  │    │                    │                         │  vector_cosine_ops)  ││
│  │ 10 │ job_postings       │ idx_jobs_search         │ GIN on description   ││
│  │    │                    │                         │  tsvector            ││
│  │ 11 │ applications       │ idx_apps_user_status    │ (user_id, status)    ││
│  │ 12 │ applications       │ idx_apps_user_job       │ (user_id, job_id)    ││
│  │    │                    │                         │  UNIQUE              ││
│  │ 13 │ episodic_memories  │ idx_episodic_user_time  │ (user_id,            ││
│  │    │                    │                         │  created_at DESC)    ││
│  │ 14 │ episodic_memories  │ idx_episodic_user_type  │ (user_id,            ││
│  │    │                    │                         │  episode_type,       ││
│  │    │                    │                         │  created_at DESC)    ││
│  │ 15 │ episodic_memories  │ idx_episodic_embedding  │ HNSW(embedding       ││
│  │    │                    │                         │  vector_cosine_ops)  ││
│  │ 16 │ semantic_memories  │ idx_semantic_user_type  │ (user_id,            ││
│  │    │                    │                         │  memory_type)        ││
│  │ 17 │ semantic_memories  │ idx_semantic_active     │ (user_id, is_active) ││
│  │    │                    │                         │  WHERE is_active=true││
│  │ 18 │ semantic_memories  │ idx_semantic_embedding  │ HNSW(embedding       ││
│  │    │                    │                         │  vector_cosine_ops)  ││
│  │ 19 │ semantic_memories  │ idx_semantic_importance │ (user_id,            ││
│  │    │                    │                         │  importance_score    ││
│  │    │                    │                         │  DESC)               ││
│  │ 20 │ semantic_memories  │ idx_semantic_text       │ GIN(to_tsvector      ││
│  │    │                    │                         │  ('english',         ││
│  │    │                    │                         │  content_text))      ││
│  │ 21 │ user_preferences   │ idx_prefs_current       │ (user_id, is_current)││
│  │    │                    │                         │  WHERE is_current=   ││
│  │    │                    │                         │  true                ││
│  │ 22 │ procedural_mems    │ idx_proc_user_active    │ (user_id, is_active) ││
│  │ 23 │ procedural_mems    │ idx_proc_scope_pattern  │ (scope, pattern_type,││
│  │    │                    │                         │  success_rate DESC)  ││
│  │ 24 │ career_timeline    │ idx_career_user_type    │ (user_id, entry_type)││
│  │ 25 │ career_timeline    │ idx_career_user_date    │ (user_id,            ││
│  │    │                    │                         │  start_date DESC)    ││
│  │ 26 │ agent_executions   │ idx_agent_user_time     │ (user_id,            ││
│  │    │                    │                         │  created_at DESC)    ││
│  │ 27 │ agent_executions   │ idx_agent_session       │ (session_id)         ││
│  │ 28 │ agent_executions   │ idx_agent_type_success  │ (agent_type,         ││
│  │    │                    │                         │  is_success)         ││
│  │ 29 │ audit_logs         │ idx_audit_user_time     │ (user_id,            ││
│  │    │                    │                         │  created_at DESC)    ││
│  │ 30 │ audit_logs         │ idx_audit_resource      │ (resource_type,      ││
│  │    │                    │                         │  resource_id)        ││
│  └──────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  HNSW INDEX CONFIGURATION:                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │ PARAMETER           │ JOB/EMBEDDING  │ EPISODIC(1536d) │ SEMANTIC(3072d)││
│  │ ───────────────────┼───────────────┼────────────────┼────────────────││
│  │ m                   │ 16             │ 12              │ 16              ││
│  │ ef_construction     │ 200            │ 150             │ 200             ││
│  │ ef_search (default) │ 100            │ 80              │ 100             ││
│  │ ef_search (max)     │ 200            │ 150             │ 200             ││
│  │ distance            │ cosine         │ cosine          │ cosine          ││
│  └──────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  PARTIAL INDEXES (smaller, faster, less write overhead):                      │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │ · idx_jobs_active ON job_postings WHERE is_active = true                 ││
│  │ · idx_apps_active ON applications WHERE status != 'rejected'             ││
│  │ · idx_semantic_active ON semantic_memories WHERE is_active = true        ││
│  │ · idx_prefs_current ON user_preferences WHERE is_current = true          ││
│  │ · idx_proc_active ON procedural_memories WHERE is_active = true          ││
│  └──────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Index Usage Map by Query Pattern

| Query Pattern | Index Used | Benefit |
|---------------|-----------|---------|
| "Get user by email during login" | `idx_users_tenant_email` | Direct lookup, < 1ms |
| "Get current preferences for user" | `idx_prefs_current` | Filtered to 1 row per user |
| "Find jobs matching user embedding" | `idx_jobs_embedding` (HNSW) | Top-50 in < 50ms |
| "Get recent episodes for user" | `idx_episodic_user_time` | Index-only scan possible |
| "Get all active applications for user" | `idx_apps_user_status` | Composite key covers query |
| "Search jobs by keyword" | `idx_jobs_search` (GIN) | Full-text search |
| "Find similar semantic memories" | `idx_semantic_embedding` (HNSW) | Top-10 in < 30ms |
| "Get agent execution history" | `idx_agent_user_time` | Efficient time-range scan |
| "Audit trail for a resource" | `idx_audit_resource` | Direct lookup |

---

## 6. Partitioning Strategy

### 6.1 Partition Plan

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PARTITIONING STRATEGY                                │
│                                                                              │
│  TABLE                     │ KEY          │ TYPE   │ RETENTION              │
│  ─────────────────────────┼─────────────┼───────┼───────────────────────  │
│  episodic_memories         │ created_at   │ RANGE  │ 90d hot, 730d cold,    │
│                            │              │ (daily)│ archive beyond          │
│  audit_logs                │ created_at   │ RANGE  │ 90d hot, 365d cold,    │
│                            │              │ (daily)│ archive beyond          │
│  agent_executions          │ created_at   │ RANGE  │ 90d hot, 365d cold     │
│                            │              │ (monthly)│                        │
│  job_postings              │ first_seen_at│ RANGE  │ Active + expired       │
│                            │              │ (monthly)│ (no delete — reference)│
│                                                                              │
│  PARTITION MANAGEMENT (pg_partman):                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  · Automatic daily partition creation (7 days ahead)                  │   │
│  │  · Automatic partition detach for expired partitions                  │   │
│  │  · Detached partitions → archived to S3 via pg_dump                  │   │
│  │  · Retention: enforced via pg_partman retention policy                │   │
│  │                                                                       │   │
│  │  Example configuration (episodic_memories):                           │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │  SELECT partman.create_parent(                               │     │   │
│  │  │    p_parent_table := 'public.episodic_memories',             │     │   │
│  │  │    p_control := 'created_at',                                │     │   │
│  │  │    p_type := 'native',                                       │     │   │
│  │  │    p_interval := '1 day',                                    │     │   │
│  │  │    p_premake := 7,                                           │     │   │
│  │  │    p_retention := '90 days',                                 │     │   │
│  │  │    p_retention_keep_table := false                           │     │   │
│  │  │  );                                                          │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  PARTITION PRUNING:                                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  · All queries include created_at filter on partitioned tables        │   │
│  │  · Application query builder enforces: WHERE created_at >=            │   │
│  │    NOW() - INTERVAL '90 days' on episodic lookups                     │   │
│  │  · For cross-partition queries: UNION ALL across hot+cold partitions  │   │
│  │  · Warning log if query scans all partitions (missing filter)         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Query Optimization

### 7.1 Critical Query Patterns

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  QUERY 1: GET USER CONTEXT PACKAGE (most frequent — every agent invocation)  │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  -- Parallel execution: 3 queries simultaneously                        │  │
│  │                                                                          │  │
│  │  -- Route A: Profile + Preferences (index-only scan, < 5ms)             │  │
│  │  SELECT p.structured_data, p.embedding, p.summary                        │  │
│  │  FROM profiles p                                                         │  │
│  │  WHERE p.user_id = $1 AND p.is_active = true;                            │  │
│  │                                                                          │  │
│  │  SELECT up.preference_data                                                │  │
│  │  FROM user_preferences up                                                │  │
│  │  WHERE up.user_id = $1 AND up.is_current = true                          │  │
│  │  LIMIT 1;                                                                │  │
│  │                                                                          │  │
│  │  -- Route B: Active applications (index scan, < 10ms)                    │  │
│  │  SELECT a.id, a.job_id, a.status, a.last_updated_at,                     │  │
│  │         j.title, j.company_id, c.name as company_name                    │  │
│  │  FROM applications a                                                      │  │
│  │  JOIN job_postings j ON a.job_id = j.id                                  │  │
│  │  JOIN companies c ON j.company_id = c.id                                 │  │
│  │  WHERE a.user_id = $1 AND a.is_archived = false                          │  │
│  │  ORDER BY a.last_updated_at DESC;                                        │  │
│  │                                                                          │  │
│  │  -- Route C: Recent episodes (index-only scan + LIMIT, < 15ms)           │  │
│  │  SELECT id, episode_type, action, context_summary, importance_score      │  │
│  │  FROM episodic_memories                                                   │  │
│  │  WHERE user_id = $1                                                       │  │
│  │    AND created_at > NOW() - INTERVAL '7 days'                            │  │
│  │  ORDER BY created_at DESC                                                 │  │
│  │  LIMIT 50;                                                               │  │
│  │                                                                          │  │
│  │  EXPECTED: < 30ms total (parallel execution)                             │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  QUERY 2: VECTOR JOB MATCHING (second most frequent)                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  -- HNSW index scan + metadata filter                                    │  │
│  │  SELECT j.id, j.title, c.name AS company, j.location, j.remote_policy,   │  │
│  │         1 - (j.job_embedding <=> $user_embedding) AS similarity           │  │
│  │  FROM job_postings j                                                      │  │
│  │  JOIN companies c ON j.company_id = c.id                                  │  │
│  │  WHERE j.is_active = true                                                 │  │
│  │    AND j.first_seen_at > NOW() - INTERVAL '30 days'                      │  │
│  │    -- Optional: location filter for performance                           │  │
│  │    -- AND (j.remote_policy = 'remote' OR                                  │  │
│  │    --      j.location->>'country' = 'US')                                 │  │
│  │  ORDER BY j.job_embedding <=> $user_embedding                             │  │
│  │  LIMIT 50;                                                               │  │
│  │                                                                          │  │
│  │  EXPECTED: < 50ms with HNSW index, warmed cache                          │  │
│  │  OPTIMIZATION: location/country pre-filter reduces vector search scope   │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  QUERY 3: SEMANTIC MEMORY VECTOR SEARCH                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  SELECT id, memory_type, subject, content_text,                           │  │
│  │         1 - (embedding <=> $query_vector) AS similarity,                  │  │
│  │         confidence, importance_score                                      │  │
│  │  FROM semantic_memories                                                    │  │
│  │  WHERE user_id = $1                                                       │  │
│  │    AND is_active = true                                                   │  │
│  │    AND importance_score > 0.2                                             │  │
│  │  ORDER BY embedding <=> $query_vector                                     │  │
│  │  LIMIT 10;                                                               │  │
│  │                                                                          │  │
│  │  EXPECTED: < 30ms with HNSW index                                        │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  QUERY 4: HYBRID JOB SEARCH (keyword + vector)                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  WITH keyword_matches AS (                                                │  │
│  │    SELECT j.id,                                                           │  │
│  │           ts_rank(to_tsvector('english', j.description_clean),            │  │
│  │                   plainto_tsquery('english', $keywords)) AS text_score    │  │
│  │    FROM job_postings j                                                    │  │
│  │    WHERE j.is_active = true                                               │  │
│  │      AND to_tsvector('english', j.description_clean) @@                   │  │
│  │          plainto_tsquery('english', $keywords)                            │  │
│  │    LIMIT 100                                                              │  │
│  │  ),                                                                       │  │
│  │  vector_matches AS (                                                      │  │
│  │    SELECT j.id,                                                           │  │
│  │           1 - (j.job_embedding <=> $query_embedding) AS vector_score      │  │
│  │    FROM job_postings j                                                    │  │
│  │    WHERE j.is_active = true                                               │  │
│  │    ORDER BY j.job_embedding <=> $query_embedding                          │  │
│  │    LIMIT 100                                                              │  │
│  │  )                                                                        │  │
│  │  SELECT j.*,                                                              │  │
│  │         COALESCE(k.text_score, 0) * 0.3 +                                 │  │
│  │         COALESCE(v.vector_score, 0) * 0.7 AS hybrid_score                 │  │
│  │  FROM job_postings j                                                      │  │
│  │  LEFT JOIN keyword_matches k ON j.id = k.id                               │  │
│  │  LEFT JOIN vector_matches v ON j.id = v.id                                │  │
│  │  WHERE k.id IS NOT NULL OR v.id IS NOT NULL                               │  │
│  │  ORDER BY hybrid_score DESC                                               │  │
│  │  LIMIT 20;                                                               │  │
│  │                                                                          │  │
│  │  EXPECTED: < 100ms (two parallel index scans + merge)                    │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Optimization Rules

| Rule | Description |
|------|-------------|
| **Always filter by tenant_id first** | Every tenant-scoped query begins with `WHERE tenant_id = $tenant_id` — enables partition pruning and RLS bypass |
| **Use index-only scans where possible** | Include frequently accessed columns in indexes or use INCLUDE clause for covering indexes |
| **Limit vector searches** | Always combine vector search with metadata filters (is_active, location, date range) to reduce HNSW traversal |
| **Parallelize independent fetches** | Profile + preferences + recent episodes fetched in parallel via connection pool |
| **Use materialized views for analytics** | Dashboard aggregations pre-computed every 15 minutes, not on every page load |
| **Connection pool hints** | Read queries → replica pool. Write queries → primary pool. Transaction → primary pool. |
| **EXPLAIN ANALYZE on all new queries** | Part of CI/CD pipeline: query plan regression detection |
| **pg_stat_statements monitoring** | Track top-20 queries by total_time weekly, optimize the worst |

### 7.3 Materialized Views

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MV: user_pipeline_summary (refreshed every 5 min)                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  SELECT user_id, status, COUNT(*) as count                                │  │
│  │  FROM applications                                                        │  │
│  │  WHERE is_archived = false                                                │  │
│  │  GROUP BY user_id, status;                                                │  │
│  │                                                                          │  │
│  │  UNIQUE INDEX on (user_id, status)                                       │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  MV: daily_job_stats (refreshed every 1 hour)                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  SELECT date_trunc('day', first_seen_at) as day,                          │  │
│  │         source_type, COUNT(*) as jobs_found                                │  │
│  │  FROM job_postings                                                        │  │
│  │  GROUP BY 1, 2;                                                          │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  MV: agent_performance_summary (refreshed every 1 hour)                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  SELECT agent_type, action_type,                                           │  │
│  │         COUNT(*) as executions,                                            │  │
│  │         AVG(latency_ms) as avg_latency,                                    │  │
│  │         SUM(tokens_used->>'total')::BIGINT as total_tokens,                │  │
│  │         AVG(CASE WHEN is_success THEN 1.0 ELSE 0.0 END) as success_rate   │  │
│  │  FROM agent_executions                                                     │  │
│  │  WHERE created_at > NOW() - INTERVAL '24 hours'                            │  │
│  │  GROUP BY agent_type, action_type;                                        │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Backup Strategy

### 8.1 Backup Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BACKUP STRATEGY                                      │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  TIER 1: CONTINUOUS WAL ARCHIVING                                     │   │
│  │  ┌────────────────────────────────────────────────────────────────┐  │   │
│  │  │ · WAL segments continuously archived to S3                      │  │   │
│  │  │ · archive_command = 'pgbackrest archive-push'                   │  │   │
│  │  │ · RPO: < 1 minute (point-in-time recovery possible)             │  │   │
│  │  │ · Retention: 7 days of WAL                                      │  │   │
│  │  └────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  TIER 2: FULL BACKUPS (pgBackRest)                                    │   │
│  │  ┌────────────────────────────────────────────────────────────────┐  │   │
│  │  │ SCHEDULE:                                                       │  │   │
│  │  │ · Daily full backup at 03:00 UTC                                │  │   │
│  │  │ · Differential backup every 6 hours                             │  │   │
│  │  │ · Incremental backup every 1 hour during business hours         │  │   │
│  │  │                                                                │  │   │
│  │  │ RETENTION:                                                      │  │   │
│  │  │ · Full backups: 30 days                                         │  │   │
│  │  │ · Differential: 7 days                                          │  │   │
│  │  │ · Archive (monthly full): 12 months                             │  │   │
│  │  │ · Archive (yearly full): 7 years (compliance)                   │  │   │
│  │  │                                                                │  │   │
│  │  │ STORAGE:                                                        │  │   │
│  │  │ · Primary: S3 Standard (same region)                            │  │   │
│  │  │ · Secondary: S3 Standard (cross-region, different account)     │  │   │
│  │  │ · Archive: S3 Glacier Deep Archive (after 30 days)             │  │   │
│  │  └────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  TIER 3: LOGICAL BACKUPS (pg_dump)                                    │   │
│  │  ┌────────────────────────────────────────────────────────────────┐  │   │
│  │  │ · Weekly logical dump of critical tables (schema + data)        │  │   │
│  │  │ · Purpose: Individual table recovery, migration, audit          │  │   │
│  │  │ · Format: Custom compressed format (pg_dump -Fc)                │  │   │
│  │  │ · Storage: S3 Standard, 90 days retention                       │  │   │
│  │  └────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  TIER 4: REPLICATION (High Availability)                              │   │
│  │  ┌────────────────────────────────────────────────────────────────┐  │   │
│  │  │ · Synchronous replication to 1 standby (same AZ)                │  │   │
│  │  │ · Asynchronous replication to 2 replicas (different AZs)       │  │   │
│  │  │ · Read replicas serve analytics + reporting traffic             │  │   │
│  │  │ · Auto-failover via Patroni/Cloud SQL in < 60 seconds           │  │   │
│  │  └────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  RPO/RTO SUMMARY:                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ SCENARIO                  │ RPO           │ RTO          │ METHOD     │   │
│  │ ─────────────────────────┼──────────────┼─────────────┼─────────── │   │
│  │ Single row recovery      │ < 1 min       │ < 5 min      │ WAL PITR   │   │
│  │ Single table recovery    │ < 1 min       │ < 30 min     │ WAL PITR   │   │
│  │ Full instance failure    │ < 1 min       │ < 60 min     │ Auto-      │   │
│  │ (same region)            │               │              │ failover   │   │
│  │ AZ failure               │ < 1 min       │ < 5 min      │ Replica    │   │
│  │                          │               │              │ promotion  │   │
│  │ Region failure           │ < 1 hour      │ < 4 hours    │ Cross-     │   │
│  │                          │               │              │ region     │   │
│  │                          │               │              │ restore    │   │
│  │ Accidental deletion      │ < 1 min       │ < 1 hour     │ WAL PITR   │   │
│  │ (user/application)       │               │              │ to before  │   │
│  │                          │               │              │ deletion   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Migration Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MIGRATION STRATEGY                                    │
│                                                                              │
│  TOOL: Alembic (Python) or Flyway (SQL)                                       │
│                                                                              │
│  RULES:                                                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 1. Every migration is backward-compatible (no breaking changes        │   │
│  │    to the schema version that's currently running in production)      │   │
│  │ 2. Additive changes first (ADD COLUMN, CREATE INDEX),                 │   │
│  │    destructive changes last (DROP COLUMN) — separate migration        │   │
│  │ 3. Heavy operations (index build, column rewrite) use                  │   │
│  │    CONCURRENTLY where possible — no table locks                       │   │
│  │ 4. Migrations run BEFORE code deploy — old code handles new schema    │   │
│  │ 5. Rollback plan documented for every migration                       │   │
│  │ 6. Staging runs full migration + smoke test before production         │   │
│  │ 7. No migration runs during peak traffic (10:00-14:00 UTC)            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  VERSION TABLE: _schema_migrations                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  version (VARCHAR) | applied_at (TIMESTAMPTZ) | checksum (VARCHAR)      │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Connection & Pooling

### 10.1 PgBouncer Configuration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PRIMARY WRITE POOL:                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  pool_mode = transaction                                              │   │
│  │  default_pool_size = 50                                               │   │
│  │  max_client_conn = 500                                                │   │
│  │  reserve_pool_size = 10                                               │   │
│  │  reserve_pool_timeout = 3                                             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  READ REPLICA POOL:                                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  pool_mode = transaction                                              │   │
│  │  default_pool_size = 150 (3 replicas × 50 each)                       │   │
│  │  max_client_conn = 1500                                               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  SESSION PRAGMA (set on every new connection):                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  SET app.tenant_id = '<current_tenant>';                               │   │
│  │  SET application_name = 'pathfinder_api';                              │   │
│  │  SET statement_timeout = '30s';  -- kill long-running queries         │   │
│  │  SET idle_in_transaction_session_timeout = '60s';                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

> *"The database is not a persistence layer. It is the foundation of the memory moat. Design it accordingly."*

**End of Database Schema Design Document**
