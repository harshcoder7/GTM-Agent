"use client";
import { useEffect, useRef } from "react";
import clsx from "clsx";
import type { AgentEvent } from "@/lib/sse";
import { AGENT_ORDER } from "./PipelineGraph";

const LABELS: Record<string, string> = {
  lead_enrichment: "Lead Enrichment",
  market_intelligence: "Market Intelligence",
  icp_profiling: "ICP Profiling",
  person_signal: "LinkedIn Signal",
  champion_scoring: "Champion Scoring",
  drafting: "Drafting",
};

export function ActiveAgentConsole({ events }: { events: AgentEvent[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Determine the most-recent currently-running agent
  let active: string | null = null;
  let activeMessage = "";
  const done = new Set<string>();
  for (const e of events) {
    const id = e.data?.agent;
    if (!id || !(AGENT_ORDER as readonly any[]).find((a) => a.id === id)) continue;
    if (e.event === "agent.status") { active = id; activeMessage = e.data.message || ""; }
    if (e.event === "agent.result") { done.add(id); if (active === id) active = null; }
  }
  // If nothing is "running" right now but some agents have completed, surface the last completed.
  if (!active) {
    for (let i = events.length - 1; i >= 0; i--) {
      const id = events[i].data?.agent;
      if (id && (AGENT_ORDER as readonly any[]).find((a) => a.id === id)) {
        active = id;
        break;
      }
    }
  }

  const lines = events.filter((e) =>
    e.event === "agent.tool" && e.data?.agent === active && e.data?.kind === "log"
  );
  const phases = events.filter((e) =>
    e.event === "agent.tool" && e.data?.agent === active && e.data?.kind !== "log"
  );

  // auto-scroll
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines.length, phases.length]);

  if (!active) {
    return (
      <div className="glass rounded-xl p-10 text-center">
        <div className="text-white/60 text-sm">Waiting for the first agent to start…</div>
        <div className="shimmer-bg h-1 rounded mt-6" />
        <div className="text-[11px] text-white/30 mt-4">If this stays empty for &gt;10s, the backend may not be sending events. Refresh the page.</div>
      </div>
    );
  }

  const isRunning = !done.has(active);

  return (
    <div className="glass rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/10 bg-white/[0.02]">
        <div className="flex items-center gap-3">
          <div className={clsx(
            "w-2 h-2 rounded-full",
            isRunning ? "bg-brand animate-pulseGlow" : "bg-emerald-400",
          )} />
          <div>
            <div className="text-xs uppercase tracking-wider text-white/40">{isRunning ? "Now running" : "Last completed"}</div>
            <div className="text-sm font-medium">{LABELS[active] || active}</div>
          </div>
        </div>
        <div className="text-[11px] text-white/50">{activeMessage}</div>
      </div>

      {phases.length > 0 && (
        <div className="px-5 py-2 border-b border-white/5 text-[12px] text-white/70 flex flex-wrap gap-2">
          {phases.slice(-3).map((p, i) => (
            <span key={i} className="px-2 py-0.5 rounded-full bg-white/[0.06] font-mono">{p.data.phase}</span>
          ))}
        </div>
      )}

      <div ref={scrollRef} className="scrollbar-thin overflow-y-auto font-mono text-[11.5px] leading-relaxed px-5 py-3 max-h-[520px] bg-black/30">
        {lines.length === 0 ? (
          <div className="text-white/40">
            <div>Connecting to {LABELS[active] || active} log stream…</div>
            <div className="shimmer-bg h-px mt-2 rounded" />
            <div className="text-[10px] text-white/30 mt-3">First lines appear within ~1s once the agent starts work. If this stays empty for &gt;15s, the underlying service may be busy — check the status pill above.</div>
          </div>
        ) : lines.map((l, i) => (
          <div key={i} className="text-white/75 whitespace-pre-wrap break-words">
            <span className="text-white/30 select-none">›</span> {l.data.phase}
          </div>
        ))}
      </div>

      <div className="px-5 py-2 border-t border-white/10 text-[10px] text-white/40 flex justify-between">
        <span>{lines.length} log lines · {phases.length} phases</span>
        <span>{isRunning ? "live" : "complete"}</span>
      </div>
    </div>
  );
}
