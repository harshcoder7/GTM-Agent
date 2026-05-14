# GTM Agent — Design Notes

Per-agent design notes + the original Langflow reference. Each folder below maps
1:1 to one of the six agents in `../backend/agents/`. The folders predate the
code: they were the original Langflow flow definitions and screenshots used to
spec the agents.

| Folder | Backend file | What's inside |
|---|---|---|
| [`lead_enrichment/`](./lead_enrichment/) | `backend/agents/lead_enrichment.py` | Flow design notes + screenshots for firmographic enrichment via deep-research `/research`. |
| [`market_intelliegence/`](./market_intelliegence/) | `backend/agents/market_intelligence.py` | Flow + signals research notes via deep-research `/signals`. |
| [`icp_flow/`](./icp_flow/) | `backend/agents/icp_profiling.py` | Web-scrape → product summary → ICP scoring design. |
| [`person_linkedin_signal/`](./person_linkedin_signal/) | `backend/agents/person_signal.py` | Apify-based per-person LinkedIn engagement extraction. |
| [`champion scoring/`](./champion%20scoring/) | `backend/agents/champion_scoring.py` | Per-person buyer-fit scoring from a LinkedIn profile. |
| [`email flow/`](./email%20flow/) | `backend/agents/drafting.py` + `backend/services/email_render.py` | Drafting + HTML rendering + brochure switcher + Composio Gmail. |
| [`old_langflow_reference.md`](./old_langflow_reference.md) | — | The original end-to-end Langflow architecture this build replaces. |

For the runtime architecture (containers, SSE, data layout) see
`../ARCHITECTURE.md`. For installation + demo steps see `../README.md`.
