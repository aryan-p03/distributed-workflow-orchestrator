"""Workflow write HTTP router: create and run endpoints."""

from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from backend.application.services.auth_service import AuthService
from backend.application.services.workflow_service import (
    WorkflowAuthorizationError,
    WorkflowNotFoundError,
    WorkflowService,
    WorkflowServiceError,
    WorkflowTaskNotFoundError,
)
from backend.application.workflow_templates import WorkflowTemplateError
from backend.domain.auth import AuthError, AuthUser, TokenError
from backend.infrastructure.repositories.sql_user_repository import SqlUserRepository
from backend.infrastructure.task_queue_dispatcher import CeleryTaskQueueDispatcher
from backend.interfaces.http.schemas.workflow_read import (
    TaskLogListResponse,
    TaskLogResponse,
    TaskReadResponse,
    WorkflowListItemResponse,
    WorkflowListResponse,
    WorkflowReadResponse,
)
from backend.interfaces.http.schemas.workflows import (
    CreateWorkflowRequest,
    WorkflowResponse,
)

_bearer = HTTPBearer(auto_error=False)


def create_workflow_router(
    session_factory: sessionmaker,  # type: ignore[type-arg]
    jwt_secret: str,
    jwt_expires_seconds: int = 3600,
) -> APIRouter:
    router = APIRouter(prefix="/workflows", tags=["workflows"])
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

    def get_db_session() -> Generator[Session]:
        session: Session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_auth_service(
        session: Session = Depends(get_db_session),
    ) -> AuthService:
        return AuthService(
            repo=SqlUserRepository(session),
            jwt_secret=jwt_secret,
            jwt_expires_seconds=jwt_expires_seconds,
        )

    def get_workflow_service(
        session: Session = Depends(get_db_session),
    ) -> WorkflowService:
        return WorkflowService(session, task_dispatcher=CeleryTaskQueueDispatcher())

    def get_current_user(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
        service: AuthService = Depends(get_auth_service),
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

    @router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
    def create_workflow(
        body: CreateWorkflowRequest,
        current_user: AuthUser = Depends(get_current_user),
        service: WorkflowService = Depends(get_workflow_service),
    ) -> WorkflowResponse:
        try:
            workflow = service.create_workflow(
                user_id=current_user.id,
                template_name=body.template_name,
                payload=body.payload,
            )
        except WorkflowTemplateError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc
        except WorkflowServiceError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        return WorkflowResponse.model_validate(workflow)

    @router.post(
        "/{workflow_id}/run",
        response_model=WorkflowResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def run_workflow(
        workflow_id: int,
        current_user: AuthUser = Depends(get_current_user),
        service: WorkflowService = Depends(get_workflow_service),
    ) -> WorkflowResponse:
        try:
            workflow = service.run_workflow(user_id=current_user.id, workflow_id=workflow_id)
        except WorkflowNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except WorkflowAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except WorkflowServiceError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        return WorkflowResponse.model_validate(workflow)

    @router.get("", response_model=WorkflowListResponse)
    def list_workflows(
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        current_user: AuthUser = Depends(get_current_user),
        service: WorkflowService = Depends(get_workflow_service),
    ) -> WorkflowListResponse:
        items = service.list_workflows(user_id=current_user.id, limit=limit, offset=offset)
        total = service.count_workflows(user_id=current_user.id)
        return WorkflowListResponse(
            items=[WorkflowListItemResponse.model_validate(item) for item in items],
            limit=limit,
            offset=offset,
            total=total,
        )

    @router.get("/{workflow_id}", response_model=WorkflowReadResponse)
    def get_workflow(
        workflow_id: int,
        current_user: AuthUser = Depends(get_current_user),
        service: WorkflowService = Depends(get_workflow_service),
    ) -> WorkflowReadResponse:
        try:
            workflow = service.get_workflow(user_id=current_user.id, workflow_id=workflow_id)
        except WorkflowNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except WorkflowAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        return WorkflowReadResponse.model_validate(workflow)

    @router.get("/{workflow_id}/tasks/{task_id}", response_model=TaskReadResponse)
    def get_workflow_task(
        workflow_id: int,
        task_id: int,
        current_user: AuthUser = Depends(get_current_user),
        service: WorkflowService = Depends(get_workflow_service),
    ) -> TaskReadResponse:
        try:
            task = service.get_task(
                user_id=current_user.id,
                workflow_id=workflow_id,
                task_id=task_id,
            )
        except WorkflowNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except WorkflowTaskNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except WorkflowAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        return TaskReadResponse.model_validate(task)

    @router.get("/{workflow_id}/tasks/{task_id}/logs", response_model=TaskLogListResponse)
    def list_workflow_task_logs(
        workflow_id: int,
        task_id: int,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        current_user: AuthUser = Depends(get_current_user),
        service: WorkflowService = Depends(get_workflow_service),
    ) -> TaskLogListResponse:
        try:
            items = service.list_task_logs(
                user_id=current_user.id,
                workflow_id=workflow_id,
                task_id=task_id,
                limit=limit,
                offset=offset,
            )
            total = service.count_task_logs(
                user_id=current_user.id,
                workflow_id=workflow_id,
                task_id=task_id,
            )
        except WorkflowNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except WorkflowTaskNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except WorkflowAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        return TaskLogListResponse(
            items=[TaskLogResponse.model_validate(item) for item in items],
            limit=limit,
            offset=offset,
            total=total,
        )

    return router
