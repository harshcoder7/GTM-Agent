"use client";
import { useEffect, useRef, useState } from "react";
import { API } from "./api";

export type AgentEvent = { event: string; data: any };

const MAX_ERRORS = 5;     // give up after this many consecutive errors
const ERROR_BUDGET_MS = 30_000; // ...within this window

export function useRunStream(runId: string | null, opts?: { skipLive?: boolean }) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [closed, setClosed] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  // External seed — used to replay a terminal run's persisted history.
  const seed = (hist: AgentEvent[]) => setEvents(hist);

  useEffect(() => {
    if (!runId) return;
    setEvents([]); setClosed(false);
    if (opts?.skipLive) { setClosed(true); return; }

    const es = new EventSource(`${API}/api/runs/${runId}/stream`);
    esRef.current = es;
    const errors: number[] = [];
    let gaveUp = false;

    const types = [
      "agent.status", "agent.tool", "agent.token", "agent.result", "agent.error",
      "gate.open", "gate.resolved", "run.complete",
    ];
    const handler = (type: string) => (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        setEvents((prev) => [...prev, { event: type, data }]);
        if (type === "run.complete") { setClosed(true); es.close(); }
        // any successful event resets the error budget
        errors.length = 0;
      } catch {}
    };
    types.forEach((t) => es.addEventListener(t, handler(t) as any));

    es.onerror = () => {
      if (gaveUp) return;
      const now = Date.now();
      errors.push(now);
      // drop errors older than the budget window
      while (errors.length && now - errors[0] > ERROR_BUDGET_MS) errors.shift();
      // closed state = the server has finished and won't accept more; don't retry
      if (es.readyState === EventSource.CLOSED || errors.length >= MAX_ERRORS) {
        gaveUp = true;
        setClosed(true);
        es.close();
      }
    };

    return () => { es.close(); };
  }, [runId]);

  return { events, closed, seed };
}
