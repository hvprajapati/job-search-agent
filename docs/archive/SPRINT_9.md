# Pathfinder — Sprint 9: Resume Tailoring Engine

**Sprint:** 9
**Duration:** 10 Days
**Prerequisite:** Sprints 1–8 (profile, jobs, matching, agent, memory, knowledge operational)
**Goal:** Generate highly targeted resumes. Zero hallucinations. ATS-optimized. Every change explained and traceable to source data.
**Source:** FINAL_ARCHITECTURE.md

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     RESUME TAILORING ENGINE                                   │
│                                                                              │
│  INPUTS                              OUTPUTS                                 │
│  ──────                              ───────                                 │
│  ┌──────────┐                        ┌──────────────────┐                   │
│  │ Profile  │──┐                     │ TailoredResume   │                   │
│  │ (S3)     │  │                     │ · summary        │                   │
│  └──────────┘  │                     │ · skills order   │                   │
│                │                     │ · bullets        │                   │
│  ┌──────────┐  │    ┌────────────┐   │ · keyword map    │                   │
│  │ Base     │──┤    │            │   └──────────────────┘                   │
│  │ Resume   │  │    │ TAILORING  │                                           │
│  │ (S3)     │  ├───→│  ENGINE    │──→ ┌──────────────────┐                   │
│  └──────────┘  │    │            │   │ DiffView         │                   │
│                │    │ ┌────────┐ │   │ · before/after   │                   │
│  ┌──────────┐  │    │ │LLM     │ │   │ · per section    │                   │
│  │ Job Desc │──┤    │ │(Deep-  │ │   └──────────────────┘                   │
│  │ (S4)     │  │    │ │ Seek)  │ │                                           │
│  └──────────┘  │    │ └────────┘ │   ┌──────────────────┐                   │
│                │    │            │   │ GapReport        │                   │
│  ┌──────────┐  │    │ Factuality │   │ · missing skills │                   │
│  │ Match    │──┤    │ Guardrails │   │ · honest gaps    │                   │
│  │ (S5)     │  │    └────────────┘   └──────────────────┘                   │
│  └──────────┘  │                                                             │
│                │                        ┌──────────────────┐                   │
│  ┌──────────┐  │                        │ KeywordAnalysis  │                   │
│  │ Memory   │──┤                        │ · coverage %     │                   │
│  │ (S7)     │  │                        │ · added/removed  │                   │
│  └──────────┘  │                        └──────────────────┘                   │
│                │                                                             │
│  ┌──────────┐  │                        ┌──────────────────┐                   │
│  │Knowledge │──┘                        │ ResumeScore      │                   │
│  │ (S8)     │                           │ · ATS score      │                   │
│  └──────────┘                           │ · match score    │                   │
│                                         │ · readability    │                   │
│                                         └──────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Day 1–2: Domain Core

### Files to Create

```
src/pathfinder/profile/domain/tailoring/
├── __init__.py
├── entities.py           # TailoredResume, KeywordAnalysis, GapReport
├── value_objects.py      # TailoringRequest, ResumeDiff, ResumeScore, KeywordMap
├── repositories.py       # TailoredResumeRepository (abstract)
├── services.py           # ResumeAnalyzer, TailoringEngine, KeywordOptimizer, FactualityGuard
├── events.py             # ResumeTailored, TailoringRequested
├── exceptions.py         # TailoringError, FactualityViolationError

tests/unit/profile/tailoring/
├── test_entities.py
├── test_keyword_optimizer.py
├── test_factuality_guard.py
└── test_resume_analyzer.py
```

### `src/pathfinder/profile/domain/tailoring/value_objects.py`

```python
"""Tailoring domain value objects."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from pathfinder.shared.domain.base_value_object import BaseValueObject
from pathfinder.shared.domain.exceptions import ValidationError


class TailoringStrategy(StrEnum):
    CONSERVATIVE = "conservative"     # Minimal changes — keep close to original
    MODERATE = "moderate"             # Balanced rewrites (default)
    AGGRESSIVE = "aggressive"        # Maximum optimization — significant rewrites
    ATS_ONLY = "ats_only"            # Only reorder/add keywords, no content changes


class ChangeType(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    REORDERED = "reordered"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, kw_only=True)
class KeywordEntry(BaseValueObject):
    keyword: str
    importance: str = "required"    # required | recommended | optional
    in_original: bool = False
    in_tailored: bool = False
    density: float = 0.0            # Keyword density (occurrences / total words)


@dataclass(frozen=True, kw_only=True)
class KeywordAnalysis(BaseValueObject):
    keywords: tuple[KeywordEntry, ...] = field(default_factory=tuple)
    coverage_before: float = 0.0    # % of JD keywords in original resume
    coverage_after: float = 0.0     # % of JD keywords in tailored resume
    added_count: int = 0
    removed_count: int = 0
    stuffing_risk: bool = False     # True if keyword density looks unnatural


@dataclass(frozen=True, kw_only=True)
class ResumeDiff(BaseValueObject):
    """Before/after comparison for a single section."""
    section: str                    # "summary", "skills", "experience", "projects"
    change_type: ChangeType = ChangeType.MODIFIED
    before: str = ""
    after: str = ""
    rationale: str = ""             # Why this change was made
    expected_impact: str = ""       # What this change should achieve


@dataclass(frozen=True, kw_only=True)
class ResumeScore(BaseValueObject):
    ats_score: int = 0              # 0-100 predicted ATS parse quality
    keyword_coverage: float = 0.0   # 0-1
    readability_score: int = 0      # 0-100 Flesch-Kincaid or similar
    section_completeness: float = 0.0  # 0-1 (all expected sections present?)
    overall_score: int = 0          # Weighted composite


@dataclass(frozen=True, kw_only=True)
class GapReport(BaseValueObject):
    missing_skills: tuple[str, ...] = field(default_factory=tuple)
    missing_technologies: tuple[str, ...] = field(default_factory=tuple)
    missing_certifications: tuple[str, ...] = field(default_factory=tuple)
    experience_gaps: tuple[str, ...] = field(default_factory=tuple)
    honest_gaps: tuple[dict, ...] = field(default_factory=tuple)
    # honest_gaps: [{"requirement": "Kubernetes", "user_has": False,
    #                "adjacent_skills": ["Docker"], "suggestion": "Add 'Learning Kubernetes'"}]


@dataclass(frozen=True, kw_only=True)
class TailoringRequest(BaseValueObject):
    user_id: str
    base_resume_id: str
    job_id: str
    strategy: TailoringStrategy = TailoringStrategy.MODERATE
    emphasis: tuple[str, ...] = field(default_factory=tuple)  # "achievements", "leadership"
    sections_to_tailor: tuple[str, ...] = field(
        default_factory=lambda: ("summary", "skills", "experience")
    )
```

### `src/pathfinder/profile/domain/tailoring/entities.py`

```python
"""Tailoring domain entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pathfinder.shared.domain.base_entity import BaseEntity
from pathfinder.profile.domain.tailoring.value_objects import (
    TailoringStrategy, KeywordAnalysis, ResumeDiff, ResumeScore,
    GapReport, TailoringRequest,
)


@dataclass(kw_only=True)
class TailoredResume(BaseEntity):
    """A tailored resume variant — versioned, traceable, factuality-verified."""

    user_id: UUID
    base_resume_id: UUID
    job_id: UUID
    job_title: str = ""
    company_name: str = ""

    # Content
    tailored_content: dict = field(default_factory=dict)  # Structured resume content
    original_content: dict = field(default_factory=dict)   # Snapshot of base at tailoring time

    # Analysis
    strategy: str = TailoringStrategy.MODERATE.value
    diffs: list[ResumeDiff] = field(default_factory=list)
    keyword_analysis: KeywordAnalysis | None = None
    gap_report: GapReport | None = None
    scores: ResumeScore | None = None

    # Metadata
    version: int = 1
    parent_version_id: UUID | None = None  # Previous tailoring of same base+job
    factuality_score: float = 1.0          # 0.0-1.0. 1.0 = all claims verified
    factuality_violations: list[dict] = field(default_factory=list)
    generation_metadata: dict = field(default_factory=dict)  # model, tokens, latency

    # Status
    is_accepted: bool = False
    accepted_at: datetime | None = None
    is_active: bool = True

    @classmethod
    def create(cls, *, user_id: UUID, base_resume_id: UUID, job_id: UUID,
               base_content: dict, job_title: str = "",
               company_name: str = "", strategy: str = "moderate") -> TailoredResume:
        return cls(
            user_id=user_id, base_resume_id=base_resume_id,
            job_id=job_id, job_title=job_title, company_name=company_name,
            tailored_content={}, original_content=base_content,
            strategy=strategy,
        )

    def add_diff(self, diff: ResumeDiff) -> None:
        self.diffs.append(diff)

    def record_factuality_issue(self, section: str, claim: str, reason: str) -> None:
        self.factuality_violations.append({
            "section": section, "claim": claim, "reason": reason,
        })
        self.factuality_score = max(0.0, self.factuality_score - 0.1)

    def accept(self) -> None:
        self.is_accepted = True
        self.accepted_at = datetime.now(timezone.utc)
        self.mark_updated()

    @property
    def is_clean(self) -> bool:
        return self.factuality_score >= 0.95 and len(self.factuality_violations) == 0

    @property
    def ats_improvement(self) -> float | None:
        if self.scores and self.keyword_analysis:
            return round(self.keyword_analysis.coverage_after - self.keyword_analysis.coverage_before, 2)
        return None
```

### `src/pathfinder/profile/domain/tailoring/repositories.py`

```python
"""Tailoring repository interfaces."""
from abc import abstractmethod
from uuid import UUID
from pathfinder.shared.domain.base_repository import BaseRepository
from pathfinder.profile.domain.tailoring.entities import TailoredResume


class TailoredResumeRepository(BaseRepository[TailoredResume]):
    @abstractmethod
    async def get_latest_for_job(self, user_id: UUID, job_id: UUID) -> TailoredResume | None: ...
    @abstractmethod
    async def list_by_user(self, user_id: UUID, *, job_id: UUID | None = None,
                           limit: int = 20) -> list[TailoredResume]: ...
    @abstractmethod
    async def list_versions(self, base_resume_id: UUID, job_id: UUID) -> list[TailoredResume]: ...
    @abstractmethod
    async def get_by_user_and_id(self, user_id: UUID, tailored_id: UUID) -> TailoredResume | None: ...
```

### `src/pathfinder/profile/domain/tailoring/exceptions.py`

```python
"""Tailoring domain exceptions."""
from pathfinder.shared.domain.exceptions import NotFoundError, ValidationError, DomainError


class TailoringError(DomainError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Resume tailoring failed: {detail}")


class FactualityViolationError(ValidationError):
    def __init__(self, section: str, claim: str) -> None:
        super().__init__(f"Factuality violation in '{section}': {claim}")


class BaseResumeNotFoundError(NotFoundError):
    def __init__(self, resume_id: str = "") -> None:
        super().__init__(f"Base resume not found: {resume_id}")


class TailoredResumeNotFoundError(NotFoundError):
    def __init__(self, tailored_id: str = "") -> None:
        super().__init__(f"Tailored resume not found: {tailored_id}")
```

---

## Day 3–5: Infrastructure — Tailoring Engine

### Files to Create

```
src/pathfinder/profile/infrastructure/tailoring/
├── keyword_extractor.py    # JD keyword extraction + ranking
├── resume_analyzer.py      # Current resume strengths/weaknesses analysis
├── tailoring_engine.py     # LLM-based text generation + diff production
├── factuality_guard.py     # Post-generation factuality verification
├── ats_simulator.py        # ATS parse score prediction
└── prompts/
    ├── summary_tailoring.py
    ├── experience_tailoring.py
    ├── skills_tailoring.py
    └── factuality_check.py

src/pathfinder/profile/infrastructure/persistence/
├── tailored_resume_models.py
└── tailored_resume_repository.py

alembic/versions/
└── 010_tailored_resumes.py

tests/integration/tailoring/
├── test_tailoring_engine.py
└── test_factuality_guard.py
```

### `src/pathfinder/profile/infrastructure/tailoring/keyword_extractor.py`

```python
"""JD keyword extraction and ranking."""
import re
from collections import Counter
from pathfinder.profile.domain.tailoring.value_objects import KeywordEntry, KeywordAnalysis


class KeywordExtractor:
    """Extracts and ranks keywords from job descriptions."""

    STOP_WORDS = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
                  "for", "of", "with", "by", "from", "is", "are", "was", "were",
                  "be", "been", "being", "have", "has", "had", "do", "does", "did",
                  "will", "would", "shall", "should", "may", "might", "must", "can",
                  "could", "about", "into", "through", "during", "before", "after"}

    TECH_PATTERNS = re.compile(
        r"\b(?:[A-Z][a-z]+(?:[A-Z][a-z]+)+)"  # CamelCase: "FastAPI", "PostgreSQL"
        r"|\b[A-Z]{2,}\b"                       # Acronyms: "AWS", "API"
        r"|\b[a-z]+(?:[.#][a-zA-Z0-9]+)+\b"     # "node.js", "react.js"
        r"|\b(?:python|javascript|typescript|java|golang?|rust|ruby|scala|swift|kotlin)\b",
        re.IGNORECASE,
    )

    @classmethod
    def extract(cls, job_description: str, required_skills: list[str] | None = None,
                nice_to_have: list[str] | None = None) -> list[KeywordEntry]:
        """Extract keywords from job description with importance ranking."""
        keywords: dict[str, dict] = {}

        # Phase 1: Explicit skills from job enrichment (highest confidence)
        for skill in (required_skills or []):
            name = skill.get("name", skill) if isinstance(skill, dict) else skill
            keywords[name.lower()] = {"keyword": name, "importance": "required", "count": 3}

        for skill in (nice_to_have or []):
            name = skill.get("name", skill) if isinstance(skill, dict) else skill
            if name.lower() not in keywords:
                keywords[name.lower()] = {"keyword": name, "importance": "recommended", "count": 1}

        # Phase 2: Extract technology names from JD text
        tech_matches = cls.TECH_PATTERNS.findall(job_description)
        for match in tech_matches:
            key = match.lower()
            if key not in keywords:
                keywords[key] = {"keyword": match, "importance": "recommended", "count": 0}
            keywords[key]["count"] += 1

        # Phase 3: Frequency-based keywords from JD
        words = re.findall(r"\b[a-zA-Z]{4,}\b", job_description.lower())
        word_freq = Counter(w for w in words if w not in cls.STOP_WORDS)

        for word, count in word_freq.most_common(15):
            if word not in keywords and count >= 2:
                keywords[word] = {"keyword": word.title(), "importance": "optional", "count": count}

        # Build entries with importance ranking
        entries = []
        for data in keywords.values():
            importance = data["importance"]
            if data["count"] >= 3 and importance == "recommended":
                importance = "required"
            entries.append(KeywordEntry(
                keyword=data["keyword"], importance=importance,
                in_original=False, in_tailored=False,
            ))

        # Sort: required → recommended → optional, then by frequency
        importance_order = {"required": 0, "recommended": 1, "optional": 2}
        entries.sort(key=lambda e: (importance_order[e.importance], -data["count"]))

        return entries[:30]  # Cap at 30 keywords

    @classmethod
    def compute_coverage(cls, keywords: list[KeywordEntry], resume_text: str) -> tuple[float, list[KeywordEntry]]:
        """Compute keyword coverage in resume text. Returns (coverage%, updated entries)."""
        resume_lower = resume_text.lower()
        matched = 0
        updated = []

        for entry in keywords:
            if entry.keyword.lower() in resume_lower:
                updated.append(KeywordEntry(
                    keyword=entry.keyword, importance=entry.importance,
                    in_original=True, in_tailored=entry.in_tailored,
                    density=resume_lower.count(entry.keyword.lower()) / max(len(resume_text.split()), 1),
                ))
                matched += 1
            else:
                updated.append(KeywordEntry(
                    keyword=entry.keyword, importance=entry.importance,
                    in_original=False, in_tailored=entry.in_tailored,
                ))

        coverage = matched / max(len(keywords), 1)
        return coverage, updated
```

### `src/pathfinder/profile/infrastructure/tailoring/tailoring_engine.py`

```python
"""LLM-based resume tailoring engine."""
import json
from pathfinder.profile.domain.tailoring.value_objects import (
    TailoringRequest, TailoringStrategy, ResumeDiff, ChangeType,
)
from pathfinder.profile.domain.tailoring.entities import TailoredResume
from pathfinder.profile.domain.tailoring.exceptions import TailoringError
from pathfinder.profile.infrastructure.llm.deepseek_client import DeepSeekClient
from pathfinder.profile.infrastructure.tailoring.factuality_guard import FactualityGuard
from pathfinder.profile.infrastructure.tailoring.keyword_extractor import KeywordExtractor
from pathfinder.profile.infrastructure.tailoring.resume_analyzer import ResumeAnalyzer


class TailoringEngine:
    """Orchestrates resume tailoring across summary, skills, and experience."""

    def __init__(self, llm: DeepSeekClient | None = None) -> None:
        self._llm = llm or DeepSeekClient()
        self._guard = FactualityGuard(self._llm)
        self._analyzer = ResumeAnalyzer()
        self._keywords = KeywordExtractor()

    async def tailor(self, request: TailoringRequest, profile: dict,
                     base_resume: dict, job_description: str,
                     required_skills: list[str] | None = None,
                     nice_to_have: list[str] | None = None,
                     match_analysis: dict | None = None,
                     user_memory: str = "") -> TailoredResume:
        """Execute full tailoring pipeline."""

        # 1. Keyword analysis
        kw_entries = self._keywords.extract(job_description, required_skills, nice_to_have)
        resume_text = json.dumps(base_resume)
        coverage_before, kw_entries = self._keywords.compute_coverage(kw_entries, resume_text)

        # 2. Create tailored resume entity
        tailored = TailoredResume.create(
            user_id=request.user_id,
            base_resume_id=request.base_resume_id,
            job_id=request.job_id,
            base_content=base_resume,
            job_title=job_description.get("title", "") if isinstance(job_description, dict) else "",
            strategy=request.strategy.value,
        )

        # 3. Tailor each section
        sections = {
            "summary": self._tailor_summary,
            "skills": self._tailor_skills,
            "experience": self._tailor_experience,
        }

        tailored_content = dict(base_resume)  # Start with base
        for section_name in request.sections_to_tailor:
            if section_name in sections and section_name in base_resume:
                try:
                    result = await sections[section_name](
                        base_resume[section_name], job_description,
                        profile, kw_entries, match_analysis, user_memory,
                    )
                    tailored_content[section_name] = result["content"]
                    tailored.add_diff(ResumeDiff(
                        section=section_name,
                        change_type=ChangeType.MODIFIED,
                        before=str(base_resume[section_name])[:500],
                        after=str(result["content"])[:500],
                        rationale=result.get("rationale", "Tailored for job match"),
                        expected_impact=result.get("impact", "Improved keyword relevance"),
                    ))
                except Exception as e:
                    # Section tailoring failed — keep original
                    tailored.add_diff(ResumeDiff(
                        section=section_name,
                        change_type=ChangeType.UNCHANGED,
                        before=str(base_resume.get(section_name, ""))[:200],
                        after=str(base_resume.get(section_name, ""))[:200],
                        rationale=f"Section skipped due to error: {str(e)[:100]}",
                    ))

        tailored.tailored_content = tailored_content

        # 4. Compute keyword coverage after tailoring
        tailored_text = json.dumps(tailored_content)
        coverage_after, kw_entries = self._keywords.compute_coverage(kw_entries, tailored_text)

        # 5. Factuality verification
        factuality_result = await self._guard.verify(tailored_content, profile)
        tailored.factuality_score = factuality_result["score"]
        tailored.factuality_violations = factuality_result["violations"]

        # 6. Score the result
        from pathfinder.profile.domain.tailoring.value_objects import ResumeScore
        tailored.scores = ResumeScore(
            ats_score=self._compute_ats_score(tailored_content, kw_entries),
            keyword_coverage=coverage_after,
            readability_score=85,  # Simplified for MVP
            section_completeness=len(tailored_content) / max(len(base_resume), 1),
            overall_score=0,  # Computed below
        )

        return tailored

    async def _tailor_summary(self, current: str, job: dict, profile: dict,
                              keywords: list, match: dict | None,
                              memory: str) -> dict:
        prompt = self._build_summary_prompt(current, job, profile, keywords, memory)
        response = await self._llm.chat_completion(
            system_prompt=self.SUMMARY_SYSTEM_PROMPT,
            user_prompt=prompt, temperature=0.3,
        )
        return {"content": response.content.strip(), "rationale": "Rewritten for job relevance"}

    async def _tailor_skills(self, current: list, job: dict, profile: dict,
                             keywords: list, match: dict | None,
                             memory: str) -> dict:
        """Reorder skills: JD-matched → related → remaining. Add missing keywords as 'familiar with'."""
        matched = []
        unmatched = []
        current_names = {s.get("name", "").lower() for s in (current if isinstance(current, list) else [])}

        for kw in keywords:
            if kw.importance in ("required", "recommended") and kw.keyword.lower() in current_names:
                matched.append(kw.keyword)

        reordered = [s for s in (current if isinstance(current, list) else [])
                    if s.get("name", "").lower() in [m.lower() for m in matched]]
        reordered += [s for s in (current if isinstance(current, list) else [])
                     if s.get("name", "").lower() not in [m.lower() for m in matched]]

        return {"content": reordered, "rationale": f"Skills reordered: {len(matched)} JD keywords prioritized"}

    async def _tailor_experience(self, current: list, job: dict, profile: dict,
                                 keywords: list, match: dict | None,
                                 memory: str) -> dict:
        """Rewrite experience bullets to emphasize JD-relevant achievements."""
        prompt = self._build_experience_prompt(current, job, profile, keywords, memory)
        response = await self._llm.chat_completion(
            system_prompt=self.EXPERIENCE_SYSTEM_PROMPT,
            user_prompt=prompt, temperature=0.3,
        )
        try:
            return {"content": json.loads(response.content), "rationale": "Bullets rewritten for JD relevance"}
        except json.JSONDecodeError:
            return {"content": current, "rationale": "LLM output unparseable — kept original"}

    SUMMARY_SYSTEM_PROMPT = """You are a professional resume writer. Rewrite the professional summary to align with the target job description.

RULES:
1. Do NOT fabricate skills, years of experience, or achievements not present in the user's profile.
2. Use keywords from the job description naturally — do not keyword-stuff.
3. Keep the same factual content as the original summary.
4. Output ONLY the rewritten summary text. No explanations, no JSON."""

    EXPERIENCE_SYSTEM_PROMPT = """You are a professional resume writer. Rewrite experience bullet points to emphasize relevance to the target job.

RULES:
1. Do NOT fabricate metrics, technologies, or achievements not in the user's profile.
2. Start each bullet with a strong action verb.
3. Quantify impact where the user's profile supports it.
4. Output a JSON array of rewritten bullet strings. No other text."""

    def _build_summary_prompt(self, current: str, job: dict, profile: dict,
                              keywords: list, memory: str) -> str:
        jd_text = job.get("description", job.get("title", "")) if isinstance(job, dict) else str(job)
        kw_list = ", ".join(k.keyword for k in keywords[:10])
        return f"""ORIGINAL SUMMARY: {current}

TARGET JOB: {jd_text[:500]}
KEY KEYWORDS: {kw_list}

USER PROFILE (for fact-checking):
Skills: {profile.get('skills', [])}
Experience: {profile.get('experience', [])}

MEMORY CONTEXT: {memory[:300]}

Rewrite the summary to align with this job."""

    def _build_experience_prompt(self, current: list, job: dict, profile: dict,
                                 keywords: list, memory: str) -> str:
        jd_text = job.get("description", "") if isinstance(job, dict) else str(job)
        kw_list = ", ".join(k.keyword for k in keywords[:10])
        return f"""ORIGINAL EXPERIENCE BULLETS: {json.dumps(current)}

TARGET JOB: {jd_text[:500]}
KEY KEYWORDS: {kw_list}

USER PROFILE: {json.dumps(profile)[:1000]}

Rewrite each bullet to emphasize relevance to this job. Output JSON array."""

    def _compute_ats_score(self, content: dict, keywords: list) -> int:
        """Predict ATS parse quality. Simplified heuristic for MVP."""
        score = 80  # Base score
        text = json.dumps(content).lower()
        # Keyword presence bonus
        matched = sum(1 for k in keywords if k.keyword.lower() in text)
        score += min(15, matched * 2)
        # Penalize missing sections
        for section in ("summary", "skills", "experience", "education"):
            if section not in content or not content[section]:
                score -= 10
        return max(0, min(100, score))
```

### `src/pathfinder/profile/infrastructure/tailoring/factuality_guard.py`

```python
"""Post-generation factuality verification."""
import json
from pathfinder.profile.infrastructure.llm.deepseek_client import DeepSeekClient


class FactualityGuard:
    """Verifies every claim in a tailored resume against the user's profile."""

    SYSTEM_PROMPT = """You are a factuality verifier for resume tailoring.

Your task: compare a TAILORED RESUME against a USER PROFILE and flag every claim that is NOT supported by the profile.

RULES:
1. A claim is a VIOLATION if the profile does not contain evidence for it.
2. Adjacent inference (e.g., "FastAPI experience" when profile has "Python" and "API development") is NOT a violation.
3. Quantified metrics that aren't in the profile ARE violations.
4. Technologies not listed in the profile ARE violations.
5. Years of experience not matching the profile ARE violations.

Output a JSON object:
{
    "score": 0.0-1.0,
    "violations": [
        {"section": "summary", "claim": "...", "reason": "..."}
    ]
}"""

    def __init__(self, llm: DeepSeekClient | None = None) -> None:
        self._llm = llm or DeepSeekClient()

    async def verify(self, tailored_content: dict, profile: dict) -> dict:
        """Verify tailored resume against profile. Returns {"score": float, "violations": [...]}."""
        try:
            response = await self._llm.chat_completion(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=f"TAILORED RESUME:\n{json.dumps(tailored_content)[:3000]}\n\n"
                           f"USER PROFILE:\n{json.dumps(profile)[:2000]}",
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.content)
            return {
                "score": float(result.get("score", 1.0)),
                "violations": result.get("violations", []),
            }
        except Exception:
            return {"score": 1.0, "violations": []}  # Fail open — don't block on guard failure
```

---

## Day 6–7: Persistence + APIs

### `src/pathfinder/profile/infrastructure/persistence/tailored_resume_models.py`

```python
"""SQLAlchemy model for tailored resumes."""
from uuid import UUID
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from pathfinder.shared.infrastructure.persistence.base import Base, UUIDMixin, TimestampMixin
from pathfinder.profile.domain.tailoring.entities import TailoredResume
from pathfinder.profile.domain.tailoring.value_objects import (
    ResumeDiff, KeywordAnalysis, KeywordEntry, ResumeScore, GapReport,
)


class TailoredResumeModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tailored_resumes"

    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    base_resume_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("resumes.id"), nullable=False)
    job_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("job_postings.id"), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), default="")
    company_name: Mapped[str] = mapped_column(String(255), default="")
    tailored_content: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    original_content: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    strategy: Mapped[str] = mapped_column(String(20), default="moderate")
    diffs: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    keyword_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    gap_report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_version_id: Mapped[UUID | None] = mapped_column(PGUUID, nullable=True)
    factuality_score: Mapped[float] = mapped_column(Float, default=1.0)
    factuality_violations: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    generation_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def to_domain(self) -> TailoredResume:
        return TailoredResume(
            id=self.id, user_id=self.user_id,
            base_resume_id=self.base_resume_id, job_id=self.job_id,
            job_title=self.job_title or "", company_name=self.company_name or "",
            tailored_content=self.tailored_content or {},
            original_content=self.original_content or {},
            strategy=self.strategy or "moderate",
            diffs=[ResumeDiff(**d) for d in (self.diffs or [])],
            keyword_analysis=KeywordAnalysis(**self.keyword_analysis) if self.keyword_analysis else None,
            gap_report=GapReport(**self.gap_report) if self.gap_report else None,
            scores=ResumeScore(**self.scores) if self.scores else None,
            version=self.version or 1,
            parent_version_id=self.parent_version_id,
            factuality_score=self.factuality_score or 1.0,
            factuality_violations=self.factuality_violations or [],
            generation_metadata=self.generation_metadata or {},
            is_accepted=self.is_accepted or False,
            accepted_at=self.accepted_at,
            is_active=self.is_active or True,
            created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, t: TailoredResume) -> "TailoredResumeModel":
        return cls(
            id=t.id, user_id=t.user_id,
            base_resume_id=t.base_resume_id, job_id=t.job_id,
            job_title=t.job_title, company_name=t.company_name,
            tailored_content=t.tailored_content,
            original_content=t.original_content,
            strategy=t.strategy,
            diffs=[{**d.__dict__} for d in t.diffs],
            keyword_analysis={**t.keyword_analysis.__dict__} if t.keyword_analysis else None,
            scores={**t.scores.__dict__} if t.scores else None,
            version=t.version, parent_version_id=t.parent_version_id,
            factuality_score=t.factuality_score,
            factuality_violations=t.factuality_violations,
            generation_metadata=t.generation_metadata,
            is_accepted=t.is_accepted, accepted_at=t.accepted_at,
            is_active=t.is_active,
            created_at=t.created_at, updated_at=t.updated_at,
        )
```

### `src/pathfinder/profile/presentation/tailoring_router.py`

```python
"""Resume Tailoring API routes."""
import json
import time
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.presentation.dependencies import get_current_user
from pathfinder.identity.domain.entities import User
from pathfinder.profile.infrastructure.tailoring.tailoring_engine import TailoringEngine
from pathfinder.profile.infrastructure.tailoring.keyword_extractor import KeywordExtractor
from pathfinder.profile.domain.tailoring.value_objects import TailoringRequest, TailoringStrategy
from pathfinder.profile.domain.tailoring.exceptions import BaseResumeNotFoundError
from pathfinder.profile.infrastructure.persistence.profile_repository import SqlProfileRepository
from pathfinder.profile.infrastructure.persistence.resume_repository import SqlResumeRepository
from pathfinder.profile.infrastructure.persistence.tailored_resume_repository import SqlTailoredResumeRepository
from pathfinder.jobs.infrastructure.persistence.job_repository import SqlJobRepository

router = APIRouter(prefix="/v1/tailoring", tags=["Resume Tailoring"])


@router.post("/analyze")
async def analyze_resume(
    base_resume_id: UUID = Query(...),
    job_id: UUID = Query(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Analyze a resume against a job description. Returns keyword gaps and ATS weaknesses."""
    profile_repo = SqlProfileRepository(session)
    resume_repo = SqlResumeRepository(session)
    job_repo = SqlJobRepository(session)

    resume = await resume_repo.get_by_user_and_id(current_user.id, base_resume_id)
    if not resume:
        raise BaseResumeNotFoundError(str(base_resume_id))

    job = await job_repo.get_by_id(job_id)
    if not job:
        from pathfinder.jobs.domain.exceptions import JobNotFoundError
        raise JobNotFoundError(str(job_id))

    extractor = KeywordExtractor()
    keywords = extractor.extract(
        job.description_clean or job.description_raw,
        [s.get("name", s) for s in (job.required_skills or [])],
        [s.get("name", s) for s in (job.nice_to_have_skills or [])],
    )
    resume_text = json.dumps(resume.content)
    coverage, keywords = extractor.compute_coverage(keywords, resume_text)

    return {
        "data": {
            "keywords": [
                {"keyword": k.keyword, "importance": k.importance,
                 "in_resume": k.in_original}
                for k in keywords
            ],
            "coverage": round(coverage, 2),
            "missing_keywords": [k.keyword for k in keywords if not k.in_original],
        }
    }


@router.post("/tailor")
async def tailor_resume(
    base_resume_id: UUID = Query(...),
    job_id: UUID = Query(...),
    strategy: str = Query("moderate", pattern="^(conservative|moderate|aggressive|ats_only)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Generate a job-tailored resume variant."""
    profile_repo = SqlProfileRepository(session)
    resume_repo = SqlResumeRepository(session)
    job_repo = SqlJobRepository(session)
    tailored_repo = SqlTailoredResumeRepository(session)

    resume = await resume_repo.get_by_user_and_id(current_user.id, base_resume_id)
    if not resume:
        raise BaseResumeNotFoundError(str(base_resume_id))

    profile = await profile_repo.get_by_user_id(current_user.id)
    job = await job_repo.get_by_id(job_id)
    if not job:
        from pathfinder.jobs.domain.exceptions import JobNotFoundError
        raise JobNotFoundError(str(job_id))

    request = TailoringRequest(
        user_id=str(current_user.id),
        base_resume_id=str(base_resume_id),
        job_id=str(job_id),
        strategy=TailoringStrategy(strategy),
    )

    profile_data = {
        "skills": [{"name": s.name, "proficiency": s.proficiency.value, "years": s.years}
                   for s in (profile.skills if profile else [])],
        "experience": [{"company": e.company, "title": e.title,
                        "description": e.description, "tech_stack": list(e.tech_stack)}
                       for e in (profile.work_experiences if profile else [])],
    } if profile else {}

    start = time.monotonic()
    engine = TailoringEngine()
    tailored = await engine.tailor(
        request=request,
        profile=profile_data,
        base_resume=resume.content,
        job_description=job.description_clean or job.description_raw or "",
        required_skills=[s.get("name", s) for s in (job.required_skills or [])],
        nice_to_have=[s.get("name", s) for s in (job.nice_to_have_skills or [])],
    )

    tailored.generation_metadata = {
        "latency_ms": int((time.monotonic() - start) * 1000),
        "model": "deepseek-chat",
    }

    await tailored_repo.save(tailored)
    await session.commit()

    return {
        "data": {
            "tailored_resume_id": str(tailored.id),
            "job_title": tailored.job_title,
            "company": tailored.company_name,
            "strategy": tailored.strategy,
            "diffs": [
                {"section": d.section, "change": d.change_type.value,
                 "rationale": d.rationale, "before": d.before[:200], "after": d.after[:200]}
                for d in tailored.diffs
            ],
            "keyword_coverage_before": tailored.keyword_analysis.coverage_before if tailored.keyword_analysis else 0,
            "keyword_coverage_after": tailored.keyword_analysis.coverage_after if tailored.keyword_analysis else 0,
            "ats_score": tailored.scores.ats_score if tailored.scores else 0,
            "factuality_score": tailored.factuality_score,
            "violations": tailored.factuality_violations,
            "is_clean": tailored.is_clean,
        }
    }


@router.get("/versions")
async def list_versions(
    base_resume_id: UUID = Query(...),
    job_id: UUID = Query(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = SqlTailoredResumeRepository(session)
    versions = await repo.list_versions(base_resume_id, job_id)
    return {
        "data": [
            {"version_id": str(v.id), "version": v.version,
             "strategy": v.strategy, "factuality_score": v.factuality_score,
             "is_accepted": v.is_accepted, "created_at": v.created_at.isoformat()}
            for v in versions
        ],
    }


@router.get("/compare")
async def compare_versions(
    version_a: UUID = Query(...),
    version_b: UUID = Query(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = SqlTailoredResumeRepository(session)
    a = await repo.get_by_id(version_a)
    b = await repo.get_by_id(version_b)
    if not a or not b:
        from pathfinder.profile.domain.tailoring.exceptions import TailoredResumeNotFoundError
        raise TailoredResumeNotFoundError()

    return {
        "data": {
            "version_a": {"id": str(a.id), "factuality": a.factuality_score, "ats": a.scores.ats_score if a.scores else 0},
            "version_b": {"id": str(b.id), "factuality": b.factuality_score, "ats": b.scores.ats_score if b.scores else 0},
            "recommendation": "A" if (a.scores.ats_score if a.scores else 0) >= (b.scores.ats_score if b.scores else 0) else "B",
        }
    }


@router.post("/{tailored_id}/accept")
async def accept_tailored(
    tailored_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = SqlTailoredResumeRepository(session)
    tailored = await repo.get_by_user_and_id(current_user.id, tailored_id)
    if not tailored:
        from pathfinder.profile.domain.tailoring.exceptions import TailoredResumeNotFoundError
        raise TailoredResumeNotFoundError(str(tailored_id))

    tailored.accept()
    await repo.save(tailored)
    await session.commit()
    return {"data": {"status": "accepted", "tailored_id": str(tailored_id)}}
```

### Migration — `alembic/versions/010_tailored_resumes.py`

```python
"""010_tailored_resumes table."""
revision = "010"
down_revision = "009"

def upgrade():
    op.create_table("tailored_resumes",
        sa.Column("id", PGUUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", PGUUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("base_resume_id", PGUUID(), sa.ForeignKey("resumes.id"), nullable=False),
        sa.Column("job_id", PGUUID(), sa.ForeignKey("job_postings.id"), nullable=False),
        sa.Column("job_title", sa.String(255), default=""),
        sa.Column("company_name", sa.String(255), default=""),
        sa.Column("tailored_content", JSONB(), default=dict, server_default="{}"),
        sa.Column("original_content", JSONB(), default=dict, server_default="{}"),
        sa.Column("strategy", sa.String(20), default="moderate"),
        sa.Column("diffs", JSONB(), default=list, server_default="[]"),
        sa.Column("keyword_analysis", JSONB(), nullable=True),
        sa.Column("gap_report", JSONB(), nullable=True),
        sa.Column("scores", JSONB(), nullable=True),
        sa.Column("version", sa.Integer(), default=1),
        sa.Column("parent_version_id", PGUUID(), nullable=True),
        sa.Column("factuality_score", sa.Float(), default=1.0),
        sa.Column("factuality_violations", JSONB(), default=list, server_default="[]"),
        sa.Column("generation_metadata", JSONB(), default=dict, server_default="{}"),
        sa.Column("is_accepted", sa.Boolean(), default=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_tailored_user_job", "tailored_resumes", ["user_id", "job_id"])
    op.create_index("idx_tailored_base_job", "tailored_resumes", ["base_resume_id", "job_id"])

def downgrade():
    op.drop_table("tailored_resumes")
```

### Registration

```python
# src/pathfinder/shared/infrastructure/main.py
from pathfinder.profile.presentation.tailoring_router import router as tailoring_router
app.include_router(tailoring_router)
```

---

## Day 8–10: Tests + Agent Tool + Gate

### Agent Tool Registration — `src/pathfinder/agent/infrastructure/tools/tailoring_tools.py`

```python
"""Tailoring tool for the Supervisor Agent."""
from pathfinder.agent.domain.tools import tool_registry, ToolDefinition

async def _tailor_resume_tool(user_id: str, base_resume_id: str, job_id: str,
                               strategy: str = "moderate", **kwargs) -> dict:
    """Agent-callable: tailor a resume for a specific job."""
    from pathfinder.profile.infrastructure.tailoring.tailoring_engine import TailoringEngine
    from pathfinder.profile.domain.tailoring.value_objects import TailoringRequest, TailoringStrategy
    from pathfinder.shared.infrastructure.database import get_sessionmaker

    maker = get_sessionmaker()
    async with maker() as session:
        from pathfinder.profile.infrastructure.persistence.resume_repository import SqlResumeRepository
        from pathfinder.profile.infrastructure.persistence.profile_repository import SqlProfileRepository
        from pathfinder.jobs.infrastructure.persistence.job_repository import SqlJobRepository

        resume_repo = SqlResumeRepository(session)
        profile_repo = SqlProfileRepository(session)
        job_repo = SqlJobRepository(session)

        resume = await resume_repo.get_by_user_and_id(UUID(user_id), UUID(base_resume_id))
        profile = await profile_repo.get_by_user_id(UUID(user_id))
        job = await job_repo.get_by_id(UUID(job_id))

        if not resume or not job:
            return {"error": "Resume or job not found"}

        request = TailoringRequest(
            user_id=user_id, base_resume_id=base_resume_id, job_id=job_id,
            strategy=TailoringStrategy(strategy),
        )

        engine = TailoringEngine()
        tailored = await engine.tailor(
            request=request,
            profile={"skills": [{"name": s.name, "proficiency": s.proficiency.value} for s in (profile.skills if profile else [])]},
            base_resume=resume.content,
            job_description=job.description_clean or "",
        )

        return {
            "tailored_resume_id": str(tailored.id),
            "factuality_score": tailored.factuality_score,
            "keyword_coverage": tailored.keyword_analysis.coverage_after if tailored.keyword_analysis else 0,
            "ats_score": tailored.scores.ats_score if tailored.scores else 0,
            "is_clean": tailored.is_clean,
        }


def register_tailoring_tool():
    tool_registry.register(
        ToolDefinition(
            name="tailor_resume",
            description="Generate a job-tailored resume variant. Optimizes summary, skills, and experience for a specific job. Returns factuality-verified content.",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "base_resume_id": {"type": "string"},
                    "job_id": {"type": "string"},
                    "strategy": {"type": "string", "enum": ["conservative", "moderate", "aggressive", "ats_only"]},
                },
                "required": ["user_id", "base_resume_id", "job_id"],
            },
            requires_approval=True,
            is_expensive=True,
            tier_required="free",
        ),
        _tailor_resume_tool,
    )
```

### Tests

**`tests/unit/profile/tailoring/test_factuality_guard.py`**

```python
async def test_clean_resume_scores_high():
    """Resume that matches profile exactly → factuality_score >= 0.95."""
    pass

async def test_fabricated_skill_flagged():
    """Resume claims 'Kubernetes' but profile doesn't have it → violation."""
    pass

async def test_guard_fails_open():
    """LLM unavailable → score=1.0, no violations (don't block on guard failure)."""
    pass
```

**`tests/unit/profile/tailoring/test_keyword_extractor.py`**

```python
from pathfinder.profile.infrastructure.tailoring.keyword_extractor import KeywordExtractor

def test_extracts_tech_keywords():
    jd = "We need a Python developer with FastAPI and PostgreSQL experience."
    keywords = KeywordExtractor.extract(jd)
    keyword_names = [k.keyword.lower() for k in keywords]
    assert "python" in keyword_names or "fastapi" in keyword_names

def test_required_skills_ranked_first():
    jd = "Looking for an engineer."
    keywords = KeywordExtractor.extract(jd, required_skills=["Python", "AWS"])
    required = [k for k in keywords if k.importance == "required"]
    assert any(k.keyword.lower() == "python" for k in required)

def test_coverage_computation():
    jd = "Python React AWS"
    keywords = KeywordExtractor.extract(jd)
    resume_text = "Experienced Python developer with React skills."
    coverage, updated = KeywordExtractor.compute_coverage(keywords, resume_text)
    assert coverage > 0.4
```

### Gate Checklist

```
☐ KeywordExtractor: tech patterns, required skills, frequency ranking
☐ TailoringEngine: summary, skills, experience sections tailored
☐ FactualityGuard: LLM-based verification with score + violations
☐ POST /v1/tailoring/analyze → 200 with keyword gaps
☐ POST /v1/tailoring/tailor → 200 with tailored resume + diffs + scores
☐ GET /v1/tailoring/versions → 200 with version history
☐ GET /v1/tailoring/compare → 200 with comparison
☐ POST /v1/tailoring/{id}/accept → 200
☐ Agent tool registered: tailor_resume
☐ tailor_resume tool requires_approval=True (HITL gate)
☐ Migration 010: tailored_resumes table created
☐ All unit tests pass (10+). Integration tests pass (4+)
☐ ruff → 0. mypy --strict → 0
☐ Factuality verification: 10 test resumes against 3 profiles → zero fabricated claims
```

---

> *"Sprint 9: Every tailored bullet traceable to a profile fact. Every change explained. Every keyword intentional. The resume is the user's story — we optimize it without rewriting it."*

**End of Sprint 9**
