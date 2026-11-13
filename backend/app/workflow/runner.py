"""Executes one workflow phase in the background and manages run status transitions."""

from __future__ import annotations

import logging

from app import db as dbmod
from app.agents.runner import AgentOutputError
from app.config import get_settings
from app.llm import provider as llm_provider
from app.models import Run
from app.services.workspace import Workspace
from app.workflow.context import Ctx
from app.workflow.graphs import build_graph

log = logging.getLogger("devteam.runner")

PHASES = {  # phase -> (status while running, status when finished)
    "planning": ("running_planning", "awaiting_plan_approval"),
    "development": ("running_development", "awaiting_change_approval"),
    "testing": ("running_testing", "awaiting_final_approval"),
}
ACTIVE_STATUSES = {"running_planning", "running_development", "running_testing"}


def execute_phase(run_id: int, phase: str) -> None:
    running, done = PHASES[phase]
    db = dbmod.SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run is None:
            return
        run.status, run.error = running, None
        run.state = {**run.state, "last_phase": phase}
        db.commit()
        ws = Workspace(run.project_id)
        ws.ensure()
        try:
            ctx = Ctx(db=db, run=run, llm=llm_provider.get_provider(), ws=ws, settings=get_settings())
            state = {**run.state, "requirements": run.project.requirements}
            build_graph(ctx, phase).invoke(state)
            run.status = done
        except llm_provider.LLMNotConfigured as exc:
            run.status, run.error = "failed", str(exc)
        except AgentOutputError as exc:
            run.status, run.error = "failed", str(exc)
        except Exception as exc:  # keep detail in logs, short message for the UI
            log.exception("workflow phase failed", extra={"run_id": run_id, "phase": phase})
            run.status, run.error = "failed", f"{type(exc).__name__}: {str(exc)[:300]}"
        db.commit()
        log.info("phase finished", extra={"run_id": run_id, "phase": phase, "status": run.status})
    finally:
        db.close()
