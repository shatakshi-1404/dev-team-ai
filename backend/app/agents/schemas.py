"""Structured outputs of every agent (validated with Pydantic v2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class UserStory(BaseModel):
    as_a: str
    i_want: str
    so_that: str


class ProductSpec(BaseModel):
    summary: str
    user_stories: list[UserStory] = Field(min_length=1)
    acceptance_criteria: list[str] = Field(min_length=1)
    non_goals: list[str] = []


class Component(BaseModel):
    name: str
    responsibility: str


class Endpoint(BaseModel):
    method: str
    path: str
    description: str


class DataModel(BaseModel):
    name: str
    fields: list[str]


class Architecture(BaseModel):
    overview: str
    components: list[Component]
    api_endpoints: list[Endpoint]
    data_models: list[DataModel]
    dependencies: list[str] = []
    file_layout: list[str]


class Task(BaseModel):
    id: str
    title: str
    description: str
    files: list[str] = Field(min_length=1)


class Plan(BaseModel):
    tasks: list[Task] = Field(min_length=1)


class ProposedChange(BaseModel):
    path: str
    action: Literal["create", "modify", "delete"]
    content: str | None = None
    rationale: str = ""


class DeveloperOutput(BaseModel):
    changes: list[ProposedChange]


class ReviewIssue(BaseModel):
    severity: Literal["blocker", "major", "minor"]
    path: str = ""
    message: str


class Review(BaseModel):
    verdict: Literal["approve", "request_changes"]
    summary: str
    issues: list[ReviewIssue] = []


class TestFile(BaseModel):
    __test__ = False
    path: str
    content: str


class TestPlan(BaseModel):
    __test__ = False
    files: list[TestFile] = Field(min_length=1)
    notes: str = ""


class DebugFix(BaseModel):
    diagnosis: str
    changes: list[ProposedChange]


class FinalReview(BaseModel):
    verdict: Literal["approve", "request_changes"]
    summary: str
    risks: list[str] = []


class DocsOutput(BaseModel):
    readme: str
    api_docs: str
