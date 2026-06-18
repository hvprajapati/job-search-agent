"""Tests for KeywordExtractor."""
import pytest
from pathfinder.profile.infrastructure.tailoring.keyword_extractor import KeywordExtractor


class TestKeywordExtraction:
    def test_extracts_tech_keywords_from_jd(self):
        jd = "We need a Python developer with FastAPI and PostgreSQL experience."
        keywords = KeywordExtractor.extract(jd)
        names = {k.keyword.lower() for k in keywords}
        assert "python" in names
        assert "fastapi" in names

    def test_required_skills_ranked_highest(self):
        jd = "Looking for an engineer."
        keywords = KeywordExtractor.extract(jd, required_skills=["Python", "AWS"])
        required = [k for k in keywords if k.importance == "required"]
        required_names = {k.keyword.lower() for k in required}
        assert "python" in required_names

    def test_nice_to_have_ranked_second(self):
        jd = "Test"
        keywords = KeywordExtractor.extract(jd, required_skills=["Python"], nice_to_have=["Docker"])
        imp_map = {k.keyword.lower(): k.importance for k in keywords}
        assert imp_map.get("python") == "required"
        assert imp_map.get("docker") == "recommended"

    def test_extract_caps_at_30_keywords(self):
        # Generate a JD with many keywords
        jd = " ".join([f"experience with {n}" for n in ["ToolA", "ToolB", "ToolC"] * 20])
        keywords = KeywordExtractor.extract(jd)
        assert len(keywords) <= 30

    def test_empty_jd_returns_empty(self):
        keywords = KeywordExtractor.extract("")
        assert len(keywords) == 0

    def test_extract_handles_dict_skills(self):
        jd = "Need a developer."
        skills = [{"name": "Python", "importance": "critical"}, {"name": "AWS"}]
        keywords = KeywordExtractor.extract(jd, required_skills=skills)
        names = {k.keyword.lower() for k in keywords}
        assert "python" in names
        assert "aws" in names


class TestCoverageComputation:
    def test_full_coverage(self):
        jd = "Python React AWS"
        keywords = KeywordExtractor.extract(jd)
        resume_text = "Experienced Python developer with React and AWS skills."
        coverage, updated = KeywordExtractor.compute_coverage(keywords, resume_text)
        assert coverage >= 0.5

    def test_no_coverage(self):
        jd = "Rust Go Erlang"
        keywords = KeywordExtractor.extract(jd)
        resume_text = "Python JavaScript developer."
        coverage, updated = KeywordExtractor.compute_coverage(keywords, resume_text)
        assert coverage == 0.0

    def test_partial_coverage(self):
        jd = "Python React AWS Docker"
        keywords = KeywordExtractor.extract(jd)
        resume_text = "Python developer with React experience."
        coverage, updated = KeywordExtractor.compute_coverage(keywords, resume_text)
        assert 0.3 < coverage < 0.8

    def test_updated_entries_preserve_order(self):
        jd = "Python AWS"
        keywords = KeywordExtractor.extract(jd)
        _, updated = KeywordExtractor.compute_coverage(keywords, "Python developer.")
        assert updated[0].in_original is True  # Python matched
        assert len(updated) == len(keywords)
