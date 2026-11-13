from __future__ import annotations

import shutil

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user, owned_project
from app.errors import AppError
from app.models import Project, User
from app.schemas import ProjectCreate, ProjectOut, SearchHit
from app.services import search as search_service
from app.services.workspace import UnsafePathError, Workspace

router = APIRouter(prefix="/projects", tags=["projects"])


def _out(p: Project) -> ProjectOut:
    out = ProjectOut.model_validate(p)
    out.latest_run_status = p.runs[0].status if p.runs else None
    return out


@router.get("", response_model=list[ProjectOut])
def list_projects(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Project).where(Project.owner_id == user.id).order_by(Project.id.desc())).all()
    return [_out(p) for p in rows]


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = Project(owner_id=user.id, name=body.name.strip(), requirements=body.requirements.strip())
    db.add(project)
    db.commit()
    Workspace(project.id).ensure()
    return _out(project)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project: Project = Depends(owned_project)):
    return _out(project)


@router.delete("/{project_id}", status_code=204)
def delete_project(project: Project = Depends(owned_project), db: Session = Depends(get_db)):
    shutil.rmtree(Workspace(project.id).root, ignore_errors=True)
    db.delete(project)
    db.commit()
    return Response(status_code=204)


@router.get("/{project_id}/files", response_model=list[str])
def list_files(project: Project = Depends(owned_project)):
    return Workspace(project.id).list_files()


@router.get("/{project_id}/files/content")
def file_content(path: str = Query(min_length=1), project: Project = Depends(owned_project)):
    try:
        content = Workspace(project.id).read(path)
    except UnsafePathError:
        raise AppError(400, "invalid_path", "Invalid file path") from None
    if content is None:
        raise AppError(404, "not_found", "File not found")
    return {"path": path, "content": content}


@router.get("/{project_id}/search", response_model=list[SearchHit])
def search_files(q: str = Query(min_length=2, max_length=100), project: Project = Depends(owned_project)):
    return search_service.search(Workspace(project.id), q)


@router.get("/{project_id}/outline")
def code_outline(project: Project = Depends(owned_project)):
    return search_service.outline(Workspace(project.id))


@router.get("/{project_id}/download")
def download(project: Project = Depends(owned_project)):
    data = Workspace(project.id).zip_bytes()
    return Response(
        data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="project-{project.id}.zip"'},
    )
