"""End-to-end workflow tests. The LLM and the Docker sandbox are replaced by test doubles ONLY here;
the application code never fabricates agent output or test results."""

import pytest

from app.services import sandbox
from tests.conftest import register
from tests.fake_llm import FakeLLM


def sbx(*statuses):
    seq = list(statuses)

    def fake(ws):
        status = seq.pop(0) if len(seq) > 1 else seq[0]
        code = {"passed": 0, "failed": 1, "error": 2, "unavailable": None}[status]
        return sandbox.SandboxResult(status, code, f"fake output: {status}", 0.1)

    return fake


@pytest.fixture
def setup(client, auth, monkeypatch):
    def _setup(llm=None, sandbox_statuses=("passed",)):
        llm = llm or FakeLLM()
        monkeypatch.setattr("app.llm.provider.get_provider", lambda: llm)
        monkeypatch.setattr("app.services.sandbox.run_tests", sbx(*sandbox_statuses))
        pid = client.post(
            "/api/projects", headers=auth, json={"name": "shortener", "requirements": "URL shortener " * 3}
        ).json()["id"]
        run = client.post(f"/api/projects/{pid}/runs", headers=auth).json()
        return llm, pid, run["id"]

    return _setup


def get_run(client, auth, rid):
    return client.get(f"/api/runs/{rid}", headers=auth).json()


def go_to_changes(client, auth, rid):
    assert get_run(client, auth, rid)["status"] == "awaiting_plan_approval"
    assert (
        client.post(f"/api/runs/{rid}/approve-plan", headers=auth, json={"confirm_dependencies": True}).status_code
        == 200
    )
    assert get_run(client, auth, rid)["status"] == "awaiting_change_approval"


def approve_all_and_apply(client, auth, rid):
    for c in client.get(f"/api/runs/{rid}/changes", headers=auth).json():
        if c["origin"] == "developer":
            assert client.post(f"/api/changes/{c['id']}/approve", headers=auth).status_code == 200
    return client.post(f"/api/runs/{rid}/apply-changes", headers=auth)


def test_happy_path_end_to_end(client, auth, setup):
    llm, pid, rid = setup()
    run = get_run(client, auth, rid)
    assert run["status"] == "awaiting_plan_approval"
    assert run["state"]["dependencies_needing_approval"] == ["left-pad-py"]
    assert [t["files"] for t in run["state"]["plan"]["tasks"]] == [["backend/app.py"]]  # unsafe path dropped

    r = client.post(f"/api/runs/{rid}/approve-plan", headers=auth, json={})
    assert r.status_code == 422 and r.json()["error"]["code"] == "dependencies_unconfirmed"
    go_to_changes(client, auth, rid)

    run = get_run(client, auth, rid)
    assert len(run["state"]["policy_rejections"]) == 2  # ../../etc/passwd and .env refused
    changes = client.get(f"/api/runs/{rid}/changes", headers=auth).json()
    assert [c["path"] for c in changes] == ["backend/app.py"]
    assert "+def shorten" in changes[0]["diff"]
    assert client.get(f"/api/projects/{pid}/files", headers=auth).json() == []  # nothing written before approval

    assert client.post(f"/api/runs/{rid}/apply-changes", headers=auth).status_code == 409  # undecided
    assert approve_all_and_apply(client, auth, rid).status_code == 200

    run = get_run(client, auth, rid)
    assert run["status"] == "awaiting_final_approval"
    assert [t["status"] for t in run["test_runs"]] == ["passed"]
    files = client.get(f"/api/projects/{pid}/files", headers=auth).json()
    assert files == ["backend/app.py", "backend/tests/test_app.py"]  # non-test path from tester refused

    assert client.post(f"/api/runs/{rid}/approve-final", headers=auth).status_code == 200
    assert get_run(client, auth, rid)["status"] == "completed"
    assert "README.md" in client.get(f"/api/projects/{pid}/files", headers=auth).json()
    agents = [s["agent"] for s in run["steps"]]
    for a in (
        "product_manager",
        "architect",
        "task_planner",
        "developer",
        "reviewer",
        "testing",
        "sandbox",
        "final_review",
        "documentation",
        "supervisor",
    ):
        assert a in agents
    assert "DebugFix" not in llm.calls


def test_repair_loop_is_bounded_and_failure_is_reported(client, auth, setup):
    llm, pid, rid = setup(sandbox_statuses=("failed",))
    go_to_changes(client, auth, rid)
    approve_all_and_apply(client, auth, rid)
    run = get_run(client, auth, rid)
    assert llm.calls.count("DebugFix") == 2 and run["repair_attempts"] == 2
    assert [t["status"] for t in run["test_runs"]] == ["failed", "failed", "failed"]
    assert run["state"]["final_test_status"] == "failed"  # never rewritten as a pass
    assert run["status"] == "awaiting_final_approval"


def test_repair_succeeds_on_second_run(client, auth, setup):
    llm, _, rid = setup(sandbox_statuses=("failed", "passed"))
    go_to_changes(client, auth, rid)
    approve_all_and_apply(client, auth, rid)
    run = get_run(client, auth, rid)
    assert llm.calls.count("DebugFix") == 1
    assert [t["status"] for t in run["test_runs"]] == ["failed", "passed"]


def test_sandbox_unavailable_skips_repair(client, auth, setup):
    llm, _, rid = setup(sandbox_statuses=("unavailable",))
    go_to_changes(client, auth, rid)
    approve_all_and_apply(client, auth, rid)
    run = get_run(client, auth, rid)
    assert run["test_runs"][0]["status"] == "unavailable" and "DebugFix" not in llm.calls
    assert run["state"]["final_test_status"] == "unavailable"


def test_reviewer_can_send_back_once(client, auth, setup):
    llm, _, rid = setup(llm=FakeLLM(review_verdicts=("request_changes", "approve")))
    go_to_changes(client, auth, rid)
    assert llm.calls.count("DeveloperOutput") == 2 and llm.calls.count("Review") == 2
    changes = client.get(f"/api/runs/{rid}/changes", headers=auth).json()
    assert len(changes) == 1  # superseded proposal hidden


def test_rejected_change_is_not_applied(client, auth, setup):
    _, pid, rid = setup()
    go_to_changes(client, auth, rid)
    cid = client.get(f"/api/runs/{rid}/changes", headers=auth).json()[0]["id"]
    client.post(f"/api/changes/{cid}/reject", headers=auth)
    r = client.post(f"/api/runs/{rid}/apply-changes", headers=auth)
    assert r.status_code == 409 and r.json()["error"]["code"] == "nothing_approved"
    assert client.get(f"/api/projects/{pid}/files", headers=auth).json() == []


def test_other_user_cannot_touch_run(client, auth, setup):
    _, _, rid = setup()
    go_to_changes(client, auth, rid)
    other = register(client, "other@example.com")
    cid = client.get(f"/api/runs/{rid}/changes", headers=auth).json()[0]["id"]
    assert client.get(f"/api/runs/{rid}", headers=other).status_code == 404
    assert client.post(f"/api/changes/{cid}/approve", headers=other).status_code == 404
    assert client.post(f"/api/runs/{rid}/apply-changes", headers=other).status_code == 404


def test_one_active_run_per_project(client, auth, setup):
    _, pid, _ = setup()
    r = client.post(f"/api/projects/{pid}/runs", headers=auth)
    assert r.status_code == 409 and r.json()["error"]["code"] == "run_in_progress"


def test_failed_llm_output_marks_run_failed_and_retry_works(client, auth, monkeypatch):
    class Broken:
        def complete_json(self, system, user):
            return "not json"

    monkeypatch.setattr("app.llm.provider.get_provider", lambda: Broken())
    pid = client.post("/api/projects", headers=auth, json={"name": "p", "requirements": "x" * 30}).json()["id"]
    rid = client.post(f"/api/projects/{pid}/runs", headers=auth).json()["id"]
    run = get_run(client, auth, rid)
    assert run["status"] == "failed" and "structured output" in run["error"]
    assert run["steps"][-1]["status"] == "failed"
    monkeypatch.setattr("app.llm.provider.get_provider", lambda: FakeLLM())
    assert client.post(f"/api/runs/{rid}/retry", headers=auth).status_code == 200
    assert get_run(client, auth, rid)["status"] == "awaiting_plan_approval"


def test_search_outline_and_download(client, auth, setup):
    _, pid, rid = setup()
    go_to_changes(client, auth, rid)
    approve_all_and_apply(client, auth, rid)
    hits = client.get(f"/api/projects/{pid}/search", headers=auth, params={"q": "shorten"}).json()
    assert any(h["path"] == "backend/app.py" for h in hits)
    outline = client.get(f"/api/projects/{pid}/outline", headers=auth).json()
    assert {"kind": "function", "name": "shorten", "line": 1} in [s for o in outline for s in o["symbols"]]
    assert client.get(f"/api/projects/{pid}/files/content", headers=auth, params={"path": "../x"}).status_code == 400
    assert client.get(f"/api/projects/{pid}/download", headers=auth).headers["content-type"] == "application/zip"


def test_agents_receive_real_context(client, auth, setup):
    """Regression: reviewer must see the proposed diff and debugger the *latest* test output."""
    seen = {}

    class Spy(FakeLLM):
        def complete_json(self, system, user):
            out = super().complete_json(system, user)
            seen.setdefault(self.calls[-1], []).append(user)
            return out

    llm, _, rid = setup(llm=Spy(), sandbox_statuses=("failed",))
    go_to_changes(client, auth, rid)
    assert "+def shorten" in seen["Review"][0]
    approve_all_and_apply(client, auth, rid)
    assert len(seen["DebugFix"]) == 2
    assert "fake output: failed" in seen["DebugFix"][1]
    assert "# fix" in seen["FinalReview"][0]  # applied repair diff visible to the final reviewer
