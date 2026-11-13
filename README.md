# DevTeam AI

An agentic software-engineering platform. You describe an application in plain English; a team of specialised
agents plans it, writes it, reviews it, tests it in a locked-down Docker sandbox, repairs it (max 2 attempts) and
documents it. **A human approves the plan, every file change and the final result.**

> Screenshots: _placeholder — add `docs/screenshots/dashboard.png`, `workflow.png`, `diff.png`, `tests.png`._

## Architecture

```
React/TS/Tailwind (Vite)  ──REST/JWT──►  FastAPI (modular monolith)  ──►  PostgreSQL (SQLAlchemy + Alembic)
                                              │
                                   LangGraph workflows (3 phases)
                                              │
                    Groq LLM (via LangChain)  +  Docker sandbox (tests only)
```

Workflow (each arrow is a LangGraph edge; ◆ = human approval, persisted in the DB between phases):

```
Requirements → Product Manager → Architect → Task Planner ◆ approve plan
  → Developer → Code Reviewer ─(major issues, 1 round)→ Developer
  → ◆ approve/reject each file change → apply to workspace
  → Testing Agent → Sandbox ─(failed/error & attempts<2)→ Debugger → Sandbox ...
  → Final Review → Documentation → ◆ final approval
```

- **Supervisor** = the LangGraph graph with conditional edges. Routing is rule-based (not an LLM); each decision is
  logged as a `supervisor` step in the execution monitor.
- Structured outputs: every agent returns JSON validated by a Pydantic v2 model (one automatic retry on invalid JSON).
- Workspaces: `backend/workspaces/<project_id>/`, never executed on the host.
- Layout: `backend/app/{routers,services,agents,workflow,llm}`, `frontend/src/{pages,components,lib}`, `sandbox/`.

## Setup (Windows PowerShell; Linux/macOS: use `source .venv/bin/activate`)

Prerequisites: Python 3.12, Node 20+, Docker Desktop.

```powershell
# 1. PostgreSQL
docker compose up -d db

# 2. Sandbox image used to run generated tests
docker build -t devteam-sandbox:latest sandbox

# 3. Backend
cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env      # then edit: SECRET_KEY, GROQ_API_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 4. Frontend (new terminal)
cd frontend
npm install
copy .env.example .env
npm run dev                 # http://localhost:5173
```

Full stack in containers instead: copy root `.env.example` to `.env`, set `WORKSPACE_HOST_PATH`, create
`backend/.env`, then `docker compose up --build` (see security note about the Docker socket).

The app **starts without `GROQ_API_KEY`**: a banner explains what is missing and starting a run returns a clear 409.

## Environment variables (`backend/.env`)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy URL (PostgreSQL) |
| `SECRET_KEY` | JWT signing key (if empty an ephemeral one is generated; logins reset on restart) |
| `GROQ_API_KEY`, `GROQ_MODEL` | LLM provider (Groq is the default and only implemented provider) |
| `WORKSPACE_ROOT`, `WORKSPACE_HOST_PATH` | Project files; host path needed only when backend runs in Docker |
| `SANDBOX_IMAGE`, `SANDBOX_TIMEOUT_SECONDS`, `SANDBOX_MEMORY`, `SANDBOX_CPUS` | Sandbox limits |
| `CORS_ORIGINS` | Allowed frontend origins |

## Commands

```powershell
cd backend;  pytest -q;  ruff check .;  ruff format --check .
cd frontend; npm test;  npm run typecheck;  npm run build
```

## Features

Auth + project ownership (404 on others' resources) · dashboard · natural-language project creation · agent
execution monitor with per-step JSON output · LangGraph orchestration with persistence (state in `runs.state`,
steps/changes/test runs in tables) · file explorer + preview + zip download · git-style diff viewer with
approve/reject · sandboxed test execution · test dashboard · max-2 repair loop · repository search and code
outline (stdlib `ast` + regex; Tree-sitter not used) · generated README/API docs · structured JSON logging.

## Security model

- Generated code is never executed on the host; tests run with `docker run --network none --user 65534
  --cap-drop ALL --read-only --memory --cpus --pids-limit`, workspace snapshot mounted **read-only**, a fixed
  environment (no backend env/secrets), a fixed command (agents cannot choose it), and a hard timeout + `docker kill`.
- The Docker socket is never mounted into sandbox containers.
- All agent-supplied paths pass `validate_rel_path` (no `..`, absolute, backslash, hidden env files, `.git`,
  symlinks) and are re-checked for containment at write time.
- Repository/test content is wrapped as `<untrusted>` data in prompts.
- Approval gates: plan (+ explicit confirmation of dependencies outside the sandbox image), each file change
  (deletes flagged), final result. Debugger/test-file writes are auto-applied but bounded (≤5 files, no deletes),
  recorded with diffs, and visible to the final reviewer.
- Test status comes only from the sandbox exit code + output parsing (0 tests collected is not a pass). If Docker
  is missing the status is `unavailable`.

### Limitations
- The compose backend mounts `/var/run/docker.sock` to launch sandboxes: that is root-equivalent on the host.
  Prefer running the backend on the host in anything but a throwaway environment.
- Only pytest is run in the sandbox; generated frontend (Vitest) tests are written but not executed.
- No network in the sandbox means generated apps can only use packages preinstalled in `sandbox/Dockerfile`.
- No Git commit/push integration (not implemented rather than faked); use the zip download.
- No rate limiting, email verification, or token revocation. LLM output quality depends on the Groq model.

## Demo: URL shortener
1. Register, **New project → "Use the URL shortener example"**.
2. **Start agent workflow**; review spec/architecture/tasks; approve (tick dependency box if shown).
3. **Changes** tab: inspect diffs, approve each, **Apply approved changes & run tests**.
4. Watch the monitor and **Tests** tab (repair attempts shown). Approve final to write README/API docs.
5. **Files** tab → download zip; run it locally.
