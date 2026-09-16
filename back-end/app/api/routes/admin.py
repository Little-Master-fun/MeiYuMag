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
from app.models.venue import ReservationCalendar
from app.schemas.application import (
    AdminApplicationStatusUpdate,
    AdminPreReviewDecision,
    ApplicationRead,
    SupplementRequest,
    SupplementRequestResponse,
)
from app.schemas.auth import UserRead, UserUpdateRequest
from app.services.email import email_service
from app.services.expiration import expiration_service
from app.services.notification import notification_service
from app.services.application_workflow import FILE_LABELS, TRANSITIONS, signed_file_types, latest_files
from app.api.routes.applications import application_read_with_review_reason
from app.services.manual_review import approve_manual_venue, confirm_key_details
from app.services.secondary_review import COUNTERSIGN_FILE, reassign_pending_reviews

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_SETTABLE_APPLICATION_STATUSES = {
    "pending_signed_files",
    "pending_admin_submit",
    "submitted",
    "completed",
    "cancelled",
    "rejected",
}


async def update_reservation_statuses(
    db: AsyncSession,
    application_id: int,
    reservation_status: str,
) -> None:
    result = await db.execute(
        select(ReservationCalendar).where(ReservationCalendar.application_id == application_id, ReservationCalendar.status != "cancelled")
    )
    for reservation in result.scalars():
        reservation.status = reservation_status


async def latest_application_file(
    db: AsyncSession,
    application_id: int,
    file_type: str,
) -> ApplicationFile | None:
    result = await db.execute(
        select(ApplicationFile)
        .where(
            ApplicationFile.application_id == application_id,
            ApplicationFile.file_type == file_type,
        )
        .order_by(ApplicationFile.version.desc())
    )
    return result.scalars().first()


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
    return [await application_read_with_review_reason(db, item) for item in result.scalars()]


@router.patch("/applications/{application_id}/status", response_model=ApplicationRead)
async def update_application_status(
    application_id: int,
    payload: AdminApplicationStatusUpdate,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationRead:
    application = await db.get(Application, application_id, with_for_update=True)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if payload.status not in ADMIN_SETTABLE_APPLICATION_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported status")

    if payload.status not in TRANSITIONS.get(application.status, set()):
        raise HTTPException(409, "当前状态不允许此操作，请刷新申请后重试")
    if payload.status == "rejected" and not (payload.reason or "").strip():
        raise HTTPException(400, "请填写未通过原因")
    if payload.status in {"submitted", "completed"}:
        latest = await latest_files(db, application_id)
        required = signed_file_types(application.application_type)
        if application.application_type == "meiyu_venue" and application.secondary_reviewer_id is not None:
            required = [*required, COUNTERSIGN_FILE]
        if application.application_type == "key_borrow":
            required = ["key_borrow_application"]
        if any(key not in latest or latest[key].review_status in {"rejected", "failed"} for key in required):
            raise HTTPException(409, "签章材料缺失或仍有待补交文件，不能确认")
        if application.application_type == "key_borrow":
            await confirm_key_details(db, application, payload.key_details, completing=payload.status == "completed")
        for item in latest.values():
            if item.review_status == "pending_admin_review":
                item.review_status = "passed"
                item.reject_reason = None

    application.status = payload.status
    application.decision_reason = payload.reason
    if payload.status in {"submitted", "completed"} and application.venue_id is not None:
        await update_reservation_statuses(db, application_id, "confirmed")
    elif payload.status in {"cancelled", "rejected"} and application.venue_id is not None:
        await update_reservation_statuses(db, application_id, "cancelled")
    await db.commit()
    await db.refresh(application)
    return await application_read_with_review_reason(db, application)


@router.post("/applications/{application_id}/pre-review-decision", response_model=ApplicationRead)
async def decide_pre_review_application(
    application_id: int,
    payload: AdminPreReviewDecision,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationRead:
    application = await db.get(Application, application_id, with_for_update=True)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if application.status != "pending_admin_pre_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is not waiting for admin pre-review",
        )

    pre_review_file = await latest_application_file(db, application_id, "pre_review_word")
    if pre_review_file is None:
        raise HTTPException(409, "初审文件缺失，无法审核")
    if payload.passed:
        await approve_manual_venue(db, application, payload)
        application.status = "pending_signed_files"
        application.decision_reason = None
        if pre_review_file is not None:
            pre_review_file.review_status = "passed"
            pre_review_file.reject_reason = None
        user = await db.get(User, application.user_id)
        if user is not None:
            await notification_service.send_and_log(
                db=db,
                application_id=application.id,
                recipients=[user.email],
                notification_type="pre_review_passed",
                subject="场地申请初审通过，请上传签字盖章版本",
                body=(
                    "您的场地申请已由管理员初审通过，请登录系统上传签字盖章版本材料。\n\n"
                    f"申请编号：{application.id}\n"
                    f"借用组织：{application.borrow_organization or application.organization or '未填写'}"
                ),
            )
    else:
        if not (payload.reason or "").strip():
            raise HTTPException(400, "请填写初审未通过原因")
        application.status = "ai_rejected"
        application.decision_reason = payload.reason or "请修正申请材料后重新提交"
        if pre_review_file is not None:
            pre_review_file.review_status = "rejected"
            pre_review_file.reject_reason = payload.reason
        await update_reservation_statuses(db, application_id, "cancelled")
        user = await db.get(User, application.user_id)
        if user:
            await notification_service.send_and_log(db=db, application_id=application.id,
                recipients=[user.email], notification_type="pre_review_rejected", subject="场地申请人工初审未通过",
                body=f"申请编号：{application.id}\n未通过原因：{payload.reason}\n请在原申请中修改并重新提交材料。")

    await db.commit()
    await db.refresh(application)
    return await application_read_with_review_reason(db, application)


@router.post("/applications/{application_id}/request-supplement")
async def request_supplement(
    application_id: int,
    payload: SupplementRequest,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SupplementRequestResponse:
    application = await db.get(Application, application_id, with_for_update=True)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    if application.status not in {"pending_admin_submit", "submitted", "supplement_required"}:
        raise HTTPException(409, "当前申请不能要求补交材料")
    allowed = set(signed_file_types(application.application_type)) | {"supporting_material"}
    if application.application_type == "key_borrow":
        allowed.add("key_borrow_application")
    if len(set(payload.file_types)) != len(payload.file_types) or not set(payload.file_types) <= allowed:
        raise HTTPException(400, "请选择该申请支持的材料类型")
    application.requested_file_types = payload.file_types
    application.decision_reason = payload.reason

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


@router.get("/users", response_model=list[UserRead])
async def list_users(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    role: str | None = None,
) -> list[UserRead]:
    query = select(User).order_by(User.created_at.desc())
    if role:
        query = query.where(User.role == role)
    result = await db.execute(query)
    return [UserRead.model_validate(user) for user in result.scalars()]


@router.patch("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.role is not None:
        if user.role == "admin" and payload.role != "admin":
            if user.id == current_admin.id:
                raise HTTPException(409, "不能移除自己的一级管理员身份")
            # Serialize primary-role changes so the last primary cannot disappear.
            admins = (await db.execute(select(User).where(User.role == "admin").order_by(User.id).with_for_update())).scalars().all()
            if len(admins) <= 1:
                raise HTTPException(409, "至少保留一位一级管理员")
        was_secondary = user.role == "secondary_admin"
        user.role = payload.role
        await db.flush()
        if was_secondary and user.role != "secondary_admin":
            await reassign_pending_reviews(db, user.id)
    if payload.is_application_allowed is not None:
        user.is_application_allowed = payload.is_application_allowed
    await db.commit()
    await db.refresh(user)
    return UserRead.model_validate(user)


@router.post("/maintenance/process-expirations")
async def process_application_expirations(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int]:
    return await expiration_service.process_yueyuan_pending_signed_files(db)
