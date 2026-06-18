"""Tests for TailoredResume entity."""
from uuid import uuid4
from pathfinder.profile.domain.tailoring.entities import TailoredResume
from pathfinder.profile.domain.tailoring.value_objects import ResumeDiff, ChangeType


class TestTailoredResume:
    def test_create_sets_defaults(self):
        uid = uuid4()
        rid = uuid4()
        jid = uuid4()
        base = {"summary": "test", "skills": []}
        t = TailoredResume.create(
            user_id=uid, base_resume_id=rid, job_id=jid, base_content=base,
        )
        assert t.user_id == uid
        assert t.version == 1
        assert t.factuality_score == 1.0
        assert t.is_active is True
        assert t.is_accepted is False
        assert t.original_content == base
        assert t.tailored_content == {}

    def test_add_diff(self):
        t = TailoredResume.create(
            user_id=uuid4(), base_resume_id=uuid4(), job_id=uuid4(),
            base_content={},
        )
        diff = ResumeDiff(section="summary", change_type=ChangeType.MODIFIED.value,
                         before="old", after="new", rationale="test")
        t.add_diff(diff)
        assert len(t.diffs) == 1
        assert t.diffs[0].section == "summary"

    def test_record_factuality_issue_reduces_score(self):
        t = TailoredResume.create(
            user_id=uuid4(), base_resume_id=uuid4(), job_id=uuid4(),
            base_content={},
        )
        assert t.factuality_score == 1.0
        t.record_factuality_issue("summary", "Claimed 10 years", "Profile says 5")
        assert t.factuality_score == 0.9
        assert len(t.factuality_violations) == 1

    def test_is_clean_with_no_violations(self):
        t = TailoredResume.create(
            user_id=uuid4(), base_resume_id=uuid4(), job_id=uuid4(),
            base_content={},
        )
        assert t.is_clean is True

    def test_is_clean_with_violations(self):
        t = TailoredResume.create(
            user_id=uuid4(), base_resume_id=uuid4(), job_id=uuid4(),
            base_content={},
        )
        t.record_factuality_issue("s", "c", "r")
        t.record_factuality_issue("s", "c", "r")
        assert t.is_clean is False

    def test_accept_sets_timestamp(self):
        t = TailoredResume.create(
            user_id=uuid4(), base_resume_id=uuid4(), job_id=uuid4(),
            base_content={},
        )
        assert t.is_accepted is False
        t.accept()
        assert t.is_accepted is True
        assert t.accepted_at is not None

    def test_ats_improvement_calculation(self):
        from pathfinder.profile.domain.tailoring.value_objects import (
            KeywordAnalysis, KeywordEntry,
        )
        t = TailoredResume.create(
            user_id=uuid4(), base_resume_id=uuid4(), job_id=uuid4(),
            base_content={},
        )
        t.keyword_analysis = KeywordAnalysis(
            keywords=tuple(), coverage_before=0.3, coverage_after=0.7,
        )
        assert t.ats_improvement == 0.4
