from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import current_user, owned_project, owned_run
from app.errors import AppError
from app.models import FileChange, Project, Run, User
from app.schemas import ChangeOut, RunOut
from app.services.workspace import Workspace, unified_diff
from app.workflow.changes import apply_change
from app.workflow.runner import execute_phase

router = APIRouter(tags=["runs"])
TERMINAL = {"completed", "rejected", "failed"}


class PlanApproval(BaseModel):
    confirm_dependencies: bool = False


def _require(run: Run, status: str) -> None:
    if run.status != status:
        raise AppError(409, "invalid_state", f"Run is '{run.status}', expected '{status}'")


def _change_out(c: FileChange) -> ChangeOut:
    return ChangeOut(
        id=c.id,
        path=c.path,
        action=c.action,
        status=c.status,
        origin=c.origin,
        rationale=c.rationale,
        diff=unified_diff(c.path, c.old_content, c.new_content),
    )


@router.get("/system/status")
def system_status():
    from app.services.sandbox import docker_available

    s = get_settings()
    return {
        "llm_configured": s.llm_configured,
        "llm_provider": s.llm_provider,
        "llm_model": s.groq_model,
        "docker_available": docker_available(),
        "max_repair_attempts": s.max_repair_attempts,
        "message": None
        if s.llm_configured
        else "GROQ_API_KEY is not configured. Set it in backend/.env to enable the agents.",
    }


@router.get("/projects/{project_id}/runs", response_model=list[RunOut])
def list_runs(project: Project = Depends(owned_project)):
    return project.runs


@router.post("/projects/{project_id}/runs", response_model=RunOut, status_code=201)
def start_run(bg: BackgroundTasks, project: Project = Depends(owned_project), db: Session = Depends(get_db)):
    if not get_settings().llm_configured:
        raise AppError(409, "llm_not_configured", "GROQ_API_KEY is not set. Configure it in backend/.env first.")
    if any(r.status not in TERMINAL for r in project.runs):
        raise AppError(409, "run_in_progress", "Finish or reject the current run before starting another")
    run = Run(project_id=project.id, status="running_planning", state={})
    db.add(run)
    db.commit()
    bg.add_task(execute_phase, run.id, "planning")
    return run


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run: Run = Depends(owned_run)):
    return run


@router.post("/runs/{run_id}/approve-plan", response_model=RunOut)
def approve_plan(body: PlanApproval, bg: BackgroundTasks, run: Run = Depends(owned_run), db: Session = Depends(get_db)):
    _require(run, "awaiting_plan_approval")
    if run.state.get("dependencies_needing_approval") and not body.confirm_dependencies:
        raise AppError(
            422,
            "dependencies_unconfirmed",
            "The plan lists dependencies outside the sandbox image; confirm them explicitly",
        )
    run.status = "running_development"
    db.commit()
    bg.add_task(execute_phase, run.id, "development")
    return run


@router.post("/runs/{run_id}/reject-plan", response_model=RunOut)
def reject_plan(run: Run = Depends(owned_run), db: Session = Depends(get_db)):
    _require(run, "awaiting_plan_approval")
    run.status = "rejected"
    db.commit()
    return run


@router.get("/runs/{run_id}/changes", response_model=list[ChangeOut])
def list_changes(run: Run = Depends(owned_run)):
    return [_change_out(c) for c in run.changes if c.status != "superseded"]


def _decide(change_id: int, status: str, user: User, db: Session) -> ChangeOut:
    change = db.get(FileChange, change_id)
    if not change or change.run.project.owner_id != user.id:
        raise AppError(404, "not_found", "Change not found")
    allowed = {"awaiting_change_approval": "developer", "awaiting_final_approval": "documentation"}
    if allowed.get(change.run.status) != change.origin or change.status not in ("pending", "approved", "rejected"):
        raise AppError(409, "invalid_state", "This change can't be decided right now")
    change.status = status
    db.commit()
    return _change_out(change)


@router.post("/changes/{change_id}/approve", response_model=ChangeOut)
def approve_change(change_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _decide(change_id, "approved", user, db)


@router.post("/changes/{change_id}/reject", response_model=ChangeOut)
def reject_change(change_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _decide(change_id, "rejected", user, db)


@router.post("/runs/{run_id}/apply-changes", response_model=RunOut)
def apply_changes(bg: BackgroundTasks, run: Run = Depends(owned_run), db: Session = Depends(get_db)):
    _require(run, "awaiting_change_approval")
    dev = [c for c in run.changes if c.origin == "developer" and c.status in ("pending", "approved", "rejected")]
    if any(c.status == "pending" for c in dev):
        raise AppError(409, "undecided_changes", "Approve or reject every proposed change first")
    approved = [c for c in dev if c.status == "approved"]
    if not approved:
        raise AppError(409, "nothing_approved", "No changes approved; reject the run instead")
    ws = Workspace(run.project_id)
    for c in approved:
        c.status = apply_change(ws, c)
    run.status = "running_testing"
    db.commit()
    bg.add_task(execute_phase, run.id, "testing")
    return run


@router.post("/runs/{run_id}/approve-final", response_model=RunOut)
def approve_final(run: Run = Depends(owned_run), db: Session = Depends(get_db)):
    _require(run, "awaiting_final_approval")
    ws = Workspace(run.project_id)
    for c in run.changes:
        if c.origin == "documentation" and c.status in ("pending", "approved"):
            c.status = apply_change(ws, c)
    run.status = "completed"
    db.commit()
    return run


@router.post("/runs/{run_id}/reject-final", response_model=RunOut)
def reject_final(run: Run = Depends(owned_run), db: Session = Depends(get_db)):
    _require(run, "awaiting_final_approval")
    for c in run.changes:
        if c.origin == "documentation" and c.status == "pending":
            c.status = "rejected"
    run.status = "rejected"
    db.commit()
    return run


@router.post("/runs/{run_id}/retry", response_model=RunOut)
def retry(bg: BackgroundTasks, run: Run = Depends(owned_run), db: Session = Depends(get_db)):
    _require(run, "failed")
    phase = run.state.get("last_phase")
    if phase not in ("planning", "development", "testing"):
        raise AppError(409, "not_retryable", "This run cannot be retried")
    if not get_settings().llm_configured:
        raise AppError(409, "llm_not_configured", "GROQ_API_KEY is not set. Configure it in backend/.env first.")
    run.status = {"planning": "running_planning", "development": "running_development", "testing": "running_testing"}[
        phase
    ]
    run.error = None
    db.commit()
    bg.add_task(execute_phase, run.id, phase)
    return run
