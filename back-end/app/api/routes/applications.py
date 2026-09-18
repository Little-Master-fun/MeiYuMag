from datetime import datetime, timezone
from datetime import date as Date
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.application import Application, ApplicationFile
from app.models.auth_profile import AuthProfile
from app.models.user import User
from app.models.key import KeyBorrowRecord
from app.models.venue import ReservationCalendar, Venue
from app.services.application_workflow import FILE_LABELS, signed_file_types, requested_types, validate_supplement_types
from app.schemas.application import (
    AiPreReviewResult,
    ApplicationRead,
    ApplicationPreReviewResponse,
    ConflictItem,
    ApplicationFileRead,
    GenericFileUploadResponse,
    GenericFilesUploadResponse,
    ReviewIssue,
    SignedFilesSubmitResponse,
    UploadedSignedFile,
)
from app.core.config import settings
from app.services.ai_review import ai_review_service
from app.services.file_storage import file_storage_service
from app.services.notification import notification_service
from app.services.secondary_review import can_read_assigned, queue_signed_review
from app.services.venue_names import normalize_venue_name

router = APIRouter(prefix="/applications", tags=["applications"])


ALLOWED_SIGNED_FILE_SUFFIXES = {".doc", ".docx", ".pdf", ".jpg", ".jpeg", ".png"}


def validate_file_suffix(file: UploadFile, label: str) -> None:
    filename = file.filename or ""
    if not any(filename.lower().endswith(suffix) for suffix in ALLOWED_SIGNED_FILE_SUFFIXES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} file type is not supported",
        )


async def next_file_version(db: AsyncSession, application_id: int, file_type: str) -> int:
    result = await db.execute(
        select(ApplicationFile)
        .where(
            ApplicationFile.application_id == application_id,
            ApplicationFile.file_type == file_type,
        )
        .order_by(ApplicationFile.version.desc())
    )
    latest = result.scalars().first()
    return 1 if latest is None else latest.version + 1


async def save_application_file(
    db: AsyncSession,
    application_id: int,
    file_type: str,
    file: UploadFile,
) -> UploadedSignedFile:
    validate_file_suffix(file, file_type)
    version = await next_file_version(db, application_id, file_type)
    stored_path = await file_storage_service.save_upload(
        file,
        f"applications/{application_id}/signed",
    )
    application_file = ApplicationFile(
        application_id=application_id,
        file_type=file_type,
        version=version,
        original_filename=file.filename or file_type,
        stored_path=stored_path,
        review_status="pending_admin_review",
    )
    db.add(application_file)
    await db.flush()
    return UploadedSignedFile(
        file_type=file_type,
        version=version,
        original_filename=application_file.original_filename,
    )


def format_application_label(application: Application) -> str:
    return (
        f"申请编号：{application.id}\n"
        f"申请类型：{application.application_type}\n"
        f"借用组织：{application.borrow_organization or application.organization or '未填写'}\n"
        f"申请人：{application.applicant_name or '未填写'}\n"
        f"申请部门：{application.applicant_department or '未填写'}"
    )


def summarize_review_problems(
    issues: list[ReviewIssue],
    conflicts: list[ConflictItem],
) -> str:
    lines = [f"{issue.type}: {issue.message}" for issue in issues]
    lines.extend(
        f"CONFLICT: {conflict.start_at} - {conflict.end_at} {conflict.message}"
        for conflict in conflicts
    )
    return "\n".join(lines)


AI_SERVICE_ERRORS = {"AI_REVIEW_REQUEST_FAILED", "AI_REVIEW_NOT_CONFIGURED", "AI_RESPONSE_PARSE_FAILED"}


def needs_manual_review(result: AiPreReviewResult) -> bool:
    return any(issue.type in AI_SERVICE_ERRORS for issue in result.issues)


async def queue_manual_pre_review(
    db: AsyncSession, user: User, file: UploadFile,
    venue_id: int | None = None, application: Application | None = None,
    additional_files: list[UploadFile] | None = None,
    reason: str = "AI 暂时无法完成初审，材料已转交管理员人工初审，无需重复提交。",
) -> ApplicationPreReviewResponse:
    venue = await db.get(Venue, venue_id) if venue_id else None
    if venue_id and venue is None:
        raise HTTPException(400, "所选场地不存在")
    if application is None:
        profile = (await db.execute(select(AuthProfile).where(AuthProfile.user_id == user.id))).scalar_one_or_none()
        application = Application(
            user_id=user.id, venue_id=venue_id,
            application_type=("yueyuan_third_floor" if "悦园三楼" in venue.name else "meiyu_venue") if venue else "venue_auto",
            organization=user.department, applicant_department=user.department,
            applicant_name=profile.name if profile else None, applicant_sduid=profile.sduid if profile else None,
        )
        db.add(application)
        await db.flush()
    application.status = "pending_admin_pre_review"
    application.decision_reason = reason
    path = await file_storage_service.save_upload(file, "pre-review")
    db.add(ApplicationFile(
        application_id=application.id, file_type="pre_review_word",
        version=await next_file_version(db, application.id, "pre_review_word"),
        original_filename=file.filename or "application.docx", stored_path=path,
        review_status="pending_admin_review",
    ))
    for extra in additional_files or []:
        await save_application_file(db, application.id, "supporting_material", extra)
    # Unverified material must not reserve a room. Old versions remain available.
    reservations = (await db.execute(select(ReservationCalendar).where(ReservationCalendar.application_id == application.id))).scalars()
    for reservation in reservations:
        reservation.status = "cancelled"
    await notification_service.notify_admins(
        db=db, application=application, notification_type="pending_admin_pre_review",
        subject="场地申请需人工初审", body=f"{reason}\n\n{format_application_label(application)}\n请在管理审核台下载原文件，核实场地、借用组织及时间后处理。人工初审前不会预占用场地。",
    )
    await db.commit()
    return ApplicationPreReviewResponse(
        passed=False, application_type=application.application_type, venue_id=application.venue_id,
        next_status=application.status, extracted_time_slots=[], issues=[ReviewIssue(type="MANUAL_REVIEW_REQUIRED", message=reason)],
        conflicts=[], application_id=application.id, borrow_organization=application.borrow_organization,
        purpose_summary=application.purpose_summary,
    )


async def evaluate_pre_review(
    db: AsyncSession,
    application_type: str,
    venue_id: int,
    file: UploadFile,
    ignored_application_id: int | None = None,
    expected_date: str | None = None,
    ai_result: AiPreReviewResult | None = None,
) -> tuple[AiPreReviewResult, list[ReviewIssue], list[ConflictItem], bool]:
    if ai_result is None:
        ai_result = await ai_review_service.pre_review_word(application_type, file)
    issues = list(ai_result.issues)
    conflicts: list[ConflictItem] = []
    # Serialize reservation decisions for the same venue after the slow AI call.
    venue = (await db.execute(select(Venue).where(Venue.id == venue_id).with_for_update())).scalar_one_or_none()
    if venue is None:
        raise HTTPException(400, "所选场地不存在")
    if not ai_result.venue_name:
        issues.append(ReviewIssue(type="MISSING_VENUE", message="文件中未识别出场地名称，请写明所申请的场地"))
    if ai_result.venue_name and normalize_venue_name(ai_result.venue_name) != normalize_venue_name(venue.name):
        issues.append(ReviewIssue(type="VENUE_MISMATCH", message=f"文件场地“{ai_result.venue_name}”与所选“{venue.name}”不一致"))
    if not ai_result.extracted_time_slots:
        issues.append(
            ReviewIssue(
                type="MISSING_TIME_SLOT",
                message="AI 未能从申请材料中提取出借用日期和具体时间段",
            )
        )

    for slot in ai_result.extracted_time_slots:
        if slot.start_at is None or slot.end_at is None:
            issues.append(
                ReviewIssue(
                    type="INVALID_TIME_SLOT",
                    message=f"无法解析借用时间：{slot.date} {slot.start_time}-{slot.end_time}",
                )
            )
            continue

        if slot.start_at.tzinfo is None or slot.end_at.tzinfo is None:
            issues.append(ReviewIssue(type="INVALID_TIME_SLOT", message="借用时间缺少时区，请重新提交"))
            continue
        if slot.end_at <= slot.start_at:
            issues.append(ReviewIssue(type="INVALID_TIME_SLOT", message="结束时间须晚于开始时间"))
        if application_type != "meiyu_venue" and slot.start_at <= datetime.now(timezone.utc):
            issues.append(ReviewIssue(type="INVALID_TIME_SLOT", message="借用时间必须在未来"))
        if expected_date and slot.start_at.astimezone(ZoneInfo("Asia/Shanghai")).date().isoformat() != expected_date:
            issues.append(ReviewIssue(type="DATE_MISMATCH", message=f"文件使用日期与所选 {expected_date} 不一致"))

        conditions = [
            ReservationCalendar.venue_id == venue_id,
            ReservationCalendar.status.in_(["pre_reserved", "confirmed", "reserved"]),
            ReservationCalendar.start_at < slot.end_at,
            ReservationCalendar.end_at > slot.start_at,
        ]
        if ignored_application_id is not None:
            conditions.append(ReservationCalendar.application_id != ignored_application_id)
        result = await db.execute(select(ReservationCalendar).where(and_(*conditions)))
        for reservation in result.scalars():
            conflicts.append(
                ConflictItem(
                    venue_id=venue_id,
                    application_id=reservation.application_id,
                    start_at=reservation.start_at,
                    end_at=reservation.end_at,
                    status=reservation.status,
                    message="申请时间与已有预约冲突",
                )
            )

    passed = ai_result.passed and not issues and not conflicts
    return ai_result, issues, conflicts, passed


async def application_read_with_review_reason(
    db: AsyncSession,
    application: Application,
) -> ApplicationRead:
    result = await db.execute(
        select(ApplicationFile)
        .where(
            ApplicationFile.application_id == application.id,
            ApplicationFile.file_type == "pre_review_word",
        )
        .order_by(ApplicationFile.version.desc())
    )
    latest_file = result.scalars().first()
    review_reason = application.decision_reason or (latest_file.reject_reason if latest_file is not None else None)
    required = (await requested_types(db, application) if application.status == "supplement_required"
                else signed_file_types(application.application_type) if application.status == "pending_signed_files" else [])
    key_record = (await db.execute(select(KeyBorrowRecord).where(KeyBorrowRecord.application_id == application.id))).scalars().first() if application.application_type == "key_borrow" else None
    return ApplicationRead.model_validate(application).model_copy(
        update={"review_reason": review_reason, "borrowed_key_name": key_record.borrowed_key_name if key_record else None,
                "requested_file_types": required if application.status == "supplement_required" else [],
                "required_files": [{"file_type": key, "label": FILE_LABELS.get(key, key)} for key in required]}
    )


@router.get("", response_model=list[ApplicationRead])
async def list_my_applications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = None,
) -> list[ApplicationRead]:
    query = select(Application).where(Application.user_id == current_user.id)
    if status_filter:
        query = query.where(Application.status == status_filter)
    query = query.order_by(Application.created_at.desc())
    result = await db.execute(query)
    return [
        await application_read_with_review_reason(db, item)
        for item in result.scalars()
    ]


async def get_owned_application_or_admin(
    db: AsyncSession,
    application_id: int,
    current_user: User,
) -> Application:
    application = await db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if application.user_id != current_user.id and current_user.role != "admin" and not can_read_assigned(application, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return application


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(
    application_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationRead:
    application = await get_owned_application_or_admin(db, application_id, current_user)
    return await application_read_with_review_reason(db, application)


async def mark_application_cancelled(
    db: AsyncSession,
    application: Application,
) -> Application:
    if application.status == "cancelled":
        return application
    if application.status in {"rejected", "completed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application cannot be cancelled in its current status",
        )
    start_at = application.start_at
    if start_at is not None and start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=timezone.utc)
    if start_at is not None and datetime.now(timezone.utc) >= start_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application cannot be cancelled after the usage start time",
        )

    application.status = "cancelled"
    result = await db.execute(
        select(ReservationCalendar).where(
            ReservationCalendar.application_id == application.id,
            ReservationCalendar.status != "cancelled",
        )
    )
    for reservation in result.scalars():
        reservation.status = "cancelled"
    await db.commit()
    await db.refresh(application)
    return application


@router.post("/{application_id}/cancel", response_model=ApplicationRead)
async def cancel_my_application(
    application_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationRead:
    application = await db.get(Application, application_id, with_for_update=True)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if application.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    application = await mark_application_cancelled(db, application)
    return ApplicationRead.model_validate(application)


@router.delete("/{application_id}", response_model=ApplicationRead)
async def delete_my_application(
    application_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationRead:
    application = await db.get(Application, application_id, with_for_update=True)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if application.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    application = await mark_application_cancelled(db, application)
    return ApplicationRead.model_validate(application)


@router.get("/{application_id}/files", response_model=list[ApplicationFileRead])
async def list_application_files(
    application_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ApplicationFileRead]:
    await get_owned_application_or_admin(db, application_id, current_user)
    result = await db.execute(
        select(ApplicationFile)
        .where(ApplicationFile.application_id == application_id)
        .order_by(ApplicationFile.file_type, ApplicationFile.version.desc())
    )
    files = []
    for item in result.scalars():
        files.append(
            ApplicationFileRead(
                id=item.id,
                application_id=item.application_id,
                file_type=item.file_type,
                version=item.version,
                original_filename=item.original_filename,
                review_status=item.review_status,
                reject_reason=item.reject_reason,
                created_at=item.created_at,
                download_url=(
                    f"{settings.api_v1_prefix}/applications/"
                    f"{application_id}/files/{item.id}/download"
                ),
            )
        )
    return files


@router.get("/{application_id}/files/{file_id}/download")
async def download_application_file(
    application_id: int,
    file_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    await get_owned_application_or_admin(db, application_id, current_user)
    application_file = await db.get(ApplicationFile, file_id)
    if application_file is None or application_file.application_id != application_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    file_path = Path(application_file.stored_path)
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found")
    return FileResponse(path=file_path, filename=application_file.original_filename)


@router.post("/{application_id}/files", response_model=GenericFileUploadResponse)
async def upload_application_file(
    application_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file_type: str = Form(...),
    file: UploadFile = File(...),
) -> GenericFileUploadResponse:
    application = await db.get(Application, application_id, with_for_update=True)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if application.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    if application.status != "supplement_required":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is not waiting for supplement files",
        )

    await validate_supplement_types(db, application, [file_type])
    await file_storage_service.validate_batch([file])
    uploaded = await save_application_file(db, application_id, file_type, file)
    application.requested_file_types = []
    application.decision_reason = None
    await queue_signed_review(db, application)
    await db.commit()
    return GenericFileUploadResponse(
        application_id=application.id,
        status=application.status,
        uploaded_file=uploaded,
    )


@router.post("/{application_id}/files/batch", response_model=GenericFilesUploadResponse)
async def upload_application_files_batch(
    application_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    files: list[UploadFile] = File(...),
    file_type: str = Form(default="supplement_file"),
    file_types: list[str] | None = Form(default=None),
) -> GenericFilesUploadResponse:
    application = await db.get(Application, application_id, with_for_update=True)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if application.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    if application.status != "supplement_required":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is not waiting for supplement files",
        )
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one supplement file is required",
        )

    types = file_types if isinstance(file_types, list) else [file_type] * len(files)
    if len(types) != len(files):
        raise HTTPException(400, "材料类型与文件数量不一致")
    await validate_supplement_types(db, application, types)
    await file_storage_service.validate_batch(files)
    uploaded_files = [await save_application_file(db, application_id, kind, file)
                      for kind, file in zip(types, files)]
    application.requested_file_types = []
    application.decision_reason = None
    await queue_signed_review(db, application)
    await db.commit()
    return GenericFilesUploadResponse(
        application_id=application.id,
        status=application.status,
        uploaded_files=uploaded_files,
    )


@router.post("/{application_id}/signed-files", response_model=SignedFilesSubmitResponse)
async def submit_signed_files(
    application_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    meiyu_signed_application_form: UploadFile | None = File(default=None),
    yueyuan_plan_file: UploadFile | None = File(default=None),
    yueyuan_plan_signed_scan: UploadFile | None = File(default=None),
    safety_responsibility_file: UploadFile | None = File(default=None),
    safety_responsibility_signed_scan: UploadFile | None = File(default=None),
    work_checklist_file: UploadFile | None = File(default=None),
    work_checklist_signed_scan: UploadFile | None = File(default=None),
    electricity_commitment_file: UploadFile | None = File(default=None),
    electricity_commitment_signed_scan: UploadFile | None = File(default=None),
) -> SignedFilesSubmitResponse:
    application = await db.get(Application, application_id, with_for_update=True)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if application.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    if application.status != "pending_signed_files":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is not waiting for signed files",
        )

    supplied = {
        "meiyu_signed_application_form": meiyu_signed_application_form,
        "yueyuan_plan_file": yueyuan_plan_file, "yueyuan_plan_signed_scan": yueyuan_plan_signed_scan,
        "safety_responsibility_file": safety_responsibility_file, "safety_responsibility_signed_scan": safety_responsibility_signed_scan,
        "work_checklist_file": work_checklist_file, "work_checklist_signed_scan": work_checklist_signed_scan,
        "electricity_commitment_file": electricity_commitment_file, "electricity_commitment_signed_scan": electricity_commitment_signed_scan,
    }
    required = signed_file_types(application.application_type)
    if not required or any(supplied[key] is None for key in required):
        raise HTTPException(400, "请按清单上传全部签章材料")
    await file_storage_service.validate_batch([supplied[key] for key in required])
    uploaded_files: list[UploadedSignedFile] = []
    if application.application_type == "meiyu_venue":
        if meiyu_signed_application_form is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="meiyu_signed_application_form is required",
            )
        uploaded_files.append(
            await save_application_file(
                db,
                application_id,
                "meiyu_signed_application_form",
                meiyu_signed_application_form,
            )
        )
    elif application.application_type == "yueyuan_third_floor":
        required_files = {
            "yueyuan_plan_file": yueyuan_plan_file,
            "yueyuan_plan_signed_scan": yueyuan_plan_signed_scan,
            "safety_responsibility_file": safety_responsibility_file,
            "safety_responsibility_signed_scan": safety_responsibility_signed_scan,
            "work_checklist_file": work_checklist_file,
            "work_checklist_signed_scan": work_checklist_signed_scan,
            "electricity_commitment_file": electricity_commitment_file,
            "electricity_commitment_signed_scan": electricity_commitment_signed_scan,
        }
        missing = [name for name, upload in required_files.items() if upload is None]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required files: {', '.join(missing)}",
            )
        for file_type, upload in required_files.items():
            if upload is not None:
                uploaded_files.append(
                    await save_application_file(db, application_id, file_type, upload)
                )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This application type does not support signed file submission",
        )

    await queue_signed_review(db, application)
    await db.commit()

    return SignedFilesSubmitResponse(
        application_id=application.id,
        application_type=application.application_type,
        status=application.status,
        uploaded_files=uploaded_files,
    )


@router.post("/pre-review", response_model=ApplicationPreReviewResponse)
async def submit_pre_review(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    application_type: str = Form(default="auto"),
    venue_id: int | None = Form(default=None),
    file: UploadFile = File(...),
    additional_files: list[UploadFile] | None = File(default=None),
    expected_date: str | None = Form(default=None),
) -> ApplicationPreReviewResponse:
    if not current_user.is_sdu_verified and not current_user.is_application_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SDU authentication or admin application permission required",
        )

    if application_type not in {"auto", "meiyu_venue", "yueyuan_third_floor"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported pre-review application type",
        )

    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .docx Word documents are accepted for pre-review",
        )

    await file_storage_service.validate_batch([file, *(additional_files or [])])
    if expected_date is not None:
        try:
            Date.fromisoformat(expected_date)
        except (ValueError, TypeError):
            raise HTTPException(400, "请选择有效的申请日期")
    ai_result = await ai_review_service.pre_review_word(application_type, file)
    if needs_manual_review(ai_result):
        return await queue_manual_pre_review(db, current_user, file, venue_id, additional_files=additional_files)
    if venue_id is None:
        # Resolve against real catalog entries; never let AI invent a venue ID.
        venues = (await db.execute(select(Venue))).scalars().all()
        matches = [item for item in venues if normalize_venue_name(item.name) == normalize_venue_name(ai_result.venue_name)]
        if len(matches) != 1:
            return await queue_manual_pre_review(db, current_user, file, additional_files=additional_files,
                reason="暂时无法自动确认申请场地，材料已转交人工初审，管理员将核对原文件。")
        venue_id = matches[0].id
    venue = await db.get(Venue, venue_id)
    if venue is None:
        raise HTTPException(400, "所选场地不存在")
    expected_type = "yueyuan_third_floor" if "悦园三楼" in venue.name else "meiyu_venue"
    if application_type == "auto":
        application_type = expected_type
    if application_type != expected_type:
        raise HTTPException(400, "申请类型与场地不匹配")
    ai_result, issues, conflicts, passed = await evaluate_pre_review(
        db,
        application_type,
        venue_id,
        file,
        expected_date=expected_date,
        ai_result=ai_result,
    )
    application_id: int | None = None
    auth_profile_result = await db.execute(
        select(AuthProfile).where(AuthProfile.user_id == current_user.id)
    )
    auth_profile = auth_profile_result.scalar_one_or_none()
    stored_path = await file_storage_service.save_upload(file, "pre-review")
    first_slot = ai_result.extracted_time_slots[0] if ai_result.extracted_time_slots else None
    last_slot = ai_result.extracted_time_slots[-1] if ai_result.extracted_time_slots else None

    application = Application(
        user_id=current_user.id,
        application_type=application_type,
        organization=ai_result.borrow_organization or ai_result.organization or current_user.department,
        borrow_organization=ai_result.borrow_organization or ai_result.organization,
        purpose_summary=ai_result.purpose_summary,
        applicant_name=auth_profile.name if auth_profile else ai_result.applicant_name,
        applicant_sduid=auth_profile.sduid if auth_profile else None,
        applicant_department=current_user.department,
        venue_id=venue_id,
        status="pending_signed_files" if passed else "ai_rejected",
        start_at=first_slot.start_at if first_slot else None,
        end_at=last_slot.end_at if last_slot else None,
    )
    db.add(application)
    await db.flush()

    db.add(
        ApplicationFile(
            application_id=application.id,
            file_type="pre_review_word",
            version=1,
            original_filename=file.filename or "application.docx",
            stored_path=stored_path,
            review_status="passed" if passed else "failed",
            reject_reason=summarize_review_problems(issues, conflicts) if not passed else None,
        )
    )
    for additional_file in additional_files or []:
        await save_application_file(
            db,
            application.id,
            "supporting_material",
            additional_file,
        )
    application_id = application.id

    if passed:
        for slot in ai_result.extracted_time_slots:
            if slot.start_at is None or slot.end_at is None:
                continue
            db.add(
                ReservationCalendar(
                    venue_id=venue_id,
                    application_id=application.id,
                    start_at=slot.start_at,
                    end_at=slot.end_at,
                    status="pre_reserved",
                )
            )
        await notification_service.send_and_log(
            db=db,
            application_id=application.id,
            recipients=[current_user.email],
            notification_type="pre_review_passed",
            subject="场地申请初审通过，请上传签字盖章版本",
            body=(
                "您的场地申请已通过初审，请登录系统上传签字盖章版本材料。\n\n"
                f"{format_application_label(application)}"
            ),
        )
    else:
        await notification_service.send_and_log(
            db=db,
            application_id=application.id,
            recipients=[current_user.email],
            notification_type="pre_review_rejected",
            subject="场地申请初审未通过",
            body=(
                "您的场地申请未通过 AI 初审，请修改申请文件后重新提交。\n\n"
                f"{format_application_label(application)}\n\n"
                f"未通过原因：\n{summarize_review_problems(issues, conflicts) or '材料不符合初审要求'}"
            ),
        )

    await db.commit()

    return ApplicationPreReviewResponse(
        passed=passed,
        application_type=application_type,
        venue_id=venue_id,
        next_status="pending_signed_files" if passed else "ai_rejected",
        extracted_time_slots=ai_result.extracted_time_slots,
        issues=issues,
        conflicts=conflicts,
        application_id=application_id,
        borrow_organization=ai_result.borrow_organization or ai_result.organization,
        purpose_summary=ai_result.purpose_summary,
    )


@router.post("/{application_id}/pre-review", response_model=ApplicationPreReviewResponse)
async def resubmit_pre_review(
    application_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    additional_files: list[UploadFile] | None = File(default=None),
) -> ApplicationPreReviewResponse:
    application = await db.get(Application, application_id, with_for_update=True)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if application.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    if application.status != "ai_rejected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only AI-rejected applications can be resubmitted",
        )
    if application.application_type not in {"meiyu_venue", "yueyuan_third_floor", "venue_auto"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This application type does not support AI pre-review",
        )
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .docx Word documents are accepted for pre-review",
        )

    await file_storage_service.validate_batch([file, *(additional_files or [])])
    ai_result = await ai_review_service.pre_review_word(
        application.application_type if application.venue_id else "auto", file)
    if needs_manual_review(ai_result):
        return await queue_manual_pre_review(db, current_user, file, application.venue_id, application, additional_files)
    if application.venue_id is None:
        matches = [v for v in (await db.execute(select(Venue))).scalars() if normalize_venue_name(v.name) == normalize_venue_name(ai_result.venue_name)]
        if len(matches) != 1:
            return await queue_manual_pre_review(db, current_user, file, application=application, additional_files=additional_files,
                reason="暂时无法自动确认申请场地，材料已转交人工初审，管理员将核对原文件。")
        application.venue_id = matches[0].id
        application.application_type = "yueyuan_third_floor" if "悦园三楼" in matches[0].name else "meiyu_venue"
    application.decision_reason = None
    ai_result, issues, conflicts, passed = await evaluate_pre_review(
        db,
        application.application_type,
        application.venue_id,
        file,
        ignored_application_id=application.id,
        ai_result=ai_result,
    )
    stored_path = await file_storage_service.save_upload(file, "pre-review")
    version = await next_file_version(db, application.id, "pre_review_word")
    first_slot = ai_result.extracted_time_slots[0] if ai_result.extracted_time_slots else None
    last_slot = ai_result.extracted_time_slots[-1] if ai_result.extracted_time_slots else None

    application.organization = (
        ai_result.borrow_organization
        or ai_result.organization
        or application.organization
        or current_user.department
    )
    application.borrow_organization = (
        ai_result.borrow_organization or ai_result.organization
    )
    application.purpose_summary = ai_result.purpose_summary
    if not application.applicant_sduid and ai_result.applicant_name:
        application.applicant_name = ai_result.applicant_name
    application.start_at = first_slot.start_at if first_slot else None
    application.end_at = last_slot.end_at if last_slot else None
    application.status = "pending_signed_files" if passed else "ai_rejected"

    db.add(
        ApplicationFile(
            application_id=application.id,
            file_type="pre_review_word",
            version=version,
            original_filename=file.filename or "application.docx",
            stored_path=stored_path,
            review_status="passed" if passed else "failed",
            reject_reason=summarize_review_problems(issues, conflicts) if not passed else None,
        )
    )
    for additional_file in additional_files or []:
        await save_application_file(
            db,
            application.id,
            "supporting_material",
            additional_file,
        )

    existing_reservations = await db.execute(
        select(ReservationCalendar).where(
            ReservationCalendar.application_id == application.id,
            ReservationCalendar.status != "cancelled",
        )
    )
    for reservation in existing_reservations.scalars():
        reservation.status = "cancelled"

    if passed:
        for slot in ai_result.extracted_time_slots:
            if slot.start_at is None or slot.end_at is None:
                continue
            db.add(
                ReservationCalendar(
                    venue_id=application.venue_id,
                    application_id=application.id,
                    start_at=slot.start_at,
                    end_at=slot.end_at,
                    status="pre_reserved",
                )
            )
        await notification_service.send_and_log(
            db=db,
            application_id=application.id,
            recipients=[current_user.email],
            notification_type="pre_review_passed",
            subject="场地申请重新初审通过",
            body=(
                "您重新提交的场地申请已通过 AI 初审，请上传签字盖章版本材料。\n\n"
                f"{format_application_label(application)}"
            ),
        )
    else:
        await notification_service.send_and_log(
            db=db,
            application_id=application.id,
            recipients=[current_user.email],
            notification_type="pre_review_rejected",
            subject="场地申请重新初审未通过",
            body=(
                "您重新提交的场地申请仍未通过 AI 初审，请根据原因继续修改。\n\n"
                f"{format_application_label(application)}\n\n"
                f"未通过原因：\n{summarize_review_problems(issues, conflicts) or '材料不符合初审要求'}"
            ),
        )

    await db.commit()
    return ApplicationPreReviewResponse(
        passed=passed,
        application_type=application.application_type,
        venue_id=application.venue_id,
        next_status=application.status,
        extracted_time_slots=ai_result.extracted_time_slots,
        issues=issues,
        conflicts=conflicts,
        application_id=application.id,
        borrow_organization=application.borrow_organization,
        purpose_summary=application.purpose_summary,
    )
