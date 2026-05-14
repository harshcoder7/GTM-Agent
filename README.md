# GTM Agent — Personalised B2B Outreach Pipeline

Zamp ASA Case Study — **PS-3 GTM**. A six-agent pipeline that takes a prospect (name + company + LinkedIn) and produces a personalised Gmail draft grounded in real public signal. One human review gate before any draft is created. Fully dockerised — runs with one command.

> **Quickstart:** `docker compose up -d` from this folder, open **http://127.0.0.1:3000**, fire a prospect through the form.

---

## What it does, in one diagram

```
[Prospect form / CSV]
        │
        ▼
   FastAPI (:8000) ───SSE───▶  Next.js (:3000) — live agent cards + logs
        │
        ▼
   LangGraph-free asyncio orchestrator
        │
   1. Lead Enrichment        deep-research /research → OpenAI 10-field schema
   2. Market Intelligence    deep-research /signals  → OpenAI 7-field schema
   3. ICP Profiling          scrape site → product summary → score (Pro/Hive/Both, 1-10)
   4. LinkedIn Signal        Apify (harvestapi/linkedin-profile-posts) → engagement summary
   5. Champion Scoring       Apify (harvestapi/linkedin-profile-scraper) → 0-10 buyer score
   6. Drafting               assemble all context → email JSON + brochure link + HTML
        │
        ▼
   [Gate 1: Human review + 5 safety checks]
        │
        ▼
   Composio Gmail → GMAIL_CREATE_EMAIL_DRAFT  (lands in your Gmail Drafts)
```

The Deep Research Agent (`../deep-research-agent-sdr/`) runs as a sidecar on `:8771` — same engine, two prompt flavours (`/research` for firmographics, `/signals` for market intel).

For deeper architecture details see [`ARCHITECTURE.md`](./ARCHITECTURE.md). For original Langflow reference and per-agent design notes see [`docs/`](./docs/).

---

## Prerequisites

| Tool | Why | Where |
|---|---|---|
| Docker Desktop (Windows / macOS / Linux) | Runs the 3 containers + volume | https://www.docker.com/products/docker-desktop |
| The `deep-research-agent-sdr/` repo as a sibling folder | Built locally by docker-compose as the research sidecar | already present at `../deep-research-agent-sdr/` in this repo |
| OpenAI API key | LLM calls + structured output | https://platform.openai.com |
| Tavily API key | Web search inside deep-research | https://tavily.com |
| Apify token | LinkedIn scraping | https://console.apify.com |
| Composio API key + Gmail auth_config | Creates Gmail drafts on Approve | https://app.composio.dev |

You can paste all four keys directly into the UI's **Settings** page after the stack is up — no need to edit `.env` for routine demos.

---

## Install (5 steps, ~5 minutes)

```powershell
# 1. clone or navigate
cd "C:\Projects\hackathon\SDR\GTM Agent"

# 2. set initial env (minimum needed for first boot)
copy .env.example .env
# open .env and fill OPENAI_API_KEY and TAVILY_API_KEY at minimum.
# APIFY_TOKEN and COMPOSIO_API_KEY can be set later from the UI.

# 3. build + start all 3 services
docker compose up -d --build

# 4. verify everything is up
curl http://127.0.0.1:8000/health      # backend
curl http://127.0.0.1:8771/health      # deep-research
curl -I http://127.0.0.1:3000          # frontend (expect 200)

# 5. open the UI
start http://127.0.0.1:3000            # Windows; macOS: open / Linux: xdg-open
```

> **Use `http://127.0.0.1:3000`, not `http://localhost:3000`** — Docker Desktop on Windows publishes ports IPv4-only, and Windows resolves `localhost` to IPv6 first. `127.0.0.1` always works.

---

## First-run setup inside the UI

1. **Settings → API keys** — paste OpenAI, Tavily, Apify keys, click **Save**, then **Test** each one. Status flips to a green "saved" pill on success. (Edits via UI persist to `/app/data/runtime_config.json` and survive container restarts — no `.env` edit required.)
2. **Settings → Gmail · via Composio** — 3-step wizard:
   1. Paste your Composio API key.
   2. Paste a Gmail `auth_config_id` (create one in Composio dashboard → Auth Configs → +Create → Gmail → copy the `auth_config_...` id).
   3. Click **Connect Gmail →**, complete the Google OAuth popup. Status flips to green "connected" with your Gmail address.
3. **Company brain** — open `/brain`. Defaults are already filled in for Zamp + Pace. Edit the sender name, product description, target ICP, and brochure URL as needed. Click **Save brain**.
4. **New run** — fire your first prospect (see "Demo prospects" below).

---

## Folder layout

```
GTM Agent/
├── README.md                  this file
├── ARCHITECTURE.md            system + flow diagrams
├── TEST_PROSPECTS.md          curated prospects per edge case
├── docker-compose.yml         3 services + a shared data volume
├── .env / .env.example        env-baked keys + URLs
│
├── backend/                   FastAPI + asyncio orchestrator
│   ├── app.py                 FastAPI entry
│   ├── config.py              Pydantic Settings
│   ├── company_brain.yaml     seed defaults (UI writes to /app/data version)
│   ├── graph.py               6-agent pipeline (run_pipeline coroutine)
│   ├── agents/                lead_enrichment, market_intelligence, icp_profiling,
│   │                          person_signal, champion_scoring, drafting
│   ├── services/              deep_research, llm, apify, composio_gmail,
│   │                          email_render, safety, brain, runtime_config,
│   │                          events (SSE bus), web_scraper, container_logs
│   ├── routers/               runs, brain, bulk, dashboard, composio, keys
│   ├── db/                    SQLAlchemy models + sessions + lightweight migrate
│   ├── prompts/               markdown per agent (icp_scoring, drafting, …)
│   └── tests/                 pytest — safety, email_render, deep_research smoke
│
├── frontend/                  Next.js 14 (App Router) + Tailwind
│   ├── app/                   /, /runs/[id], /dashboard, /brain, /settings
│   ├── components/            PipelineGraph, AgentCard, GateReview, EmailPreview,
│   │                          ActiveAgentConsole, StatusPill
│   └── lib/                   api.ts (runtime-host API URL), sse.ts (EventSource hook)
│
└── docs/                      design notes + Langflow reference per agent
    ├── lead_enrichment/
    ├── market_intelliegence/
    ├── icp_flow/
    ├── person_linkedin_signal/
    ├── champion scoring/
    ├── email flow/
    └── old_langflow_reference.md
```

---

## How a single run looks

1. **You** type a prospect into the form (Full name, Company, LinkedIn URL, Title, Email, Domain). Pick research depth (1 / 2 / 3 cycles).
2. POST `/api/runs` returns `run_id`; orchestrator kicks off `run_pipeline()` as an asyncio task.
3. Browser opens an SSE stream `/api/runs/{id}/stream` and renders:
   - The 6-node pipeline graph at the top (nodes glow as they activate)
   - A live agent console showing the currently-running agent's log lines streamed straight from the deep-research / Apify sidecars
   - Per-agent cards on the right with structured results + citation chips + an expandable raw-JSON dump
4. On **drafting** completion, status flips to `awaiting_review` and Gate 1 opens:
   - Editable email preview (renders the exact HTML)
   - 5 safety checks (placeholder leak, spammy subject, ICP fit, brochure attached, recipient allowlist)
   - Approve / Edit & approve / Regenerate / Reject buttons
5. **Approve** → backend calls Composio `GMAIL_CREATE_EMAIL_DRAFT` → the draft lands in your connected Gmail's Drafts folder. You manually click Send inside Gmail when you're ready.

Every step persists to SQLite + a JSON `events_history` column. Past runs replay in full when you click them from `/dashboard`.

---

## Demo prospects (Zamp / Pace brain)

| # | Path | Prospect | Expected outcome |
|---|---|---|---|
| 1 | **Happy** | `CJ Gustafson` · CFO · Patreon · `https://www.linkedin.com/in/cjgustafson/` | ICP 8-9, Hot. Rich personalisation from his LinkedIn posts. |
| 2 | **Cold** | `Anu Hariharan` · VC · Avra | ICP < 5. Pipeline halts at ICP step, no draft created. |
| 3 | **Placeholder leak** | Same as #1 with the demo checkbox ticked | Pipeline runs to Gate 1; safety check catches `{{first_name}}`; Approve disabled. |
| 4 | **Weak LinkedIn signal** | A prospect whose LinkedIn isn't in harvestapi's cache | Person Signal returns `signal_strength: weak`; drafting falls back to company-level hook. |

See `TEST_PROSPECTS.md` for the canonical demo script.

---

## Common commands

```powershell
# bring stack up
docker compose up -d

# tail backend logs
docker logs gtmagent-backend-1 --tail 50 -f

# wipe all run data (keeps brain + keys)
docker compose exec backend python -c "from db.session import SessionLocal;from db import models;db=SessionLocal();[db.query(c).delete() for c in (models.SafetyCheck,models.Citation,models.Draft,models.Run,models.Bulk)];db.commit()"

# or use the UI's "Clear all runs" button on /dashboard

# rebuild a single service after a code change
docker compose build backend && docker compose up -d backend

# nuke and restart (rebuilds everything)
docker compose down && docker compose up -d --build

# run backend tests
docker compose exec backend pytest -q
```

---

## API surface (frontend uses these)

```
GET    /health                           backend liveness
GET    /api/health/deps                  pings the deep-research sidecar
POST   /api/runs                         create a run (returns run_id)
GET    /api/runs                         list runs (for dashboard)
GET    /api/runs/{id}                    full run detail (incl. events_history)
GET    /api/runs/{id}/stream             SSE — live agent events
GET    /api/runs/{id}/safety             current safety check results
POST   /api/runs/{id}/review             Gate 1 — approve / edit / regenerate / reject
DELETE /api/runs/{id}                    delete one run
DELETE /api/runs                         delete all runs
POST   /api/bulk                         CSV upload — fans out runs

GET    /api/brain                        read company_brain.yaml
PUT    /api/brain                        write company_brain.yaml

GET    /api/keys                         OpenAI / Tavily / Apify status
PUT    /api/keys                         set / clear any of them
POST   /api/keys/test/{name}             live verify a key

PUT    /api/composio/api-key             store Composio API key
PUT    /api/composio/auth-config         store Gmail auth_config_id
POST   /api/composio/gmail/connect       initiate OAuth → returns redirect URL
GET    /api/composio/gmail/status        live status (?ping=1 to verify)
POST   /api/composio/gmail/disconnect    clear connection

GET    /api/stats                        dashboard counters
```

Plus deep-research sidecar (`http://127.0.0.1:8771`):

```
GET  /health
POST /research                           firmographics research
POST /signals                            market intelligence research
GET  /logs/stream                        SSE — streams research internal logs
```

---

## What's persisted where

| Where | What |
|---|---|
| `/app/data/gtm.db` (Docker volume `gtm-data`) | SQLite — runs, drafts, citations, safety_checks, events_history |
| `/app/data/runtime_config.json` (same volume) | API keys + Composio connection state, set via UI |
| `/app/data/company_brain.yaml` (same volume) | Customer-specific config (Zamp / Pace, target ICP, allowlist) |
| In-memory `services/events.py` | SSE bus for live runs; persisted to DB on terminal state |

The volume `gtm-data` survives `docker compose down` and rebuilds. To start completely fresh, also remove the volume: `docker compose down -v`.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `localhost:3000` fails but `127.0.0.1:3000` works | Windows IPv6 vs Docker Desktop IPv4-only publish | Use `127.0.0.1` everywhere |
| Pages hang / "loading" forever | Docker Desktop pipe stuck | Quit and restart Docker Desktop, then `docker compose up -d` |
| Composio "Invalid API key" | Pasted the env-var name + value together | Re-copy just the key from app.composio.dev → Settings → API Keys |
| Apify run says "Free Apify plan can only run via UI" | Actor is paid-tier-only via API | We use `harvestapi/linkedin-profile-scraper` (free) by default — confirm via `/settings` |
| Safety check `recipient_allowlist` fails | `SEND_MODE=send` and recipient not on allowlist | Add the address to Company Brain → Allowlist, or stay in `draft` mode |
| Pipeline stuck on `enriching` for >2 min | Deep-research sidecar busy or quota | `docker logs gtmagent-deep-research-1 --tail 50` — check Tavily/OpenAI errors |
| Browser console: CORS error | Backend's `CORS_ORIGINS` doesn't include this page's origin | Add origin to `.env` `CORS_ORIGINS` (comma-separated), then `docker compose up -d backend` |

---

## License / credits

Built for the Zamp AI Solutions Associate case study (May 2026). Deep Research Agent sidecar reused from `../deep-research-agent-sdr/`. UI uses Next.js + Tailwind; backend uses FastAPI + SQLAlchemy + the OpenAI SDK + Apify SDK + Composio's v3 REST API.
