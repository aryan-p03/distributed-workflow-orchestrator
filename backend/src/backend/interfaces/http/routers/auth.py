"""Auth HTTP router: register, login, me, and logout endpoints.

Transport concerns only — business logic lives in :class:`AuthService`.
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from backend.application.services.auth_service import AuthService
from backend.domain.auth import AuthError, AuthUser, TokenError
from backend.infrastructure.repositories.sql_user_repository import SqlUserRepository
from backend.interfaces.http.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

_bearer = HTTPBearer(auto_error=False)


def create_auth_router(
    session_factory: sessionmaker,  # type: ignore[type-arg]
    jwt_secret: str,
    jwt_expires_seconds: int = 3600,
) -> APIRouter:
    """Return an :class:`APIRouter` wired to *session_factory* and JWT config."""

    router = APIRouter(prefix="/auth", tags=["auth"])

    cookie_name = "access_token"

    def _extract_access_token(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None,
    ) -> str:
        if credentials is not None:
            return credentials.credentials

        cookie_token = request.cookies.get(cookie_name)
        if cookie_token:
            return cookie_token

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def get_auth_service() -> Generator[AuthService]:
        session: Session = session_factory()
        try:
            repo = SqlUserRepository(session)
            yield AuthService(
                repo=repo,
                jwt_secret=jwt_secret,
                jwt_expires_seconds=jwt_expires_seconds,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_current_user(
        request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
        service: Annotated[AuthService, Depends(get_auth_service)],
    ) -> AuthUser:
        token = _extract_access_token(request, credentials)
        try:
            return service.get_current_user(token)
        except (TokenError, AuthError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    @router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
    def register(
        body: RegisterRequest,
        service: Annotated[AuthService, Depends(get_auth_service)],
    ) -> UserResponse:
        try:
            user = service.register(
                email=body.email,
                username=body.username,
                password=body.password,
            )
        except AuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc
        return UserResponse.model_validate(user)

    @router.post("/login", response_model=TokenResponse)
    def login(
        body: LoginRequest,
        response: Response,
        service: Annotated[AuthService, Depends(get_auth_service)],
    ) -> TokenResponse:
        try:
            token = service.login(email=body.email, password=body.password)
        except AuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        response.set_cookie(
            key=cookie_name,
            value=token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=jwt_expires_seconds,
            path="/",
        )
        return TokenResponse(access_token=token)

    @router.get("/me", response_model=UserResponse)
    def me(
        current_user: Annotated[AuthUser, Depends(get_current_user)],
    ) -> UserResponse:
        return UserResponse.model_validate(current_user)

    @router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(
        request: Request,
        response: Response,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
        service: Annotated[AuthService, Depends(get_auth_service)],
    ) -> None:
        token = _extract_access_token(request, credentials)
        service.logout(token)
        response.delete_cookie(key=cookie_name, path="/")

    return router
