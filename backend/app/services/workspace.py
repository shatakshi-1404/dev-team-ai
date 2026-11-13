"""Project workspaces on disk, with strict path validation (no traversal, no symlinks, no secrets)."""

from __future__ import annotations

import difflib
import io
import re
import shutil
import zipfile
from pathlib import Path

from app.config import get_settings

SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9_.\-/]+$")
DENIED_SEGMENTS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
MAX_PATH_LEN = 200


class UnsafePathError(ValueError):
    pass


def validate_rel_path(path: str) -> str:
    """Return a normalised relative POSIX path or raise UnsafePathError."""
    if not isinstance(path, str) or not path or len(path) > MAX_PATH_LEN:
        raise UnsafePathError("empty or too long path")
    if path.startswith("/") or "\\" in path or "\x00" in path or not SAFE_PATH_RE.match(path):
        raise UnsafePathError(f"disallowed path: {path!r}")
    parts = path.split("/")
    for part in parts:
        if part in ("", ".", "..") or part in DENIED_SEGMENTS or part.startswith(".env"):
            raise UnsafePathError(f"disallowed path segment in {path!r}")
    return "/".join(parts)


class Workspace:
    def __init__(self, project_id: int):
        self.root = (get_settings().workspace_root / str(project_id)).resolve()

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, rel: str) -> Path:
        rel = validate_rel_path(rel)
        target = self.root.joinpath(rel)
        # reject symlinks anywhere along the path, then confirm containment
        cur = self.root
        for part in rel.split("/"):
            cur = cur / part
            if cur.is_symlink():
                raise UnsafePathError(f"symlink not allowed: {rel}")
        if self.root not in target.resolve().parents:
            raise UnsafePathError(f"path escapes workspace: {rel}")
        return target

    def exists(self, rel: str) -> bool:
        return self.resolve(rel).is_file()

    def read(self, rel: str) -> str | None:
        p = self.resolve(rel)
        if not p.is_file():
            return None
        return p.read_text(encoding="utf-8", errors="replace")

    def write(self, rel: str, content: str) -> None:
        if len(content.encode()) > get_settings().max_file_bytes:
            raise UnsafePathError(f"file too large: {rel}")
        p = self.resolve(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def delete(self, rel: str) -> None:
        p = self.resolve(rel)
        if p.is_file():
            p.unlink()

    def list_files(self) -> list[str]:
        if not self.root.exists():
            return []
        out: list[str] = []
        for p in sorted(self.root.rglob("*")):
            if p.is_symlink() or not p.is_file():
                continue
            rel = p.relative_to(self.root).as_posix()
            try:
                validate_rel_path(rel)
            except UnsafePathError:
                continue
            out.append(rel)
        return out

    def snapshot_to(self, dest: Path) -> None:
        """Copy validated files into dest (used for sandbox runs)."""
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        for rel in self.list_files():
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.root / rel, target)

    def zip_bytes(self) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for rel in self.list_files():
                z.write(self.root / rel, rel)
        return buf.getvalue()


def unified_diff(path: str, old: str | None, new: str | None) -> str:
    a = (old or "").splitlines(keepends=True)
    b = (new or "").splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            a,
            b,
            fromfile=f"a/{path}" if old is not None else "/dev/null",
            tofile=f"b/{path}" if new is not None else "/dev/null",
        )
    )
