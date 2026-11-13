"""Run tests for generated code inside a restricted Docker container.

Generated code is NEVER executed on the host. If Docker is unavailable the result is
status="unavailable" -- we never fabricate a pass.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings, get_settings
from app.services.workspace import Workspace

log = logging.getLogger("devteam.sandbox")

# The agents cannot choose the command; only this fixed argv is ever run.
TEST_COMMAND = ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--maxfail=5", "--tb=short"]
MAX_OUTPUT_CHARS = 20_000
_PASSED_RE = re.compile(r"(\d+) passed")


@dataclass
class SandboxResult:
    status: str  # passed | failed | error | unavailable
    exit_code: int | None
    output: str
    duration_seconds: float


def docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=8).returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def _host_path(path: Path, s: Settings) -> str:
    """Translate a backend-visible path to the host path when the backend runs inside Docker."""
    if s.workspace_host_path:
        rel = path.resolve().relative_to(s.workspace_root.resolve())
        return str(Path(s.workspace_host_path) / rel)
    return str(path.resolve())


def build_docker_command(host_dir: str, name: str, s: Settings) -> list[str]:
    cmd = [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        "--user",
        "65534:65534",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "--memory",
        s.sandbox_memory,
        "--memory-swap",
        s.sandbox_memory,
        "--cpus",
        s.sandbox_cpus,
        "--pids-limit",
        str(s.sandbox_pids_limit),
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        "-e",
        "HOME=/tmp",
        "-v",
        f"{host_dir}:/workspace:ro",
        "-w",
        "/workspace",
    ]
    if not s.sandbox_network_enabled:
        cmd += ["--network", "none"]
    # No docker socket, no host env passthrough, no secrets: only the fixed env above.
    return cmd + [s.sandbox_image, *TEST_COMMAND]


def classify(exit_code: int, output: str) -> str:
    if exit_code == 0:
        m = _PASSED_RE.search(output)
        return "passed" if m and int(m.group(1)) > 0 else "error"  # 0 passed tests is not a pass
    return "failed" if exit_code == 1 else "error"  # 5 = no tests collected, others = infra/usage errors


def run_tests(workspace: Workspace) -> SandboxResult:
    s = get_settings()
    if not docker_available():
        return SandboxResult("unavailable", None, "Docker is not available; tests were NOT run.", 0.0)
    snap = (s.workspace_root / "_sandbox" / uuid.uuid4().hex).resolve()
    name = f"devteam-sbx-{uuid.uuid4().hex[:12]}"
    start = time.monotonic()
    try:
        workspace.snapshot_to(snap)
        cmd = build_docker_command(_host_path(snap, s), name, s)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=s.sandbox_timeout_seconds + 15)
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", name], capture_output=True)
            return SandboxResult(
                "error", None, f"Timed out after {s.sandbox_timeout_seconds}s.", time.monotonic() - start
            )
        out = (proc.stdout + proc.stderr)[-MAX_OUTPUT_CHARS:]
        return SandboxResult(classify(proc.returncode, out), proc.returncode, out, time.monotonic() - start)
    except Exception as exc:  # infrastructure failure: report honestly as error
        log.exception("sandbox failure")
        return SandboxResult("error", None, f"Sandbox failure: {type(exc).__name__}", time.monotonic() - start)
    finally:
        shutil.rmtree(snap, ignore_errors=True)
