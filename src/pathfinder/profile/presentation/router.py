"""Profile and Resume API routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.presentation.dependencies import get_current_user
from pathfinder.identity.domain.entities import User
from pathfinder.profile.infrastructure.persistence.profile_repository import SqlProfileRepository
from pathfinder.profile.infrastructure.persistence.resume_repository import SqlResumeRepository
from pathfinder.profile.domain.exceptions import ProfileNotFoundError, ResumeNotFoundError

router = APIRouter(prefix="/v1", tags=["Profile & Resumes"])


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = SqlProfileRepository(session)
    profile = await repo.get_by_user_id(current_user.id)
    if not profile:
        raise ProfileNotFoundError(str(current_user.id))
    return {
        "data": {
            "profile_id": str(profile.id),
            "user_id": str(profile.user_id),
            "version": profile.version,
            "full_name": profile.full_name,
            "headline": profile.headline,
            "email": profile.email,
            "phone": profile.phone,
            "location": profile.location,
            "summary": profile.summary,
            "skills": [
                {"name": s.name, "proficiency": s.proficiency.value, "years": s.years}
                for s in profile.skills
            ],
            "work_experiences": [
                {"company": e.company, "title": e.title, "description": e.description}
                for e in profile.work_experiences
            ],
            "education": [
                {"institution": e.institution, "degree": e.degree, "field": e.field}
                for e in profile.education
            ],
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }
    }


@router.post("/profile/import/resume")
async def import_resume(
    file: UploadFile = File(...),
    merge_strategy: str = Form("merge"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Upload and parse a resume file to populate profile."""
    from pathfinder.profile.infrastructure.llm.deepseek_client import DeepSeekClient
    import json, io, PyPDF2

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        from pathfinder.shared.domain.exceptions import ValidationError
        raise ValidationError("File exceeds 10MB limit", field="file")

    # Extract text
    text = ""
    content_type = file.content_type or ""
    if "pdf" in content_type:
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text = "\n\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception:
            raise ValidationError("Could not read PDF file", field="file")
    elif "docx" in content_type or "word" in content_type:
        try:
            from docx import Document
            doc = Document(io.BytesIO(file_bytes))
            text = "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            raise ValidationError("Could not read DOCX file", field="file")
    elif "text/plain" in content_type:
        text = file_bytes.decode("utf-8", errors="ignore")
    else:
        raise ValidationError("Unsupported file type. Use PDF, DOCX, or TXT.", field="file")

    if not text or len(text.strip()) < 50:
        raise ValidationError("Could not extract meaningful text from file", field="file")

    # Parse with LLM (gracefully degrades if unavailable)
    llm = DeepSeekClient()
    parsed = {}
    try:
        resp = await llm.chat_completion(
            system_prompt="Extract structured profile data from this resume. Output JSON with: full_name, headline, email, phone, location{city,state,country}, summary, work_experiences[{company,title,start_date,end_date,description,achievements[],tech_stack[]}], education[{institution,degree,field,graduation_year}], skills[{name,years}]. Only include information explicitly in the resume.",
            user_prompt=text[:6000],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        if resp.content:
            parsed = json.loads(resp.content)
    except json.JSONDecodeError:
        pass  # LLM returned empty or unparseable — use regex fallback

    # Fallback: basic regex extraction if LLM unavailable
    if not parsed:
        import re
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
        phone_match = re.search(r'\+?[\d\s\(\)-]{7,15}', text)
        parsed = {
            "full_name": text.strip().split('\n')[0][:100] if text else "",
            "email": email_match.group(0) if email_match else "",
            "phone": phone_match.group(0) if phone_match else "",
        }
        logger = __import__('logging').getLogger(__name__)
        logger.info("Resume parsed with regex fallback (LLM unavailable)")

    # Create or update profile
    repo = SqlProfileRepository(session)
    profile = await repo.get_by_user_id(current_user.id)
    if profile is None:
        from pathfinder.profile.domain.entities import Profile
        from pathfinder.profile.domain.value_objects import WorkExperience, Education, Skill
        profile = Profile.create_empty(user_id=current_user.id)

    if merge_strategy == "replace" or not profile.full_name:
        profile.full_name = parsed.get("full_name", profile.full_name)
        profile.headline = parsed.get("headline", profile.headline)
        profile.email = parsed.get("email", profile.email)
        profile.phone = parsed.get("phone", profile.phone)
        profile.location = parsed.get("location")
        profile.summary = parsed.get("summary", "")

    await repo.save(profile)
    await session.commit()

    return {"data": {"profile_id": str(profile.id), "parsed_fields": list(parsed.keys()),
                     "confidence": {"full_name": 0.9 if parsed.get("full_name") else 0.0}}}


@router.get("/resumes")
async def list_resumes(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = SqlResumeRepository(session)
    resumes = await repo.list_by_user(current_user.id, limit=50)
    return {
        "data": [
            {
                "resume_id": str(r.id), "name": r.name,
                "is_base": r.is_base, "template_id": r.template_id,
                "tailored_for_job_id": str(r.tailored_for_job_id) if r.tailored_for_job_id else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in resumes
        ],
        "meta": {"count": len(resumes)},
    }


@router.post("/resumes", status_code=201)
async def create_resume(
    body: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from pathfinder.profile.domain.entities import Resume
    repo = SqlResumeRepository(session)
    resume = Resume.create_base(
        user_id=current_user.id,
        name=body.get("name", "Untitled"),
        template_id=body.get("template_id", "modern_professional"),
        content=body.get("content", {}),
    )
    await repo.save(resume)
    return {"data": {"resume_id": str(resume.id), "name": resume.name}}


@router.get("/resumes/{resume_id}")
async def get_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = SqlResumeRepository(session)
    resume = await repo.get_by_user_and_id(current_user.id, resume_id)
    if not resume:
        raise ResumeNotFoundError(str(resume_id))
    return {"data": {"resume": {"resume_id": str(resume.id), "name": resume.name}, "content": resume.content}}


@router.delete("/resumes/{resume_id}", status_code=204)
async def delete_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from fastapi.responses import Response
    repo = SqlResumeRepository(session)
    resume = await repo.get_by_user_and_id(current_user.id, resume_id)
    if not resume:
        raise ResumeNotFoundError(str(resume_id))
    await repo.delete(resume)
    return Response(status_code=204)
