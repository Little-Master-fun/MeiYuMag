"""Scoped signing handoff. Primary admins alone handle users and AI fallback."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.user import User
from app.services.application_workflow import latest_files
from app.services.notification import notification_service

SECONDARY_STATES = {"pending_secondary_review", "pending_secondary_signature"}
COUNTERSIGN_FILE = "meiyu_countersigned_scan"


def can_read_assigned(application: Application, user: User) -> bool:
    return (user.role == "secondary_admin" and application.application_type == "meiyu_venue"
            and application.secondary_reviewer_id == user.id and application.user_id != user.id)


async def queue_signed_review(db: AsyncSession, application: Application) -> None:
    """Called once after a full signed/supplement upload; never for pre-review."""
    reviewer = None
    if application.application_type == "meiyu_venue":
        eligible = select(User).where(User.role == "secondary_admin", User.id != application.user_id).with_for_update()
        # Keep the same reviewer on corrections while their assignment is active.
        if application.secondary_reviewer_id:
            reviewer = (await db.execute(eligible.where(User.id == application.secondary_reviewer_id))).scalar_one_or_none()
        if reviewer is None:
            reviewer = (await db.execute(eligible.order_by(User.id).limit(1))).scalar_one_or_none()
        previous_scan = (await latest_files(db, application.id)).get(COUNTERSIGN_FILE)
        if previous_scan:
            previous_scan.review_status = "rejected"
            previous_scan.reject_reason = "申请材料已更新，需重新签章"
    application.secondary_reviewer_id = reviewer.id if reviewer else None
    application.decision_reason = None
    if reviewer:
        application.status = "pending_secondary_review"
        await notification_service.send_and_log(
            db=db, application_id=application.id, recipients=[reviewer.email],
            notification_type="pending_secondary_review", subject="美育场地签章材料待您审核",
            body=f"申请编号：{application.id}\n申请人已提交签字盖章材料。请登录系统打开“签章工作台”，下载并核对材料，通过后完成再次签字盖章，上传扫描件交一级管理员确认。",
        )
    else:
        application.status = "pending_admin_submit"
        await notification_service.notify_admins(
            db=db, application=application, notification_type="pending_admin_submit",
            subject="申请材料待审核", body=f"申请编号：{application.id}\n材料已提交，请登录审核台处理。",
        )


async def reassign_pending_reviews(db: AsyncSession, removed_user_id: int) -> None:
    # Revoke access immediately, without stranding pending signing work.
    applications = (await db.execute(select(Application).where(
        Application.secondary_reviewer_id == removed_user_id,
        Application.status.in_(SECONDARY_STATES),
    ).with_for_update())).scalars().all()
    for application in applications:
        application.secondary_reviewer_id = None
        await queue_signed_review(db, application)
