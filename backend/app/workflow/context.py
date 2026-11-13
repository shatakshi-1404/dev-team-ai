from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.llm.provider import LLMProvider
from app.models import FileChange, Run, TestRun
from app.services.workspace import Workspace


@dataclass
class Ctx:
    db: Session
    run: Run
    llm: LLMProvider
    ws: Workspace
    settings: Settings

    # Always query: relationship collections on `run` are cached and go stale as nodes add rows.
    def changes(self, **filters) -> list[FileChange]:
        q = select(FileChange).where(FileChange.run_id == self.run.id).order_by(FileChange.id)
        for k, v in filters.items():
            q = q.where(getattr(FileChange, k) == v)
        return list(self.db.scalars(q))

    def test_runs(self) -> list[TestRun]:
        return list(self.db.scalars(select(TestRun).where(TestRun.run_id == self.run.id).order_by(TestRun.id)))
