export function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    queued: "bg-white/10 text-white/60",
    enriching: "bg-brand/30 text-white",
    market: "bg-brand/30 text-white",
    icp: "bg-brand/30 text-white",
    person: "bg-brand/30 text-white",
    champion: "bg-brand/30 text-white",
    drafting: "bg-brand/30 text-white",
    awaiting_review: "bg-yellow-500/30 text-yellow-200",
    drafted: "bg-emerald-500/30 text-emerald-300",
    escalated: "bg-orange-500/30 text-orange-300",
    rejected: "bg-red-500/30 text-red-300",
    cancelled: "bg-white/15 text-white/50",
    error: "bg-red-500/40 text-red-200",
  };
  return <span className={`text-[10px] px-2 py-0.5 rounded-full uppercase tracking-wider ${map[status] || "bg-white/10"}`}>{status}</span>;
}
