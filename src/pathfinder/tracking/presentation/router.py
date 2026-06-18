"""Application Tracking API routes."""
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.presentation.dependencies import get_current_user
from pathfinder.identity.domain.entities import User
from pathfinder.tracking.domain.entities import Application, ApplicationStatus
from pathfinder.shared.domain.exceptions import NotFoundError, ValidationError

router = APIRouter(prefix="/v1/applications", tags=["Applications"])


@router.get("")
async def list_applications(
    status: str | None = Query(None),
    is_archived: bool = Query(False),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select
    from pathfinder.tracking.infrastructure.persistence.models import ApplicationModel

    stmt = select(ApplicationModel).where(
        ApplicationModel.user_id == current_user.id,
        ApplicationModel.is_archived == is_archived,
    )
    if status:
        stmt = stmt.where(ApplicationModel.status == status)
    stmt = stmt.order_by(ApplicationModel.last_updated_at.desc()).limit(50)

    result = await session.execute(stmt)
    models = result.scalars().all()

    counts = {}
    for s in [ApplicationStatus.SAVED, ApplicationStatus.APPLIED, ApplicationStatus.PHONE_SCREEN,
              ApplicationStatus.TECHNICAL_INTERVIEW, ApplicationStatus.ONSITE, ApplicationStatus.OFFER]:
        cstmt = select(ApplicationModel).where(
            ApplicationModel.user_id == current_user.id,
            ApplicationModel.status == s,
            ApplicationModel.is_archived == False,
        )
        cr = await session.execute(cstmt)
        counts[s] = len(cr.scalars().all())

    return {
        "data": [{"application_id": str(m.id), "job_id": str(m.job_id),
                  "status": m.status, "applied_at": m.applied_at.isoformat() if m.applied_at else None,
                  "notes": m.notes} for m in models],
        "meta": {"count": len(models), "pipeline_summary": counts},
    }


@router.post("", status_code=201)
async def create_application(
    job_id: UUID = Query(...),
    status: str = Query("saved"),
    resume_id: UUID | None = Query(None),
    notes: str = Query(""),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if status not in (ApplicationStatus.SAVED, ApplicationStatus.APPLIED):
        raise ValidationError("Initial status must be 'saved' or 'applied'", field="status")

    from sqlalchemy import select
    from pathfinder.tracking.infrastructure.persistence.models import ApplicationModel

    existing = await session.execute(
        select(ApplicationModel).where(
            ApplicationModel.user_id == current_user.id,
            ApplicationModel.job_id == job_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValidationError("Already applied to this job", field="job_id")

    app = Application(user_id=current_user.id, job_id=job_id, resume_id=resume_id,
                      status=status, notes=notes)
    if status == ApplicationStatus.APPLIED:
        app.applied_at = datetime.now(timezone.utc)
        app.status_history = [{"from": ApplicationStatus.SAVED, "to": ApplicationStatus.APPLIED,
                               "at": app.applied_at.isoformat()}]

    from pathfinder.tracking.infrastructure.persistence.models import ApplicationModel
    model = ApplicationModel.from_domain(app)
    session.add(model)
    await session.commit()
    return {"data": {"application_id": str(app.id), "status": app.status}}


@router.patch("/{application_id}")
async def update_application(
    application_id: UUID,
    status: str | None = Query(None),
    notes: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from pathfinder.tracking.infrastructure.persistence.models import ApplicationModel

    model = await session.get(ApplicationModel, application_id)
    if not model or model.user_id != current_user.id:
        raise NotFoundError("Application not found")

    if status:
        app = model.to_domain()
        try:
            app.transition(status)
            model.status = app.status
            model.status_history = app.status_history
        except ValueError as e:
            raise ValidationError(str(e), field="status")

    if notes is not None:
        model.notes = notes

    model.last_updated_at = datetime.now(timezone.utc)
    await session.commit()
    return {"data": {"application_id": str(application_id), "status": model.status}}


@router.get("/{application_id}")
async def get_application(
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from pathfinder.tracking.infrastructure.persistence.models import ApplicationModel
    model = await session.get(ApplicationModel, application_id)
    if not model or model.user_id != current_user.id:
        raise NotFoundError("Application not found")
    return {"data": {"application_id": str(model.id), "job_id": str(model.job_id),
                     "status": model.status, "status_history": model.status_history,
                     "notes": model.notes, "applied_at": model.applied_at.isoformat() if model.applied_at else None}}


@router.delete("/{application_id}", status_code=204)
async def delete_application(
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from pathfinder.tracking.infrastructure.persistence.models import ApplicationModel
    model = await session.get(ApplicationModel, application_id)
    if not model or model.user_id != current_user.id:
        raise NotFoundError("Application not found")
    await session.delete(model)
    await session.commit()
    return Response(status_code=204)
