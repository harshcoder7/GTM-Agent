"use client";
import { useEffect, useState } from "react";
import { jget, jpost, API } from "@/lib/api";
import { EmailPreview } from "./EmailPreview";
import clsx from "clsx";

type Draft = {
  id: number; version: number;
  subject: string; greeting: string; introduction: string;
  pain_point: string; product_desc: string; bullet_points: string[]; cta: string;
  html: string; approved: boolean;
};
type SafetyCheck = { check: string; passed: boolean; explanation: string };

export function GateReview({ runId, latest, onResolved }: {
  runId: string; latest: Draft; onResolved: () => void;
}) {
  const [edit, setEdit] = useState<Draft>(latest);
  const [checks, setChecks] = useState<SafetyCheck[]>([]);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftDone, setDraftDone] = useState<{mode?: string, draftId?: string} | null>(null);

  useEffect(() => { setEdit(latest); }, [latest.id]);
  useEffect(() => {
    jget<{checks: SafetyCheck[]}>(`/api/runs/${runId}/safety`).then((r) => setChecks(r.checks)).catch(() => {});
  }, [runId, latest.id]);

  const allPass = checks.length > 0 && checks.every((c) => c.passed);

  async function act(decision: string) {
    setBusy(true); setError(null);
    try {
      const payload: any = { decision };
      if (decision === "edit_approve") {
        payload.edits = {
          subject: edit.subject, greeting: edit.greeting, introduction: edit.introduction,
          pain_point: edit.pain_point, product_desc: edit.product_desc,
          bullet_points: edit.bullet_points, cta: edit.cta,
        };
      }
      const r = await jpost<any>(`/api/runs/${runId}/review`, payload);
      if (r.blocked) {
        setChecks(r.failed_checks ? [...r.failed_checks, ...checks.filter((c) => c.passed)] : checks);
        setError("Safety checks failed — fix the draft before approving.");
      } else if (r.draft_id) {
        setDraftDone({ mode: r.mode, draftId: r.draft_id });
        onResolved();
      } else if (decision === "reject") {
        onResolved();
      } else if (decision === "regenerate") {
        onResolved();
      }
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  if (draftDone) {
    return (
      <div className="glass rounded-xl p-8 text-center">
        <div className="text-emerald-400 text-xl font-semibold mb-2">✓ Gmail draft created</div>
        <div className="text-sm text-white/60">
          Mode: {draftDone.mode} · Draft id: <span className="font-mono">{draftDone.draftId}</span>
        </div>
        <a href="https://mail.google.com/mail/u/0/#drafts" target="_blank" rel="noopener noreferrer"
          className="inline-block mt-5 px-4 py-2 rounded-md brand-gradient text-white font-medium">
          Open Gmail Drafts →
        </a>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6">
      <div className="space-y-4">
        <EmailPreview html={edit.html} subject={edit.subject} />
        {editing && (
          <div className="glass rounded-xl p-5 space-y-3">
            <Editable k="subject"      label="Subject"       v={edit.subject}      onChange={(v) => setEdit({ ...edit, subject: v })} />
            <Editable k="greeting"     label="Greeting"      v={edit.greeting}     onChange={(v) => setEdit({ ...edit, greeting: v })} />
            <Editable k="introduction" label="Introduction"  v={edit.introduction} onChange={(v) => setEdit({ ...edit, introduction: v })} ta />
            <Editable k="pain_point"   label="Pain point"    v={edit.pain_point}   onChange={(v) => setEdit({ ...edit, pain_point: v })} ta />
            <Editable k="product_desc" label="Product desc"  v={edit.product_desc} onChange={(v) => setEdit({ ...edit, product_desc: v })} ta />
            <div>
              <div className="text-xs text-white/50 mb-1">Bullet points (one per line)</div>
              <textarea
                value={edit.bullet_points.join("\n")}
                onChange={(e) => setEdit({ ...edit, bullet_points: e.target.value.split("\n").filter(Boolean) })}
                className="w-full bg-black/30 border border-white/10 rounded-md p-2 text-sm font-mono"
                rows={4}
              />
            </div>
            <Editable k="cta" label="CTA" v={edit.cta} onChange={(v) => setEdit({ ...edit, cta: v })} />
          </div>
        )}
      </div>

      <div className="space-y-4">
        <div className="glass rounded-xl p-5">
          <div className="text-xs uppercase tracking-wider text-white/50 mb-3">Safety checks</div>
          <ul className="space-y-2 text-sm">
            {checks.length === 0 && <li className="text-white/40 text-xs">Running…</li>}
            {checks.map((c, i) => (
              <li key={i} className="flex gap-2 items-start">
                <span className={clsx(
                  "w-4 h-4 rounded-full text-[10px] flex items-center justify-center font-bold shrink-0 mt-0.5",
                  c.passed ? "bg-emerald-500/30 text-emerald-300" : "bg-red-500/30 text-red-300"
                )}>{c.passed ? "✓" : "✗"}</span>
                <div className="min-w-0">
                  <div className="text-white/90 capitalize">{c.check.replace(/_/g, " ")}</div>
                  <div className="text-[11px] text-white/50">{c.explanation}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="glass rounded-xl p-5 space-y-2">
          <div className="text-xs uppercase tracking-wider text-white/50 mb-2">Actions</div>
          <button onClick={() => act(editing ? "edit_approve" : "approve")}
            disabled={busy || !allPass}
            className={clsx(
              "w-full px-4 py-2.5 rounded-md font-medium transition",
              allPass ? "brand-gradient text-white hover:opacity-90" : "bg-white/5 text-white/30 cursor-not-allowed",
            )}>
            {editing ? "Approve edited draft" : "Approve & create Gmail draft"}
          </button>
          <button onClick={() => setEditing((e) => !e)} disabled={busy}
            className="w-full px-4 py-2 rounded-md border border-white/15 text-sm hover:bg-white/5">
            {editing ? "Cancel edits" : "Edit draft"}
          </button>
          <button onClick={() => act("regenerate")} disabled={busy}
            className="w-full px-4 py-2 rounded-md border border-white/15 text-sm hover:bg-white/5">
            Regenerate
          </button>
          <button onClick={() => act("reject")} disabled={busy}
            className="w-full px-4 py-2 rounded-md border border-red-500/30 text-sm text-red-300 hover:bg-red-500/10">
            Reject run
          </button>
          {error && <div className="text-xs text-red-300 mt-2">{error}</div>}
          {!allPass && checks.length > 0 && (
            <div className="text-[11px] text-white/40 leading-relaxed mt-2">
              Approve is disabled until all checks pass.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Editable({ k, label, v, onChange, ta }: { k: string; label: string; v: string; onChange: (v: string) => void; ta?: boolean }) {
  return (
    <div>
      <div className="text-xs text-white/50 mb-1">{label}</div>
      {ta ? (
        <textarea value={v} onChange={(e) => onChange(e.target.value)}
          className="w-full bg-black/30 border border-white/10 rounded-md p-2 text-sm" rows={3} />
      ) : (
        <input value={v} onChange={(e) => onChange(e.target.value)}
          className="w-full bg-black/30 border border-white/10 rounded-md p-2 text-sm" />
      )}
    </div>
  );
}
