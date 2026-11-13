from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import Project, Run, User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    user_id = decode_access_token(creds.credentials) if creds else None
    user = db.get(User, user_id) if user_id else None
    if not user:
        raise AppError(401, "unauthorized", "Missing or invalid credentials")
    return user


def owned_project(project_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    # 404 (not 403) so project ids of other users are not revealed
    if not project or project.owner_id != user.id:
        raise AppError(404, "not_found", "Project not found")
    return project


def owned_run(run_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Run:
    run = db.get(Run, run_id)
    if not run or run.project.owner_id != user.id:
        raise AppError(404, "not_found", "Run not found")
    return run
