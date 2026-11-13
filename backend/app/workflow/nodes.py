"""LangGraph node implementations. Each returns a partial state update (JSON-serialisable dict)."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from app.agents import prompts
from app.agents.runner import run_agent, untrusted
from app.agents.schemas import (
    Architecture,
    DebugFix,
    DeveloperOutput,
    DocsOutput,
    FinalReview,
    Plan,
    ProductSpec,
    ProposedChange,
    Review,
    TestPlan,
)
from app.models import AgentStep, FileChange
from app.services import sandbox
from app.services.workspace import UnsafePathError, unified_diff, validate_rel_path
from app.workflow.changes import build_changes, is_test_path, save_changes
from app.workflow.context import Ctx

# Packages preinstalled in the sandbox image (no network inside the sandbox, so nothing else can be installed).
SANDBOX_PACKAGES = {
    "pytest",
    "fastapi",
    "httpx",
    "sqlalchemy",
    "pydantic",
    "pyjwt",
    "bcrypt",
    "email-validator",
    "python-multipart",
    "uvicorn",
}
_PKG_NAME = re.compile(r"^[A-Za-z0-9_.\-]+")


def supervisor_log(ctx: Ctx, decision: str, reason: str) -> None:
    """Record a (rule-based, non-LLM) supervisor routing decision in the execution monitor."""
    now = datetime.now(UTC)
    ctx.db.add(
        AgentStep(
            run_id=ctx.run.id,
            agent="supervisor",
            status="succeeded",
            started_at=now,
            finished_at=now,
            output={"decision": decision, "reason": reason},
        )
    )
    ctx.db.commit()


def _paths(ctx: Ctx, overlay: dict[str, str | None]) -> list[str]:
    paths = set(ctx.ws.list_files()) | {p for p, c in overlay.items() if c is not None}
    return sorted(p for p in paths if overlay.get(p, "") is not None)


def _files_block(ctx: Ctx, paths: list[str], overlay: dict[str, str | None], per_file=8000, total=40000) -> str:
    out, used = [], 0
    for p in paths:
        try:
            content = overlay[p] if p in overlay else ctx.ws.read(p)
        except UnsafePathError:
            continue
        if content is None:
            continue
        chunk = f'<file path="{p}">\n{content[:per_file]}\n</file>'
        if used + len(chunk) > total:
            break
        out.append(chunk)
        used += len(chunk)
    return untrusted("\n".join(out)) if out else "(no files)"


def _diffs_text(changes: list[FileChange], limit=40000) -> str:
    text = "\n".join(f"### {c.action} {c.path}\n{unified_diff(c.path, c.old_content, c.new_content)}" for c in changes)
    return untrusted(text[:limit])


# ---- Phase 1: planning -------------------------------------------------------------------------------------
def product_manager(ctx: Ctx, state: dict) -> dict:
    spec = run_agent(ctx.llm, prompts.PM, f"Requirements:\n{untrusted(state['requirements'])}", ProductSpec)
    return {"spec": spec.model_dump()}


def architect(ctx: Ctx, state: dict) -> dict:
    user = f"Requirements:\n{untrusted(state['requirements'])}\n\nProduct spec:\n{json.dumps(state['spec'])}"
    arch = run_agent(ctx.llm, prompts.ARCHITECT, user, Architecture)
    flagged = []
    for dep in arch.dependencies:
        m = _PKG_NAME.match(dep.strip())
        name = (m.group(0) if m else dep).lower()
        if name not in SANDBOX_PACKAGES:
            flagged.append(dep)
    return {"architecture": arch.model_dump(), "dependencies_needing_approval": flagged}


def task_planner(ctx: Ctx, state: dict) -> dict:
    system = prompts.PLANNER.replace("{max_tasks}", str(ctx.settings.max_tasks))
    plan = run_agent(ctx.llm, system, f"Architecture:\n{json.dumps(state['architecture'])}", Plan)
    tasks = []
    for t in plan.tasks[: ctx.settings.max_tasks]:
        files = []
        for f in t.files:
            try:
                files.append(validate_rel_path(f))
            except UnsafePathError:
                continue
        if files:
            tasks.append({**t.model_dump(), "files": files})
    if not tasks:
        raise ValueError("Planner produced no tasks with valid file paths")
    return {"plan": {"tasks": tasks}}


# ---- Phase 2: development + review -------------------------------------------------------------------------
def developer(ctx: Ctx, state: dict) -> dict:
    revision = state.get("review") if state.get("review", {}).get("verdict") == "request_changes" else None
    overlay: dict[str, str | None] = {}
    old_pending = ctx.changes(status="pending", origin="developer")
    if revision:
        overlay = {c.path: c.new_content for c in old_pending}
        issue_paths = [i["path"] for i in revision["issues"] if i.get("path")]
        tasks = [
            {
                "id": "revise",
                "title": "Address code review findings",
                "files": issue_paths or list(overlay),
                "description": "Fix these review issues: " + json.dumps(revision["issues"]),
            }
        ]
    else:
        tasks = state["plan"]["tasks"]
    net, rejected = [], []
    for task in tasks:
        user = (
            f"Requirements:\n{untrusted(state['requirements'])}\n\n"
            f"Architecture:\n{json.dumps(state['architecture'])}\n\n"
            f"All project paths: {json.dumps(_paths(ctx, overlay))}\n\nTask: {json.dumps(task)}\n\n"
            f"Current content of relevant files:\n{_files_block(ctx, task['files'], overlay)}"
        )
        out = run_agent(ctx.llm, prompts.DEVELOPER, user, DeveloperOutput)
        net, rej = build_changes(ctx, out.changes, overlay, "developer")
        rejected += rej
    if not net:
        raise ValueError("Developer agent produced no file changes")
    for c in old_pending:
        c.status = "superseded"
    ctx.db.commit()
    save_changes(ctx, net, "pending")
    return {"proposed_files": [c["path"] for c in net], "policy_rejections": rejected}


def reviewer(ctx: Ctx, state: dict) -> dict:
    pending = ctx.changes(status="pending", origin="developer")
    user = (
        f"Acceptance criteria:\n{json.dumps(state['spec']['acceptance_criteria'])}\n\n"
        f"Proposed diffs:\n{_diffs_text(pending)}"
    )
    review = run_agent(ctx.llm, prompts.REVIEWER, user, Review)
    return {"review": review.model_dump(), "review_round": state.get("review_round", 0) + 1}


def route_after_review(ctx: Ctx, state: dict) -> str:
    review = state["review"]
    serious = any(i["severity"] in ("blocker", "major") for i in review["issues"])
    if review["verdict"] == "request_changes" and serious and state["review_round"] < 2:
        supervisor_log(ctx, "revise", "Reviewer requested changes; sending back to Developer (one revision allowed)")
        return "developer"
    supervisor_log(ctx, "await_change_approval", "Review complete; waiting for human approval of file changes")
    return "end"


# ---- Phase 3: testing, repair, final review, docs ------------------------------------------------------------
def test_generator(ctx: Ctx, state: dict) -> dict:
    sources = [p for p in ctx.ws.list_files() if p.endswith(".py") and not is_test_path(p)]
    if not sources:
        raise ValueError("No approved Python source files to test")
    user = (
        f"Acceptance criteria:\n{json.dumps(state['spec']['acceptance_criteria'])}\n\n"
        f"API endpoints:\n{json.dumps(state['architecture']['api_endpoints'])}\n\n"
        f"Source files:\n{_files_block(ctx, sources, {})}"
    )
    plan = run_agent(ctx.llm, prompts.TESTER, user, TestPlan)
    proposals = [
        ProposedChange(path=f.path, action="create", content=f.content, rationale="generated test")
        for f in plan.files
        if _safe_test_path(f.path)
    ]
    overlay: dict[str, str | None] = {}
    net, _ = build_changes(ctx, proposals, overlay, "tester", allow_delete=False)
    if not net:
        raise ValueError("Testing agent produced no valid test files")
    for c in net:
        ctx.ws.write(c["path"], c["new_content"])
    save_changes(ctx, net, "applied")
    return {"generated_tests": [c["path"] for c in net]}


def _safe_test_path(path: str) -> bool:
    try:
        return is_test_path(validate_rel_path(path))
    except UnsafePathError:
        return False


def run_sandbox_tests(ctx: Ctx, state: dict) -> dict:
    from app.models import TestRun

    result = sandbox.run_tests(ctx.ws)
    ctx.db.add(
        TestRun(
            run_id=ctx.run.id,
            attempt=ctx.run.repair_attempts,
            status=result.status,
            exit_code=result.exit_code,
            output=result.output,
            duration_seconds=result.duration_seconds,
        )
    )
    ctx.db.commit()
    return {"test_status": result.status}


def route_after_tests(ctx: Ctx, state: dict) -> str:
    status = state["test_status"]
    if status in ("failed", "error") and ctx.run.repair_attempts < ctx.settings.max_repair_attempts:
        supervisor_log(
            ctx,
            "repair",
            f"Tests {status}; repair attempt {ctx.run.repair_attempts + 1}/{ctx.settings.max_repair_attempts}",
        )
        return "debugger"
    reasons = {"passed": "Tests passed", "unavailable": "Sandbox unavailable; tests were not run; no repair attempted"}
    reason = reasons.get(status, f"Tests {status} and repair budget exhausted")
    supervisor_log(ctx, "final_review", reason)
    return "final_review"


def debugger(ctx: Ctx, state: dict) -> dict:
    ctx.run.repair_attempts += 1
    ctx.db.commit()
    last = ctx.test_runs()[-1]
    mentioned = [p for p in ctx.ws.list_files() if p in last.output]
    candidates = mentioned + [p for p in ctx.ws.list_files() if p not in mentioned]
    user = (
        f"Failing test output:\n{untrusted(last.output[-8000:])}\n\nProject files:\n{_files_block(ctx, candidates, {})}"
    )
    fix = run_agent(ctx.llm, prompts.DEBUGGER, user, DebugFix)
    overlay: dict[str, str | None] = {}
    net, rejected = build_changes(ctx, fix.changes[:5], overlay, "debugger", allow_delete=False)
    for c in net:
        ctx.ws.write(c["path"], c["new_content"])
    save_changes(ctx, net, "applied")
    return {"last_diagnosis": fix.diagnosis, "repair_files": [c["path"] for c in net], "policy_rejections": rejected}


def final_review(ctx: Ctx, state: dict) -> dict:
    applied = ctx.changes(status="applied")
    runs = ctx.test_runs()
    latest = runs[-1].status if runs else "not_run"
    user = (
        f"Acceptance criteria:\n{json.dumps(state['spec']['acceptance_criteria'])}\n\n"
        f"MEASURED test status: {latest} (repair attempts used: {ctx.run.repair_attempts})\n\n"
        f"Applied changes:\n{_diffs_text(applied)}"
    )
    review = run_agent(ctx.llm, prompts.FINAL_REVIEW, user, FinalReview)
    return {"final_review": review.model_dump(), "final_test_status": latest}


def documentation(ctx: Ctx, state: dict) -> dict:
    files = [p for p in ctx.ws.list_files() if p not in ("README.md", "docs/API.md")]
    endpoints = json.dumps(state["architecture"]["api_endpoints"])
    user = (
        f"Product summary: {state['spec']['summary']}\n\nEndpoints:\n{endpoints}\n\n"
        f"Files:\n{_files_block(ctx, files, {}, per_file=3000, total=30000)}"
    )
    docs = run_agent(ctx.llm, prompts.DOCS, user, DocsOutput)
    proposals = [
        ProposedChange(path=p, action="create", content=c, rationale="generated documentation")
        for p, c in (("README.md", docs.readme), ("docs/API.md", docs.api_docs))
    ]
    net, _ = build_changes(ctx, proposals, {}, "documentation", allow_delete=False)
    save_changes(ctx, net, "pending")
    return {"docs_files": [c["path"] for c in net]}
