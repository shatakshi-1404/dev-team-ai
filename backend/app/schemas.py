from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v: str) -> str:
        if len(v.encode()) > 72:
            raise ValueError("password must be at most 72 bytes")
        return v


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    requirements: str = Field(min_length=20, max_length=8000)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    requirements: str
    created_at: datetime
    latest_run_status: str | None = None


class StepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    agent: str
    status: str
    output: Any | None
    error: str | None
    started_at: datetime
    finished_at: datetime | None


class TestRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    attempt: int
    status: str
    exit_code: int | None
    output: str
    duration_seconds: float
    created_at: datetime


class ChangeOut(BaseModel):
    id: int
    path: str
    action: str
    status: str
    origin: str
    rationale: str
    diff: str


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    status: str
    state: dict
    repair_attempts: int
    error: str | None
    created_at: datetime
    updated_at: datetime
    steps: list[StepOut]
    test_runs: list[TestRunOut]


class SearchHit(BaseModel):
    path: str
    line: int
    text: str
