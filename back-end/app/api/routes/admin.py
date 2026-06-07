from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.application import Application, ApplicationFile
from app.models.notification import NotificationLog
from app.models.user import User
from app.schemas.application import (
    ApplicationRead,
    SupplementRequest,
    SupplementRequestResponse,
)
from app.schemas.auth import UserRead
from app.services.email import email_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/applications", response_model=list[ApplicationRead])
async def list_all_applications(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = None,
    application_type: str | None = None,
) -> list[ApplicationRead]:
    query = select(Application)
    if status_filter:
        query = query.where(Application.status == status_filter)
    if application_type:
        query = query.where(Application.application_type == application_type)
    query = query.order_by(Application.created_at.desc())
    result = await db.execute(query)
    return [ApplicationRead.model_validate(item) for item in result.scalars()]


@router.post("/applications/{application_id}/request-supplement")
async def request_supplement(
    application_id: int,
    payload: SupplementRequest,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SupplementRequestResponse:
    application = await db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    for file_type in payload.file_types:
        result = await db.execute(
            select(ApplicationFile)
            .where(
                ApplicationFile.application_id == application_id,
                ApplicationFile.file_type == file_type,
            )
            .order_by(ApplicationFile.version.desc())
        )
        latest_file = result.scalars().first()
        if latest_file is not None:
            latest_file.review_status = "rejected"
            latest_file.reject_reason = payload.reason

    application.status = "supplement_required"
    user = await db.get(User, application.user_id)
    recipient = user.email if user else ""
    body = (
        f"您的申请（编号 {application.id}）需要补交材料。\n"
        f"需要补交：{', '.join(payload.file_types)}\n"
        f"原因：{payload.reason}\n"
        "请登录系统查看详情并上传补交文件。"
    )
    notification_status = "skipped"
    error_message = None
    if recipient:
        try:
            notification_status = email_service.send_text_email(
                recipient=recipient,
                subject="场地申请材料补交通知",
                body=body,
            )
        except Exception as exc:
            notification_status = "failed"
            error_message = str(exc)

    db.add(
        NotificationLog(
            application_id=application.id,
            recipient=recipient,
            notification_type="supplement_required",
            status=notification_status,
            error_message=error_message,
            sent_at=datetime.now(timezone.utc) if notification_status == "sent" else None,
        )
    )
    await db.commit()
    return SupplementRequestResponse(
        application_id=application.id,
        status=application.status,
        requested_file_types=payload.file_types,
        reason=payload.reason,
        notification_status=notification_status,
    )


@router.post("/users/{user_id}/allow-application", response_model=UserRead)
async def allow_user_application(
    user_id: int,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_application_allowed = True
    await db.commit()
    await db.refresh(user)
    return UserRead.model_validate(user)
