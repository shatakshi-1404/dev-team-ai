"""LangGraph definitions. The Supervisor is the graph itself: explicit nodes + conditional routing,
with every routing decision logged to the execution monitor."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.models import AgentStep
from app.workflow import nodes
from app.workflow.context import Ctx


class State(TypedDict, total=False):
    requirements: str
    spec: dict
    architecture: dict
    dependencies_needing_approval: list
    plan: dict
    review: dict
    review_round: int
    proposed_files: list
    policy_rejections: list
    generated_tests: list
    test_status: str
    last_diagnosis: str
    repair_files: list
    final_review: dict
    final_test_status: str
    docs_files: list


def _instrument(ctx: Ctx, agent: str, fn: Callable[[Ctx, dict], dict]) -> Callable[[dict], dict]:
    """Record every agent execution (start, output, failure) and persist state after each node."""

    def node(state: dict) -> dict:
        step = AgentStep(run_id=ctx.run.id, agent=agent, status="running")
        ctx.db.add(step)
        ctx.db.commit()
        try:
            update = fn(ctx, state)
        except Exception as exc:
            step.status, step.error = "failed", f"{type(exc).__name__}: {str(exc)[:1500]}"
            step.finished_at = datetime.now(UTC)
            ctx.db.commit()
            raise
        step.status, step.output = "succeeded", update
        step.finished_at = datetime.now(UTC)
        ctx.run.state = {**ctx.run.state, **update}
        ctx.db.commit()
        return update

    return node


def _route(ctx: Ctx, fn: Callable[[Ctx, dict], str]) -> Callable[[dict], str]:
    return lambda state: fn(ctx, state)


def build_graph(ctx: Ctx, phase: str) -> Any:
    g = StateGraph(State)
    if phase == "planning":
        for name, fn in (
            ("product_manager", nodes.product_manager),
            ("architect", nodes.architect),
            ("task_planner", nodes.task_planner),
        ):
            g.add_node(name, _instrument(ctx, name, fn))
        g.add_edge(START, "product_manager")
        g.add_edge("product_manager", "architect")
        g.add_edge("architect", "task_planner")
        g.add_edge("task_planner", END)
    elif phase == "development":
        g.add_node("developer", _instrument(ctx, "developer", nodes.developer))
        g.add_node("reviewer", _instrument(ctx, "reviewer", nodes.reviewer))
        g.add_edge(START, "developer")
        g.add_edge("developer", "reviewer")
        g.add_conditional_edges(
            "reviewer", _route(ctx, nodes.route_after_review), {"developer": "developer", "end": END}
        )
    elif phase == "testing":
        g.add_node("testing", _instrument(ctx, "testing", nodes.test_generator))
        g.add_node("sandbox", _instrument(ctx, "sandbox", nodes.run_sandbox_tests))
        g.add_node("debugger", _instrument(ctx, "debugger", nodes.debugger))
        g.add_node("final_review", _instrument(ctx, "final_review", nodes.final_review))
        g.add_node("documentation", _instrument(ctx, "documentation", nodes.documentation))
        g.add_edge(START, "testing")
        g.add_edge("testing", "sandbox")
        g.add_conditional_edges(
            "sandbox", _route(ctx, nodes.route_after_tests), {"debugger": "debugger", "final_review": "final_review"}
        )
        g.add_edge("debugger", "sandbox")
        g.add_edge("final_review", "documentation")
        g.add_edge("documentation", END)
    else:
        raise ValueError(f"unknown phase {phase}")
    return g.compile()
