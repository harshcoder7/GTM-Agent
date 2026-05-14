"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { jget, jdelete } from "@/lib/api";
import { StatusPill } from "@/components/StatusPill";

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [confirmClearAll, setConfirmClearAll] = useState(false);

  async function reload() {
    const ac = new AbortController();
    try {
      const [s, r] = await Promise.all([
        jget("/api/stats", { signal: ac.signal }),
        jget("/api/runs?limit=200", { signal: ac.signal }),
      ]);
      setStats(s); setRuns(r);
    } catch {}
  }
  useEffect(() => { reload(); }, []);

  async function deleteOne(id: string) {
    if (!confirm(`Delete run ${id}? This is permanent.`)) return;
    setBusy(id);
    try {
      await jdelete(`/api/runs/${id}`);
      setRuns((rs) => rs.filter((r) => r.id !== id));
      reload();
    } catch (e: any) {
      alert(`Failed: ${e.message || e}`);
    } finally { setBusy(null); }
  }

  async function clearAll() {
    setBusy("all");
    try {
      await jdelete("/api/runs");
      setRuns([]); setStats(null);
      setConfirmClearAll(false);
      reload();
    } catch (e: any) {
      alert(`Failed: ${e.message || e}`);
    } finally { setBusy(null); }
  }

  const derived = useMemo(() => {
    if (!runs.length) return { total: 0, drafted: 0, escalated: 0, rejected: 0, awaiting_review: 0, avg_icp_score: null as number | null };
    let drafted = 0, escalated = 0, rejected = 0, awaiting = 0;
    const icps: number[] = [];
    for (const r of runs) {
      if (r.status === "drafted") drafted++;
      else if (r.status === "escalated") escalated++;
      else if (r.status === "rejected") rejected++;
      else if (r.status === "awaiting_review") awaiting++;
      if (typeof r.icp_score === "number") icps.push(r.icp_score);
    }
    return {
      total: runs.length, drafted, escalated, rejected, awaiting_review: awaiting,
      avg_icp_score: icps.length ? Math.round((icps.reduce((a, b) => a + b, 0) / icps.length) * 100) / 100 : null,
    };
  }, [runs]);
  const s = stats || derived;

  return (
    <div className="space-y-8">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-semibold">Dashboard</h1>
          <p className="text-white/60 mt-1 text-sm">Cross-run history, status, outputs.</p>
        </div>
        {runs.length > 0 && (
          <div>
            {!confirmClearAll ? (
              <button onClick={() => setConfirmClearAll(true)}
                className="px-3 py-2 rounded-md border border-red-500/30 text-sm text-red-300 hover:bg-red-500/10">
                Clear all runs
              </button>
            ) : (
              <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 rounded-md px-3 py-1.5">
                <span className="text-xs text-red-200">Delete all {runs.length} runs?</span>
                <button onClick={clearAll} disabled={busy === "all"}
                  className="text-xs px-2 py-1 rounded bg-red-500 hover:bg-red-600 text-white disabled:opacity-50">
                  {busy === "all" ? "Deleting…" : "Yes, clear"}
                </button>
                <button onClick={() => setConfirmClearAll(false)}
                  className="text-xs px-2 py-1 rounded border border-white/15 hover:bg-white/5">Cancel</button>
              </div>
            )}
          </div>
        )}
      </header>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Stat label="Total runs"        v={s.total} />
        <Stat label="Drafted"           v={s.drafted}         tone="emerald" />
        <Stat label="Awaiting review"   v={s.awaiting_review} tone="yellow"  />
        <Stat label="Escalated"         v={s.escalated}       tone="orange"  />
        <Stat label="Avg ICP score"     v={s.avg_icp_score ?? "—"} />
      </div>

      <div className="glass rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/[0.04] text-xs uppercase text-white/50">
            <tr>
              <th className="text-left p-3">Prospect</th>
              <th className="text-left p-3">Company</th>
              <th className="text-left p-3">Status</th>
              <th className="text-left p-3">ICP</th>
              <th className="text-left p-3">Fit</th>
              <th className="text-left p-3">Started</th>
              <th className="text-left p-3">Run id</th>
              <th className="text-right p-3 pr-4"></th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id} className="border-t border-white/5 hover:bg-white/[0.02]">
                <td className="p-3">
                  <Link href={`/runs/${r.id}`} className="text-white hover:underline">{r.prospect?.full_name || "—"}</Link>
                </td>
                <td className="p-3 text-white/70">{r.prospect?.company || "—"}</td>
                <td className="p-3"><StatusPill status={r.status} /></td>
                <td className="p-3 font-mono">{r.icp_score ?? "—"}</td>
                <td className="p-3">{r.product_fit ?? "—"}</td>
                <td className="p-3 text-white/50 text-xs">{r.created_at?.slice(0, 19).replace("T", " ")}</td>
                <td className="p-3 font-mono text-xs text-white/40">{r.id}</td>
                <td className="p-3 pr-4 text-right">
                  <button onClick={() => deleteOne(r.id)} disabled={busy === r.id}
                    title="Delete this run"
                    className="text-[11px] px-2 py-1 rounded border border-red-500/20 text-red-300/80 hover:text-red-300 hover:bg-red-500/10 hover:border-red-500/40 disabled:opacity-40 transition">
                    {busy === r.id ? "…" : "Delete"}
                  </button>
                </td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr><td colSpan={8} className="p-10 text-center text-white/40 text-sm">No runs yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, v, tone }: { label: string; v: any; tone?: string }) {
  const toneCls = tone === "emerald" ? "text-emerald-300"
                : tone === "yellow"  ? "text-yellow-200"
                : tone === "orange"  ? "text-orange-300"
                : "text-white";
  const display = v === null || v === undefined ? "—" : String(v);
  return (
    <div className="glass rounded-xl p-5">
      <div className="text-[11px] uppercase tracking-wider text-white/40">{label}</div>
      <div className={`text-3xl font-semibold mt-2 ${toneCls}`}>{display}</div>
    </div>
  );
}
