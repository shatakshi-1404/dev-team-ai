import { parseDiff } from "../lib/diff";

const ROW: Record<string, string> = {
  add: "bg-emerald-50 text-emerald-900",
  del: "bg-red-50 text-red-900",
  hunk: "bg-sky-50 text-sky-800",
  meta: "bg-slate-100 text-slate-500",
  ctx: "",
};
const SIGN: Record<string, string> = { add: "+", del: "-", hunk: "", meta: "", ctx: " " };

export function DiffViewer({ diff }: { diff: string }) {
  const lines = parseDiff(diff);
  if (!lines.length) return <p className="p-3 text-sm text-slate-500">No textual changes.</p>;
  return (
    <div className="overflow-x-auto rounded border border-slate-200 font-mono text-xs" data-testid="diff">
      {lines.map((l, i) => (
        <div key={i} className={`flex whitespace-pre ${ROW[l.kind]}`} data-kind={l.kind}>
          <span className="w-10 shrink-0 select-none px-1 text-right text-slate-400">{l.oldNo ?? ""}</span>
          <span className="w-10 shrink-0 select-none px-1 text-right text-slate-400">{l.newNo ?? ""}</span>
          <span className="w-4 shrink-0 select-none text-center">{SIGN[l.kind]}</span>
          <span>{l.text}</span>
        </div>
      ))}
    </div>
  );
}
