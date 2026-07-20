from pydantic import EmailStr, Field

from app.modules.users.application.schemas import UserResponse
from app.shared.schema import CamelCaseModel


class LoginRequest(CamelCaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(CamelCaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(CamelCaseModel):
    refresh_token: str


class ChangePasswordRequest(CamelCaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


class RecoverPasswordRequest(CamelCaseModel):
    email: EmailStr


class ResetPasswordRequest(CamelCaseModel):
    token: str
    new_password: str = Field(min_length=6, max_length=128)


class SessionResponse(CamelCaseModel):
    session_id: str
    user_agent: str | None
    created_at: str
    expires_at: str
