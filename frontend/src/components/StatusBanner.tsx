import type { SystemStatus } from "../types";

export function StatusBanner({ status }: { status: SystemStatus | null }) {
  if (!status) return null;
  const warnings: string[] = [];
  if (!status.llm_configured) warnings.push(status.message ?? "The LLM provider is not configured.");
  if (!status.docker_available)
    warnings.push(
      "Docker is not available to the backend: generated tests will NOT be executed (reported as 'unavailable').",
    );
  if (!warnings.length) return null;
  return (
    <div role="alert" className="border-b border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900">
      {warnings.map((w) => (
        <p key={w}>⚠ {w}</p>
      ))}
    </div>
  );
}
