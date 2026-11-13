import pytest

from app.config import get_settings
from app.services import sandbox
from app.services.workspace import UnsafePathError, Workspace, validate_rel_path


@pytest.mark.parametrize(
    "bad",
    [
        "../x",
        "a/../../x",
        "/etc/passwd",
        "a\\b",
        ".env",
        "a/.env.local",
        ".git/config",
        "node_modules/x",
        "a//b",
        "",
        "a b",
        "a/./b",
        "x\x00y",
    ],
)
def test_bad_paths_rejected(bad):
    with pytest.raises(UnsafePathError):
        validate_rel_path(bad)


def test_good_paths():
    assert validate_rel_path("backend/app/main.py") == "backend/app/main.py"


def test_workspace_blocks_symlink_escape(tmp_path):
    ws = Workspace(999)
    ws.ensure()
    (ws.root / "link").symlink_to(tmp_path)
    with pytest.raises(UnsafePathError):
        ws.write("link/pwned.txt", "x")
    assert not (tmp_path / "pwned.txt").exists()


def test_docker_command_is_restricted():
    cmd = sandbox.build_docker_command("/host/dir", "n", get_settings())
    joined = " ".join(cmd)
    assert "--network none" in joined and "--cap-drop ALL" in joined and "--read-only" in joined
    assert "--user 65534:65534" in joined and "--memory" in joined and "--pids-limit" in joined
    assert "docker.sock" not in joined and "--privileged" not in joined
    assert cmd.count("-e") == 2 and "/host/dir:/workspace:ro" in joined  # only fixed env vars, read-only mount


def test_classify_never_reports_false_pass():
    assert sandbox.classify(0, "3 passed in 0.1s") == "passed"
    assert sandbox.classify(0, "no tests ran") == "error"
    assert sandbox.classify(1, "1 failed") == "failed"
    assert sandbox.classify(5, "") == "error"
    assert sandbox.classify(2, "3 passed") == "error"


def test_unavailable_when_no_docker(monkeypatch):
    monkeypatch.setattr(sandbox, "docker_available", lambda: False)
    ws = Workspace(998)
    ws.ensure()
    r = sandbox.run_tests(ws)
    assert r.status == "unavailable" and r.exit_code is None


def test_migrations_upgrade_cleanly(tmp_path, monkeypatch):
    import subprocess
    import sys

    env = {"DATABASE_URL": f"sqlite:///{tmp_path}/m.db", "PATH": "/usr/bin:/bin", "SECRET_KEY": "x"}
    r = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    import sqlite3

    tables = {t[0] for t in sqlite3.connect(tmp_path / "m.db").execute("select name from sqlite_master")}
    assert {"users", "projects", "runs", "agent_steps", "file_changes", "test_runs"} <= tables
