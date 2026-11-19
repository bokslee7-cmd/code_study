from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Credentials(BaseModel):
    """Request body of register and login. Format rules live in UserService."""

    email: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    skill_level: str | None


class RegisterResponse(BaseModel):
    user: UserResponse


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class LoginResponse(TokenResponse):
    user: UserResponse
