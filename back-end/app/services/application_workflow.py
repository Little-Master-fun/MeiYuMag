from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationFile


FILE_LABELS = {
    "pre_review_word": "初审申请文件",
    "supporting_material": "证明或说明材料",
    "meiyu_signed_application_form": "签字盖章申请表",
    "yueyuan_plan_file": "活动策划书",
    "yueyuan_plan_signed_scan": "活动策划书签章扫描件",
    "safety_responsibility_file": "安全责任书",
    "safety_responsibility_signed_scan": "安全责任书签章扫描件",
    "work_checklist_file": "工作检查清单",
    "work_checklist_signed_scan": "工作检查清单签章扫描件",
    "electricity_commitment_file": "用电承诺书",
    "electricity_commitment_signed_scan": "用电承诺书签章扫描件",
    "key_borrow_application": "钥匙借用申请表",
}


def signed_file_types(application_type: str) -> list[str]:
    if application_type == "meiyu_venue":
        return ["meiyu_signed_application_form"]
    if application_type == "yueyuan_third_floor":
        return [key for key in FILE_LABELS if key.startswith(("yueyuan_", "safety_", "work_", "electricity_"))]
    return []


async def latest_files(db: AsyncSession, application_id: int) -> dict[str, ApplicationFile]:
    rows = (await db.execute(select(ApplicationFile).where(
        ApplicationFile.application_id == application_id,
    ).order_by(ApplicationFile.version.desc(), ApplicationFile.id.desc()))).scalars()
    latest = {}
    for row in rows:
        latest.setdefault(row.file_type, row)
    return latest


async def requested_types(db: AsyncSession, application: Application) -> list[str]:
    if application.requested_file_types:
        return application.requested_file_types
    # Existing requests created before the structured supplement checklist.
    return [key for key, item in (await latest_files(db, application.id)).items()
            if item.review_status == "rejected"]


async def validate_supplement_types(db: AsyncSession, application: Application, types: list[str]) -> None:
    required = await requested_types(db, application)
    if not required:
        raise HTTPException(409, "补交清单缺失，请联系管理员重新指定材料")
    if len(types) != len(set(types)) or set(types) != set(required):
        labels = "、".join(FILE_LABELS.get(key, key) for key in required)
        raise HTTPException(400, f"请按清单一次提交全部补交材料：{labels}，每项一份")


TRANSITIONS = {
    "pending_admin_submit": {"submitted", "rejected", "cancelled"},
    "submitted": {"completed", "cancelled"},
    "pending_signed_files": {"cancelled"},
    "supplement_required": {"cancelled"},
    "ai_rejected": {"cancelled"},
    "pending_admin_pre_review": {"cancelled"},
}
