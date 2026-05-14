# GTM Agent — Architecture

Personalised B2B outreach pipeline. Prospect in → Gmail draft out, with one human gate before sending.

---

## System

```
┌────────────────────────────────────────────────────────────────────────┐
│                         Browser (127.0.0.1:3000)                       │
│  New run · Dashboard · Company brain · Settings · Live run + Gate 1    │
└─────────────────────────────┬──────────────────────────────────────────┘
                              │  HTTP + SSE
                              ▼
┌────────────────────────────────────────────────────────────────────────┐
│                Next.js 14 frontend  (Tailwind + RSC)                   │
│  • lib/sse.ts — EventSource hook with retry cap                        │
│  • Pipeline graph + per-agent cards + email preview                    │
└─────────────────────────────┬──────────────────────────────────────────┘
                              │  fetch /api/*
                              ▼
┌────────────────────────────────────────────────────────────────────────┐
│              FastAPI backend  (127.0.0.1:8000)                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  routers/  →  graph.py orchestrator  →  agents/  →  services/   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  SSE bus · SQLite + runtime_config.json + company_brain.yaml           │
└──────┬────────────────┬────────────────┬────────────────┬──────────────┘
       │                │                │                │
       ▼                ▼                ▼                ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Deep        │  │ OpenAI       │  │ Apify        │  │ Composio v3  │
│ Research    │  │ structured   │  │ harvestapi/  │  │ /tools/      │
│ (:8771)     │  │ output       │  │ dev_fusion   │  │ execute      │
│ /research   │  │ gpt-4o /     │  │ LinkedIn     │  │ GMAIL_CREATE │
│ /signals    │  │ gpt-4o-mini  │  │ scrapers     │  │ _EMAIL_DRAFT │
│ /logs/stream│  │              │  │              │  │              │
└──────┬──────┘  └──────────────┘  └──────────────┘  └──────────────┘
       │                                                              
       ▼                                                              
┌─────────────┐                                                       
│ Tavily      │                                                       
│ search +    │                                                       
│ scrape      │                                                       
└─────────────┘                                                       
```

---

## The 6 agents

```
[Prospect form / CSV]
        │
        ▼
   POST /api/runs  ───SSE───▶  Browser (live agent cards + logs)
        │
        ▼
   graph.py orchestrator
        │
        ├─ 1. Lead Enrichment      → deep-research /research, OpenAI 10-field schema
        │
        ├─ 2. Market Intelligence  → deep-research /signals,  OpenAI 7-field schema
        │
        ├─ 3. ICP Profiling        → scrape company site → product summary →
        │                            OpenAI scoring (Pro / Hive / Both, score 1-10)
        │                            if score < 5 → ESCALATE (refuse to draft)
        │
        ├─ 4. LinkedIn Signal      → Apify harvestapi/linkedin-profile-posts →
        │                            OpenAI engagement summary
        │
        ├─ 5. Champion Scoring     → Apify harvestapi/linkedin-profile-scraper →
        │                            normalize → OpenAI 0-10 score
        │
        └─ 6. Drafting             → OpenAI compose email (subject/intro/pain/
                                     product/bullets/cta) + brochure switcher
                                     + HTML render
        │
        ▼
   [Gate 1 — Human review]
   • Editable email preview (renders the exact HTML the recipient sees)
   • 5 safety checks: placeholder leak, spammy subject, ICP fit, brochure,
     recipient allowlist (informational in draft mode)
   • Approve · Edit & approve · Regenerate · Reject
        │
        ▼ (on Approve)
   Composio Gmail → GMAIL_CREATE_EMAIL_DRAFT
        │
        ▼
   Draft lands in user's connected Gmail (Drafts folder)
```

---

## Real-time streaming

```
agent runs ──▶ services/events.py  ──▶  per-run asyncio.Queue
                  │                              │
                  │ persists on terminal state   │ EventSource
                  ▼                              ▼
            runs.events_history             Browser SSE
            (JSON column)                   useRunStream
                  │                              │
                  ▼                              ▼
       Past-run replay seeds              Live agent cards,
       events from DB                     pipeline graph,
                                          ActiveAgentConsole
```

Deep-research logs flow the same way:

```
deep-research handler ──▶ asyncio.to_thread(run_full_research)
                          (frees the event loop)
                                  │
                                  ▼
                          Python logger
                                  │
                                  ▼
                          /logs/stream SSE
                                  │
                                  ▼
                          backend tailer ──▶ agent.tool kind=log
                                                    ▼
                                          Live log card on UI
```

Apify actor logs use the same path via `apify-client`'s `run.log().stream()`.

---

## Data layout

```
runs  ─┬─ prospect_json
       ├─ enriched_lead  (Lead Enrichment result)
       ├─ market_intel   (Market Intelligence result)
       ├─ icp            (ICP Profiling result)
       ├─ person_signal  (LinkedIn Signal result)
       ├─ champion       (Champion Scoring result)
       ├─ events_history (replayable SSE log)
       ├─ research_cycles (1–3, chosen by user)
       └─ composio_draft_id + drafted_at
        │
        ├──▶ drafts[]    (versioned email drafts, gate edits)
        ├──▶ citations[] (Tavily sources, per agent)
        └──▶ safety_checks[] (Gate 1 results)

company_brain.yaml      (UI-editable: products, ICP, sender, allowlist)
runtime_config.json     (UI-editable: OpenAI/Tavily/Apify/Composio keys + entity)
                        — both live in the /app/data volume → survive rebuilds
```

---

## Container topology

```
docker compose up
   │
   ├─ deep-research (port 8771)   ./deep-research-agent-sdr/Dockerfile
   │     gpt-4o-mini · Tavily · /research, /signals, /logs/stream SSE
   │
   ├─ backend       (port 8000)   ./backend/Dockerfile
   │     FastAPI · SQLite + JSON sidecars in /app/data volume
   │     reads OPENAI/TAVILY/APIFY/COMPOSIO keys from runtime_config (UI-editable)
   │
   └─ frontend      (port 3000)   ./frontend/Dockerfile
         Next.js standalone · talks to backend on same hostname as browser
```

All three: `restart: unless-stopped`. Volume `gtm-data` holds DB + configs.

---

## What runs when you click Approve

```
Click "Approve & create Gmail draft"
        │
        ▼
POST /api/runs/{id}/review {decision: approve}
        │
        ▼
safety.run_all(draft, icp, product_fit, recipient) → 5 checks
        │
        ├─ any fails → 409 / blocked + reasons → UI shows which row failed
        │
        └─ all pass
                │
                ▼
        composio_gmail.create_draft(recipient, subject, html)
                │
                ▼
        POST https://backend.composio.dev/api/v3/tools/execute/
             GMAIL_CREATE_EMAIL_DRAFT
             {user_id: entity_id, arguments: {recipient_email, subject, body, is_html}}
                │
                ▼
        Draft created in user's Gmail · run.status = "drafted"
        Persist events_history snapshot · close SSE
```

---

## Configurable from UI (no .env edits, no restart)

| Where | What |
|---|---|
| `/settings` → API keys | OpenAI, Tavily, Apify keys with Test buttons |
| `/settings` → Gmail · Composio | 3-step wizard: API key → auth_config_id → OAuth connect |
| `/brain` | Sender info, products, target ICP, preferred tone, allowlist |
| `/` (new run form) | Research depth (1 / 2 / 3 cycles), placeholder-leak demo toggle |

---

## Edge cases handled

1. **Cold prospect** — ICP < 5 → pipeline halts at step 3, run escalates.
2. **Placeholder leak** — `{{first_name}}` in draft body → Gate 1 safety blocks approval.
3. **Low LinkedIn activity** — Apify returns 0 posts → Person Signal returns `signal_strength: weak`, drafting falls back to company-level hook.
4. **Ambiguous identity / no LinkedIn** — agents skip gracefully with explicit empty-state results, pipeline continues.
5. **Backend hiccup mid-run** — `restart: unless-stopped` + stale-run reaper on startup marks orphaned runs `cancelled`.
6. **Past-run replay** — `events_history` column lets you reopen any old run and see every agent's logs, sources, durations.
