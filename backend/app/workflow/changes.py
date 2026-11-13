"""Create, validate and apply FileChange records."""

from __future__ import annotations

import logging

from app.models import FileChange
from app.services.workspace import UnsafePathError, Workspace, validate_rel_path
from app.workflow.context import Ctx

log = logging.getLogger("devteam.changes")


def is_test_path(path: str) -> bool:
    return path.endswith(".py") and (path.startswith("tests/") or path.startswith("backend/tests/"))


def build_changes(
    ctx: Ctx, proposals: list, overlay: dict[str, str | None], origin: str, allow_delete: bool = True
) -> tuple[list[dict], list[str]]:
    """Fold proposals into one net change per path against the workspace.

    `overlay` maps path -> staged content (None = deleted) and is updated in place.
    Returns (net changes, policy rejections).
    """
    rejected: list[str] = []
    rationale: dict[str, list[str]] = {}
    for p in proposals:
        try:
            path = validate_rel_path(p.path)
        except UnsafePathError as exc:
            rejected.append(str(exc))
            continue
        exists = overlay[path] is not None if path in overlay else ctx.ws.exists(path)
        if p.action == "delete":
            if not allow_delete or not exists:
                rejected.append(f"delete not allowed/needed: {path}")
                continue
            overlay[path] = None
        else:
            if p.content is None or len(p.content.encode()) > ctx.settings.max_file_bytes:
                rejected.append(f"missing or oversized content: {path}")
                continue
            overlay[path] = p.content
        rationale.setdefault(path, []).append(p.rationale)
    if len(overlay) > ctx.settings.max_files_per_run:
        raise ValueError(f"too many files changed (>{ctx.settings.max_files_per_run})")
    net: list[dict] = []
    for path, final in overlay.items():
        original = ctx.ws.read(path)
        if final == original:
            continue
        action = "create" if original is None else ("delete" if final is None else "modify")
        net.append(
            {
                "path": path,
                "action": action,
                "old_content": original,
                "new_content": final,
                "rationale": " ".join(r for r in rationale.get(path, []) if r)[:1000],
                "origin": origin,
            }
        )
    return net, rejected


def save_changes(ctx: Ctx, net: list[dict], status: str) -> list[FileChange]:
    rows = [FileChange(run_id=ctx.run.id, status=status, **c) for c in net]
    ctx.db.add_all(rows)
    ctx.db.commit()
    return rows


def apply_change(ws: Workspace, ch: FileChange) -> str:
    """Write one approved change to the workspace. Returns the resulting status."""
    current = ws.read(ch.path)
    if current != ch.old_content:  # file moved on since the proposal: never overwrite silently
        return "conflict"
    if ch.action == "delete":
        ws.delete(ch.path)
    else:
        ws.write(ch.path, ch.new_content or "")
    return "applied"
