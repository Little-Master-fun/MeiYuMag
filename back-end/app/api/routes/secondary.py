from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_secondary_admin
from app.api.routes.applications import application_read_with_review_reason, save_application_file
from app.db.session import get_db
from app.models.application import Application
from app.models.user import User
from app.schemas.application import ApplicationRead, SecondaryReviewDecision
from app.services.application_workflow import latest_files
from app.services.file_storage import file_storage_service
from app.services.notification import notification_service
from app.services.secondary_review import COUNTERSIGN_FILE, can_read_assigned

router = APIRouter(prefix="/secondary", tags=["secondary-signature-review"])


async def assigned_application(db: AsyncSession, application_id: int, reviewer: User) -> Application:
    application = await db.get(Application, application_id, with_for_update=True)
    if application is None:
        raise HTTPException(404, "Application not found")
    if not can_read_assigned(application, reviewer):
        raise HTTPException(403, "仅可处理指派给自己的美育场地签章材料")
    return application


@router.get("/applications", response_model=list[ApplicationRead])
async def list_assigned(
    reviewer: Annotated[User, Depends(get_current_secondary_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ApplicationRead]:
    rows = (await db.execute(select(Application).where(
        Application.secondary_reviewer_id == reviewer.id,
        Application.application_type == "meiyu_venue",
        Application.user_id != reviewer.id,
    ).order_by(Application.updated_at.desc()))).scalars().all()
    return [await application_read_with_review_reason(db, item) for item in rows]


@router.post("/applications/{application_id}/decision", response_model=ApplicationRead)
async def decide(
    application_id: int, payload: SecondaryReviewDecision,
    reviewer: Annotated[User, Depends(get_current_secondary_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationRead:
    application = await assigned_application(db, application_id, reviewer)
    if application.status != "pending_secondary_review":
        raise HTTPException(409, "当前申请不在签章审核阶段，请刷新后重试")
    signed = (await latest_files(db, application.id)).get("meiyu_signed_application_form")
    if signed is None:
        raise HTTPException(409, "用户签章材料缺失")
    if payload.passed:
        signed.review_status = "passed"
        signed.reject_reason = None
        application.status = "pending_secondary_signature"
        application.decision_reason = None
    else:
        reason = (payload.reason or "").strip()
        if not reason:
            raise HTTPException(400, "请填写需要修正的原因")
        signed.review_status = "rejected"
        signed.reject_reason = reason
        application.status = "supplement_required"
        application.requested_file_types = ["meiyu_signed_application_form"]
        application.decision_reason = reason
        applicant = await db.get(User, application.user_id)
        await notification_service.send_and_log(
            db=db, application_id=application.id, recipients=[applicant.email] if applicant else [],
            notification_type="supplement_required", subject="签章申请材料需要修正",
            body=f"申请编号：{application.id}\n原因：{reason}\n请在原申请中重新提交清晰完整的签字盖章扫描件。",
        )
    await db.commit()
    await db.refresh(application)
    return await application_read_with_review_reason(db, application)


@router.post("/applications/{application_id}/countersigned-file", response_model=ApplicationRead)
async def upload_countersigned(
    application_id: int,
    reviewer: Annotated[User, Depends(get_current_secondary_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
) -> ApplicationRead:
    application = await assigned_application(db, application_id, reviewer)
    if application.status != "pending_secondary_signature":
        raise HTTPException(409, "请先审核通过用户签章材料，再提交再次签章扫描件")
    if not (file.filename or "").lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
        raise HTTPException(400, "请提交 PDF、PNG 或 JPG 格式的再次签字盖章扫描件")
    await file_storage_service.validate_batch([file])
    await save_application_file(db, application.id, COUNTERSIGN_FILE, file)
    application.status = "pending_admin_submit"
    application.decision_reason = None
    await notification_service.notify_admins(
        db=db, application=application, notification_type="secondary_signature_completed",
        subject="美育场地再次签章材料已提交，请最终审核",
        body=f"申请编号：{application.id}\n二级管理员已审核并上传再次签字盖章扫描件。请登录一级管理员审核台下载材料并最终确认。",
    )
    await db.commit()
    await db.refresh(application)
    return await application_read_with_review_reason(db, application)
