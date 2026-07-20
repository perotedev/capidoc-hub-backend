from fastapi import APIRouter, Request

from app.modules.auth.api.v1.dependencies import AuthServiceDep, CurrentUser
from app.modules.auth.application.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RecoverPasswordRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SessionResponse,
    TokenResponse,
    VerifyResetCodeRequest,
)
from app.modules.users.application.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, http_request: Request, service: AuthServiceDep) -> TokenResponse:
    user_agent = http_request.headers.get("user-agent")
    return await service.login(request, user_agent)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest, service: AuthServiceDep) -> TokenResponse:
    return await service.refresh(request.refresh_token)


@router.post("/logout", status_code=204)
async def logout(request: RefreshRequest, service: AuthServiceDep) -> None:
    await service.logout(request.refresh_token)


@router.post("/logout-all", status_code=204)
async def logout_all(current_user: CurrentUser, service: AuthServiceDep) -> None:
    await service.logout_all(current_user.id)


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(current_user: CurrentUser, service: AuthServiceDep) -> list[SessionResponse]:
    sessions = await service.list_sessions(current_user.id)
    return [
        SessionResponse(
            session_id=session.session_id,
            user_agent=session.user_agent,
            created_at=session.created_at.isoformat(),
            expires_at=session.expires_at.isoformat(),
        )
        for session in sessions
    ]


@router.post("/change-password", status_code=204)
async def change_password(
    request: ChangePasswordRequest, current_user: CurrentUser, service: AuthServiceDep
) -> None:
    await service.change_password(current_user.id, request.current_password, request.new_password)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post("/recover-password", status_code=204)
async def recover_password(request: RecoverPasswordRequest, service: AuthServiceDep) -> None:
    await service.request_password_reset(request.email)


@router.post("/verify-reset-code", status_code=204)
async def verify_reset_code(request: VerifyResetCodeRequest, service: AuthServiceDep) -> None:
    await service.verify_reset_code(request.email, request.code)


@router.post("/reset-password", status_code=204)
async def reset_password(request: ResetPasswordRequest, service: AuthServiceDep) -> None:
    await service.reset_password(request.email, request.code, request.new_password)
