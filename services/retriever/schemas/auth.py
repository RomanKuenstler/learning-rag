from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AuthTokenPayload(BaseModel):
    token: str
    expires_at: datetime
    max_expires_at: datetime


class CurrentUserRead(BaseModel):
    id: int
    username: str
    displayname: str
    role: str
    status: str
    force_password_change: bool


class AuthLoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class AuthLoginResponse(BaseModel):
    token: str
    expires_at: datetime
    max_expires_at: datetime
    user: CurrentUserRead


class PasswordChangeRequest(BaseModel):
    current_password: str | None = None
    new_password: str = Field(min_length=1)
    confirm_password: str = Field(min_length=1)


class AuthMeResponse(BaseModel):
    user: CurrentUserRead
    expires_at: datetime
    max_expires_at: datetime


class PasswordChangeResponse(AuthLoginResponse):
    pass


class AdminUserCreateRequest(BaseModel):
    username: str = Field(min_length=1)
    displayname: str = Field(min_length=1)
    role: str = Field(pattern="^(user|admin|student)$")


class AdminUserUpdateRequest(BaseModel):
    displayname: str | None = Field(default=None, min_length=1)
    role: str | None = Field(default=None, pattern="^(user|admin|student)$")
    status: str | None = Field(default=None, pattern="^(active|inactive)$")
    force_password_change: bool | None = None


class AdminUserRead(CurrentUserRead):
    created_at: datetime
    updated_at: datetime
