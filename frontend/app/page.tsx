"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { jget, jpost, API } from "@/lib/api";
import { StatusPill } from "@/components/StatusPill";

type Run = { id: string; created_at: string; status: string; icp_score?: number;
  product_fit?: string; prospect: any; route_decision?: string };

export default function NewRunPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [runs, setRuns] = useState<Run[]>([]);
  const [form, setForm] = useState({
    full_name: "", company: "", linkedin_url: "", job_title: "", email: "", domain: "",
  });
  const [forcePh, setForcePh] = useState(false);
  const [cycles, setCycles] = useState(1);

  useEffect(() => {
    jget<Run[]>("/api/runs?limit=8").then(setRuns).catch(() => {});
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;          // hard-stop double submits
    setBusy(true);
    try {
      const r = await jpost<{ run_id: string }>("/api/runs", {
        prospect: form, force_placeholder: forcePh, research_cycles: cycles,
      });
      router.push(`/runs/${r.run_id}`);
      // intentionally leave busy=true so the button stays disabled until nav completes
    } catch (err: any) {
      alert(err.message || String(err));
      setBusy(false);
    }
  }

  async function uploadCsv(file: File) {
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch(`${API}/api/bulk`, { method: "POST", body: fd });
    const j = await r.json();
    if (j.run_ids?.length) router.push(`/runs/${j.run_ids[0]}`);
  }

  return (
    <div className="space-y-8">
      <header>
        <div className="text-xs text-white/40 uppercase tracking-wider">PS-3 GTM</div>
        <h1 className="text-3xl font-semibold mt-1">Personalised outreach pipeline</h1>
        <p className="text-white/60 mt-2 max-w-2xl">
          Submit a prospect. Six agents stream in real time. One human gate. Output: a Gmail draft grounded in real public signal.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-8">
        <form onSubmit={submit} className="glass rounded-xl p-6 space-y-4">
          <div className="text-xs uppercase tracking-wider text-white/50">Single prospect</div>
          <div className="grid grid-cols-2 gap-3">
            <Inp label="Full name *"  value={form.full_name}    onChange={(v) => setForm({ ...form, full_name: v })} required />
            <Inp label="Company *"    value={form.company}      onChange={(v) => setForm({ ...form, company: v })} required />
            <Inp label="LinkedIn URL" value={form.linkedin_url} onChange={(v) => setForm({ ...form, linkedin_url: v })} />
            <Inp label="Title"        value={form.job_title}    onChange={(v) => setForm({ ...form, job_title: v })} />
            <Inp label="Email"        value={form.email}        onChange={(v) => setForm({ ...form, email: v })} />
            <Inp label="Domain"       value={form.domain}       onChange={(v) => setForm({ ...form, domain: v })} placeholder="acme.com" />
          </div>
          <div className="flex flex-wrap items-center gap-6 pt-1">
            <label className="flex items-center gap-2 text-xs text-white/70">
              <span>Research depth</span>
              <div className="flex rounded-md overflow-hidden border border-white/10">
                {[1, 2, 3].map((n) => (
                  <button type="button" key={n}
                    onClick={() => setCycles(n)}
                    className={`px-3 py-1 text-xs font-mono transition ${cycles === n ? "brand-gradient text-white" : "bg-black/30 text-white/60 hover:bg-white/5"}`}>
                    {n}
                  </button>
                ))}
                <span className="px-2 py-1 text-[10px] text-white/40 self-center">cycle{cycles > 1 ? "s" : ""}</span>
              </div>
              <span className="text-[10px] text-white/40">
                {cycles === 1 ? "~45s · fastest" : cycles === 2 ? "~90s · balanced" : "~140s · thorough"}
              </span>
            </label>
            <label className="flex items-center gap-2 text-xs text-white/60">
              <input type="checkbox" checked={forcePh} onChange={(e) => setForcePh(e.target.checked)} />
              Inject placeholder leak (demo edge case)
            </label>
          </div>
          <div className="flex gap-3">
            <button disabled={busy} className="brand-gradient text-white px-5 py-2.5 rounded-md font-medium disabled:opacity-50">
              {busy ? "Starting…" : "Run pipeline →"}
            </button>
            <label className="px-4 py-2.5 rounded-md border border-white/15 text-sm cursor-pointer hover:bg-white/5">
              Upload CSV
              <input type="file" accept=".csv" className="hidden"
                onChange={(e) => e.target.files?.[0] && uploadCsv(e.target.files[0])} />
            </label>
          </div>
        </form>

        <div className="glass rounded-xl p-6">
          <div className="text-xs uppercase tracking-wider text-white/50 mb-3">Recent runs</div>
          <div className="space-y-2">
            {runs.length === 0 && <div className="text-white/30 text-sm">No runs yet.</div>}
            {runs.map((r) => (
              <Link key={r.id} href={`/runs/${r.id}`}
                className="block px-3 py-2 rounded-md hover:bg-white/5 transition">
                <div className="flex items-center justify-between gap-2">
                  <div className="truncate">
                    <div className="text-sm">{r.prospect?.full_name || "—"} <span className="text-white/40">· {r.prospect?.company}</span></div>
                    <div className="text-[11px] text-white/40 font-mono">{r.id}</div>
                  </div>
                  <StatusPill status={r.status} />
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Inp({ label, value, onChange, required, placeholder }: any) {
  return (
    <label className="block">
      <div className="text-[11px] text-white/50 mb-1">{label}</div>
      <input value={value} onChange={(e) => onChange(e.target.value)} required={required} placeholder={placeholder}
        className="w-full bg-black/30 border border-white/10 rounded-md p-2 text-sm" />
    </label>
  );
}

