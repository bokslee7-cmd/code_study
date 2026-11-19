from typing import Literal

from fastapi import APIRouter

from src.api.exceptions import ConflictException, ForbiddenException, NotFoundException

router = APIRouter(prefix="/test-errors", tags=["test-errors"])


@router.get("")
async def trigger_error(
    type: Literal["notfound", "forbidden", "conflict"] | None = None,
) -> dict[str, str]:
    """Dev-only endpoint to check the error response format for each exception."""
    if type == "notfound":
        raise NotFoundException()
    if type == "forbidden":
        raise ForbiddenException()
    if type == "conflict":
        raise ConflictException()
    return {"status": "ok"}
