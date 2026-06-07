from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.application import Application, ApplicationFile
from app.models.auth_profile import AuthProfile
from app.models.key import KeyBorrowRecord, KeyResource
from app.models.user import User
from app.schemas.key import KeyBorrowResponse, KeyResourceRead
from app.services.file_storage import file_storage_service

router = APIRouter(prefix="/keys", tags=["keys"])

ALLOWED_KEY_FILE_SUFFIXES = {".doc", ".docx", ".pdf", ".jpg", ".jpeg", ".png"}


@router.get("", response_model=list[KeyResourceRead])
async def list_keys(db: AsyncSession = Depends(get_db)) -> list[KeyResourceRead]:
    result = await db.execute(select(KeyResource).order_by(KeyResource.name))
    return [KeyResourceRead.model_validate(key) for key in result.scalars()]


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
    await db.commit()

    return KeyBorrowResponse(
        application_id=application.id,
        key_id=key_id,
        status=application.status,
        borrowed_at=borrowed_at,
        expected_return_at=expected_return_at,
        uploaded_file_version=1,
    )
