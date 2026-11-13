import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChangesPanel } from "./ChangesPanel";
import { DiffViewer } from "./DiffViewer";
import { PlanPanel } from "./PlanPanel";
import { StatusBanner } from "./StatusBanner";
import { TestsPanel } from "./TestsPanel";
import type { Change, Run } from "../types";

const status = {
  llm_configured: false,
  llm_provider: "groq",
  llm_model: "m",
  docker_available: false,
  max_repair_attempts: 2,
  message: "GROQ_API_KEY is not configured.",
};

describe("StatusBanner", () => {
  it("shows configuration and docker warnings instead of crashing", () => {
    render(<StatusBanner status={status} />);
    expect(screen.getByRole("alert")).toHaveTextContent("GROQ_API_KEY is not configured.");
    expect(screen.getByRole("alert")).toHaveTextContent("will NOT be executed");
  });
  it("renders nothing when everything is configured", () => {
    const { container } = render(
      <StatusBanner status={{ ...status, llm_configured: true, docker_available: true }} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});

describe("DiffViewer", () => {
  it("marks added and removed lines", () => {
    render(<DiffViewer diff={"--- a/x\n+++ b/x\n@@ -1,1 +1,1 @@\n-old\n+new\n"} />);
    expect(document.querySelector('[data-kind="add"]')).toHaveTextContent("new");
    expect(document.querySelector('[data-kind="del"]')).toHaveTextContent("old");
  });
});

describe("ChangesPanel", () => {
  const change: Change = {
    id: 1,
    path: "app.py",
    action: "create",
    status: "pending",
    origin: "developer",
    rationale: "core",
    diff: "+++ b/app.py\n@@ -0,0 +1,1 @@\n+x\n",
  };
  it("blocks apply until every change is decided and wires approve/reject", async () => {
    const onDecide = vi.fn();
    render(
      <ChangesPanel
        changes={[change]}
        decidableOrigin="developer"
        busy={false}
        onDecide={onDecide}
        onApply={() => undefined}
      />,
    );
    expect(screen.getByRole("button", { name: /apply approved/i })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(onDecide).toHaveBeenCalledWith(1, true);
    await userEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(onDecide).toHaveBeenCalledWith(1, false);
  });
  it("warns about destructive deletes and hides decisions when not decidable", () => {
    render(
      <ChangesPanel
        changes={[{ ...change, action: "delete", status: "applied" }]}
        decidableOrigin={null}
        busy={false}
        onDecide={() => undefined}
      />,
    );
    expect(screen.getByText(/Destructive change/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
  });
});

describe("PlanPanel", () => {
  const state = {
    spec: { summary: "S", user_stories: [], acceptance_criteria: ["AC1"], non_goals: [] },
    architecture: {
      overview: "O",
      components: [],
      api_endpoints: [],
      data_models: [],
      dependencies: [],
      file_layout: [],
    },
    plan: { tasks: [{ id: "1", title: "T", description: "", files: ["a.py"] }] },
    dependencies_needing_approval: ["left-pad-py"],
  };
  it("requires explicit dependency confirmation", async () => {
    const onApprove = vi.fn();
    render(
      <PlanPanel state={state} canDecide busy={false} onApprove={onApprove} onReject={() => undefined} />,
    );
    const btn = screen.getByRole("button", { name: /approve plan/i });
    expect(btn).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(btn);
    expect(onApprove).toHaveBeenCalledWith(true);
  });
});

describe("TestsPanel", () => {
  const base = {
    id: 1,
    project_id: 1,
    status: "awaiting_final_approval",
    state: {},
    repair_attempts: 0,
    error: null,
    created_at: "",
    updated_at: "",
    steps: [],
  };
  it("never presents unavailable results as passing", () => {
    const run: Run = {
      ...base,
      test_runs: [
        {
          id: 1,
          attempt: 0,
          status: "unavailable",
          exit_code: null,
          output: "Docker is not available",
          duration_seconds: 0,
          created_at: "",
        },
      ],
    };
    render(<TestsPanel run={run} />);
    expect(screen.getByText(/no tests were executed/i)).toBeInTheDocument();
    expect(screen.queryByText("passed")).toBeNull();
  });
});
