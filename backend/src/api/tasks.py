from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile

from src.api.dependencies import CurrentUser, get_code_upload_service, get_task_service
from src.api.exceptions import VALIDATION_ERROR, AppError
from src.api.schemas.task import (
    CodeFileResponse,
    TaskCodeResponse,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)
from src.services.code_analysis.code_upload_service import CodeUploadService, PreparedUpload
from src.services.task_service import TaskService
from src.utils.file_validator import MAX_UPLOAD_SIZE_BYTES

router = APIRouter(tags=["tasks"])

TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
CodeUploadServiceDep = Annotated[CodeUploadService, Depends(get_code_upload_service)]


async def _read_files(uploads: list[UploadFile]) -> list[tuple[str, bytes]]:
    # One byte over the limit is enough for validation to reject it without buffering more.
    return [
        (upload.filename or "", await upload.read(MAX_UPLOAD_SIZE_BYTES + 1)) for upload in uploads
    ]


def _missing_field(field: str, message: str) -> AppError:
    return AppError(400, VALIDATION_ERROR, message, details={"field": field})


@router.get("/projects/{project_id}/tasks", response_model=TaskListResponse)
async def list_tasks(
    project_id: UUID, user: CurrentUser, tasks: TaskServiceDep
) -> TaskListResponse:
    rows = await tasks.list_for_project(project_id, user.id)
    return TaskListResponse(tasks=[TaskResponse.model_validate(row) for row in rows])


@router.post("/projects/{project_id}/tasks", status_code=201, response_model=TaskResponse)
async def create_task(
    project_id: UUID,
    user: CurrentUser,
    tasks: TaskServiceDep,
    uploads: CodeUploadServiceDep,
    title: Annotated[str, Form()],
    upload_method: Annotated[Literal["file", "folder", "paste"], Form()],
    description: Annotated[str | None, Form()] = None,
    files: Annotated[list[UploadFile], File()] = [],  # noqa: B006 (never mutated)
    code: Annotated[str | None, Form()] = None,
    language: Annotated[str | None, Form()] = None,
) -> TaskResponse:
    """multipart/form-data. file/folder send `files` (folder: the relative path is the
    file name); paste sends `code` and `language`. Validation happens before the task exists."""
    prepared: PreparedUpload
    if upload_method == "paste":
        if code is None:
            raise _missing_field("code", "붙여넣을 코드를 입력하세요.")
        if language is None:
            raise _missing_field("language", "코드 언어를 선택하세요.")
        prepared = uploads.prepare_paste(code, language)
    else:
        contents = await _read_files(files)
        if upload_method == "folder":
            prepared = uploads.prepare_folder(contents)
        else:
            prepared = uploads.prepare_files(contents)
    task = await tasks.create(user.id, project_id, title, description, upload_method=upload_method)
    await uploads.store(user.id, task, prepared)
    await tasks.start_document_generation(task)
    return TaskResponse.model_validate(task)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID, user: CurrentUser, tasks: TaskServiceDep) -> TaskResponse:
    task = await tasks.get_owned(task_id, user.id)
    return TaskResponse.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID, body: TaskUpdate, user: CurrentUser, tasks: TaskServiceDep
) -> TaskResponse:
    # exclude_unset: fields the client did not send stay UNSET in the service (kept as they are).
    task = await tasks.update(task_id, user.id, **body.model_dump(exclude_unset=True))
    return TaskResponse.model_validate(task)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: UUID, user: CurrentUser, tasks: TaskServiceDep) -> None:
    await tasks.soft_delete(task_id, user.id)


@router.get("/tasks/{task_id}/code", response_model=TaskCodeResponse)
async def get_task_code(
    task_id: UUID, user: CurrentUser, tasks: TaskServiceDep, uploads: CodeUploadServiceDep
) -> TaskCodeResponse:
    task = await tasks.get_owned(task_id, user.id)
    contents = await uploads.get_code(task)
    summary = task.uploaded_code
    assert summary is not None  # get_code raises 404 when the task has no upload
    return TaskCodeResponse(
        task_id=task.id,
        detected_language=summary.detected_language,
        complexity_level=summary.complexity_level,
        total_lines=summary.total_lines,
        total_files=summary.total_files,
        upload_size_bytes=summary.upload_size_bytes,
        files=[
            CodeFileResponse(
                id=item.file.id,
                file_name=item.file.file_name,
                file_path=item.file.file_path,
                file_extension=item.file.file_extension,
                file_size_bytes=item.file.file_size_bytes,
                language=item.language,
                content=item.content,
            )
            for item in contents
        ],
    )
