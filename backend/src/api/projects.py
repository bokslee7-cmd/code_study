from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from src.api.dependencies import CurrentUser, get_project_service
from src.api.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from src.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])

ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


@router.get("", response_model=ProjectListResponse)
async def list_projects(user: CurrentUser, projects: ProjectServiceDep) -> ProjectListResponse:
    rows = await projects.get_user_projects(user.id)
    return ProjectListResponse(projects=[ProjectResponse.model_validate(row) for row in rows])


@router.post("", status_code=201, response_model=ProjectResponse)
async def create_project(
    body: ProjectCreate, user: CurrentUser, projects: ProjectServiceDep
) -> ProjectResponse:
    project = await projects.create(user.id, body.title, body.description)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID, user: CurrentUser, projects: ProjectServiceDep
) -> ProjectResponse:
    project = await projects.get_owned(project_id, user.id)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID, body: ProjectUpdate, user: CurrentUser, projects: ProjectServiceDep
) -> ProjectResponse:
    # exclude_unset: fields the client did not send stay UNSET in the service (kept as they are).
    project = await projects.update(project_id, user.id, **body.model_dump(exclude_unset=True))
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: UUID, user: CurrentUser, projects: ProjectServiceDep) -> None:
    await projects.soft_delete(project_id, user.id)
