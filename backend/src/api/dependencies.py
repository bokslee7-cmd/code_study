from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.exceptions import UnauthorizedException
from src.db.session import get_session
from src.models import User
from src.services.auth.token_service import INVALID_TOKEN_MESSAGE, TokenService
from src.services.auth.user_service import UserService
from src.services.code_analysis.code_upload_service import CodeUploadService
from src.services.document.document_queue_service import DocumentQueueService
from src.services.project_service import ProjectService
from src.services.task_service import TaskService

# auto_error=False: a missing header must become our 401 ErrorResponse, not FastAPI's default.
_bearer_scheme = HTTPBearer(auto_error=False, description="Access token (JWT)")


def get_user_service(session: Annotated[AsyncSession, Depends(get_session)]) -> UserService:
    return UserService(session)


def get_token_service(session: Annotated[AsyncSession, Depends(get_session)]) -> TokenService:
    return TokenService(session)


def get_project_service(session: Annotated[AsyncSession, Depends(get_session)]) -> ProjectService:
    return ProjectService(session)


def get_task_service(session: Annotated[AsyncSession, Depends(get_session)]) -> TaskService:
    return TaskService(session)


def get_code_upload_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CodeUploadService:
    return CodeUploadService(session)


def get_document_queue_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentQueueService:
    return DocumentQueueService(session)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Route protection: the user behind the `Authorization: Bearer <access token>` header.

    Raises 401 when the header is missing or the token is invalid or expired, and also when the
    user no longer exists (a still-valid token of a deleted account).
    """
    if credentials is None or not credentials.credentials:
        raise UnauthorizedException()
    user_id = TokenService(session).verify_access_token(credentials.credentials)
    user = await UserService(session).get_by_id(user_id)
    if user is None:
        raise UnauthorizedException(INVALID_TOKEN_MESSAGE)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
