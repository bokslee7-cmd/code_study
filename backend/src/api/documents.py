from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends

from src.api.dependencies import (
    CurrentUser,
    get_code_upload_service,
    get_document_queue_service,
    get_task_service,
)
from src.api.exceptions import NotFoundException
from src.api.schemas.document import (
    DocumentFile,
    DocumentResponse,
    DocumentStatus,
    DocumentStatusResponse,
)
from src.models import LearningDocument, Task
from src.services.code_analysis.code_upload_service import CodeUploadService
from src.services.document.document_queue_service import (
    DocumentQueueService,
    estimate_remaining_seconds,
    failed_chapters,
)
from src.services.task_service import TaskService

router = APIRouter(tags=["documents"])

TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
CodeUploadServiceDep = Annotated[CodeUploadService, Depends(get_code_upload_service)]
DocumentQueueDep = Annotated[DocumentQueueService, Depends(get_document_queue_service)]

DOCUMENT_NOT_FOUND_MESSAGE = (
    "이 태스크의 학습 문서를 찾을 수 없습니다. 코드를 업로드한 태스크인지 확인하세요."  # noqa: E501 (Korean text is double width)
)
DOCUMENT_NOT_FOUND_SUGGESTION = "태스크에 코드를 업로드하면 학습 문서가 자동으로 만들어집니다."


async def _owned_document(
    task_id: UUID, user_id: UUID, tasks: TaskService, queue: DocumentQueueService
) -> tuple[Task, LearningDocument]:
    """Ownership is checked first (same 404/403 as /tasks/{id}); then the document must exist."""
    task = await tasks.get_owned(task_id, user_id)
    document = await queue.get_document(task_id)
    if document is None:
        raise NotFoundException(
            DOCUMENT_NOT_FOUND_MESSAGE,
            details={"task_id": str(task_id)},
            suggestion=DOCUMENT_NOT_FOUND_SUGGESTION,
        )
    return task, document


def _status(document: LearningDocument) -> DocumentStatus:
    # The column is nullable in the migration; a row without a status has not started.
    return cast(DocumentStatus, document.generation_status or LearningDocument.PENDING)


@router.get("/tasks/{task_id}/document", response_model=DocumentResponse)
async def get_document(
    task_id: UUID,
    user: CurrentUser,
    tasks: TaskServiceDep,
    uploads: CodeUploadServiceDep,
    queue: DocumentQueueDep,
) -> DocumentResponse:
    task, document = await _owned_document(task_id, user.id, tasks, queue)
    contents = await uploads.get_code(task)
    return DocumentResponse(
        id=document.id,
        task_id=document.task_id,
        status=_status(document),
        content=document.content,
        failed_chapters=failed_chapters(document.content),
        generation_error=document.generation_error,
        generation_started_at=document.generation_started_at,
        generation_completed_at=document.generation_completed_at,
        files=[
            DocumentFile(
                path=item.file.file_path or item.file.file_name,
                language=item.language,
                content=item.content,
            )
            for item in contents
        ],
    )


@router.get("/tasks/{task_id}/document/status", response_model=DocumentStatusResponse)
async def get_document_status(
    task_id: UUID, user: CurrentUser, tasks: TaskServiceDep, queue: DocumentQueueDep
) -> DocumentStatusResponse:
    _, document = await _owned_document(task_id, user.id, tasks, queue)
    return DocumentStatusResponse(
        task_id=document.task_id,
        status=_status(document),
        generation_started_at=document.generation_started_at,
        generation_completed_at=document.generation_completed_at,
        generation_error=document.generation_error,
        failed_chapters=failed_chapters(document.content),
        estimated_remaining_seconds=estimate_remaining_seconds(document),
    )
