from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    organization: str = Field(min_length=1, max_length=255)
    mobile: str = Field(min_length=11, max_length=11, pattern=r"^\d+$")
    sms_code: str = Field(min_length=6, max_length=6, pattern=r"^\d+$")


class RegistrationSmsRequest(BaseModel):
    mobile: str = Field(min_length=11, max_length=11, pattern=r"^\d+$")
    image_code: str = Field(min_length=4, max_length=4, pattern=r"^\d+$")


class LoginRequest(BaseModel):
    account: str = Field(
        min_length=1,
        max_length=255,
        description="Email, verified mobile number, or verified SDU ID",
    )
    password: str = Field(min_length=1, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class OrganizationUpdateRequest(BaseModel):
    organization: str = Field(min_length=1, max_length=255)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: int
    email: str
    role: str
    department: str | None
    is_sdu_verified: bool
    is_application_allowed: bool

    model_config = {"from_attributes": True}


class AuthResponse(TokenPair):
    user: UserRead


class AdminUserRead(UserRead):
    """Primary-admin roster only; do not expose identity data in shared user responses."""

    verified_name: str | None = None


class UserUpdateRequest(BaseModel):
    role: str | None = Field(default=None, pattern="^(user|admin|secondary_admin)$")
    is_application_allowed: bool | None = None
