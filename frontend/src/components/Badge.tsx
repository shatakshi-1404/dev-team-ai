const COLORS: Record<string, string> = {
  succeeded: "bg-emerald-100 text-emerald-800",
  passed: "bg-emerald-100 text-emerald-800",
  applied: "bg-emerald-100 text-emerald-800",
  approved: "bg-emerald-100 text-emerald-800",
  completed: "bg-emerald-100 text-emerald-800",
  running: "bg-blue-100 text-blue-800",
  failed: "bg-red-100 text-red-800",
  error: "bg-red-100 text-red-800",
  rejected: "bg-red-100 text-red-800",
  conflict: "bg-red-100 text-red-800",
  unavailable: "bg-amber-100 text-amber-800",
  pending: "bg-amber-100 text-amber-800",
};

export function Badge({ value }: { value: string }) {
  const cls = value.startsWith("running") ? COLORS.running : (COLORS[value] ?? "bg-slate-100 text-slate-700");
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {value.replaceAll("_", " ")}
    </span>
  );
}
