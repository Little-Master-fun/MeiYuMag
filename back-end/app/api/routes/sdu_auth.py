from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.auth_profile import AuthProfile
from app.models.user import User
from app.schemas.sdu_auth import SduAuthResponse
from app.services.sdu_auth import sdu_auth_service

router = APIRouter(prefix="/sdu-auth", tags=["sdu-auth"])


@router.post("/code")
async def get_image_code(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    return await sdu_auth_service.get_image_code(response)


@router.post("/sms", status_code=201)
async def send_sms_code(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    mobile: str = Body(max_length=11, min_length=11, pattern=r"^\d+$"),
    code: str = Body(max_length=4, min_length=4, pattern=r"^\d+$"),
) -> dict[str, str]:
    await sdu_auth_service.send_sms_code(request, mobile, code)
    return {"message": "sms code sent"}


@router.post("/login", response_model=SduAuthResponse)
async def sdu_sms_login(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    mobile: str = Body(max_length=11, min_length=11, pattern=r"^\d+$"),
    code: str = Body(max_length=6, min_length=6, pattern=r"^\d+$"),
    department: str = Body(min_length=1, max_length=255),
) -> SduAuthResponse:
    profile = await sdu_auth_service.sms_login(request, mobile, code)

    existing_sduid = await db.execute(
        select(AuthProfile).where(AuthProfile.sduid == profile.sduid)
    )
    profile_for_sduid = existing_sduid.scalar_one_or_none()
    if profile_for_sduid is not None and profile_for_sduid.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This SDU account is already bound to another user",
        )

    existing_user_profile = await db.execute(
        select(AuthProfile).where(AuthProfile.user_id == current_user.id)
    )
    auth_profile = existing_user_profile.scalar_one_or_none()
    if auth_profile is None:
        auth_profile = AuthProfile(user_id=current_user.id, sduid=profile.sduid, name=profile.name)
        db.add(auth_profile)

    auth_profile.sduid = profile.sduid
    auth_profile.name = profile.name
    auth_profile.sex = profile.sex
    auth_profile.person_type = profile.type
    auth_profile.school = profile.school
    auth_profile.sdu_email = profile.email
    auth_profile.mobile = profile.tel
    auth_profile.verified_at = datetime.now(timezone.utc)

    current_user.is_sdu_verified = True
    current_user.department = department.strip()

    await db.commit()
    await db.refresh(current_user)

    return SduAuthResponse(
        message="SDU authentication completed",
        profile=profile,
        is_sdu_verified=current_user.is_sdu_verified,
    )
