"use client";
import { useEffect, useState } from "react";
import { jget, jpost, jput, API } from "@/lib/api";

type KeyStatus = { configured: boolean; preview: string };
type KeysState = { openai: KeyStatus; tavily: KeyStatus; apify: KeyStatus };

type GmailStatus = {
  has_api_key: boolean;
  has_auth_config: boolean;
  auth_config_id_preview: string;
  entity_id: string;
  connection_id: string;
  connected: boolean;
  status: string;
  email: string | null;
  error?: string;
};

export default function Settings() {
  const [backend, setBackend] = useState<any>(null);
  const [deps, setDeps] = useState<any>(null);

  const [backendErr, setBackendErr] = useState<string | null>(null);
  const [depsErr, setDepsErr] = useState<string | null>(null);

  useEffect(() => {
    jget("/health").then(setBackend).catch((e) => { setBackendErr(e.message || String(e)); });
    jget("/api/health/deps").then(setDeps).catch((e) => { setDepsErr(e.message || String(e)); });
  }, []);

  return (
    <div className="space-y-6 max-w-3xl">
      <header>
        <h1 className="text-3xl font-semibold">Settings</h1>
        <p className="text-white/60 mt-1 text-sm">Manage API keys and Gmail connection.</p>
      </header>

      <HealthPanel backend={backend} deps={deps} backendErr={backendErr} depsErr={depsErr} />
      <KeysPanel />
      <GmailPanel />
    </div>
  );
}

/* ---------------- Health ---------------- */

function HealthPanel({ backend, deps, backendErr, depsErr }: {
  backend: any; deps: any; backendErr: string | null; depsErr: string | null;
}) {
  return (
    <div className="glass rounded-xl p-6 space-y-3">
      <div className="text-xs uppercase tracking-wider text-white/50 mb-2">Service health</div>
      <HealthRow label="Backend" state={backendErr ? "error" : backend ? (backend.ok ? "ok" : "down") : "loading"}
                 value={backend?.ok ? "OK" : backendErr || "—"} />
      <HealthRow label="Send mode" state={backend ? "ok" : "loading"} value={backend?.send_mode || "—"} />
      <HealthRow label="Deep Research API"
                 state={depsErr ? "error" : deps ? (deps.deep_research ? "ok" : "down") : "loading"}
                 value={deps?.deep_research ? "OK" : depsErr || "—"} />
      {(backendErr || depsErr) && (
        <div className="text-[11px] text-red-300 mt-2">
          {backendErr && <div>Backend fetch failed: {backendErr}</div>}
          {depsErr && <div>Deps fetch failed: {depsErr}</div>}
          Hint: if your browser shows a CORS error in DevTools, the backend's
          <code className="text-white"> CORS_ORIGINS</code> may not include this page's origin. Restart the backend after editing <code className="text-white">.env</code>.
        </div>
      )}
    </div>
  );
}

function HealthRow({ label, state, value }: { label: string; state: "loading" | "ok" | "down" | "error"; value: string }) {
  const cls = state === "ok" ? "bg-emerald-500/30 text-emerald-300"
            : state === "loading" ? "bg-white/10 text-white/60"
            : "bg-red-500/30 text-red-300";
  return (
    <div className="flex items-center justify-between">
      <div className="text-white/80 text-sm">{label}</div>
      <div className={`text-xs px-2 py-0.5 rounded-full ${cls} flex items-center gap-1`}>
        {state === "loading" && <span className="w-1.5 h-1.5 rounded-full bg-white/40 animate-pulseGlow" />}
        {value}
      </div>
    </div>
  );
}

/* ---------------- API keys (OpenAI / Tavily / Apify) ---------------- */

function KeysPanel() {
  const [keys, setKeys] = useState<KeysState | null>(null);
  const [vals, setVals] = useState({ openai_api_key: "", tavily_api_key: "", apify_token: "" });
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<Record<string, string>>({});

  async function reload() {
    try { setKeys(await jget<KeysState>("/api/keys")); } catch { setKeys(null); }
  }
  useEffect(() => { reload(); }, []);

  async function saveOne(field: keyof typeof vals) {
    const v = vals[field].trim();
    if (!v) return;
    setBusy(field);
    try {
      await jput("/api/keys", { [field]: v });
      setVals({ ...vals, [field]: "" });
      setMsg({ ...msg, [field]: "Saved" });
      await reload();
      setTimeout(() => setMsg((m) => { const c = { ...m }; delete c[field]; return c; }), 2000);
    } catch (e: any) {
      setMsg({ ...msg, [field]: `Error: ${e.message || e}` });
    } finally { setBusy(null); }
  }

  async function testOne(name: "openai" | "tavily" | "apify") {
    setBusy(`test-${name}`);
    try {
      const r = await jpost<any>(`/api/keys/test/${name}`, {});
      setMsg({ ...msg, [name]: r.ok ? `✓ valid${r.username ? ` (${r.username})` : ""}` : `✗ ${r.error || r.status || "invalid"}` });
    } catch (e: any) {
      setMsg({ ...msg, [name]: `✗ ${e.message || e}` });
    } finally { setBusy(null); }
  }

  async function clearOne(field: keyof typeof vals) {
    setBusy(field);
    try {
      await jput("/api/keys", { [field]: "" });
      await reload();
    } finally { setBusy(null); }
  }

  return (
    <div className="glass rounded-xl p-6 space-y-5">
      <div className="text-xs uppercase tracking-wider text-white/50">API keys</div>

      <KeyField
        label="OpenAI" testName="openai" field="openai_api_key"
        placeholder="sk-..."
        status={keys?.openai} value={vals.openai_api_key}
        onChange={(v) => setVals({ ...vals, openai_api_key: v })}
        onSave={() => saveOne("openai_api_key")} onTest={() => testOne("openai")}
        onClear={() => clearOne("openai_api_key")}
        busy={busy} msg={msg.openai_api_key || msg.openai}
        help="Used by all 6 agents + the deep-research service. Get one at platform.openai.com."
      />

      <KeyField
        label="Tavily" testName="tavily" field="tavily_api_key"
        placeholder="tvly-..."
        status={keys?.tavily} value={vals.tavily_api_key}
        onChange={(v) => setVals({ ...vals, tavily_api_key: v })}
        onSave={() => saveOne("tavily_api_key")} onTest={() => testOne("tavily")}
        onClear={() => clearOne("tavily_api_key")}
        busy={busy} msg={msg.tavily_api_key || msg.tavily}
        help="Web search used by Lead Enrichment + Market Intelligence. Sign up at tavily.com."
      />

      <KeyField
        label="Apify" testName="apify" field="apify_token"
        placeholder="apify_api_..."
        status={keys?.apify} value={vals.apify_token}
        onChange={(v) => setVals({ ...vals, apify_token: v })}
        onSave={() => saveOne("apify_token")} onTest={() => testOne("apify")}
        onClear={() => clearOne("apify_token")}
        busy={busy} msg={msg.apify_token || msg.apify}
        help="LinkedIn scraping (posts + champion profile). Get a token at console.apify.com."
      />
    </div>
  );
}

function KeyField({ label, field, testName, placeholder, status, value, onChange, onSave, onTest, onClear, busy, msg, help }: any) {
  const isBusy = busy === field || busy === `test-${testName}`;
  return (
    <div className="space-y-2 border-t border-white/5 pt-4 first:border-t-0 first:pt-0">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium">{label}</div>
        {status?.configured ? (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/30 text-emerald-300 uppercase tracking-wider">
            saved · <span className="font-mono">{status.preview}</span>
          </span>
        ) : (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/10 text-white/60 uppercase tracking-wider">not set</span>
        )}
      </div>
      <div className="flex gap-2">
        <input type="password" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
          className="flex-1 bg-black/30 border border-white/10 rounded-md p-2 text-sm font-mono" />
        <button onClick={onSave} disabled={!value.trim() || isBusy}
          className="brand-gradient text-white px-3 py-2 rounded-md text-sm font-medium disabled:opacity-30 disabled:cursor-not-allowed">
          Save
        </button>
        {status?.configured && (
          <>
            <button onClick={onTest} disabled={isBusy}
              className="px-3 py-2 rounded-md border border-white/15 text-sm hover:bg-white/5 disabled:opacity-50">Test</button>
            <button onClick={onClear} disabled={isBusy}
              className="px-3 py-2 rounded-md border border-red-500/30 text-sm text-red-300 hover:bg-red-500/10 disabled:opacity-50">Clear</button>
          </>
        )}
      </div>
      <div className="flex justify-between gap-3 text-[11px]">
        <span className="text-white/40">{help}</span>
        {msg && <span className={msg.startsWith("✓") || msg === "Saved" ? "text-emerald-300" : "text-red-300"}>{msg}</span>}
      </div>
    </div>
  );
}

/* ---------------- Composio + Gmail OAuth ---------------- */

function GmailPanel() {
  const [gm, setGm] = useState<GmailStatus | null>(null);
  const [composioKey, setComposioKey] = useState("");
  const [authCfg, setAuthCfg] = useState("");
  const [entity, setEntity] = useState("default");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function reload(withPing: boolean = false) {
    try {
      const url = withPing ? "/api/composio/gmail/status?ping=1" : "/api/composio/gmail/status";
      const s = await jget<GmailStatus>(url);
      setGm(s);
      if (s.entity_id) setEntity(s.entity_id);
    } catch {
      setGm(null);
    }
  }
  useEffect(() => { reload(false); }, []);

  async function saveKey() {
    if (!composioKey.trim()) return;
    setBusy("key"); setErr(null);
    try {
      await jput("/api/composio/api-key", { api_key: composioKey.trim() });
      setComposioKey("");
      await reload();
    } catch (e: any) { setErr(e.message || String(e)); }
    finally { setBusy(null); }
  }

  async function saveAuthCfg() {
    if (!authCfg.trim()) return;
    setBusy("auth"); setErr(null);
    try {
      await jput("/api/composio/auth-config", { auth_config_id: authCfg.trim() });
      setAuthCfg("");
      await reload();
    } catch (e: any) { setErr(e.message || String(e)); }
    finally { setBusy(null); }
  }

  async function connect() {
    setBusy("connect"); setErr(null);
    try {
      const r = await jpost<{ redirect_url: string }>("/api/composio/gmail/connect", { entity_id: entity });
      window.open(r.redirect_url, "_blank", "noopener");
      // After OAuth lands, poll WITH ping so the UI flips to "connected".
      setTimeout(() => { reload(true); }, 3000);
      setTimeout(() => { reload(true); }, 8000);
      setTimeout(() => { reload(true); }, 15000);
    } catch (e: any) { setErr(e.message || String(e)); }
    finally { setBusy(null); }
  }

  async function disconnect() {
    setBusy("disconnect");
    try {
      await jpost("/api/composio/gmail/disconnect", {});
      await reload();
    } finally { setBusy(null); }
  }

  return (
    <div className="glass rounded-xl p-6 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-wider text-white/50">Gmail · via Composio</div>
          <div className="text-sm text-white/80 mt-0.5">
            When you Approve a draft at Gate 1, it lands in the Drafts folder of this Gmail account.
          </div>
        </div>
        <GmailBadge gm={gm} />
      </div>

      {gm?.connected && (
        <div className="rounded-md bg-emerald-500/10 border border-emerald-500/30 px-3 py-2 text-sm">
          <span className="text-emerald-300">✓ Connected</span>
          {gm.email && <> · Drafts → <span className="font-mono text-white">{gm.email}</span></>}
          <span className="text-white/40"> · entity <span className="font-mono">{gm.entity_id}</span></span>
        </div>
      )}

      {/* Step 1 — Composio API key */}
      <Step n={1} title="Composio API key" done={!!gm?.has_api_key}>
        <div className="flex gap-2">
          <input type="password" placeholder="paste Composio API key…" value={composioKey}
            onChange={(e) => setComposioKey(e.target.value)}
            className="flex-1 bg-black/30 border border-white/10 rounded-md p-2 text-sm font-mono" />
          <button onClick={saveKey} disabled={busy === "key" || !composioKey.trim()}
            className="brand-gradient text-white px-3 py-2 rounded-md text-sm font-medium disabled:opacity-30">
            Save
          </button>
        </div>
        <Tip>Get it at <a className="text-brand-soft underline" href="https://app.composio.dev" target="_blank" rel="noopener noreferrer">app.composio.dev</a> → Settings → API Keys.</Tip>
      </Step>

      {/* Step 2 — Gmail auth_config_id */}
      <Step n={2} title="Gmail auth config id" done={!!gm?.has_auth_config} disabled={!gm?.has_api_key}>
        <div className="flex gap-2">
          <input placeholder={gm?.has_auth_config ? `currently: ${gm.auth_config_id_preview}` : "auth_config_xxxxxx"}
            value={authCfg} onChange={(e) => setAuthCfg(e.target.value)}
            className="flex-1 bg-black/30 border border-white/10 rounded-md p-2 text-sm font-mono" />
          <button onClick={saveAuthCfg} disabled={busy === "auth" || !authCfg.trim()}
            className="brand-gradient text-white px-3 py-2 rounded-md text-sm font-medium disabled:opacity-30">
            Save
          </button>
        </div>
        <Tip>
          In Composio dashboard → <strong>Auth Configs</strong> → <strong>+ Create new</strong> → pick <strong>Gmail</strong> → copy the id (starts with <code className="text-white">auth_config_</code>).
        </Tip>
      </Step>

      {/* Step 3 — connect */}
      <Step n={3} title="Connect Gmail" done={!!gm?.connected} disabled={!gm?.has_api_key || !gm?.has_auth_config}>
        <div className="flex items-center gap-2 flex-wrap">
          <input value={entity} onChange={(e) => setEntity(e.target.value)}
            placeholder="entity id (default)"
            className="bg-black/30 border border-white/10 rounded-md p-2 text-sm font-mono w-48" />
          {!gm?.connected ? (
            <button onClick={connect} disabled={busy === "connect" || !gm?.has_api_key || !gm?.has_auth_config}
              className="brand-gradient text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-30">
              {busy === "connect" ? "Opening OAuth…" : "Connect Gmail →"}
            </button>
          ) : (
            <button onClick={disconnect} disabled={busy === "disconnect"}
              className="px-4 py-2 rounded-md border border-red-500/30 text-sm text-red-300 hover:bg-red-500/10">
              Disconnect
            </button>
          )}
          <button onClick={() => reload(true)} className="px-3 py-2 rounded-md border border-white/15 text-sm hover:bg-white/5">
            Re-check
          </button>
        </div>
        <Tip>
          Clicking <strong>Connect Gmail</strong> opens Google OAuth in a new tab. Pick the account you want drafts to land in, grant access, then come back here and click <strong>Re-check</strong>.
        </Tip>
      </Step>

      {err && <div className="text-xs text-red-300">{err}</div>}
      {gm?.status && gm?.status !== "no_api_key" && gm?.status !== "no_auth_config" && (
        <div className="text-[11px] text-white/40">
          Composio status: <span className="font-mono">{gm.status}</span>
          {gm.connection_id && <> · connection <span className="font-mono">{gm.connection_id.slice(0, 10)}…</span></>}
        </div>
      )}
    </div>
  );
}

function Step({ n, title, done, disabled, children }: any) {
  return (
    <div className={`rounded-lg border ${done ? "border-emerald-500/30 bg-emerald-500/[0.04]" : disabled ? "border-white/5 bg-white/[0.01] opacity-60" : "border-white/10"} p-4 space-y-2`}>
      <div className="flex items-center gap-2">
        <div className={`w-5 h-5 rounded-full text-[11px] flex items-center justify-center font-semibold ${done ? "bg-emerald-500 text-white" : "bg-white/10 text-white/60"}`}>
          {done ? "✓" : n}
        </div>
        <div className="text-sm font-medium">{title}</div>
      </div>
      {children}
    </div>
  );
}

function Tip({ children }: { children: React.ReactNode }) {
  return <div className="text-[11px] text-white/50 leading-relaxed">{children}</div>;
}

function GmailBadge({ gm }: { gm: GmailStatus | null }) {
  if (!gm) return <Pill tone="grey" text="loading" />;
  if (gm.connected) return <Pill tone="emerald" text="connected" />;
  if (gm.has_api_key && gm.has_auth_config) return <Pill tone="yellow" text="awaiting connect" />;
  if (gm.has_api_key) return <Pill tone="yellow" text="needs auth config" />;
  return <Pill tone="grey" text="not configured" />;
}

function Pill({ tone, text }: { tone: string; text: string }) {
  const m: Record<string, string> = {
    emerald: "bg-emerald-500/30 text-emerald-300",
    red:     "bg-red-500/30 text-red-300",
    yellow:  "bg-yellow-500/30 text-yellow-200",
    grey:    "bg-white/10 text-white/60",
  };
  return <span className={`text-[10px] px-2 py-0.5 rounded-full uppercase tracking-wider ${m[tone]}`}>{text}</span>;
}

