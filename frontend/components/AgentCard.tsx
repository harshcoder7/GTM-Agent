"use client";
import clsx from "clsx";
import { useState } from "react";
import type { AgentEvent } from "@/lib/sse";

const LABELS: Record<string, string> = {
  lead_enrichment: "Lead Enrichment",
  market_intelligence: "Market Intelligence",
  icp_profiling: "ICP Profiling",
  person_signal: "LinkedIn Signal",
  champion_scoring: "Champion Scoring",
  drafting: "Drafting",
  system: "Orchestrator",
  composio: "Gmail Draft",
};

export function AgentCard({ agentId, events }: { agentId: string; events: AgentEvent[] }) {
  const [logsOpen, setLogsOpen] = useState(false);
  const [rawOpen, setRawOpen] = useState(false);
  const mine = events.filter((e) => e.data?.agent === agentId);
  if (mine.length === 0) return null;
  const status = mine.filter((e) => e.event === "agent.status").slice(-1)[0];
  const tools = mine.filter((e) => e.event === "agent.tool");
  const logs = tools.filter((t) => t.data.kind === "log");
  const phases = tools.filter((t) => t.data.kind !== "log");
  const result = mine.filter((e) => e.event === "agent.result").slice(-1)[0];
  const error = mine.filter((e) => e.event === "agent.error").slice(-1)[0];

  const state = error ? "error" : result ? "done" : status ? "running" : "idle";
  const duration = result?.data?.duration_secs as number | undefined;

  const visibleLogs = logsOpen ? logs : logs.slice(-5);

  return (
    <div className={clsx(
      "rounded-lg border p-4 mb-3 transition",
      state === "running" && "border-brand/40 bg-brand/[0.04]",
      state === "done"    && "border-emerald-500/30 bg-emerald-500/[0.04]",
      state === "error"   && "border-red-500/40 bg-red-500/[0.05]",
      state === "idle"    && "border-white/10 bg-white/[0.02]",
    )}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="text-sm font-medium">{LABELS[agentId] || agentId}</div>
          {duration !== undefined && (
            <span className="text-[10px] text-white/40 font-mono">{duration}s</span>
          )}
        </div>
        <Pill state={state} />
      </div>
      {status && <div className="text-xs text-white/70 mb-1">{status.data.message}</div>}

      {phases.length > 0 && (
        <ul className="text-[11px] text-white/60 space-y-0.5 mt-1">
          {phases.slice(-4).map((t, i) => (
            <li key={i} className="font-mono break-words">› {t.data.phase}</li>
          ))}
        </ul>
      )}

      {logs.length > 0 && (
        <div className="mt-2 bg-black/40 border border-white/5 rounded-md">
          <button onClick={() => setLogsOpen((o) => !o)}
            className="w-full flex items-center justify-between px-2 py-1 border-b border-white/5 hover:bg-white/[0.03]">
            <span className="text-[10px] uppercase tracking-wider text-white/40">Live log · {logs.length} lines</span>
            <span className="text-[10px] text-white/50">{logsOpen ? "▾ collapse" : "▸ expand"}</span>
          </button>
          <div className={clsx(
            "scrollbar-thin overflow-y-auto px-2 py-1 font-mono text-[10.5px] leading-snug text-white/70",
            logsOpen ? "max-h-96" : "max-h-24"
          )}>
            {visibleLogs.map((t, i) => (
              <div key={i} className="whitespace-pre-wrap break-words">
                <span className="text-white/30">›</span> {t.data.phase}
              </div>
            ))}
          </div>
        </div>
      )}

      {error && <div className="text-xs text-red-300 mt-2">⚠ {error.data.error}</div>}
      {result && (
        <>
          <ResultBlock agentId={agentId} data={result.data} />
          <RawToggle data={result.data} open={rawOpen} onToggle={() => setRawOpen((o) => !o)} />
        </>
      )}
    </div>
  );
}

function Pill({ state }: { state: string }) {
  const map: Record<string, string> = {
    running: "bg-brand text-white animate-pulseGlow",
    done: "bg-emerald-500/80 text-white",
    error: "bg-red-500 text-white",
    idle: "bg-white/10 text-white/60",
  };
  return <span className={clsx("text-[10px] px-2 py-0.5 rounded-full uppercase tracking-wider", map[state])}>{state}</span>;
}

function ResultBlock({ agentId, data }: { agentId: string; data: any }) {
  const citations = (data.citations || []) as { url: string; title?: string }[];

  let body: React.ReactNode = null;
  if (agentId === "lead_enrichment" && data.enriched_lead) {
    const e = data.enriched_lead;
    body = (
      <Block>
        <Field k="Company"    v={e.company} />
        <Field k="Overview"   v={e.overview} />
        <Field k="Size"       v={e.size} />
        <Field k="Revenue"    v={e.revenue} />
        <Field k="Domain"     v={e.domain} />
        <Field k="Funding"    v={e.funding_information} />
        <Field k="Latest round" v={e.latest_funding_round} />
        <Field k="Investors"  v={e.investors} />
        <Field k="LinkedIn"   v={e.linkedin_url} />
      </Block>
    );
  } else if (agentId === "market_intelligence" && data.market_intel) {
    const m = data.market_intel;
    body = (
      <Block>
        <Field k="Industry"           v={m.industry} />
        <Field k="Customer segments"  v={m.customer_segments} />
        <Field k="Business model"     v={m.business_model} />
        <Field k="Geographic presence" v={m.geographic_presence} />
        <Field k="Product launches"    v={m.product_launches} />
        <Field k="Press & PR"          v={m.press_pr} />
        <Field k="Social activity"     v={m.social_media_activity} />
      </Block>
    );
  } else if (agentId === "icp_profiling" && data.icp) {
    const i = data.icp;
    body = (
      <Block>
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <span className="text-white/40 text-[12px]">Fit:</span>
          <span className="px-2 py-0.5 rounded brand-gradient text-white text-[10px] font-semibold uppercase">{i.product_fit}</span>
          <span className="text-white/40 text-[12px]">Score:</span>
          <span className="font-mono text-[12px]">{i.icp_score}</span>
          <span className="text-white/40 text-[12px]">Readiness:</span>
          <span className="text-[12px]">{i.engagement_readiness}</span>
          <span className="text-white/40 text-[12px]">Level:</span>
          <span className="text-[12px]">{i.prospect_level}</span>
        </div>
        <Field k="Justification" v={i.justification} />
        <Field k="Use case"      v={i.use_case} />
        {i.product_summary && <Collapsible label="Product summary (scraped from their site)" body={i.product_summary} />}
        {data.route === "escalate" && (
          <div className="mt-2 text-red-300 text-[11px]">⚠ Route: ESCALATE — refusing to draft.</div>
        )}
      </Block>
    );
  } else if (agentId === "person_signal" && data.person_signal) {
    const p = data.person_signal;
    body = (
      <Block>
        <Field k="Person"                v={p.person_name} />
        <Field k="Signal strength"       v={p.signal_strength} />
        <Field k="Writing style"         v={p.writing_style} />
        <Field k="Recent focus"          v={p.recent_focus} />
        <Field k="Engagement trend"      v={p.engagement_trend} />
        <Field k="Personalization angle" v={p.best_personalization_angle} />
        <Field k="Example opening line"  v={p.example_opening_line} mono />
        {p.core_themes?.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {p.core_themes.map((t: string, i: number) => (
              <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.06] border border-white/10">{t}</span>
            ))}
          </div>
        )}
      </Block>
    );
  } else if (agentId === "champion_scoring" && data.champion) {
    const c = data.champion;
    const np = c.normalized_profile;
    body = (
      <Block>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-white/40 text-[12px]">Champion score:</span>
          <span className="font-mono text-[14px] text-white">{c.champion_score} / 10</span>
          <span className="text-white/40 text-[12px]">Product fit:</span>
          <span className="text-[12px]">{c.product_fit}</span>
        </div>
        <Field k="Reasoning" v={c.reasoning} />
        {np && (
          <Collapsible
            label={`Normalized profile · ${np.current_title || "?"} @ ${np.current_company || "?"}`}
            body={
              <div className="space-y-1">
                <KV k="Name" v={np.full_name} />
                <KV k="Headline" v={np.headline} />
                <KV k="Location" v={np.location} />
                <KV k="Followers" v={np.followers?.toLocaleString?.() || np.followers} />
                <KV k="Connections" v={np.connections} />
                {np.about && <KV k="About" v={np.about} />}
                {np.experience?.length > 0 && (
                  <div className="pt-1">
                    <div className="text-[10px] uppercase text-white/40 mb-1">Experience</div>
                    {np.experience.map((e: any, i: number) => (
                      <div key={i} className="text-[11px] text-white/70 mb-0.5">
                        • <span className="text-white">{e.title}</span> @ {e.company} <span className="text-white/40">({e.duration})</span>
                      </div>
                    ))}
                  </div>
                )}
                {np.education?.length > 0 && (
                  <div className="pt-1">
                    <div className="text-[10px] uppercase text-white/40 mb-1">Education</div>
                    {np.education.map((e: any, i: number) => (
                      <div key={i} className="text-[11px] text-white/70 mb-0.5">
                        • {e.school} <span className="text-white/40">{e.degree}</span>
                      </div>
                    ))}
                  </div>
                )}
                {np.skills?.length > 0 && (
                  <div className="pt-1">
                    <div className="text-[10px] uppercase text-white/40 mb-1">Top skills</div>
                    <div className="flex flex-wrap gap-1">
                      {np.skills.map((s: string, i: number) => (
                        <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.06] border border-white/10">{s}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            }
          />
        )}
      </Block>
    );
  } else if (agentId === "drafting" && data.draft) {
    const d = data.draft;
    body = (
      <Block>
        <Field k="Subject"      v={d.subject} />
        <Field k="Greeting"     v={d.greeting} />
        <Field k="Introduction" v={d.introduction} />
        <Field k="Pain point"   v={d.pain_point} />
        <Field k="Product desc" v={d.product_desc} />
        {d.bullet_points?.length > 0 && (
          <div className="mt-1">
            <div className="text-[11px] text-white/40 mb-1">Bullet points</div>
            <ul className="text-[12px] text-white/80 space-y-0.5">
              {d.bullet_points.map((b: string, i: number) => <li key={i}>• {b}</li>)}
            </ul>
          </div>
        )}
        <Field k="CTA" v={d.cta} />
      </Block>
    );
  }

  return (
    <>
      {body}
      {citations.length > 0 && <CitationChips items={citations} />}
    </>
  );
}

function RawToggle({ data, open, onToggle }: { data: any; open: boolean; onToggle: () => void }) {
  return (
    <div className="mt-2 border-t border-white/5 pt-2">
      <button onClick={onToggle} className="text-[10px] uppercase tracking-wider text-white/40 hover:text-white/70">
        {open ? "▾ Hide raw output" : "▸ Show raw output (full JSON)"}
      </button>
      {open && (
        <pre className="mt-2 bg-black/40 border border-white/5 rounded-md p-2 text-[10.5px] leading-snug text-white/70 overflow-x-auto max-h-80 scrollbar-thin whitespace-pre-wrap break-words">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

function CitationChips({ items }: { items: { url: string; title?: string }[] }) {
  const [show, setShow] = useState(false);
  const visible = show ? items : items.slice(0, 6);
  return (
    <div className="mt-2 pt-2 border-t border-white/5">
      <div className="flex items-center justify-between mb-1">
        <div className="text-[10px] uppercase tracking-wider text-white/40">Sources · {items.length}</div>
        {items.length > 6 && (
          <button onClick={() => setShow((s) => !s)} className="text-[10px] text-white/50 hover:text-white">
            {show ? "show fewer" : `show all ${items.length}`}
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-1">
        {visible.map((c, i) => {
          let host = "";
          try { host = new URL(c.url).hostname.replace(/^www\./, ""); } catch { host = c.url.slice(0, 40); }
          return (
            <a key={i} href={c.url} target="_blank" rel="noopener noreferrer"
              title={c.title || c.url}
              className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.05] hover:bg-white/[0.1] text-white/70 hover:text-white border border-white/10 transition truncate max-w-[220px]">
              {host}
            </a>
          );
        })}
      </div>
    </div>
  );
}

function Block({ children }: { children: React.ReactNode }) {
  return <div className="mt-2 text-[12px] space-y-1.5">{children}</div>;
}

function Field({ k, v, mono }: { k: string; v: any; mono?: boolean }) {
  if (v === undefined || v === null || v === "") return null;
  return (
    <div>
      <div className="text-[10.5px] uppercase tracking-wider text-white/40">{k}</div>
      <div className={clsx("text-white/85 leading-relaxed whitespace-pre-wrap break-words",
                           mono && "font-mono text-[11.5px] text-white/75")}>
        {typeof v === "string" ? v : JSON.stringify(v)}
      </div>
    </div>
  );
}

function KV({ k, v }: { k: string; v: any }) {
  if (!v) return null;
  return (
    <div className="text-[11.5px]">
      <span className="text-white/40">{k}: </span>
      <span className="text-white/80 whitespace-pre-wrap break-words">{typeof v === "string" ? v : JSON.stringify(v)}</span>
    </div>
  );
}

function Collapsible({ label, body }: { label: string; body: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-1">
      <button onClick={() => setOpen((o) => !o)}
        className="text-[10px] uppercase tracking-wider text-white/40 hover:text-white/70">
        {open ? "▾" : "▸"} {label}
      </button>
      {open && (
        <div className="mt-1 p-2 bg-black/30 border border-white/5 rounded">
          {typeof body === "string"
            ? <div className="text-[11.5px] text-white/75 leading-relaxed whitespace-pre-wrap break-words">{body}</div>
            : body}
        </div>
      )}
    </div>
  );
}
