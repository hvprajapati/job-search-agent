"""JD keyword extraction and ranking."""
from __future__ import annotations
import re
from collections import Counter
from pathfinder.profile.domain.tailoring.value_objects import KeywordEntry


class KeywordExtractor:
    """Extracts and ranks keywords from job descriptions."""

    STOP_WORDS: set[str] = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "shall", "should", "may", "might", "must", "can",
        "could", "about", "into", "through", "during", "before", "after",
        "that", "this", "these", "those", "it", "its", "they", "them",
        "we", "you", "our", "your", "their", "not", "no", "all", "each",
        "every", "both", "few", "more", "most", "other", "some", "such",
        "only", "own", "same", "so", "than", "too", "very", "just",
    }

    TECH_PATTERN: re.Pattern = re.compile(
        r"\b(?:[A-Z][a-z]+(?:[A-Z][a-z]+)+)"   # CamelCase
        r"|\b[A-Z]{2,}\b"                        # Acronyms
        r"|\b[a-z]+(?:[.#+][a-zA-Z0-9]+)+\b"     # dotted/slashed
        r"|\b(?:python|javascript|typescript|java|golang?|rust|ruby|scala|"
        r"swift|kotlin|sql|graphql|react|angular|vue|django|flask|fastapi|"
        r"spring|node\.js|express|docker|kubernetes|k8s|aws|gcp|azure|"
        r"terraform|ansible|jenkins|gitlab|github|postgresql|mysql|mongodb|"
        r"redis|kafka|rabbitmq|elasticsearch|spark|hadoop|tensorflow|pytorch|"
        r"pandas|numpy|scikit|selenium|cypress|jest|mocha|linux|unix)\b",
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
            key = name.lower().strip()
            if key and key not in keywords:
                keywords[key] = {"keyword": name.strip(), "importance": "required", "count": 3}

        for skill in (nice_to_have or []):
            name = skill.get("name", skill) if isinstance(skill, dict) else skill
            key = name.lower().strip()
            if key and key not in keywords:
                keywords[key] = {"keyword": name.strip(), "importance": "recommended", "count": 1}

        # Phase 2: Extract technology names from JD text
        for match in cls.TECH_PATTERN.findall(job_description):
            key = match.lower()
            if key not in keywords:
                keywords[key] = {"keyword": match, "importance": "recommended", "count": 0}
            keywords[key]["count"] += 1

        # Phase 3: Frequency-based keywords
        words = re.findall(r"\b[a-zA-Z]{4,}\b", job_description.lower())
        word_freq = Counter(w for w in words if w not in cls.STOP_WORDS)
        for word, count in word_freq.most_common(15):
            if word not in keywords and count >= 2:
                keywords[word] = {"keyword": word.title(), "importance": "optional", "count": count}

        # Build entries
        entries: list[KeywordEntry] = []
        importance_order = {"required": 0, "recommended": 1, "optional": 2}

        for data in keywords.values():
            imp = data["importance"]
            if data["count"] >= 3 and imp == "recommended":
                imp = "required"
            entries.append(KeywordEntry(
                keyword=data["keyword"], importance=imp,
                in_original=False, in_tailored=False,
            ))

        entries.sort(key=lambda e: importance_order.get(e.importance, 2))
        return entries[:30]

    @classmethod
    def compute_coverage(cls, keywords: list[KeywordEntry],
                         resume_text: str) -> tuple[float, list[KeywordEntry]]:
        """Compute keyword coverage in resume text."""
        resume_lower = resume_text.lower()
        word_count = max(len(resume_text.split()), 1)
        matched = 0
        updated: list[KeywordEntry] = []

        for entry in keywords:
            kw_lower = entry.keyword.lower()
            count = resume_lower.count(kw_lower)
            if count > 0:
                updated.append(KeywordEntry(
                    keyword=entry.keyword, importance=entry.importance,
                    in_original=True, in_tailored=entry.in_tailored,
                    density=count / word_count,
                ))
                matched += 1
            else:
                updated.append(KeywordEntry(
                    keyword=entry.keyword, importance=entry.importance,
                    in_original=False, in_tailored=entry.in_tailored,
                ))

        coverage = matched / max(len(keywords), 1)
        return coverage, updated
