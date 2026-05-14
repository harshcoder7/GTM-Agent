"use client";
import { useEffect, useState } from "react";
import { jget, jput } from "@/lib/api";

type Product = { name: string; short: string; fit_signals?: string[]; brochure_url?: string };
type Brain = {
  company?: { name?: string; sender_name?: string; sender_title?: string; sender_email?: string; website?: string };
  products?: Product[];
  target_icp?: string;
  preferred_tone?: string;
  allowlist_emails?: string[];
};

export default function BrainPage() {
  const [b, setB] = useState<Brain>({ products: [], company: {}, allowlist_emails: [] });
  const [loaded, setLoaded] = useState(false);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Fetch in background — render the form immediately so it always opens.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const d = await jget<Brain>("/api/brain");
        if (alive && d) setB({ products: [], company: {}, allowlist_emails: [], ...d });
      } catch (e: any) {
        if (alive) setErr(e.message || String(e));
      } finally {
        if (alive) setLoaded(true);
      }
    })();
    return () => { alive = false; };
  }, []);

  async function save() {
    setErr(null);
    try {
      await jput("/api/brain", b);
      setSaved(true); setTimeout(() => setSaved(false), 1800);
    } catch (e: any) {
      setErr(e.message || String(e));
    }
  }
  function addProduct() {
    setB({ ...b, products: [...(b.products || []), { name: "", short: "", fit_signals: [], brochure_url: "" }] });
  }
  function updateProduct(i: number, patch: Partial<Product>) {
    const ps = [...(b.products || [])]; ps[i] = { ...ps[i], ...patch }; setB({ ...b, products: ps });
  }
  function removeProduct(i: number) {
    const ps = [...(b.products || [])]; ps.splice(i, 1); setB({ ...b, products: ps });
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <header>
        <h1 className="text-3xl font-semibold">Company brain</h1>
        <p className="text-white/60 mt-1 text-sm">The only customer-specific config. All agent prompts read from here.</p>
        {!loaded && <div className="mt-2 text-[11px] text-white/40">Loading current values…</div>}
        {err && <div className="mt-2 text-[11px] text-red-300">⚠ {err} — you can still edit, Save will retry.</div>}
      </header>

      <div className="glass rounded-xl p-6 space-y-4">
        <div className="text-xs uppercase tracking-wider text-white/50">Your company</div>
        <div className="grid grid-cols-2 gap-3">
          <Inp label="Company name"   v={b.company?.name}         onChange={(v) => setB({ ...b, company: { ...b.company, name: v } })} />
          <Inp label="Website"        v={b.company?.website}      onChange={(v) => setB({ ...b, company: { ...b.company, website: v } })} />
          <Inp label="Sender name"    v={b.company?.sender_name}  onChange={(v) => setB({ ...b, company: { ...b.company, sender_name: v } })} />
          <Inp label="Sender title"   v={b.company?.sender_title} onChange={(v) => setB({ ...b, company: { ...b.company, sender_title: v } })} />
          <Inp label="Sender email"   v={b.company?.sender_email} onChange={(v) => setB({ ...b, company: { ...b.company, sender_email: v } })} />
          <Inp label="Preferred tone" v={b.preferred_tone}        onChange={(v) => setB({ ...b, preferred_tone: v })} />
        </div>
      </div>

      <div className="glass rounded-xl p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div className="text-xs uppercase tracking-wider text-white/50">Products</div>
          <button onClick={addProduct} className="text-xs px-3 py-1 rounded border border-white/15 hover:bg-white/5">+ Add product</button>
        </div>
        {(b.products || []).map((p, i) => (
          <div key={i} className="border border-white/10 rounded-lg p-5 space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <Inp label="Product name" v={p.name} onChange={(v) => updateProduct(i, { name: v })} />
              <Inp label="Brochure URL" v={p.brochure_url || ""} onChange={(v) => updateProduct(i, { brochure_url: v })} />
            </div>
            <TA label="Short description (what it does, who it's for)" v={p.short} onChange={(v) => updateProduct(i, { short: v })} rows={7} />
            <TA label="Fit signals (comma separated — when this product fits)"
              v={(p.fit_signals || []).join(", ")}
              onChange={(v) => updateProduct(i, { fit_signals: v.split(",").map((x) => x.trim()).filter(Boolean) })}
              rows={3} />
            <div className="pt-1 border-t border-white/5">
              <button onClick={() => removeProduct(i)} className="text-xs text-red-300/80 hover:text-red-300">Remove product</button>
            </div>
          </div>
        ))}
      </div>

      <div className="glass rounded-xl p-6 space-y-3">
        <div className="text-xs uppercase tracking-wider text-white/50">Target ICP</div>
        <TA label="Describe the kind of company you sell to (industry, size, signals, decision-makers)…"
          v={b.target_icp || ""} onChange={(v) => setB({ ...b, target_icp: v })} rows={5} />
      </div>

      <div className="glass rounded-xl p-6 space-y-3">
        <div className="text-xs uppercase tracking-wider text-white/50">Allowlist (real-send only)</div>
        <Inp label="Comma-separated emails — only these can receive real (non-draft) sends"
          v={(b.allowlist_emails || []).join(", ")}
          onChange={(v) => setB({ ...b, allowlist_emails: v.split(",").map((x) => x.trim()).filter(Boolean) })} />
      </div>

      <div className="flex items-center gap-3 sticky bottom-0 bg-[#0b0d12]/80 backdrop-blur py-3">
        <button onClick={save} className="brand-gradient text-white px-5 py-2.5 rounded-md font-medium">Save brain</button>
        {saved && <span className="text-emerald-300 text-sm">✓ Saved</span>}
      </div>
    </div>
  );
}

function Inp({ label, v, onChange }: any) {
  return (
    <label className="block">
      <div className="text-[11px] text-white/50 mb-1">{label}</div>
      <input value={v || ""} onChange={(e) => onChange(e.target.value)}
        className="w-full bg-black/30 border border-white/10 rounded-md p-2 text-sm" />
    </label>
  );
}
function TA({ label, v, onChange, rows }: any) {
  return (
    <label className="block">
      <div className="text-[11px] text-white/50 mb-1">{label}</div>
      <textarea value={v || ""} onChange={(e) => onChange(e.target.value)} rows={rows || 2}
        className="w-full bg-black/30 border border-white/10 rounded-md p-2 text-sm" />
    </label>
  );
}
