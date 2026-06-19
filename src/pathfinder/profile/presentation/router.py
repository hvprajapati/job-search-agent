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
    from pathfinder.shared.domain.exceptions import ValidationError
    import json, io, PyPDF2

    file_bytes = await file.read()

    # ── Phase 0: Input validation (before any extraction) ──
    if len(file_bytes) == 0:
        raise ValidationError("File is empty. Please upload a valid resume.", field="file")
    if len(file_bytes) > 10 * 1024 * 1024:
        raise ValidationError("File exceeds 10MB limit", field="file")

    content_type = file.content_type or ""
    supported = ("pdf" in content_type or "docx" in content_type or "word" in content_type or
                 "text/plain" in content_type or content_type == "application/octet-stream")
    if not supported and content_type:
        raise ValidationError(
            f"Unsupported file type: {content_type}. Please upload PDF, DOCX, or TXT.",
            field="file",
        )

    # ── Phase 1: Extract text ──
    text = ""
    if "pdf" in content_type:
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text = "\n\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception:
            raise ValidationError("Could not read PDF file. It may be corrupted or password-protected.", field="file")
    elif "docx" in content_type or "word" in content_type:
        try:
            from docx import Document
            doc = Document(io.BytesIO(file_bytes))
            text = "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            raise ValidationError("Could not read DOCX file. It may be corrupted.", field="file")
    else:
        # text/plain or unknown — try UTF-8 decode
        try:
            text = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            raise ValidationError("Could not decode file content as text.", field="file")

    # ── Phase 2: Content quality check ──
    if not text or len(text.strip()) < 20:
        raise ValidationError(
            "Could not extract meaningful text from file. Resumes must contain at least 20 characters.",
            field="file",
        )

    # Parse with LLM (gracefully degrades if unavailable)
    llm = DeepSeekClient()
    parsed = {}
    try:
        resp = await llm.chat_completion(
            system_prompt=(
                "You are a resume parser. Extract structured data from the resume text. "
                "Output ONLY valid JSON — no markdown, no explanations.\n\n"
                "JSON schema:\n"
                "{\n"
                '  "full_name": "string",\n'
                '  "headline": "string",\n'
                '  "email": "string",\n'
                '  "phone": "string",\n'
                '  "location": {"city": "string", "state": "string", "country": "string"},\n'
                '  "summary": "string",\n'
                '  "skills": [{"name": "Python", "years": 8, "proficiency": "expert"}],\n'
                '  "work_experiences": [{"company": "...", "title": "...", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "description": "...", "achievements": ["..."], "tech_stack": ["..."]}],\n'
                '  "education": [{"institution": "...", "degree": "BS/MS/PhD", "field": "Computer Science", "graduation_year": 2020}]\n'
                "}\n\n"
                "RULES:\n"
                "1. For skills: extract EVERY technical skill, tool, language, framework, platform, and methodology mentioned. "
                "Set proficiency based on years/context (8y+ → expert, 5-7y → advanced, 2-4y → intermediate, <2y → beginner). "
                "Include soft-skill-like tech terms (MLOps, A/B Testing, Distributed Training, CI/CD).\n"
                "2. For work_experiences: every position with company/title. Parse dates if present. "
                "Extract achievements as an array of bullet strings. Extract tech_stack as array of technology names used.\n"
                "3. For education: every degree with institution, field, graduation year.\n"
                "4. Only include information explicitly found in the resume. Never fabricate.\n"
                "5. If a field is not found, omit it or set to empty string/null."
            ),
            user_prompt=text[:8000],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        if resp.content:
            parsed = json.loads(resp.content)
    except (json.JSONDecodeError, Exception):
        pass  # LLM returned empty or unparseable — use regex fallback

    # Fallback: regex extraction if LLM unavailable
    if not parsed:
        import re
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
        phone_match = re.search(r'\+?[\d\s\(\)-]{7,15}', text)

        # Regex skill extraction using technology patterns
        tech_skills = set()
        tech_pattern = re.compile(
            r"\b(?:Python|JavaScript|TypeScript|Java|Golang?|Rust|Ruby|Scala|"
            r"Swift|Kotlin|SQL|GraphQL|React|Angular|Vue\.?js|Django|Flask|FastAPI|"
            r"Spring|Node\.js|Express|Docker|Kubernetes|K8s|AWS|GCP|Azure|"
            r"Terraform|Ansible|Jenkins|GitLab|GitHub|PostgreSQL|MySQL|MongoDB|"
            r"Redis|Kafka|RabbitMQ|Elasticsearch|Spark|Hadoop|TensorFlow|PyTorch|"
            r"Pandas|NumPy|Scikit-learn|Selenium|Cypress|Jest|Mocha|Linux|Unix|"
            r"CUDA|MLOps|RAG|LLM|Generative\s*AI|A/B\s*Testing|CI/CD|"
            r"Feature\s*Engineering|Model\s*Deployment|Distributed\s*Training|"
            r"Vector\s*Search|Embeddings?|Airflow|Prometheus|Grafana|Nginx|"
            r"CircleCI|Travis|Bitbucket|JIRA|Confluence|Figma|Sketch)\b",
            re.IGNORECASE,
        )
        for match in tech_pattern.finditer(text):
            skill_name = match.group(0).strip()
            if len(skill_name) >= 2:
                tech_skills.add(skill_name)

        # Regex experience extraction
        experiences = []
        exp_section = re.search(
            r"(?:WORK|EXPERIENCE|EMPLOYMENT|PROFESSIONAL\s*EXPERIENCE).*?(?=EDUCATION|SKILLS|CERTIFICATION|PROJECTS|$)",
            text, re.IGNORECASE | re.DOTALL,
        )
        if exp_section:
            exp_text = exp_section.group(0)
            # Match "Company — Role (dates)" or "Company, Role" patterns
            exp_blocks = re.findall(
                r"([A-Z][A-Za-z\s&.,]+)(?:—|–|-|,)\s*([A-Z][A-Za-z\s]+?)(?:\s*\(.*?\d{4}.*?\)|\s*\(.*?present.*?\))",
                exp_text,
            )
            for company, title in exp_blocks[:10]:
                company = company.strip()
                title = title.strip()
                if len(company) > 2 and len(title) > 2:
                    experiences.append({"company": company, "title": title})

        # Regex education extraction
        education_list = []
        edu_section = re.search(
            r"(?:EDUCATION|ACADEMIC).*?(?=SKILLS|CERTIFICATION|PROJECTS|WORK|EXPERIENCE|$)",
            text, re.IGNORECASE | re.DOTALL,
        )
        if edu_section:
            edu_text = edu_section.group(0)
            edu_blocks = re.findall(
                r"([A-Z][A-Za-z\s&.,]+(?:University|College|Institute)[A-Za-z\s&.,]*).*?(BS|MS|BA|MA|MBA|PhD|Bachelor|Master|Doctorate|B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?).*?((?:Computer|Electrical|Mechanical|Data|Software|Chemical|Civil|Aerospace)\s*(?:Science|Engineering|Math))",
                edu_text,
            )
            for inst, deg, fld in edu_blocks[:5]:
                education_list.append({
                    "institution": inst.strip(),
                    "degree": deg.strip(),
                    "field": fld.strip(),
                })

        parsed = {
            "full_name": text.strip().split('\n')[0][:100] if text else "",
            "email": email_match.group(0) if email_match else "",
            "phone": phone_match.group(0) if phone_match else "",
            "skills": [{"name": s} for s in sorted(tech_skills)],
            "work_experiences": experiences,
            "education": education_list,
        }
        logger = __import__('logging').getLogger(__name__)
        logger.info(f"Resume parsed with regex fallback: {len(tech_skills)} skills, {len(experiences)} experiences, {len(education_list)} education")

    # ── Convert parsed output to domain value objects ──
    from pathfinder.profile.domain.value_objects import (
        Skill, SkillProficiency, SkillCategory,
        WorkExperience, Education,
    )
    import uuid as _uuid

    def _parse_skills(raw: list) -> list[Skill]:
        """Convert LLM-parsed skills to Skill VOs. Handles both string lists and dict lists."""
        skills = []
        proficiency_map = {
            "expert": SkillProficiency.EXPERT, "advanced": SkillProficiency.ADVANCED,
            "intermediate": SkillProficiency.INTERMEDIATE, "beginner": SkillProficiency.BEGINNER,
        }
        for item in (raw or []):
            if isinstance(item, str):
                skills.append(Skill(name=item.strip()))
            elif isinstance(item, dict) and item.get("name"):
                prof_str = (item.get("proficiency") or "").lower()
                prof = proficiency_map.get(prof_str, SkillProficiency.INTERMEDIATE)
                skills.append(Skill(
                    name=item["name"].strip(),
                    years=float(item.get("years", 0) or 0),
                    proficiency=prof,
                ))
        return skills

    def _parse_experiences(raw: list) -> list[WorkExperience]:
        """Convert LLM-parsed experiences to WorkExperience VOs."""
        exps = []
        for item in (raw or []):
            if not isinstance(item, dict):
                continue
            company = item.get("company", "")
            if not company or not company.strip():
                continue
            start_date = None
            end_date = None
            try:
                from datetime import date
                sd = item.get("start_date", "")
                if sd and str(sd).strip():
                    start_date = date.fromisoformat(str(sd).strip()[:10])
                ed = item.get("end_date", "")
                if ed and str(ed).strip() and str(ed).strip().lower() not in ("present", "current", "null", ""):
                    end_date = date.fromisoformat(str(ed).strip()[:10])
            except (ValueError, TypeError):
                pass
            exp_id = _uuid.uuid4().hex[:8]
            exp = WorkExperience(
                experience_id=exp_id,
                company=company.strip(),
                title=str(item.get("title", "")).strip(),
                start_date=start_date,
                end_date=end_date,
                is_current=bool(
                    str(item.get("end_date", "")).strip().lower() in ("present", "current") or
                    (item.get("is_current"))
                ),
                description=str(item.get("description", "")).strip(),
                achievements=tuple(
                    a for a in (item.get("achievements") or []) if isinstance(a, str) and a.strip()
                ),
                tech_stack=tuple(
                    t for t in (item.get("tech_stack") or []) if isinstance(t, str) and t.strip()
                ),
            )
            exps.append(exp)
        return exps

    def _parse_education(raw: list) -> list[Education]:
        """Convert LLM-parsed education to Education VOs."""
        edu_list = []
        for item in (raw or []):
            if not isinstance(item, dict):
                continue
            institution = item.get("institution", "")
            if not institution or not institution.strip():
                continue
            grad_year = None
            try:
                gy = item.get("graduation_year")
                if gy and str(gy).strip():
                    grad_year = int(gy)
            except (ValueError, TypeError):
                pass
            edu = Education(
                education_id=_uuid.uuid4().hex[:8],
                institution=institution.strip(),
                degree=str(item.get("degree", "")).strip(),
                field=str(item.get("field", "")).strip(),
                graduation_year=grad_year,
            )
            edu_list.append(edu)
        return edu_list

    # ── Create or update profile ──
    repo = SqlProfileRepository(session)
    profile = await repo.get_by_user_id(current_user.id)
    if profile is None:
        from pathfinder.profile.domain.entities import Profile
        profile = Profile.create_empty(user_id=current_user.id)

    if merge_strategy == "replace" or not profile.full_name:
        profile.full_name = parsed.get("full_name", profile.full_name)
        profile.headline = parsed.get("headline", profile.headline)
        profile.email = parsed.get("email", profile.email)
        profile.phone = parsed.get("phone", profile.phone)
        profile.location = parsed.get("location")
        profile.summary = parsed.get("summary", "")

        # Structured fields — convert and persist
        profile.skills = _parse_skills(parsed.get("skills", []))
        profile.work_experiences = _parse_experiences(parsed.get("work_experiences", []))
        profile.education = _parse_education(parsed.get("education", []))

        profile.parsing_confidence = {
            "full_name": 0.9 if parsed.get("full_name") else 0.0,
            "skills": 0.7 if parsed.get("skills") else 0.0,
            "experience": 0.7 if parsed.get("work_experiences") else 0.0,
            "education": 0.7 if parsed.get("education") else 0.0,
        }
    elif merge_strategy == "merge":
        # Merge: only fill in fields that are empty in existing profile
        if not profile.full_name:
            profile.full_name = parsed.get("full_name", "")
        if not profile.headline:
            profile.headline = parsed.get("headline", "")
        if not profile.email:
            profile.email = parsed.get("email", "")
        if not profile.phone:
            profile.phone = parsed.get("phone", "")
        if not profile.location:
            profile.location = parsed.get("location")
        if not profile.summary:
            profile.summary = parsed.get("summary", "")

        # Merge skills: add new ones not already present (dedup by name)
        existing_skill_names = {s.name.lower() for s in profile.skills}
        new_skills = _parse_skills(parsed.get("skills", []))
        for skill in new_skills:
            if skill.name.lower() not in existing_skill_names:
                profile.skills.append(skill)

        # Merge experiences: add new ones not already present (dedup by company+title)
        existing_exp_keys = {(e.company.lower(), e.title.lower()) for e in profile.work_experiences}
        new_exps = _parse_experiences(parsed.get("work_experiences", []))
        for exp in new_exps:
            if (exp.company.lower(), exp.title.lower()) not in existing_exp_keys:
                profile.work_experiences.append(exp)

        # Merge education: add new ones not already present (dedup by institution+degree)
        existing_edu_keys = {(e.institution.lower(), e.degree.lower()) for e in profile.education}
        new_edu = _parse_education(parsed.get("education", []))
        for edu in new_edu:
            if (edu.institution.lower(), edu.degree.lower()) not in existing_edu_keys:
                profile.education.append(edu)

        # Update confidence for fields that were filled
        profile.parsing_confidence = {
            **(profile.parsing_confidence or {}),
            "skills": 0.7 if parsed.get("skills") else profile.parsing_confidence.get("skills", 0),
            "experience": 0.7 if parsed.get("work_experiences") else profile.parsing_confidence.get("experience", 0),
            "education": 0.7 if parsed.get("education") else profile.parsing_confidence.get("education", 0),
        }

    await repo.save(profile)
    await session.commit()

    return {
        "data": {
            "profile_id": str(profile.id),
            "parsed_fields": list(parsed.keys()),
            "skills_extracted": len(profile.skills),
            "experiences_extracted": len(profile.work_experiences),
            "education_extracted": len(profile.education),
            "confidence": profile.parsing_confidence,
        }
    }


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
