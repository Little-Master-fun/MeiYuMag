from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_user_by_email,
    get_user_by_mobile,
    get_user_by_sduid,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.auth_profile import AuthProfile
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    OrganizationUpdateRequest,
    RefreshTokenRequest,
    RegistrationSmsRequest,
    RegisterRequest,
    TokenPair,
    UserRead,
)
from app.services.sdu_auth import sdu_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def build_token_pair(user: User) -> TokenPair:
    subject = str(user.id)
    extra = {"role": user.role}
    return TokenPair(
        access_token=create_access_token(subject, extra=extra),
        refresh_token=create_refresh_token(subject, extra=extra),
    )


@router.post("/register/code")
async def get_registration_image_code(response: Response) -> Response:
    return await sdu_auth_service.get_image_code(response)


@router.post("/register/sms", status_code=status.HTTP_201_CREATED)
async def send_registration_sms_code(
    payload: RegistrationSmsRequest,
    request: Request,
) -> dict[str, str]:
    await sdu_auth_service.send_sms_code(request, payload.mobile, payload.image_code)
    return {"message": "sms code sent"}


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    existing_user = await get_user_by_email(db, payload.email)
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    sdu_profile = await sdu_auth_service.sms_login(request, payload.mobile, payload.sms_code)
    existing_profile_result = await db.execute(
        select(AuthProfile).where(AuthProfile.sduid == sdu_profile.sduid)
    )
    if existing_profile_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This SDU account is already registered",
        )

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        department=payload.organization.strip(),
        is_sdu_verified=True,
    )
    db.add(user)
    try:
        await db.flush()
        db.add(
            AuthProfile(
                user_id=user.id,
                sduid=sdu_profile.sduid,
                name=sdu_profile.name,
                sex=sdu_profile.sex,
                person_type=sdu_profile.type,
                school=sdu_profile.school,
                sdu_email=sdu_profile.email,
                mobile=sdu_profile.tel or payload.mobile,
                verified_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or SDU account already registered",
        ) from exc
    await db.refresh(user)

    tokens = build_token_pair(user)
    return AuthResponse(**tokens.model_dump(), user=UserRead.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    account = payload.account.strip()
    user = await get_user_by_email(db, account)
    if user is None:
        user = await get_user_by_sduid(db, account)
    if user is None:
        user = await get_user_by_mobile(db, account)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid account or password",
        )

    tokens = build_token_pair(user)
    return AuthResponse(**tokens.model_dump(), user=UserRead.model_validate(user))


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    try:
        token_payload = decode_token(payload.refresh_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if token_payload.get("token_use") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = token_payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = await db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return build_token_pair(user)


@router.get("/me", response_model=UserRead)
async def read_me(current_user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me/organization", response_model=UserRead)
async def update_my_organization(
    payload: OrganizationUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    current_user.department = payload.organization.strip()
    await db.commit()
    await db.refresh(current_user)
    return UserRead.model_validate(current_user)
