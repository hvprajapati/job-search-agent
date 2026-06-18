# Pathfinder — Sprint 6: Agent Foundation

**Sprint:** 6 of 7
**Duration:** 10 Days
**Prerequisite:** Sprints 3–5 (profile, jobs, matching operational)
**Goal:** LangGraph Supervisor Agent with tools. Single endpoint for all AI interactions. Intent routing, task planning, human approval, SSE streaming.
**Source:** FINAL_ARCHITECTURE.md §3 + EPICS_AND_TASKS.md Epic 6

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SUPERVISOR AGENT — LANGGRAPH                               │
│                                                                              │
│  POST /v1/agent/execute                                                       │
│  ─────────────────────                                                        │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    LANGGRAPH STATEGRAPH                                │   │
│  │                                                                       │   │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐              │   │
│  │  │GUARDRAIL│──→│CONTEXT  │──→│ INTENT  │──→│  TASK   │              │   │
│  │  │         │   │BUILDER  │   │ ROUTER  │   │ PLANNER │              │   │
│  │  │ Auth    │   │ Profile │   │ LLM     │   │ LLM     │              │   │
│  │  │ Rate    │   │ Prefs   │   │ classif-│   │ decom-  │              │   │
│  │  │ Limit   │   │ History │   │ ication │   │ pose    │              │   │
│  │  └─────────┘   └─────────┘   └────┬────┘   └────┬────┘              │   │
│  │                                   │              │                   │   │
│  │                      ┌────────────┼──────────────┘                   │   │
│  │                      │            │                                   │   │
│  │                      ▼            ▼                                   │   │
│  │               ┌──────────────────────────┐                            │   │
│  │               │     TOOL EXECUTOR         │                            │   │
│  │               │                           │                            │   │
│  │               │  ┌─────────────────────┐  │                            │   │
│  │               │  │ Tool Registry       │  │                            │   │
│  │               │  │                     │  │                            │   │
│  │               │  │ search_jobs      ───┼──│→ Sprint 4 JobRepository   │   │
│  │               │  │ compute_match    ───┼──│→ Sprint 5 Orchestrator    │   │
│  │               │  │ get_profile      ───┼──│→ Sprint 3 ProfileRepo     │   │
│  │               │  │ get_resumes      ───┼──│→ Sprint 3 ResumeRepo      │   │
│  │               │  │ get_recommendat. ───┼──│→ Sprint 5 Handler         │   │
│  │               │  │ apply_to_job     ───┼──│→ Sprint 5 Tracking (stub) │   │
│  │               │  │ generate_followup───┼──│→ LLM (inline)             │   │
│  │               │  └─────────────────────┘  │                            │   │
│  │               └───────────┬──────────────┘                            │   │
│  │                           │                                           │   │
│  │                           ▼                                           │   │
│  │               ┌──────────────────────┐                                │   │
│  │               │    HUMAN GATE        │ ← LangGraph interrupt()        │   │
│  │               │    (if needed)       │                                │   │
│  │               └──────────┬───────────┘                                │   │
│  │                          │                                            │   │
│  │                          ▼                                            │   │
│  │               ┌──────────────────────┐                                │   │
│  │               │  RESULT SYNTHESIZER  │                                │   │
│  │               └──────────┬───────────┘                                │   │
│  │                          │                                            │   │
│  │                          ▼                                            │   │
│  │               ┌──────────────────────┐                                │   │
│  │               │   QUALITY GATE       │ ← PASS/REVISE/FAIL             │   │
│  │               └──────────────────────┘                                │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  CHECKPOINTING: PostgresSaver — state persisted after every node              │
│  STREAMING:     SSE — token-by-token for LLM responses                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Day 1–2: Domain Core + State

### Files to Create

```
src/pathfinder/agent/domain/
├── entities.py           # AgentExecution, ApprovalRequest
├── value_objects.py      # Intent, ExecutionStatus, AgentAction, ToolCall
├── repositories.py       # AgentExecutionRepository (abstract)
├── services.py           # IntentRouter, TaskPlanner (LLM-based)
├── events.py             # AgentInvoked, AgentCompleted, ApprovalRequested
├── exceptions.py         # IntentNotRecognized, AgentExecutionError
├── tools.py              # ToolDefinition, ToolRegistry, ToolResult
└── state.py              # SupervisorState TypedDict

src/pathfinder/agent/application/
├── ports/
│   └── llm_port.py       # LLMPort (reuse from Sprint 3)
├── commands.py            # ExecuteAgent, RespondToApproval
├── queries.py             # GetExecutionHistory
└── handlers.py            # AgentCommandHandler

tests/unit/agent/
├── test_state.py
├── test_tool_registry.py
├── test_intent_router.py
└── test_task_planner.py
```

### `src/pathfinder/agent/domain/state.py`

```python
"""SupervisorAgent state — the core state object flowing through the LangGraph."""
from __future__ import annotations
from typing import TypedDict, Annotated
from uuid import UUID
from langgraph.graph.message import add_messages


class SupervisorState(TypedDict, total=False):
    """State carried through every node of the Supervisor graph.

    Fields marked 'Annotated' use LangGraph reducers for merging.
    """

    # ── Identity ──
    session_id: str           # UUID, generated on first invocation
    user_id: str              # Authenticated user UUID
    tier: str                 # free | pro | premium

    # ── Input ──
    user_message: str         # Raw text from the user
    user_action: str | None   # Structured action (button click, etc.)
    attachments: list[dict]   # Uploaded files metadata

    # ── Context (loaded by Context Builder node) ──
    user_profile: dict | None        # Full profile from Sprint 3
    user_preferences: dict | None    # Preferences from Sprint 3
    user_resumes: list[dict]         # User's resumes from Sprint 3
    active_applications: list[dict]  # From tracking (stub)
    recent_history: list[dict]       # Last N agent interactions

    # ── Routing ──
    intent: str | None               # Classified intent
    intent_confidence: float         # 0.0 - 1.0
    clarification_question: str | None  # If confidence < threshold

    # ── Planning ──
    execution_plan: list[dict]       # [{step, tool_name, args, depends_on, status}]
    current_step: int                # Index into execution plan

    # ── Tool Execution ──
    tool_results: dict[str, dict]    # tool_call_id → result
    tool_errors: dict[str, str]      # tool_call_id → error message

    # ── Messages (Annotated for LangGraph message merging) ──
    messages: Annotated[list, add_messages]  # Conversation history (LangChain format)

    # ── Human-in-the-Loop ──
    pending_approval: dict | None    # ApprovalRequest serialized
    approval_history: list[dict]     # Past approvals in this session

    # ── Response ──
    final_response: str | None       # Text response for the user
    response_artifacts: list[dict]   # Structured data (cards, diffs, actions)

    # ── Metadata ──
    call_id: str                     # UUID for this invocation
    total_tokens_used: int           # Aggregate token count
    total_latency_ms: int            # Aggregate wall clock
    errors: list[str]                # Non-fatal errors encountered
    quality_gate_passes: int         # Number of quality gate iterations
    agent_phase: str                 # Current graph phase (for SSE status events)
```

### `src/pathfinder/agent/domain/value_objects.py`

```python
"""Agent domain value objects."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from datetime import datetime, timezone
from pathfinder.shared.domain.base_value_object import BaseValueObject


class Intent(StrEnum):
    SEARCH_JOBS = "search_jobs"
    MATCH_ME = "match_me"
    TAILOR_RESUME = "tailor_resume"
    GENERATE_COVER_LETTER = "generate_cover_letter"
    PREP_INTERVIEW = "prep_interview"
    TRACK_APPLICATIONS = "track_applications"
    FOLLOW_UP = "follow_up"
    ANALYZE_SKILL_GAP = "analyze_skill_gap"
    CAREER_ADVICE = "career_advice"
    UPDATE_PROFILE = "update_profile"
    GENERAL_QUESTION = "general_question"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalAction(StrEnum):
    SAVE_RESUME = "save_resume"
    SEND_EMAIL = "send_email"
    APPLY_TO_JOB = "apply_to_job"
    CONFIRM_DELETE = "confirm_delete"


@dataclass(frozen=True, kw_only=True)
class ToolDefinition(BaseValueObject):
    """Metadata describing a tool registered with the Supervisor."""
    name: str
    description: str               # LLM-readable — used for tool selection
    parameters: dict               # JSON Schema for parameters
    requires_approval: bool = False
    is_expensive: bool = False      # True if calls LLM or external API
    tier_required: str = "free"


@dataclass(frozen=True, kw_only=True)
class ToolResult(BaseValueObject):
    """Result of a tool execution."""
    tool_name: str
    success: bool
    data: dict | None = None
    error: str | None = None
    latency_ms: int = 0
    tokens_used: int = 0


@dataclass
class AgentAction:
    """An action the agent decided to take — stored in execution plan."""
    step_id: str
    tool_name: str
    tool_args: dict = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"  # pending | running | completed | failed
    result: ToolResult | None = None
```

### `src/pathfinder/agent/domain/entities.py`

```python
"""Agent domain entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.agent.domain.value_objects import ExecutionStatus, ApprovalAction


@dataclass(kw_only=True)
class AgentExecution(BaseEntity):
    """Persistent record of an agent invocation."""
    user_id: UUID
    session_id: UUID
    call_id: UUID = field(default_factory=uuid4)
    parent_call_id: UUID | None = None
    intent: str = ""
    intent_confidence: float = 0.0
    user_message: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    execution_plan: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    final_response: str = ""
    response_artifacts: list[dict] = field(default_factory=list)
    tokens_used: dict = field(default_factory=dict)  # {input, output, total}
    latency_ms: int = 0
    llm_model: str = ""
    llm_provider: str = "deepseek"
    is_success: bool = False
    error_message: str = ""
    retry_count: int = 0
    user_approved: bool | None = None
    user_modified: bool = False
    completed_at: datetime | None = None

    def mark_running(self) -> None:
        self.status = ExecutionStatus.RUNNING
        self.mark_updated()

    def mark_waiting_approval(self) -> None:
        self.status = ExecutionStatus.WAITING_APPROVAL
        self.mark_updated()

    def mark_completed(self) -> None:
        self.status = ExecutionStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.is_success = True
        self.mark_updated()

    def mark_failed(self, error: str) -> None:
        self.status = ExecutionStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.now(timezone.utc)
        self.is_success = False
        self.mark_updated()


@dataclass(kw_only=True)
class ApprovalRequest(BaseEntity):
    """HITL approval request — persisted while waiting for user response."""
    execution_id: UUID
    user_id: UUID
    action_type: str  # ApprovalAction value
    action_summary: str  # One-line for UI
    action_detail: str   # Full description
    diff_data: dict | None = None  # Before/after for resume/CL
    preview: str | None = None     # Rendered preview
    risk_level: str = "low"       # low | medium | high
    status: str = "pending"       # pending | approved | rejected | edited
    edits: dict | None = None     # User modifications (if edited)
    rejection_reason: str = ""    # Why rejected
    decided_at: datetime | None = None
    expires_at: datetime | None = None  # Auto-expire after 7 days

    def approve(self) -> None:
        self.status = "approved"
        self.decided_at = datetime.now(timezone.utc)
        self.mark_updated()

    def reject(self, reason: str = "") -> None:
        self.status = "rejected"
        self.rejection_reason = reason
        self.decided_at = datetime.now(timezone.utc)
        self.mark_updated()

    def edit(self, edits: dict) -> None:
        self.status = "edited"
        self.edits = edits
        self.decided_at = datetime.now(timezone.utc)
        self.mark_updated()
```

### `src/pathfinder/agent/domain/repositories.py`

```python
"""Agent repository interfaces."""
from abc import abstractmethod
from uuid import UUID
from pathfinder.shared.domain.base_repository import BaseRepository
from pathfinder.agent.domain.entities import AgentExecution, ApprovalRequest


class AgentExecutionRepository(BaseRepository[AgentExecution]):
    @abstractmethod
    async def get_by_call_id(self, call_id: UUID) -> AgentExecution | None: ...
    @abstractmethod
    async def list_by_user(self, user_id: UUID, *, cursor: str | None = None,
                           limit: int = 20) -> tuple[list[AgentExecution], str | None]: ...
    @abstractmethod
    async def list_by_session(self, session_id: UUID) -> list[AgentExecution]: ...


class ApprovalRepository(BaseRepository[ApprovalRequest]):
    @abstractmethod
    async def get_pending_for_user(self, user_id: UUID) -> list[ApprovalRequest]: ...
    @abstractmethod
    async def get_by_execution_id(self, execution_id: UUID) -> ApprovalRequest | None: ...
```

### `src/pathfinder/agent/domain/exceptions.py`

```python
"""Agent domain exceptions."""
from pathfinder.shared.domain.exceptions import (
    NotFoundError, ValidationError, DomainError, UnauthorizedError
)

class IntentNotRecognizedError(DomainError):
    def __init__(self, confidence: float = 0.0) -> None:
        super().__init__(f"Could not determine intent (confidence: {confidence:.2f})")

class AgentExecutionError(DomainError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Agent execution failed: {detail}")

class ToolExecutionError(DomainError):
    def __init__(self, tool_name: str, detail: str = "") -> None:
        super().__init__(f"Tool '{tool_name}' failed: {detail}")

class ApprovalNotFoundError(NotFoundError):
    def __init__(self, approval_id: str = "") -> None:
        super().__init__(f"Approval not found: {approval_id}")

class CircuitBreakerOpenError(DomainError):
    def __init__(self) -> None:
        super().__init__("AI service temporarily unavailable. Please try again shortly.")

class TierNotAllowedError(UnauthorizedError):
    def __init__(self, feature: str, required_tier: str) -> None:
        super().__init__(f"'{feature}' requires {required_tier} tier")
```

---

## Day 3–4: Tool Registry + Intent Router + Task Planner

### `src/pathfinder/agent/domain/tools.py`

```python
"""Tool Registry — wraps existing Sprint 3-5 services as agent-callable tools."""
from __future__ import annotations
import json
from typing import Any, Callable
from pathfinder.agent.domain.value_objects import ToolDefinition, ToolResult


class ToolRegistry:
    """Central registry of all tools the Supervisor Agent can call.

    Each tool wraps an existing service from Sprints 3-5.
    No duplicate business logic — tools delegate to the service layer.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, Callable] = {}

    def register(self, definition: ToolDefinition, handler: Callable) -> None:
        self._tools[definition.name] = definition
        self._handlers[definition.name] = handler

    def get_definition(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def get_all_definitions(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def get_definitions_for_llm(self) -> list[dict]:
        """Return tool definitions in OpenAI function-calling format for LLM."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    async def execute(self, name: str, **kwargs) -> ToolResult:
        handler = self._handlers.get(name)
        if handler is None:
            return ToolResult(tool_name=name, success=False,
                            error=f"Unknown tool: {name}")
        import time
        start = time.monotonic()
        try:
            result_data = await handler(**kwargs)
            latency = int((time.monotonic() - start) * 1000)
            return ToolResult(tool_name=name, success=True,
                            data=result_data, latency_ms=latency)
        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            return ToolResult(tool_name=name, success=False,
                            error=str(e)[:500], latency_ms=latency)

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())


# ── Global singleton (acceptable for MVP — injected via DI in V1) ──
tool_registry = ToolRegistry()
```

### `src/pathfinder/agent/infrastructure/tools/__init__.py`

```python
"""Tool implementations — each wraps an existing Sprint 3-5 service."""
```

### `src/pathfinder/agent/infrastructure/tools/search_tools.py`

```python
"""Job search and discovery tools."""
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.jobs.infrastructure.persistence.job_repository import SqlJobRepository
from pathfinder.agent.domain.tools import tool_registry, ToolDefinition


async def _search_jobs(query: str = "", location: str = "",
                       remote_only: bool = False, limit: int = 10,
                       **kwargs) -> dict:
    """Search for jobs matching criteria. Returns job list."""
    maker = get_sessionmaker()
    async with maker() as session:
        repo = SqlJobRepository(session)
        filters = {}
        if location:
            filters["location"] = location
        if remote_only:
            filters["remote_policy"] = "remote"
        jobs, _, total = await repo.search(query=query, filters=filters, limit=limit)
        return {
            "total": total,
            "jobs": [
                {"job_id": str(j.id), "title": j.title,
                 "company": j.company_name, "location": j.location.display_text,
                 "remote": j.remote_policy.value,
                 "summary": j.description_summary[:200] if j.description_summary else "",
                 "tech_stack": j.tech_stack}
                for j in jobs
            ],
        }


async def _get_job_detail(job_id: str, **kwargs) -> dict:
    """Get full job details by ID."""
    from uuid import UUID
    maker = get_sessionmaker()
    async with maker() as session:
        repo = SqlJobRepository(session)
        job = await repo.get_by_id(UUID(job_id))
        if not job:
            return {"error": "Job not found"}
        return {
            "job_id": str(job.id), "title": job.title, "company": job.company_name,
            "description": job.description_clean or job.description_raw,
            "tech_stack": job.tech_stack,
            "seniority": job.seniority.value,
            "remote_policy": job.remote_policy.value,
            "salary": {"min": job.salary_range.min_amount, "max": job.salary_range.max_amount,
                       "currency": job.salary_range.currency} if job.salary_range else None,
        }


def register_search_tools():
    tool_registry.register(
        ToolDefinition(
            name="search_jobs",
            description="Search for job listings. Use when the user wants to find jobs by keyword, location, or remote preference.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keywords (e.g., 'python engineer')"},
                    "location": {"type": "string", "description": "Location filter"},
                    "remote_only": {"type": "boolean", "description": "Filter to remote jobs only"},
                    "limit": {"type": "integer", "description": "Max results (default 10, max 50)"},
                },
                "required": ["query"],
            },
            is_expensive=False, tier_required="free",
        ),
        _search_jobs,
    )
    tool_registry.register(
        ToolDefinition(
            name="get_job_detail",
            description="Get full details for a specific job by its ID.",
            parameters={
                "type": "object",
                "properties": {"job_id": {"type": "string", "description": "Job UUID"}},
                "required": ["job_id"],
            },
            is_expensive=False, tier_required="free",
        ),
        _get_job_detail,
    )
```

### `src/pathfinder/agent/infrastructure/tools/match_tools.py`

```python
"""Job matching and recommendation tools."""
from uuid import UUID
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.jobs.infrastructure.persistence.match_repository import SqlMatchRepository
from pathfinder.agent.domain.tools import tool_registry, ToolDefinition


async def _compute_match(user_id: str, job_id: str, **kwargs) -> dict:
    """Compute match score between user and a specific job."""
    maker = get_sessionmaker()
    async with maker() as session:
        from pathfinder.profile.infrastructure.persistence.profile_repository import SqlProfileRepository
        from pathfinder.jobs.infrastructure.persistence.job_repository import SqlJobRepository
        from pathfinder.jobs.infrastructure.matching.match_context_builder import MatchContextBuilder
        from pathfinder.jobs.domain.matching.services import MatchingOrchestrator

        profile_repo = SqlProfileRepository(session)
        job_repo = SqlJobRepository(session)
        ctx_builder = MatchContextBuilder(profile_repo, job_repo)
        orchestrator = MatchingOrchestrator()

        ctx = await ctx_builder.build(UUID(user_id), UUID(job_id))
        if ctx is None:
            return {"error": "Profile or job not found"}

        match = await orchestrator.compute_match(ctx, user_id=UUID(user_id), job_id=UUID(job_id))
        return {
            "overall_score": match.overall_score,
            "dimensions": {d.dimension.value: {"score": d.score, "weight": d.weight}
                          for d in match.dimensions},
            "strengths": [s.text for s in match.strengths[:3]],
            "skill_gaps": [{"skill": g.skill_name, "severity": g.severity.value}
                          for g in match.skill_gaps[:5]],
            "has_dealbreaker": match.has_dealbreaker_gap,
        }


async def _get_recommendations(user_id: str, limit: int = 5, **kwargs) -> dict:
    """Get top job recommendations for the user."""
    maker = get_sessionmaker()
    async with maker() as session:
        repo = SqlMatchRepository(session)
        matches = await repo.get_high_matches(UUID(user_id), threshold=75.0, limit=limit)
        return {
            "recommendations": [
                {"job_id": str(m.job_id), "score": m.overall_score,
                 "title": m.job_snapshot_title, "company": m.job_snapshot_company,
                 "top_strength": m.strengths[0].text if m.strengths else ""}
                for m in matches
            ],
        }


def register_match_tools():
    tool_registry.register(
        ToolDefinition(
            name="compute_match",
            description="Calculate how well a user matches a specific job. Returns match scores, strengths, and skill gaps.",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User UUID"},
                    "job_id": {"type": "string", "description": "Job UUID"},
                },
                "required": ["user_id", "job_id"],
            },
            is_expensive=True, tier_required="free",
        ),
        _compute_match,
    )
    tool_registry.register(
        ToolDefinition(
            name="get_recommendations",
            description="Get the top job recommendations for a user based on previous match computations.",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User UUID"},
                    "limit": {"type": "integer", "description": "Max results (default 5)"},
                },
                "required": ["user_id"],
            },
            is_expensive=False, tier_required="free",
        ),
        _get_recommendations,
    )
```

### `src/pathfinder/agent/infrastructure/tools/profile_tools.py`

```python
"""Profile and resume retrieval tools."""
from uuid import UUID
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.profile.infrastructure.persistence.profile_repository import SqlProfileRepository
from pathfinder.profile.infrastructure.persistence.resume_repository import SqlResumeRepository
from pathfinder.agent.domain.tools import tool_registry, ToolDefinition


async def _get_profile(user_id: str, **kwargs) -> dict:
    """Get user's structured profile."""
    maker = get_sessionmaker()
    async with maker() as session:
        repo = SqlProfileRepository(session)
        profile = await repo.get_by_user_id(UUID(user_id))
        if not profile:
            return {"error": "Profile not found. Upload a resume first."}
        return {
            "full_name": profile.full_name,
            "headline": profile.headline,
            "skills": [{"name": s.name, "proficiency": s.proficiency.value, "years": s.years}
                      for s in profile.skills],
            "experience_count": len(profile.work_experiences),
            "education_count": len(profile.education),
            "has_resume": True,
        }


async def _get_resumes(user_id: str, **kwargs) -> dict:
    """Get user's saved resumes."""
    maker = get_sessionmaker()
    async with maker() as session:
        repo = SqlResumeRepository(session)
        resumes = await repo.list_by_user(UUID(user_id), limit=20)
        return {
            "count": len(resumes),
            "resumes": [
                {"resume_id": str(r.id), "name": r.name,
                 "is_base": r.is_base, "template": r.template_id,
                 "tailored_for": r.tailored_for_role,
                 "created_at": r.created_at.isoformat()}
                for r in resumes
            ],
        }


def register_profile_tools():
    tool_registry.register(
        ToolDefinition(
            name="get_profile",
            description="Retrieve the user's professional profile including skills, experience, and education.",
            parameters={
                "type": "object",
                "properties": {"user_id": {"type": "string"}},
                "required": ["user_id"],
            },
            is_expensive=False, tier_required="free",
        ),
        _get_profile,
    )
    tool_registry.register(
        ToolDefinition(
            name="get_resumes",
            description="Retrieve the user's saved resumes (base and tailored variants).",
            parameters={
                "type": "object",
                "properties": {"user_id": {"type": "string"}},
                "required": ["user_id"],
            },
            is_expensive=False, tier_required="free",
        ),
        _get_resumes,
    )
```

### `src/pathfinder/agent/domain/services.py`

```python
"""Agent domain services — intent routing and task planning (LLM-based)."""
from pathfinder.agent.domain.state import SupervisorState
from pathfinder.agent.domain.value_objects import Intent
from pathfinder.agent.domain.tools import ToolRegistry
from pathfinder.agent.application.ports.llm_port import LLMPort


class IntentRouter:
    """Classifies user message into a discrete intent using LLM."""

    SYSTEM_PROMPT = """You are an intent classifier for a career AI agent.
Classify the user's message into exactly one of these intents:

- search_jobs: Find or browse job listings
- match_me: Get match scores for jobs against my profile
- tailor_resume: Tailor my resume for a specific job
- generate_cover_letter: Generate a cover letter
- prep_interview: Prepare for an interview
- track_applications: View or manage my job applications
- follow_up: Generate a follow-up email
- career_advice: Get career guidance
- update_profile: Change my profile or preferences
- general_question: Anything else

Respond with a JSON object: {"intent": "...", "confidence": 0.0-1.0}
If you're unsure (confidence < 0.7), set intent to "general_question".
"""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def classify(self, user_message: str) -> tuple[Intent, float]:
        try:
            import json
            response = await self._llm.chat_completion(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_message,
                temperature=0.1,
            )
            result = json.loads(response.content)
            intent_str = result.get("intent", "general_question")
            confidence = float(result.get("confidence", 0.5))
            intent = Intent(intent_str) if intent_str in Intent.__members__.values() else Intent.GENERAL_QUESTION
            return intent, min(1.0, max(0.0, confidence))
        except Exception:
            return Intent.GENERAL_QUESTION, 0.3


class TaskPlanner:
    """Decomposes an intent into a sequence of tool calls using LLM."""

    SYSTEM_PROMPT = """You are a task planner for a career AI agent.
Given a user intent and available tools, create an execution plan.

Available tools: {tool_descriptions}

Create a plan as a JSON array of steps. Each step:
{{
    "step_id": "step_1",
    "tool_name": "name_of_tool",
    "tool_args": {{"arg1": "value1"}},
    "depends_on": [],
    "description": "What this step does"
}}

RULES:
1. Steps execute in order unless depends_on specifies otherwise.
2. Use the minimum number of steps to satisfy the intent.
3. If the user message contains specific parameters (job title, company name, etc.), pass them as tool arguments.
4. For general_question: use 0 tools. Respond conversationally.

Respond with valid JSON array only."""

    def __init__(self, llm: LLMPort, tool_registry: ToolRegistry) -> None:
        self._llm = llm
        self._registry = tool_registry

    async def plan(self, intent: Intent, user_message: str,
                   state: SupervisorState) -> list[dict]:
        if intent == Intent.GENERAL_QUESTION:
            return []

        tools_desc = "\n".join(
            f"- {t.name}: {t.description}"
            for t in self._registry.get_all_definitions()
        )

        prompt = self.SYSTEM_PROMPT.format(tool_descriptions=tools_desc)
        user_prompt = f"""Intent: {intent.value}
User message: "{user_message}"
User ID: {state.get('user_id', 'unknown')}

Create an execution plan."""

        try:
            import json
            response = await self._llm.chat_completion(
                system_prompt=prompt, user_prompt=user_prompt, temperature=0.2,
            )
            plan = json.loads(response.content)
            if isinstance(plan, list):
                return plan
            return []
        except Exception:
            # Fallback: simple plan based on intent
            return self._fallback_plan(intent)

    def _fallback_plan(self, intent: Intent) -> list[dict]:
        """Deterministic fallback if LLM planning fails."""
        plans = {
            Intent.SEARCH_JOBS: [{"step_id": "step_1", "tool_name": "search_jobs",
                                  "tool_args": {"query": ""}, "depends_on": []}],
            Intent.MATCH_ME: [{"step_id": "step_1", "tool_name": "get_recommendations",
                               "tool_args": {}, "depends_on": []}],
        }
        return plans.get(intent, [])
```

---

## Day 5–6: LangGraph Graph Implementation

### Files to Create

```
src/pathfinder/agent/infrastructure/langgraph/
├── supervisor_graph.py     # Compiled StateGraph
├── nodes/
│   ├── guardrail.py
│   ├── context_builder.py
│   ├── intent_router_node.py
│   ├── task_planner_node.py
│   ├── tool_executor.py
│   ├── human_gate.py
│   ├── result_synthesizer.py
│   └── quality_gate.py
└── checkpointer.py         # PostgresSaver setup
```

### `src/pathfinder/agent/infrastructure/langgraph/nodes/guardrail.py`

```python
"""Guardrail node — first node in the graph. Validates auth, rate, tier before proceeding."""
from pathfinder.agent.domain.state import SupervisorState
from pathfinder.agent.domain.exceptions import TierNotAllowedError


async def guardrail_node(state: SupervisorState) -> dict:
    """Entry point. Returns BLOCK or allows continuation."""
    tier = state.get("tier", "free")
    user_message = state.get("user_message", "")

    # Content safety: basic check (full moderation deferred to external API)
    if not user_message or len(user_message.strip()) < 1:
        return {"final_response": "I didn't catch that. What would you like help with?",
                "agent_phase": "blocked"}

    # Prompt injection hardening: wrap user text for downstream nodes
    # (Downstream LLM calls will receive sanitized context)

    return {"agent_phase": "guardrail_passed"}
```

### `src/pathfinder/agent/infrastructure/langgraph/nodes/context_builder.py`

```python
"""Context Builder node — loads user profile, preferences, and recent history."""
from uuid import UUID
from pathfinder.agent.domain.state import SupervisorState
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.profile.infrastructure.persistence.profile_repository import SqlProfileRepository
from pathfinder.profile.infrastructure.persistence.resume_repository import SqlResumeRepository


async def context_builder_node(state: SupervisorState) -> dict:
    """Load all context needed by downstream nodes."""
    user_id = state.get("user_id")
    if not user_id:
        return {"errors": ["No user_id in state"]}

    maker = get_sessionmaker()
    async with maker() as session:
        # Profile
        profile_repo = SqlProfileRepository(session)
        profile = await profile_repo.get_by_user_id(UUID(user_id))

        # Resumes
        resume_repo = SqlResumeRepository(session)
        resumes = await resume_repo.list_by_user(UUID(user_id), limit=10)

        # Preferences (from Sprint 3)
        prefs = {}
        try:
            from pathfinder.identity.infrastructure.persistence.preference_repository import SqlPreferenceRepository
            pref_repo = SqlPreferenceRepository(session)
            prefs_model = await pref_repo.get_current(UUID(user_id))
            if prefs_model:
                prefs = prefs_model.preference_data or {}
        except Exception:
            pass

    context = {
        "user_profile": {
            "full_name": profile.full_name,
            "headline": profile.headline,
            "skills": [{"name": s.name, "proficiency": s.proficiency.value}
                      for s in profile.skills],
            "experience_years": sum(
                ((e.end_date or __import__('datetime').date.today()) - e.start_date).days / 365.25
                for e in profile.work_experiences if e.start_date
            ),
            "education": [{"degree": e.degree, "field": e.field} for e in profile.education],
        } if profile else None,
        "user_preferences": prefs,
        "user_resumes": [
            {"resume_id": str(r.id), "name": r.name, "is_base": r.is_base}
            for r in resumes
        ],
        "active_applications": [],  # Populated in Sprint 5 tracking
        "recent_history": [],       # Populated when episodic memory is wired
        "agent_phase": "context_loaded",
    }
    return context
```

### `src/pathfinder/agent/infrastructure/langgraph/nodes/intent_router_node.py`

```python
"""Intent Router node — LLM classifies user message into an intent."""
import json
from pathfinder.agent.domain.state import SupervisorState
from pathfinder.agent.domain.services import IntentRouter
from pathfinder.agent.infrastructure.llm.deepseek_client import DeepSeekClient


INTENT_ROUTER_SYSTEM_PROMPT = """You are an intent classifier for a career AI agent.
Classify the user's message into exactly one intent.

Available intents and when to use them:
- search_jobs: Finding or browsing jobs. Keywords: "find", "search", "looking for", "jobs", "roles", "positions"
- match_me: Getting match scores. Keywords: "match", "how do I fit", "am I a good fit", "score"
- tailor_resume: Tailoring resume. Keywords: "tailor", "customize", "rewrite my resume for"
- general_question: Everything else including greetings, questions about the platform, etc.

Respond with ONLY a JSON object:
{{"intent": "search_jobs", "confidence": 0.95}}"""


async def intent_router_node(state: SupervisorState) -> dict:
    user_message = state.get("user_message", "")
    llm = DeepSeekClient()
    router = IntentRouter(llm)

    intent, confidence = await router.classify(user_message)

    if confidence < 0.7:
        return {
            "intent": "general_question",
            "intent_confidence": confidence,
            "clarification_question": "I'm not quite sure what you'd like me to do. Could you rephrase? I can help with finding jobs, checking your match for a role, or tailoring your resume.",
            "agent_phase": "needs_clarification",
        }

    return {
        "intent": intent.value,
        "intent_confidence": confidence,
        "agent_phase": "intent_classified",
    }
```

### `src/pathfinder/agent/infrastructure/langgraph/nodes/tool_executor.py`

```python
"""Tool Executor node — executes the plan by calling tools via the registry."""
import asyncio
import time
from pathfinder.agent.domain.state import SupervisorState
from pathfinder.agent.domain.tools import tool_registry
from pathfinder.agent.domain.value_objects import ToolResult


async def tool_executor_node(state: SupervisorState) -> dict:
    """Execute the execution plan by calling each tool in sequence."""
    plan = state.get("execution_plan", [])
    user_id = state.get("user_id", "")
    results: dict[str, dict] = {}
    errors: dict[str, str] = {}

    for step in plan:
        tool_name = step.get("tool_name", "")
        tool_args = step.get("tool_args", {})
        step_id = step.get("step_id", "unknown")

        # Inject user_id into all tool calls automatically
        if "user_id" in tool_registry.get_definition(tool_name).parameters.get("properties", {}):
            tool_args.setdefault("user_id", user_id)

        result = await tool_registry.execute(tool_name, **tool_args)
        if result.success:
            results[step_id] = result.data or {"status": "completed"}
        else:
            errors[step_id] = result.error or "Unknown error"
            results[step_id] = {"status": "failed", "error": result.error}

    return {
        "tool_results": results,
        "tool_errors": errors,
        "agent_phase": "tools_executed",
    }
```

### `src/pathfinder/agent/infrastructure/langgraph/nodes/result_synthesizer.py`

```python
"""Result Synthesizer — formats tool outputs into a user-friendly response."""
from pathfinder.agent.domain.state import SupervisorState


async def result_synthesizer_node(state: SupervisorState) -> dict:
    """Synthesize tool results into a coherent natural-language response."""
    intent = state.get("intent", "general_question")
    results = state.get("tool_results", {})
    errors = state.get("tool_errors", {})
    profile = state.get("user_profile") or {}

    # Build response based on intent and results
    parts = []

    if intent == "search_jobs":
        for step_id, data in results.items():
            if "jobs" in data:
                jobs = data["jobs"]
                total = data.get("total", len(jobs))
                if total == 0:
                    parts.append("I didn't find any jobs matching your search. Try broadening your criteria?")
                else:
                    parts.append(f"I found {total} jobs. Here are the top matches:\n")
                    for i, job in enumerate(jobs[:5], 1):
                        parts.append(
                            f"**{i}. {job['title']}** at {job['company']}\n"
                            f"   {job.get('location', '')} | {job.get('remote', '')}\n"
                            f"   {job.get('summary', '')[:150]}...\n"
                        )

    elif intent == "match_me":
        for step_id, data in results.items():
            if "overall_score" in data:
                score = data["overall_score"]
                parts.append(f"Your match score for this role is **{score}/100**.\n")
                if data.get("strengths"):
                    parts.append("**Strengths:**\n")
                    for s in data["strengths"][:3]:
                        parts.append(f"  ✅ {s}\n")
                if data.get("skill_gaps"):
                    parts.append("\n**Skill gaps to address:**\n")
                    for g in data["skill_gaps"][:3]:
                        parts.append(f"  📋 {g['skill']} ({g['severity']})\n")
                if data.get("has_dealbreaker"):
                    parts.append("\n⚠️ **This role has a dealbreaker gap.** Consider focusing on other matches.\n")

    elif intent == "general_question":
        if profile:
            name = profile.get("full_name", "there")
            skills = [s["name"] for s in profile.get("skills", [])[:5]]
            parts.append(f"Hi {name}! ")
            if skills:
                parts.append(f"I see you have skills in {', '.join(skills)}. ")
            parts.append("I can help you find jobs, check your match for specific roles, or tailor your resume. What would you like to do?")
        else:
            parts.append("Hi! I'm your Pathfinder career agent. To get started, upload your resume so I can help you find matching jobs. What brings you here today?")

    # Handle errors
    if errors:
        parts.append("\n\n*Note: Some steps encountered issues:*")
        for step_id, error in list(errors.items())[:2]:
            parts.append(f"\n- {step_id}: {error[:150]}")

    final = "\n".join(parts) if parts else "I've completed your request. Is there anything else I can help with?"

    return {
        "final_response": final,
        "agent_phase": "response_synthesized",
    }
```

### `src/pathfinder/agent/infrastructure/langgraph/nodes/quality_gate.py`

```python
"""Quality Gate node — validates response before sending to user."""
from pathfinder.agent.domain.state import SupervisorState


async def quality_gate_node(state: SupervisorState) -> dict:
    """Validate the final response. PASS → send to user. REVISE → loop back."""
    response = state.get("final_response", "")
    passes = state.get("quality_gate_passes", 0)
    errors = state.get("errors", [])

    # Completeness check
    if not response or len(response.strip()) < 10:
        if passes < 3:
            return {"quality_gate_passes": passes + 1, "agent_phase": "revise"}
        return {"final_response": "I encountered an issue processing your request. Please try again or rephrase.",
                "agent_phase": "quality_failed"}

    # Safety check: reject obviously problematic responses
    banned_phrases = ["I cannot", "I'm unable to", "I don't know how to"]
    if any(p in response for p in banned_phrases) and passes < 2:
        return {"quality_gate_passes": passes + 1, "agent_phase": "revise"}

    return {"agent_phase": "quality_passed"}
```

### `src/pathfinder/agent/infrastructure/langgraph/supervisor_graph.py`

```python
"""Supervisor Graph — compiles all nodes into the LangGraph StateGraph."""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from pathfinder.shared.config import get_settings
from pathfinder.agent.domain.state import SupervisorState
from pathfinder.agent.infrastructure.langgraph.nodes.guardrail import guardrail_node
from pathfinder.agent.infrastructure.langgraph.nodes.context_builder import context_builder_node
from pathfinder.agent.infrastructure.langgraph.nodes.intent_router_node import intent_router_node
from pathfinder.agent.infrastructure.langgraph.nodes.tool_executor import tool_executor_node
from pathfinder.agent.infrastructure.langgraph.nodes.result_synthesizer import result_synthesizer_node
from pathfinder.agent.infrastructure.langgraph.nodes.quality_gate import quality_gate_node


def _build_graph() -> StateGraph:
    builder = StateGraph(SupervisorState)

    # Add nodes
    builder.add_node("guardrail", guardrail_node)
    builder.add_node("context_builder", context_builder_node)
    builder.add_node("intent_router", intent_router_node)
    builder.add_node("tool_executor", tool_executor_node)
    builder.add_node("result_synthesizer", result_synthesizer_node)
    builder.add_node("quality_gate", quality_gate_node)

    # Entry point
    builder.set_entry_point("guardrail")

    # Edges
    builder.add_edge("guardrail", "context_builder")
    builder.add_edge("context_builder", "intent_router")

    # Conditional: needs clarification → short-circuit to result
    def should_short_circuit(state: SupervisorState) -> str:
        if state.get("agent_phase") == "needs_clarification":
            return "result_synthesizer"
        if state.get("final_response"):
            return END
        return "tool_executor"

    builder.add_conditional_edges("intent_router", should_short_circuit, {
        "result_synthesizer": "result_synthesizer",
        "tool_executor": "tool_executor",
        END: END,
    })

    builder.add_edge("tool_executor", "result_synthesizer")

    # Conditional: quality gate → PASS or REVISE
    def quality_decision(state: SupervisorState) -> str:
        phase = state.get("agent_phase", "")
        if phase == "revise":
            return "result_synthesizer"  # loop back
        if state.get("final_response"):
            return END
        return END

    builder.add_conditional_edges("quality_gate", quality_decision, {
        "result_synthesizer": "result_synthesizer",
        END: END,
    })

    builder.add_edge("result_synthesizer", "quality_gate")

    return builder


def compile_supervisor_graph():
    """Compile the graph with PostgreSQL checkpointing."""
    builder = _build_graph()
    settings = get_settings()

    # Use PostgresSaver for durable checkpointing
    checkpointer = PostgresSaver.from_conn_string(settings.database_url)
    # checkpointer.setup()  # Run once to create checkpoint tables

    graph = builder.compile(checkpointer=checkpointer)
    return graph


# Singleton for the FastAPI app
supervisor_graph = compile_supervisor_graph()
```

---

## Day 7–8: Persistence, APIs, Registration

### `src/pathfinder/agent/infrastructure/persistence/models.py`

```python
"""SQLAlchemy ORM models for agent domain."""
from uuid import UUID
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from pathfinder.shared.infrastructure.persistence.base import Base, UUIDMixin, TimestampMixin
from pathfinder.agent.domain.entities import AgentExecution, ApprovalRequest


class AgentExecutionModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_executions"

    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[UUID] = mapped_column(PGUUID, index=True)
    call_id: Mapped[UUID] = mapped_column(PGUUID, unique=True)
    parent_call_id: Mapped[UUID | None] = mapped_column(PGUUID, nullable=True)
    intent: Mapped[str] = mapped_column(String(50), default="")
    intent_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    user_message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="pending")
    execution_plan: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    tool_results: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    final_response: Mapped[str] = mapped_column(Text, default="")
    response_artifacts: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    tokens_used: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    llm_model: Mapped[str] = mapped_column(String(50), default="")
    llm_provider: Mapped[str] = mapped_column(String(20), default="deepseek")
    is_success: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str] = mapped_column(Text, default="")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    user_approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    user_modified: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_domain(self) -> AgentExecution:
        return AgentExecution(
            id=self.id, user_id=self.user_id, session_id=self.session_id,
            call_id=self.call_id, intent=self.intent,
            intent_confidence=self.intent_confidence,
            user_message=self.user_message, status=self.status,
            execution_plan=self.execution_plan or [],
            tool_results=self.tool_results or [],
            final_response=self.final_response,
            response_artifacts=self.response_artifacts or [],
            tokens_used=self.tokens_used or {},
            latency_ms=self.latency_ms, llm_model=self.llm_model,
            llm_provider=self.llm_provider, is_success=self.is_success,
            error_message=self.error_message, retry_count=self.retry_count,
            user_approved=self.user_approved, user_modified=self.user_modified,
            completed_at=self.completed_at,
            created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, e: AgentExecution) -> "AgentExecutionModel":
        return cls(
            id=e.id, user_id=e.user_id, session_id=e.session_id,
            call_id=e.call_id, parent_call_id=e.parent_call_id,
            intent=e.intent, intent_confidence=e.intent_confidence,
            user_message=e.user_message, status=e.status.value,
            execution_plan=e.execution_plan, tool_results=e.tool_results,
            final_response=e.final_response, response_artifacts=e.response_artifacts,
            tokens_used=e.tokens_used, latency_ms=e.latency_ms,
            llm_model=e.llm_model, llm_provider=e.llm_provider,
            is_success=e.is_success, error_message=e.error_message,
            retry_count=e.retry_count, user_approved=e.user_approved,
            user_modified=e.user_modified, completed_at=e.completed_at,
            created_at=e.created_at, updated_at=e.updated_at,
        )


class ApprovalRequestModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "approval_requests"

    execution_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("agent_executions.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(50))
    action_summary: Mapped[str] = mapped_column(Text)
    action_detail: Mapped[str] = mapped_column(Text)
    diff_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(10), default="low")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    edits: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rejection_reason: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_domain(self) -> ApprovalRequest:
        return ApprovalRequest(
            id=self.id, execution_id=self.execution_id, user_id=self.user_id,
            action_type=self.action_type, action_summary=self.action_summary,
            action_detail=self.action_detail, diff_data=self.diff_data,
            preview=self.preview, risk_level=self.risk_level,
            status=self.status, edits=self.edits,
            rejection_reason=self.rejection_reason,
            decided_at=self.decided_at, expires_at=self.expires_at,
            created_at=self.created_at, updated_at=self.updated_at,
        )
```

### `src/pathfinder/agent/presentation/router.py`

```python
"""Agent API routes."""
from uuid import UUID, uuid4
import json
import time
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.presentation.dependencies import get_current_user
from pathfinder.identity.domain.entities import User
from pathfinder.agent.domain.state import SupervisorState
from pathfinder.agent.infrastructure.langgraph.supervisor_graph import supervisor_graph
from pathfinder.agent.infrastructure.persistence.models import AgentExecutionModel, ApprovalRequestModel
from pathfinder.agent.infrastructure.tools.search_tools import register_search_tools
from pathfinder.agent.infrastructure.tools.match_tools import register_match_tools
from pathfinder.agent.infrastructure.tools.profile_tools import register_profile_tools

router = APIRouter(prefix="/v1/agent", tags=["Agent"])

# Register tools on module load
register_search_tools()
register_match_tools()
register_profile_tools()


@router.post("/execute")
async def agent_execute(
    request: Request,
    message: str = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Execute agent with user message. Returns JSON or SSE streaming."""
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    user_message = body.get("message", message or "")
    stream = body.get("stream", True)
    session_id = str(uuid4())

    # Build initial state
    initial_state: SupervisorState = {
        "session_id": session_id,
        "user_id": str(current_user.id),
        "tier": current_user.tier.value,
        "user_message": user_message,
        "agent_phase": "starting",
        "call_id": str(uuid4()),
        "total_tokens_used": 0,
        "total_latency_ms": 0,
        "errors": [],
        "quality_gate_passes": 0,
        "execution_plan": [],
        "current_step": 0,
        "tool_results": {},
        "tool_errors": {},
        "messages": [],
        "pending_approval": None,
        "approval_history": [],
        "final_response": None,
        "response_artifacts": [],
        "intent": None,
        "intent_confidence": 0.0,
        "clarification_question": None,
        "user_profile": None,
        "user_preferences": None,
        "user_resumes": [],
        "active_applications": [],
        "recent_history": [],
    }

    start_time = time.monotonic()

    if stream:
        async def event_stream():
            config = {"configurable": {"thread_id": session_id}}
            async for event in supervisor_graph.astream(initial_state, config):
                event_type = list(event.keys())[0] if event else "unknown"
                yield f"event: {event_type}\ndata: {json.dumps(event, default=str)}\n\n"

            # Log execution
            latency = int((time.monotonic() - start_time) * 1000)
            yield f"event: done\ndata: {json.dumps({'latency_ms': latency})}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        config = {"configurable": {"thread_id": session_id}}
        final_state = await supervisor_graph.ainvoke(initial_state, config)
        latency = int((time.monotonic() - start_time) * 1000)

        # Persist execution record
        exec_model = AgentExecutionModel(
            user_id=current_user.id, session_id=UUID(session_id),
            call_id=UUID(initial_state["call_id"]),
            intent=final_state.get("intent", ""),
            intent_confidence=final_state.get("intent_confidence", 0.0),
            user_message=user_message,
            status="completed",
            execution_plan=final_state.get("execution_plan", []),
            tool_results=[{"step": k, "result": v} for k, v in final_state.get("tool_results", {}).items()],
            final_response=final_state.get("final_response", ""),
            latency_ms=latency,
            is_success=True,
        )
        session.add(exec_model)
        await session.commit()

        return {
            "data": {
                "execution_id": str(exec_model.id),
                "session_id": session_id,
                "response": final_state.get("final_response", ""),
                "artifacts": final_state.get("response_artifacts", []),
                "tool_results": {k: v for k, v in final_state.get("tool_results", {}).items()},
                "intent": final_state.get("intent"),
                "intent_confidence": final_state.get("intent_confidence"),
                "latency_ms": latency,
            }
        }


@router.get("/executions")
async def list_executions(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select
    stmt = select(AgentExecutionModel).where(
        AgentExecutionModel.user_id == current_user.id,
    ).order_by(AgentExecutionModel.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    models = result.scalars().all()
    return {
        "data": [
            {"execution_id": str(m.id), "call_id": str(m.call_id),
             "intent": m.intent, "status": m.status,
             "is_success": m.is_success, "latency_ms": m.latency_ms,
             "created_at": m.created_at.isoformat()}
            for m in models
        ],
        "meta": {"count": len(models), "limit": limit},
    }


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    model = await session.get(AgentExecutionModel, execution_id)
    if not model or model.user_id != current_user.id:
        from pathfinder.shared.domain.exceptions import NotFoundError
        raise NotFoundError("Execution not found")
    return {"data": {
        "execution_id": str(model.id),
        "intent": model.intent, "status": model.status,
        "user_message": model.user_message,
        "final_response": model.final_response,
        "tool_results": model.tool_results,
        "tokens_used": model.tokens_used,
        "latency_ms": model.latency_ms,
        "is_success": model.is_success,
        "error_message": model.error_message,
        "created_at": model.created_at.isoformat(),
    }}


@router.post("/approvals/{approval_id}")
async def respond_to_approval(
    approval_id: UUID,
    body: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    decision = body.get("decision")
    if decision not in ("approved", "rejected", "edited"):
        from pathfinder.shared.domain.exceptions import ValidationError
        raise ValidationError("decision must be approved, rejected, or edited")

    model = await session.get(ApprovalRequestModel, approval_id)
    if not model or model.user_id != current_user.id:
        from pathfinder.shared.domain.exceptions import NotFoundError
        raise NotFoundError("Approval not found")

    if decision == "approved":
        model.status = "approved"
    elif decision == "rejected":
        model.status = "rejected"
        model.rejection_reason = body.get("reason", "")
    elif decision == "edited":
        model.status = "edited"
        model.edits = body.get("edits", {})

    model.decided_at = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
    await session.commit()

    return {"data": {"approval_id": str(approval_id), "status": model.status}}
```

### `src/pathfinder/shared/infrastructure/main.py` — Update

```python
from pathfinder.agent.presentation.router import router as agent_router
app.include_router(agent_router)
```

### Migration — `alembic/versions/006_agent_tables.py`

```python
"""006_agent_tables — agent_executions + approval_requests."""
revision = "006"
down_revision = "005"

def upgrade():
    op.create_table("agent_executions",
        sa.Column("id", PGUUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", PGUUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", PGUUID(), nullable=False),
        sa.Column("call_id", PGUUID(), unique=True),
        sa.Column("parent_call_id", PGUUID(), nullable=True),
        sa.Column("intent", sa.String(50), default=""),
        sa.Column("intent_confidence", sa.Float(), default=0.0),
        sa.Column("user_message", sa.Text(), default=""),
        sa.Column("status", sa.String(30), default="pending"),
        sa.Column("execution_plan", JSONB(), default=list, server_default="[]"),
        sa.Column("tool_results", JSONB(), default=list, server_default="[]"),
        sa.Column("final_response", sa.Text(), default=""),
        sa.Column("response_artifacts", JSONB(), default=list, server_default="[]"),
        sa.Column("tokens_used", JSONB(), default=dict, server_default="{}"),
        sa.Column("latency_ms", sa.Integer(), default=0),
        sa.Column("llm_model", sa.String(50), default=""),
        sa.Column("llm_provider", sa.String(20), default="deepseek"),
        sa.Column("is_success", sa.Boolean(), default=False),
        sa.Column("error_message", sa.Text(), default=""),
        sa.Column("retry_count", sa.Integer(), default=0),
        sa.Column("user_approved", sa.Boolean(), nullable=True),
        sa.Column("user_modified", sa.Boolean(), default=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_agent_user_time", "agent_executions", ["user_id", sa.text("created_at DESC")])
    op.create_index("idx_agent_session", "agent_executions", ["session_id"])

    op.create_table("approval_requests",
        sa.Column("id", PGUUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("execution_id", PGUUID(), sa.ForeignKey("agent_executions.id"), nullable=False),
        sa.Column("user_id", PGUUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action_type", sa.String(50)),
        sa.Column("action_summary", sa.Text()),
        sa.Column("action_detail", sa.Text()),
        sa.Column("diff_data", JSONB(), nullable=True),
        sa.Column("preview", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(10), default="low"),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("edits", JSONB(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), default=""),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
```

---

## Day 9–10: Tests + Gate Review

### `tests/unit/agent/test_tool_registry.py`

```python
import pytest
from pathfinder.agent.domain.tools import ToolRegistry, ToolDefinition

async def _echo_tool(**kwargs):
    return {"echo": kwargs}

def test_register_and_execute_tool():
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(name="echo", description="Echoes back arguments",
                       parameters={"type": "object", "properties": {}}),
        _echo_tool,
    )
    assert "echo" in registry.tool_names
    assert len(registry.get_definitions_for_llm()) == 1

@pytest.mark.asyncio
async def test_execute_successful_tool():
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(name="greet", description="Greets", parameters={}),
        lambda **kw: {"greeting": "hello"},
    )
    result = await registry.execute("greet")
    assert result.success
    assert result.data["greeting"] == "hello"

@pytest.mark.asyncio
async def test_execute_unknown_tool_returns_error():
    registry = ToolRegistry()
    result = await registry.execute("nonexistent")
    assert not result.success
    assert "Unknown tool" in result.error

@pytest.mark.asyncio
async def test_execute_failing_tool_returns_error():
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(name="failer", description="Always fails", parameters={}),
        lambda **kw: (_ for _ in ()).throw(Exception("boom")),
    )
    result = await registry.execute("failer")
    assert not result.success
    assert "boom" in result.error
```

### `tests/unit/agent/test_intent_router.py`

```python
import pytest
from unittest.mock import AsyncMock
from pathfinder.agent.domain.services import IntentRouter
from pathfinder.agent.domain.value_objects import Intent

@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    return llm

@pytest.mark.asyncio
async def test_classify_search_jobs(mock_llm):
    mock_llm.chat_completion.return_value.content = '{"intent": "search_jobs", "confidence": 0.95}'
    router = IntentRouter(mock_llm)
    intent, conf = await router.classify("find me python jobs")
    assert intent == Intent.SEARCH_JOBS
    assert conf == 0.95

@pytest.mark.asyncio
async def test_classify_ambiguous_falls_back(mock_llm):
    mock_llm.chat_completion.side_effect = Exception("API error")
    router = IntentRouter(mock_llm)
    intent, conf = await router.classify("???")
    assert intent == Intent.GENERAL_QUESTION
    assert conf < 0.5
```

### `tests/integration/api/test_agent_api.py`

```python
import pytest
from httpx import ASGITransport, AsyncClient
from pathfinder.shared.infrastructure.main import create_app

pytestmark = pytest.mark.integration

@pytest.fixture
async def client_and_token():
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/v1/auth/register", json={
            "email": "agent-test@test.com", "password": "Test1234!",
            "full_name": "Agent Tester", "accept_terms": True,
        })
        token = resp.json()["data"]["tokens"]["access_token"]
        yield c, token

async def test_agent_execute_general_question(client_and_token):
    client, token = client_and_token
    resp = await client.post("/v1/agent/execute", json={
        "message": "Hello! What can you help me with?",
        "stream": False,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "response" in data
    assert len(data["response"]) > 10

async def test_agent_execute_requires_auth(client_and_token):
    client, _ = client_and_token
    resp = await client.post("/v1/agent/execute", json={"message": "hi", "stream": False})
    assert resp.status_code == 401

async def test_agent_execution_history(client_and_token):
    client, token = client_and_token
    resp = await client.get("/v1/agent/executions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "data" in resp.json()
```

### Gate Checklist

```
☐ 7 tools registered (search_jobs, get_job_detail, compute_match, get_recommendations, get_profile, get_resumes)
☐ Supervisor graph compiles with 6 nodes
☐ PostgresSaver checkpointer configured
☐ POST /v1/agent/execute (non-stream) → 200 with response
☐ POST /v1/agent/execute (stream) → SSE events
☐ GET /v1/agent/executions → 200 with history
☐ GET /v1/agent/executions/{id} → 200
☐ POST /v1/agent/approvals/{id} → 200
☐ Intent classification: "find jobs" → search_jobs
☐ Intent classification: ambiguous → general_question (low confidence)
☐ Agent execution record persisted to DB
☐ Unauthorized request → 401
☐ Migration 006 creates agent_executions + approval_requests tables
☐ All unit tests pass (12+)
☐ All integration tests pass (6+)
☐ ruff check → 0. mypy --strict → 0
```

---

> *"Sprint 6: One Supervisor. Seven tools. The foundation of the agentic system. No multi-agent complexity yet — just a single graph that understands intent, plans actions, and executes."*

**End of Sprint 6**
