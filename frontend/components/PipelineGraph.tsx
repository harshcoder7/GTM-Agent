"use client";
import clsx from "clsx";

export const AGENT_ORDER = [
  { id: "lead_enrichment",      label: "Lead Enrichment",      hint: "Firmographics + funding" },
  { id: "market_intelligence",  label: "Market Intelligence",  hint: "Signals + recent news" },
  { id: "icp_profiling",        label: "ICP Profiling",        hint: "Fit + product routing" },
  { id: "person_signal",        label: "LinkedIn Signal",      hint: "Personal hook" },
  { id: "champion_scoring",     label: "Champion Score",       hint: "Decision-maker fit" },
  { id: "drafting",             label: "Drafting",             hint: "Email + brochure" },
] as const;

export type AgentState = "idle" | "running" | "done" | "error";

export function PipelineGraph({ states, durations }: {
  states: Record<string, AgentState>;
  durations?: Record<string, number>;
}) {
  return (
    <div className="glass rounded-xl p-5">
      <div className="text-xs uppercase tracking-wider text-white/50 mb-4">Pipeline</div>
      <div className="flex items-center gap-2 overflow-x-auto scrollbar-thin pb-2">
        {AGENT_ORDER.map((a, i) => {
          const s = states[a.id] || "idle";
          return (
            <div key={a.id} className="flex items-center gap-2 shrink-0">
              <Node label={a.label} hint={a.hint} state={s} index={i + 1} duration={durations?.[a.id]} />
              {i < AGENT_ORDER.length - 1 && <Connector active={s === "done"} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Node({ label, hint, state, index, duration }: {
  label: string; hint: string; state: AgentState; index: number; duration?: number;
}) {
  return (
    <div
      className={clsx(
        "min-w-[180px] rounded-lg border px-3 py-3 transition relative",
        state === "idle"    && "bg-white/[0.02] border-white/10",
        state === "running" && "bg-brand/10 border-brand/40 animate-pulseGlow",
        state === "done"    && "bg-emerald-500/10 border-emerald-500/40",
        state === "error"   && "bg-red-500/10 border-red-500/40",
      )}
    >
      <div className="flex items-center gap-2">
        <div className={clsx(
          "w-5 h-5 rounded-full text-[11px] flex items-center justify-center font-semibold",
          state === "idle"    && "bg-white/10 text-white/60",
          state === "running" && "bg-brand text-white",
          state === "done"    && "bg-emerald-500 text-white",
          state === "error"   && "bg-red-500 text-white",
        )}>{index}</div>
        <div className="text-sm font-medium">{label}</div>
        {duration !== undefined && (
          <span className="ml-auto text-[10px] text-white/40 font-mono">{duration}s</span>
        )}
      </div>
      <div className="text-[11px] text-white/40 mt-1">{hint}</div>
    </div>
  );
}

function Connector({ active }: { active: boolean }) {
  return (
    <div className="relative h-px w-8 bg-white/10 overflow-hidden">
      {active && <div className="absolute inset-0 bg-gradient-to-r from-brand to-brand-soft" />}
    </div>
  );
}
