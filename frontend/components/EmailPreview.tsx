"use client";

export function EmailPreview({ html, subject }: { html: string; subject: string }) {
  return (
    <div className="rounded-xl border border-white/10 overflow-hidden">
      <div className="px-4 py-2 bg-white/[0.04] border-b border-white/10 flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-red-400" />
        <div className="w-2 h-2 rounded-full bg-yellow-400" />
        <div className="w-2 h-2 rounded-full bg-emerald-400" />
        <div className="ml-3 text-xs text-white/60">Subject: <span className="text-white">{subject}</span></div>
      </div>
      <iframe
        title="Email preview"
        srcDoc={`<!doctype html><html><head><meta charset="utf-8"/></head>${html}</html>`}
        sandbox=""
        className="w-full bg-white"
        style={{ height: 760, border: 0 }}
      />
    </div>
  );
}
