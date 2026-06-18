"""LLM-based resume tailoring engine with factuality guardrails."""
from __future__ import annotations
import json
import logging
from pathfinder.profile.domain.tailoring.value_objects import (
    TailoringRequest, ResumeDiff, ResumeScore, KeywordAnalysis, ChangeType,
)
from pathfinder.profile.domain.tailoring.entities import TailoredResume
from pathfinder.profile.infrastructure.llm.deepseek_client import DeepSeekClient
from pathfinder.profile.infrastructure.tailoring.keyword_extractor import KeywordExtractor
from pathfinder.profile.infrastructure.tailoring.factuality_guard import FactualityGuard

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = """You are a professional resume writer. Rewrite ONLY the professional summary.

CRITICAL RULES:
1. ONLY use facts present in the user profile. NEVER fabricate skills, years, or achievements.
2. Naturally incorporate keywords from the job description — do NOT keyword-stuff.
3. Keep the same length as the original summary (±20%).
4. Output ONLY the rewritten summary text. No JSON. No explanations. No markdown."""

EXPERIENCE_SYSTEM_PROMPT = """You are a professional resume writer. Rewrite experience bullet points.

CRITICAL RULES:
1. For each bullet, ONLY reference technologies and achievements confirmed in the user profile.
2. Start each bullet with a strong action verb.
3. Quantify impact ONLY where the profile provides the numbers.
4. Output a JSON array of rewritten bullet strings. No other text.
Example: ["Designed and built REST APIs using FastAPI, reducing latency by 30%", ...]"""


class TailoringEngine:
    """Orchestrates resume tailoring: keyword analysis → section rewriting → factuality verification."""

    def __init__(self, llm: DeepSeekClient | None = None) -> None:
        self._llm = llm or DeepSeekClient()
        self._guard = FactualityGuard(self._llm)

    async def tailor(self, request: TailoringRequest, profile: dict,
                     base_resume: dict, job_description: str,
                     required_skills: list[str] | None = None,
                     nice_to_have: list[str] | None = None,
                     match_analysis: dict | None = None,
                     user_memory: str = "") -> TailoredResume:
        """Execute full tailoring pipeline."""

        # 1. Keyword analysis
        kw_entries = KeywordExtractor.extract(job_description, required_skills, nice_to_have)
        resume_text = json.dumps(base_resume)
        coverage_before, kw_entries = KeywordExtractor.compute_coverage(kw_entries, resume_text)

        # 2. Create entity
        job_title = ""
        if isinstance(job_description, dict):
            job_title = job_description.get("title", "")
        tailored = TailoredResume.create(
            user_id=request.user_id, base_resume_id=request.base_resume_id,
            job_id=request.job_id, base_content=base_resume,
            job_title=job_title or "",
            strategy=request.strategy,
        )

        # 3. Tailor each section
        tailored_content = dict(base_resume)

        if "summary" in request.sections_to_tailor and base_resume.get("summary"):
            try:
                result = await self._tailor_summary(
                    str(base_resume["summary"]), job_description, profile,
                    kw_entries, user_memory,
                )
                tailored_content["summary"] = result["content"]
                tailored.add_diff(ResumeDiff(
                    section="summary", change_type=ChangeType.MODIFIED.value,
                    before=str(base_resume["summary"])[:500],
                    after=str(result["content"])[:500],
                    rationale="Rewritten for job keyword alignment",
                ))
            except Exception as e:
                logger.warning(f"Summary tailoring failed: {e}")

        if "skills" in request.sections_to_tailor and base_resume.get("skills"):
            try:
                reordered = self._tailor_skills(base_resume["skills"], kw_entries)
                tailored_content["skills"] = reordered
                tailored.add_diff(ResumeDiff(
                    section="skills", change_type=ChangeType.REORDERED.value,
                    before=str(base_resume["skills"])[:200],
                    after=str(reordered)[:200],
                    rationale=f"Reordered to prioritize {sum(1 for k in kw_entries if k.importance in ('required','recommended'))} JD keywords",
                ))
            except Exception as e:
                logger.warning(f"Skills tailoring failed: {e}")

        if "experience" in request.sections_to_tailor and base_resume.get("experience"):
            try:
                result = await self._tailor_experience(
                    base_resume["experience"], job_description, profile,
                    kw_entries, user_memory,
                )
                tailored_content["experience"] = result["content"]
                tailored.add_diff(ResumeDiff(
                    section="experience", change_type=ChangeType.MODIFIED.value,
                    before=str(base_resume["experience"])[:500],
                    after=str(result["content"])[:500],
                    rationale="Bullets rewritten for JD relevance",
                ))
            except Exception as e:
                logger.warning(f"Experience tailoring failed: {e}")

        tailored.tailored_content = tailored_content

        # 4. Post-tailoring keyword coverage
        tailored_text = json.dumps(tailored_content)
        coverage_after, kw_entries = KeywordExtractor.compute_coverage(kw_entries, tailored_text)
        added = sum(1 for k in kw_entries if not k.in_original and k.in_tailored)

        tailored.keyword_analysis = KeywordAnalysis(
            keywords=tuple(kw_entries),
            coverage_before=round(coverage_before, 2),
            coverage_after=round(coverage_after, 2),
            added_count=added,
            removed_count=0,
            stuffing_risk=coverage_after - coverage_before > 0.4,
        )

        # 5. Factuality verification
        fact_result = await self._guard.verify(tailored_content, profile)
        tailored.factuality_score = fact_result["score"]
        tailored.factuality_violations = fact_result["violations"]

        # 6. Score
        tailored.scores = ResumeScore(
            ats_score=self._compute_ats(tailored_content, kw_entries),
            keyword_coverage=round(coverage_after, 2),
            readability_score=85,
            section_completeness=round(len(tailored_content) / max(len(base_resume), 1), 2),
            overall_score=0,
        )

        return tailored

    async def _tailor_summary(self, current: str, job_description: str,
                              profile: dict, keywords: list, memory: str) -> dict:
        jd_text = job_description if isinstance(job_description, str) else job_description.get("description", "")
        kw_list = ", ".join(k.keyword for k in keywords[:10])
        prompt = (
            f"ORIGINAL SUMMARY:\n{current}\n\n"
            f"TARGET JOB DESCRIPTION:\n{jd_text[:600]}\n\n"
            f"KEY KEYWORDS TO INCLUDE: {kw_list}\n\n"
            f"USER PROFILE (for fact-checking only):\n{json.dumps(profile)[:800]}\n\n"
            f"MEMORY CONTEXT:\n{memory[:200]}\n\n"
            f"Rewrite the summary to align with this job."
        )
        response = await self._llm.chat_completion(
            system_prompt=SUMMARY_SYSTEM_PROMPT, user_prompt=prompt, temperature=0.3,
        )
        return {"content": response.content.strip()}

    def _tailor_skills(self, current: list, keywords: list) -> list:
        """Reorder skills: JD-matched first, then by proficiency, then remaining."""
        if not isinstance(current, list):
            return current
        keyword_names = {k.keyword.lower() for k in keywords if k.importance in ("required", "recommended")}
        matched = [s for s in current if s.get("name", "").lower() in keyword_names]
        remaining = [s for s in current if s.get("name", "").lower() not in keyword_names]
        # Sort matched by proficiency
        prof_order = {"expert": 0, "advanced": 1, "intermediate": 2, "beginner": 3}
        matched.sort(key=lambda s: prof_order.get(s.get("proficiency", ""), 5))
        return matched + remaining

    async def _tailor_experience(self, current: list, job_description: str,
                                  profile: dict, keywords: list, memory: str) -> dict:
        jd_text = job_description if isinstance(job_description, str) else job_description.get("description", "")
        kw_list = ", ".join(k.keyword for k in keywords[:10])
        prompt = (
            f"ORIGINAL EXPERIENCE BULLETS:\n{json.dumps(current)}\n\n"
            f"TARGET JOB:\n{jd_text[:500]}\n\n"
            f"KEY KEYWORDS: {kw_list}\n\n"
            f"USER PROFILE:\n{json.dumps(profile)[:800]}\n\n"
            f"Rewrite each bullet to emphasize JD relevance. Output JSON array only."
        )
        response = await self._llm.chat_completion(
            system_prompt=EXPERIENCE_SYSTEM_PROMPT, user_prompt=prompt, temperature=0.3,
        )
        try:
            return {"content": json.loads(response.content)}
        except json.JSONDecodeError:
            return {"content": current}

    @staticmethod
    def _compute_ats(content: dict, keywords: list) -> int:
        score = 75
        text = json.dumps(content).lower()
        # Keyword presence bonus
        matched = sum(1 for k in keywords if k.keyword.lower() in text)
        score += min(15, matched)
        # Section completeness
        for section in ("summary", "skills", "experience", "education"):
            if section in content and content[section]:
                score += 2
            else:
                score -= 5
        return max(0, min(100, score))
