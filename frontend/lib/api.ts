// Compute API base URL at runtime so the frontend always uses the same
// hostname the browser is on. This sidesteps Windows + Docker Desktop's
// IPv6-vs-IPv4 localhost flakiness: if the user opens 127.0.0.1:3000, API
// calls go to 127.0.0.1:8000 (IPv4, works). If they open localhost:3000 and
// localhost resolves cleanly, calls go to localhost:8000. Either way works.

function computeApi(): string {
  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:8000`;
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

export const API = computeApi();

export async function jget<T = any>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, { cache: "no-store", ...init });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function jpost<T = any>(path: string, body: any, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body), ...init,
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function jput<T = any>(path: string, body: any, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body), ...init,
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function jdelete<T = any>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, { method: "DELETE", ...init });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
