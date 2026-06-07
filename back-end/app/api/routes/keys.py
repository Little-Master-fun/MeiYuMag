from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.db.session import get_db
from app.models.application import Application, ApplicationFile
from app.models.auth_profile import AuthProfile
from app.models.key import KeyBorrowRecord, KeyResource
from app.models.user import User
from app.schemas.key import (
    KeyBorrowResponse,
    KeyCheckoutResponse,
    KeyResourceRead,
    KeyResourceUpdate,
    KeyReturnResponse,
)
from app.services.file_storage import file_storage_service
from app.services.notification import notification_service

router = APIRouter(prefix="/keys", tags=["keys"])

ALLOWED_KEY_FILE_SUFFIXES = {".doc", ".docx", ".pdf", ".jpg", ".jpeg", ".png"}


@router.get("", response_model=list[KeyResourceRead])
async def list_keys(db: AsyncSession = Depends(get_db)) -> list[KeyResourceRead]:
    result = await db.execute(select(KeyResource).order_by(KeyResource.name))
    return [KeyResourceRead.model_validate(key) for key in result.scalars()]


@router.patch("/{key_id}", response_model=KeyResourceRead)
async def update_key_resource(
    key_id: int,
    payload: KeyResourceUpdate,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KeyResourceRead:
    key = await db.get(KeyResource, key_id)
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key resource not found")
    if payload.name is not None:
        key.name = payload.name
    if payload.room_name is not None:
        key.room_name = payload.room_name
    if payload.status is not None:
        key.status = payload.status
    await db.commit()
    await db.refresh(key)
    return KeyResourceRead.model_validate(key)


@router.post("/borrow", response_model=KeyBorrowResponse)
async def create_key_borrow_application(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_id: int = Form(...),
    borrowed_at: datetime | None = Form(default=None),
    expected_return_at: datetime | None = Form(default=None),
    file: UploadFile = File(...),
) -> KeyBorrowResponse:
    if not current_user.is_sdu_verified and not current_user.is_application_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SDU authentication or admin application permission required",
        )

    key = await db.get(KeyResource, key_id)
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key resource not found")
    if key.status not in {"available", "borrowable"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Key is not available")
    filename = file.filename or ""
    if not any(filename.lower().endswith(suffix) for suffix in ALLOWED_KEY_FILE_SUFFIXES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Key borrowing application file type is not supported",
        )

    auth_profile_result = await db.execute(
        select(AuthProfile).where(AuthProfile.user_id == current_user.id)
    )
    auth_profile = auth_profile_result.scalar_one_or_none()
    stored_path = await file_storage_service.save_upload(file, "key-borrow")

    application = Application(
        user_id=current_user.id,
        application_type="key_borrow",
        organization=current_user.department,
        applicant_name=auth_profile.name if auth_profile else None,
        applicant_sduid=auth_profile.sduid if auth_profile else None,
        applicant_department=current_user.department,
        key_id=key_id,
        status="pending_admin_submit",
        start_at=borrowed_at,
        end_at=expected_return_at,
    )
    db.add(application)
    await db.flush()

    db.add(
        ApplicationFile(
            application_id=application.id,
            file_type="key_borrow_application",
            version=1,
            original_filename=file.filename or "key-borrow-application",
            stored_path=stored_path,
            review_status="pending_admin_review",
        )
    )
    db.add(
        KeyBorrowRecord(
            key_id=key_id,
            application_id=application.id,
            borrowed_at=borrowed_at,
            expected_return_at=expected_return_at,
        )
    )
    await notification_service.notify_admins(
        db=db,
        application=application,
        notification_type="pending_admin_submit",
        subject="有钥匙借用申请待管理员提交",
        body=(
            "用户已提交钥匙借用申请，申请进入待管理员提交状态。\n\n"
            f"申请编号：{application.id}\n"
            f"钥匙编号：{key_id}\n"
            f"申请人：{application.applicant_name or '未填写'}\n"
            f"申请部门：{application.applicant_department or '未填写'}"
        ),
    )
    await db.commit()

    return KeyBorrowResponse(
        application_id=application.id,
        key_id=key_id,
        status=application.status,
        borrowed_at=borrowed_at,
        expected_return_at=expected_return_at,
        uploaded_file_version=1,
    )


async def get_key_borrow_record_or_404(
    db: AsyncSession,
    application_id: int,
) -> tuple[Application, KeyBorrowRecord, KeyResource]:
    application = await db.get(Application, application_id)
    if application is None or application.application_type != "key_borrow":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key application not found")
    result = await db.execute(
        select(KeyBorrowRecord).where(KeyBorrowRecord.application_id == application_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key record not found")
    key = await db.get(KeyResource, record.key_id)
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key resource not found")
    return application, record, key


@router.post("/borrow-records/{application_id}/checkout", response_model=KeyCheckoutResponse)
async def checkout_key(
    application_id: int,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KeyCheckoutResponse:
    application, record, key = await get_key_borrow_record_or_404(db, application_id)
    borrowed_at = record.borrowed_at or datetime.now(timezone.utc)
    record.borrowed_at = borrowed_at
    key.status = "borrowed"
    application.status = "submitted"
    await db.commit()
    return KeyCheckoutResponse(
        application_id=application.id,
        key_id=key.id,
        key_status=key.status,
        borrowed_at=borrowed_at,
    )


@router.post("/borrow-records/{application_id}/return", response_model=KeyReturnResponse)
async def return_key(
    application_id: int,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KeyReturnResponse:
    application, record, key = await get_key_borrow_record_or_404(db, application_id)
    returned_at = datetime.now(timezone.utc)
    record.returned_at = returned_at
    key.status = "available"
    application.status = "completed"
    await db.commit()
    return KeyReturnResponse(
        application_id=application.id,
        key_id=key.id,
        key_status=key.status,
        returned_at=returned_at,
    )
