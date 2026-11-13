export interface SystemStatus {
  llm_configured: boolean;
  llm_provider: string;
  llm_model: string;
  docker_available: boolean;
  max_repair_attempts: number;
  message: string | null;
}
export interface Project {
  id: number;
  name: string;
  requirements: string;
  created_at: string;
  latest_run_status: string | null;
}
export interface Step {
  id: number;
  agent: string;
  status: "running" | "succeeded" | "failed";
  output: unknown;
  error: string | null;
  started_at: string;
  finished_at: string | null;
}
export interface TestRun {
  id: number;
  attempt: number;
  status: "passed" | "failed" | "error" | "unavailable";
  exit_code: number | null;
  output: string;
  duration_seconds: number;
  created_at: string;
}
export interface RunState {
  spec?: {
    summary: string;
    user_stories: { as_a: string; i_want: string; so_that: string }[];
    acceptance_criteria: string[];
    non_goals: string[];
  };
  architecture?: {
    overview: string;
    components: { name: string; responsibility: string }[];
    api_endpoints: { method: string; path: string; description: string }[];
    data_models: { name: string; fields: string[] }[];
    dependencies: string[];
    file_layout: string[];
  };
  dependencies_needing_approval?: string[];
  plan?: { tasks: { id: string; title: string; description: string; files: string[] }[] };
  review?: {
    verdict: string;
    summary: string;
    issues: { severity: string; path: string; message: string }[];
  };
  final_review?: { verdict: string; summary: string; risks: string[] };
  final_test_status?: string;
  policy_rejections?: string[];
  last_diagnosis?: string;
}
export interface Run {
  id: number;
  project_id: number;
  status: string;
  state: RunState;
  repair_attempts: number;
  error: string | null;
  created_at: string;
  updated_at: string;
  steps: Step[];
  test_runs: TestRun[];
}
export interface Change {
  id: number;
  path: string;
  action: "create" | "modify" | "delete";
  status: string;
  origin: string;
  rationale: string;
  diff: string;
}
export interface SearchHit {
  path: string;
  line: number;
  text: string;
}
export interface OutlineEntry {
  path: string;
  symbols: { kind: string; name: string; line: number }[];
}
