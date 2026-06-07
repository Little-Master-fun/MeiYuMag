from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.application import Application, ApplicationFile
from app.models.auth_profile import AuthProfile
from app.models.user import User
from app.models.venue import ReservationCalendar
from app.schemas.application import (
    ApplicationRead,
    ApplicationPreReviewResponse,
    ConflictItem,
    GenericFileUploadResponse,
    ReviewIssue,
    SignedFilesSubmitResponse,
    UploadedSignedFile,
)
from app.services.ai_review import ai_review_service
from app.services.file_storage import file_storage_service

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
    return UploadedSignedFile(
        file_type=file_type,
        version=version,
        original_filename=application_file.original_filename,
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
    return [ApplicationRead.model_validate(item) for item in result.scalars()]


@router.post("/{application_id}/files", response_model=GenericFileUploadResponse)
async def upload_application_file(
    application_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file_type: str = Form(...),
    file: UploadFile = File(...),
) -> GenericFileUploadResponse:
    application = await db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if application.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    if application.status != "supplement_required":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is not waiting for supplement files",
        )

    uploaded = await save_application_file(db, application_id, file_type, file)
    application.status = "pending_admin_submit"
    await db.commit()
    return GenericFileUploadResponse(
        application_id=application.id,
        status=application.status,
        uploaded_file=uploaded,
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
    application = await db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if application.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    if application.status not in {"pending_signed_files", "supplement_required"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is not waiting for signed files",
        )

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

    application.status = "pending_admin_submit"
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
    application_type: str = Form(...),
    venue_id: int = Form(...),
    file: UploadFile = File(...),
) -> ApplicationPreReviewResponse:
    if not current_user.is_sdu_verified and not current_user.is_application_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SDU authentication or admin application permission required",
        )

    if application_type not in {"meiyu_venue", "yueyuan_third_floor"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported pre-review application type",
        )

    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .docx Word documents are accepted for pre-review",
        )

    ai_result = await ai_review_service.pre_review_word(application_type, file)
    issues = list(ai_result.issues)
    conflicts: list[ConflictItem] = []

    if ai_result.extracted_time_slots:
        for slot in ai_result.extracted_time_slots:
            if slot.start_at is None or slot.end_at is None:
                issues.append(
                    ReviewIssue(
                        type="INVALID_TIME_SLOT",
                        message=f"无法解析借用时间：{slot.date} {slot.start_time}-{slot.end_time}",
                    )
                )
                continue

            result = await db.execute(
                select(ReservationCalendar).where(
                    and_(
                        ReservationCalendar.venue_id == venue_id,
                        ReservationCalendar.status.in_(["pre_reserved", "confirmed", "reserved"]),
                        ReservationCalendar.start_at < slot.end_at,
                        ReservationCalendar.end_at > slot.start_at,
                    )
                )
            )
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
    application_id: int | None = None
    if passed:
        auth_profile_result = await db.execute(
            select(AuthProfile).where(AuthProfile.user_id == current_user.id)
        )
        auth_profile = auth_profile_result.scalar_one_or_none()
        first_slot = ai_result.extracted_time_slots[0]
        last_slot = ai_result.extracted_time_slots[-1]
        stored_path = await file_storage_service.save_upload(file, "pre-review")

        application = Application(
            user_id=current_user.id,
            application_type=application_type,
            organization=ai_result.organization or current_user.department,
            applicant_name=auth_profile.name if auth_profile else None,
            applicant_sduid=auth_profile.sduid if auth_profile else None,
            applicant_department=current_user.department,
            venue_id=venue_id,
            status="pending_signed_files",
            start_at=first_slot.start_at,
            end_at=last_slot.end_at,
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
                review_status="passed",
            )
        )

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

        await db.commit()
        application_id = application.id

    return ApplicationPreReviewResponse(
        passed=passed,
        application_type=application_type,
        venue_id=venue_id,
        next_status="pending_signed_files" if passed else "pre_review_failed",
        extracted_time_slots=ai_result.extracted_time_slots,
        issues=issues,
        conflicts=conflicts,
        application_id=application_id,
    )
