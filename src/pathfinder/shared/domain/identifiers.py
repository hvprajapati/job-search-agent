"""Strongly-typed identifier newtypes."""
from uuid import UUID, uuid4
from typing import NewType

UserId = NewType("UserId", UUID)
TenantId = NewType("TenantId", UUID)
JobId = NewType("JobId", UUID)
ApplicationId = NewType("ApplicationId", UUID)
ResumeId = NewType("ResumeId", UUID)
SessionId = NewType("SessionId", UUID)
CoverLetterId = NewType("CoverLetterId", UUID)
InterviewId = NewType("InterviewId", UUID)
ApprovalId = NewType("ApprovalId", UUID)


def new_user_id() -> UserId:
    return UserId(uuid4())


def new_tenant_id() -> TenantId:
    return TenantId(uuid4())


def new_job_id() -> JobId:
    return JobId(uuid4())


def new_application_id() -> ApplicationId:
    return ApplicationId(uuid4())


def new_resume_id() -> ResumeId:
    return ResumeId(uuid4())


def new_session_id() -> SessionId:
    return SessionId(uuid4())
