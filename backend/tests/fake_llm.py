"""Scripted LLM used ONLY by tests to drive the workflow deterministically."""

import json

MAIN_PY = "def shorten(url):\n    return 'abc123'\n"
TEST_PY = "from backend.app import shorten\n\ndef test_shorten():\n    assert shorten('x') == 'abc123'\n"


class FakeLLM:
    def __init__(self, review_verdicts=("approve",)):
        self.calls: list[str] = []
        self.review_verdicts = list(review_verdicts)

    def complete_json(self, system: str, user: str) -> str:
        name = next(
            n
            for n in (
                "ProductSpec",
                "Architecture",
                "Plan",
                "DeveloperOutput",
                "Review",
                "TestPlan",
                "DebugFix",
                "FinalReview",
                "DocsOutput",
            )
            if f'"title": "{n}"' in system
        )
        self.calls.append(name)
        return json.dumps(getattr(self, f"_{name}")())

    def _ProductSpec(self):
        return {
            "summary": "URL shortener",
            "user_stories": [{"as_a": "user", "i_want": "short links", "so_that": "sharing"}],
            "acceptance_criteria": ["shorten returns code"],
            "non_goals": [],
        }

    def _Architecture(self):
        return {
            "overview": "mono",
            "components": [{"name": "api", "responsibility": "serve"}],
            "api_endpoints": [{"method": "POST", "path": "/shorten", "description": "make"}],
            "data_models": [{"name": "Link", "fields": ["code"]}],
            "dependencies": ["fastapi", "left-pad-py"],
            "file_layout": ["backend/app.py"],
        }

    def _Plan(self):
        return {"tasks": [{"id": "t1", "title": "core", "description": "d", "files": ["backend/app.py", "../evil.py"]}]}

    def _DeveloperOutput(self):
        return {
            "changes": [
                {"path": "backend/app.py", "action": "create", "content": MAIN_PY, "rationale": "core"},
                {"path": "../../etc/passwd", "action": "create", "content": "x", "rationale": "attack"},
                {"path": ".env", "action": "create", "content": "SECRET=1", "rationale": "attack"},
            ]
        }

    def _Review(self):
        verdict = self.review_verdicts.pop(0) if self.review_verdicts else "approve"
        issues = [{"severity": "major", "path": "backend/app.py", "message": "fix"}] if verdict != "approve" else []
        return {"verdict": verdict, "summary": "s", "issues": issues}

    def _TestPlan(self):
        return {
            "files": [
                {"path": "backend/tests/test_app.py", "content": TEST_PY},
                {"path": "backend/evil_not_test.py", "content": "x"},
            ]
        }

    def _DebugFix(self):
        return {
            "diagnosis": "d",
            "changes": [{"path": "backend/app.py", "action": "modify", "content": MAIN_PY + "# fix\n"}],
        }

    def _FinalReview(self):
        return {"verdict": "approve", "summary": "ok", "risks": []}

    def _DocsOutput(self):
        return {"readme": "# App\n", "api_docs": "# API\n"}
