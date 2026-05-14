"use client";
import { useEffect, useMemo, useState } from "react";
import { jget } from "@/lib/api";
import { useRunStream } from "@/lib/sse";
import { PipelineGraph, AGENT_ORDER, AgentState } from "@/components/PipelineGraph";
import { AgentCard } from "@/components/AgentCard";
import { ActiveAgentConsole } from "@/components/ActiveAgentConsole";
import { GateReview } from "@/components/GateReview";
import { StatusPill } from "@/components/StatusPill";

export default function RunPage({ params }: { params: { id: string } }) {
  const runId = params.id;
  const [run, setRun] = useState<any>(null);
  const isTerminal = run && ["drafted", "escalated", "rejected", "error", "cancelled"].includes(run.status);
  const { events, seed } = useRunStream(runId, { skipLive: isTerminal });

  // For terminal runs, replay the persisted SSE history so AgentCards render.
  useEffect(() => {
    if (!run) return;
    const hist = (run.events_history || []) as { event: string; data: any }[];
    if (isTerminal && hist.length > 0 && events.length === 0) {
      seed(hist);
    }
  }, [run?.id, run?.status, isTerminal]);

  // Initial fetch + milestone refetch, both with AbortController so unmount
  // cancels in-flight requests (prevents stuck navigation feeling).
  useEffect(() => {
    const ac = new AbortController();
    (async () => {
      try {
        const r = await jget(`/api/runs/${runId}`, { signal: ac.signal });
        setRun(r);
      } catch {}
    })();
    return () => ac.abort();
  }, [runId]);

  const milestoneCount = useMemo(
    () => events.filter((e) => e.event === "gate.open" || e.event === "run.complete" || e.event === "gate.resolved").length,
    [events]
  );
  useEffect(() => {
    if (milestoneCount === 0) return;
    const ac = new AbortController();
    const t = setTimeout(async () => {
      try {
        const r = await jget(`/api/runs/${runId}`, { signal: ac.signal });
        setRun(r);
      } catch {}
    }, 300);
    return () => { ac.abort(); clearTimeout(t); };
  }, [milestoneCount, runId]);

  const { states, durations } = useMemo(() => {
    const s: Record<string, AgentState> = {};
    const d: Record<string, number> = {};
    for (const a of AGENT_ORDER) s[a.id] = "idle";
    for (const e of events) {
      const id = e.data?.agent;
      if (!id || !(id in s)) continue;
      if (e.event === "agent.status") s[id] = "running";
      if (e.event === "agent.result") {
        s[id] = "done";
        if (typeof e.data.duration_secs === "number") d[id] = e.data.duration_secs;
      }
      if (e.event === "agent.error")  s[id] = "error";
    }
    return { states: s, durations: d };
  }, [events]);

  const latestDraft = run?.drafts?.[run.drafts.length - 1];
  const showGate = run?.status === "awaiting_review" && latestDraft;
  const escalated = run?.status === "escalated";
  const drafted = run?.status === "drafted";
  const rejected = run?.status === "rejected";
  const cancelled = run?.status === "cancelled";
  const errored = run?.status === "error";
  const inFlight = run && ["queued", "enriching", "market", "icp", "person", "champion", "drafting"].includes(run.status);
  const stuckAwaiting = run?.status === "awaiting_review" && !latestDraft;

  return (
    <div className="space-y-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs text-white/40 uppercase tracking-wider">Run · <span className="font-mono">{runId}</span></div>
          <h1 className="text-2xl font-semibold mt-1">{run?.prospect?.full_name || "…"}</h1>
          <div className="text-white/60 text-sm">
            {run?.prospect?.job_title} · <span className="text-white">{run?.prospect?.company}</span>
            {run?.prospect?.linkedin_url && (
              <> · <a className="text-brand-soft hover:underline" href={run.prospect.linkedin_url} target="_blank" rel="noopener noreferrer">LinkedIn ↗</a></>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          {run?.status && <StatusPill status={run.status} />}
          {run?.icp_score != null && (
            <div className="text-xs text-white/60">ICP: <span className="font-mono text-white">{run.icp_score}</span> · {run.product_fit}</div>
          )}
        </div>
      </header>

      <PipelineGraph states={states} durations={durations} />

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_420px] gap-6">
        <div>
          {!run && (
            <div className="glass rounded-xl p-10 text-center">
              <div className="text-white/60 text-sm">Loading run…</div>
              <div className="shimmer-bg h-1 rounded mt-5" />
            </div>
          )}
          {escalated && (
            <div className="glass rounded-xl p-8 text-center mb-6">
              <div className="text-orange-300 text-xl font-semibold mb-2">⚠ Pipeline escalated</div>
              <div className="text-sm text-white/70 max-w-xl mx-auto">{run.escalation_reason}</div>
            </div>
          )}
          {rejected && (
            <div className="glass rounded-xl p-8 text-center mb-6">
              <div className="text-red-300 text-xl font-semibold mb-2">✗ Run rejected by reviewer</div>
            </div>
          )}
          {cancelled && (
            <div className="glass rounded-xl p-8 text-center mb-6">
              <div className="text-white/60 text-xl font-semibold mb-2">⏸ Run cancelled</div>
              <div className="text-sm text-white/50 max-w-xl mx-auto">{run.escalation_reason || "This run was cancelled before it completed."}</div>
            </div>
          )}
          {errored && (
            <div className="glass rounded-xl p-8 text-center mb-6">
              <div className="text-red-300 text-xl font-semibold mb-2">✗ Pipeline error</div>
              <div className="text-sm text-white/70 max-w-xl mx-auto whitespace-pre-wrap">{run.escalation_reason || "Unknown error — check backend logs."}</div>
            </div>
          )}
          {drafted && latestDraft && (
            <div className="glass rounded-xl p-8 text-center mb-6">
              <div className="text-emerald-400 text-xl font-semibold mb-2">✓ Gmail draft created</div>
              <div className="text-sm text-white/60">Draft id: <span className="font-mono">{run.composio_draft_id}</span></div>
              <a href="https://mail.google.com/mail/u/0/#drafts" target="_blank" rel="noopener noreferrer"
                className="inline-block mt-4 px-4 py-2 rounded-md brand-gradient text-white font-medium">
                Open Gmail Drafts →
              </a>
            </div>
          )}
          {showGate && (
            <GateReview runId={runId} latest={latestDraft} onResolved={async () => {
              try { setRun(await jget(`/api/runs/${runId}`)); } catch {}
            }} />
          )}
          {stuckAwaiting && (
            <div className="glass rounded-xl p-8 text-center mb-6">
              <div className="text-yellow-200 text-lg font-semibold mb-2">Awaiting draft</div>
              <div className="text-sm text-white/60">The pipeline reached Gate 1 but no draft was persisted. The events log on the right may have details.</div>
            </div>
          )}
          {run && inFlight && (
            <ActiveAgentConsole events={events} />
          )}
        </div>

        <div className="max-h-[calc(100vh-220px)] overflow-y-auto scrollbar-thin pr-1">
          {AGENT_ORDER.map((a) => <AgentCard key={a.id} agentId={a.id} events={events} />)}
        </div>
      </div>
    </div>
  );
}
