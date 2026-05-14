
# SDR Agent — End-to-End Architecture

> Detailed walkthrough of how the SDR workflow moves data from a raw CSV upload all the way to a personalized outreach email, across the Streamlit UI, the Agent Hive Langflow runtime, the deep research FastAPI agent, and the supporting flows for technographics, champion scoring, person engagement, and brochure-attached email generation.

---

## 1. The big picture

There are **three layers** in this system:

```
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 1 — Streamlit Web UI  (this repo: sdr-web-ui/)                │
│   • Uploads CSV, holds workflow state per-session                   │
│   • Calls Langflow flows via HTTPS POST                             │
│   • Parses the embedded ```json``` block out of each response       │
└─────────────────────┬───────────────────────────────────────────────┘
                      │   POST  https://flow.agenthive.tech/api/v1/run/<flow>
                      │   header: x-api-key
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 2 — Agent Hive (Langflow runtime, flow.agenthive.tech)        │
│   • Hosts the 11 flow JSONs (see §3)                                │
│   • Each flow is a DAG of components (LLM, Tavily, scraper, schema) │
│   • Forces structured JSON output via a `StructuredOutput` node     │
└─────────────────────┬───────────────────────────────────────────────┘
                      │   internal node-to-node wiring + outbound calls
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 3 — External services + side cars                             │
│   • Deep Research Agent (FastAPI) at http://34.58.1.42:8771         │
│       → source: deep-research-agent-sdr/                            │
│       → used by Lead Enrichment + Market Intelligence flows         │
│   • Tavily (web search)                                             │
│   • OpenAI (gpt-4o, gpt-4o-mini, gpt-4.1-nano)                      │
│   • Google Gemini (gemini-2.5-flash, gemini-1.5-pro)                │
│   • Apify (LinkedIn scraping for person engagement + champion)      │
│   • QPIAI Knowledge Base (internal semantic DB for technographics)  │
│   • Web Search "no-API" (domain finder)                             │
└─────────────────────────────────────────────────────────────────────┘
```

**Key insight:** the Streamlit app is a thin client. All the actual research, scraping, scoring, and email drafting happens server-side on Agent Hive. The deep research agent (`deep-research-agent-sdr/`) is **already deployed at `34.58.1.42:8771`** and is being called as a sub-tool from inside the Lead Enrichment and Market Intelligence Langflow flows — it is *not* a missing piece, it's the engine that powers those two flows.

---

## 2. The 11 flows — inventory

Stored in `SDR workflows json/`. Endpoints on `flow.agenthive.tech/api/v1/run/<name>`.

| # | Flow file | Endpoint (or UUID) | Called from this repo? | Stage in pipeline |
|---|---|---|---|---|
| 1 | `api-domain-finder.json` | UUID `c8656154-…` | ✅ `domain.py` (CLI only) | 0 — pre-enrichment |
| 2 | `api-lead-enrichment.json` | `/run/lead-enrichment` | ✅ `sections/lead_enrichment.py` | 1 — enrichment |
| 3 | `api-icp-profiling.json` | `/run/icp-profiling` | ✅ `sections/icp_profiling.py` | 2 — qualification |
| 4 | `api-market-intelligence.json` | `/run/market-intelligence` | ✅ `sections/market_intelligence.py` | 3 — signals |
| 5 | `api - person engagement signal.json` | (not yet wired) | ❌ | 4 — per-person prep |
| 6 | `api - champion scoring.json` | (not yet wired) | ❌ | 5 — contact scoring |
| 7 | `v3-technographics retreival.json` | (not yet wired) | ❌ | 1b — tech-stack enrichment |
| 8 | `v3-software-list.json` | (not yet wired) | ❌ | 1c — tech taxonomy lookup |
| 9 | `v3- knowledge base ingestion.json` | (not yet wired) | ❌ | offline — KB maintenance |
| 10 | `langflow - pre-filter using 500 char.json` | (not yet wired) | ❌ | offline — pre-RAG chunking |
| 11 | `email-from-csv.json` | (not yet wired) | ❌ | 6 — outreach draft |

**The Streamlit UI only invokes 4 of the 11 flows today** (lead-enrichment, icp-profiling, market-intelligence, plus the standalone domain-finder via `domain.py`). The other 7 are built on Agent Hive but not yet exposed through the Streamlit app — they're the next features to wire in.

---

## 3. The data object that flows through everything

The Streamlit app holds a single in-memory list in `st.session_state.workflow_data["data"]` — each element is **one company**, mutated in place as each stage runs. Schema grows over time:

```
After CSV upload (stage 0):
{
  "company": {"Company Name", "Company Domain", "Company Website",
              "Company Industry", "Company Employee Count", "Company Founded",
              "Company Headquarters", "Company Revenue Range",
              "Company Linkedin Url", "Company Crunchbase Url",
              "Company Funding Rounds", "Company Last Funding Round Amount", …},
  "people":  [{"Name", "First name", "Last name", "Email", "Mobile Number",
               "Company Phone", "Title", "Linkedin", "Location"}, …]
}

After Lead Enrichment (stage 1):
+ "enriched_lead": {Company, Overview, Size, Revenue, Domain,
                    Funding Information, Latest Funding Round,
                    Investors, LinkedIn URL, Sources[]}
+ "enrichment_timestamp", "enrichment_timestamp_numeric"

After ICP Profiling (stage 2):
+ "icp_analysis": {Product Fit, ICP Score, Prospect Level,
                   Engagement Readiness, Justification, Use Case}
+ "icp_analysis_timestamp", "icp_analysis_timestamp_numeric"

After Market Intelligence (stage 3):
+ "market_intelligence": {Industry, Customer Segments, Business Model,
                          Geographic Presence, Product Launches,
                          Press & PR, Social Media Activity}
+ "intelligence_timestamp", "intelligence_timestamp_numeric"

(Future stages would similarly add:)
+ "tech_stack": {…}                  ← from technographics flow
+ "person_signals": [{…}, …]          ← per-person LinkedIn engagement
+ "champion_score": {…}               ← per-person champion qualification
+ "outreach_email": {subject, body, html, brochure_url}
```

Note that **`people` is preserved across all stages but only used at export time and in the future per-person flows** — the company-level flows never see it.

---

## 4. The Streamlit ↔ Langflow handshake (universal pattern)

Every section that calls a flow follows **the same five-step pattern**:

### 4.1 — Build the input value

```python
# example: lead_enrichment.py:32-36
company_info = row_data.get('company', {})
payload = {
    "output_type": "chat",
    "input_type":  "chat",
    "input_value": json.dumps(company_info)   # the actual content
}
```

The flow expects all real input as a JSON string in `input_value`. Langflow then parses it on its side (via `MarkdownJSONParserComponent` or a custom parser) and routes the fields into the graph.

### 4.2 — Optional: override Langflow component config with `tweaks`

```python
# icp_profiling.py:77-82
payload["tweaks"] = {
    "GoogleGenerativeAIModel-r4iC7": {
        "model_name": "gemini-2.5-flash"
    }
}
```

`tweaks` lets the client override any node's template field at runtime — used by ICP to pin Gemini's model name.

### 4.3 — POST to the flow endpoint

```python
response = requests.post(
    "https://flow.agenthive.tech/api/v1/run/<flow-name>",
    json=payload,
    headers={"Content-Type": "application/json",
             "x-api-key": os.getenv("AGENT_HIVE_API_KEY")},
    timeout=300  # 180–360s depending on flow
)
```

### 4.4 — Parse the embedded ```` ```json ```` block

Langflow returns a Chat-style response where the LLM's structured output is **buried inside a `messages[].message` string as a fenced JSON block**. The walk path is:

```
api_response
└── outputs[]
    └── outputs[]
        └── messages[]
            └── message  (string)
                └── "...```json\n{...}\n```..."
```

Identical parser used in all three sections (`lead_enrichment.py:60-97`, `icp_profiling.py:106-149`, `market_intelligence.py:67-114`):

```python
def process_api_response(api_response):
    for output in api_response.get("outputs", []):
        for item in output.get("outputs", []):
            for msg in item.get("messages", []):
                text = msg.get("message", "")
                if "```json" in text:
                    block = text.split("```json")[1].split("```")[0].strip()
                    return json.loads(block)
    return {"enrichment_status": "no_..._found", ...}
```

### 4.5 — Write the parsed dict back onto the row

```python
st.session_state.workflow_data["data"][actual_index]['enriched_lead'] = processed_data
st.session_state.workflow_data["data"][actual_index]['enrichment_timestamp'] = "..."
```

That's it. Every flow integration in the Streamlit app follows this exact pattern.

---

## 5. Flow-by-flow deep dive

### 5.1 — Domain Finder (`api-domain-finder.json`)

**Endpoint:** `/api/v1/run/c8656154-f3f0-44f3-b989-8f2a004bf56c` (UUID, no slug)
**Called from:** `domain.py:29` (standalone CLI, **not** wired into the Streamlit app)

**Purpose:** Given a company name, resolve its official website domain.

**Component graph:**

```
ChatInput (company name)
   ↓
Agent  (tool-using LLM, Gemini)
   ↳ uses tool: WebSearchNoAPI  (public web search, no API key needed)
   ↓
ChatOutput → JSON { "Company Domain": "example.com" | "Not found" }
```

**Agent system prompt** (verbatim from the JSON):

> You are an assistant that finds the official website domain of a given company using a search tool. Given a company name, use search to identify the most likely official website domain. Return your answer only as a JSON object: `{ "Company Domain": "example.com" }`. If you cannot find a valid or trustworthy official domain, return `{ "Company Domain": "Not found" }`. Do not include any extra text or explanation — only return the JSON.

**Where it fits:** This is the flow `domain.py` already uses to enrich CSVs with company domains before they're uploaded into the Streamlit pipeline. To wire it into the UI, we'd add a `sections/domain_resolution.py` that loops over rows where `company['Company Domain']` is empty and fills it via this flow.

---

### 5.2 — Lead Enrichment (`api-lead-enrichment.json`)

**Endpoint:** `/api/v1/run/lead-enrichment`
**Called from:** `sections/lead_enrichment.py:40`

**Purpose:** Take a thin company dict (name + domain) and produce a firmographic profile with funding, size, revenue, and citations.

**Component graph:**

```
ChatInput (json.dumps of row['company'])
   ↓
CustomComponent "Research Agent"  ← calls http://34.58.1.42:8771/research
                                    (cycles=2 by default)
   ↓                                source: deep-research-agent-sdr/server/main_working.py
LanguageModelComponent  (default: gpt-4o, configurable)
   ↓
StructuredOutput  (forces 10-field JSON schema)
   ↓
ChatOutput → ```json { Company, Overview, Size, Revenue, Domain, … } ```
```

**The Research Agent component is the deep-research-agent FastAPI service** (`deep-research-agent-sdr/`). It runs the iterative loop in `research_controller.py:210`:

1. Generate a search query via chain-of-thought prompting (`prompt_templates.py:CHAIN_OF_THOUGHT_QUERY_PROMPT`)
2. Tavily search → top N results
3. Scrape top M URLs (BeautifulSoup)
4. Summarize with the LLM (`SUMMARIZATION_PROMPT`)
5. Reflect on gaps (`REFLECTION_PROMPT`)
6. Repeat for `cycles` iterations
7. Emit a final report (`FINAL_REPORT_PROMPT`)

That final report gets fed into the Lead Enrichment flow's structured-output node, which constrains the LLM to emit exactly 10 fields.

**Output schema (10 fields):**

| Field | Type | Source |
|---|---|---|
| `Company` | str | Echo of company name |
| `Overview` | str | LLM-summarized from research |
| `Size` | str | e.g. "Approximately 24 employees" |
| `Revenue` | str | e.g. "Estimated at $3.5 million" |
| `Domain` | str | e.g. "ageyetech.com" |
| `Funding Information` | str | Total raised |
| `Latest Funding Round` | str | Date + round |
| `Investors` | str | Comma-separated, or "NOT FOUND" |
| `LinkedIn URL` | str | Company LinkedIn page |
| `Sources` | list[str] | Tavily URLs used |

**Default LLM:** `gpt-4o` (configurable via the Language Model component's provider/model dropdown — supports gpt-4o-mini, gpt-4.1-2025-04-14, gemini-2.5-flash, gemini-1.5-pro, claude-3.5-sonnet).

---

### 5.3 — ICP Profiling (`api-icp-profiling.json`)

**Endpoint:** `/api/v1/run/icp-profiling`
**Called from:** `sections/icp_profiling.py:86`

**Purpose:** Score how well an enriched lead fits the user's Ideal Customer Profile, including scraping the company website for product-fit signals.

**Component graph (most complex of the flows — 19 nodes):**

```
ChatInput  (json.dumps of {enriched_lead, domain, product_context, target_icp})
   ↓
MarkdownJSONParser  (extracts the 4 fields)
   ↓ ↓ ↓ ↓
ParserComponent ×4  (one per field: domain | product_context | enriched | target_icp)
   ↓
WebsiteScraperComponent  ← uses `domain` to fetch + scrape the company site
   ↓
Prompt-ac2Ej  ("extract product summary from scraped site")
   ↓
GoogleGenerativeAIModel  (gemini-2.5-flash, pinned via tweaks)
   ↓
Prompt-MMRJ4 + Prompt-sI2iS  (system + user prompts combining products_summary + enriched + product_context + target_icp)
   ↓
OpenAIModel  (final ICP fit scoring)
   ↓
StructuredOutput  (6-field schema)
   ↓
ChatOutput → ```json { Product Fit, ICP Score, Prospect Level, … } ```
```

**The flow does TWO LLM passes:**
1. **Gemini pass** — extracts a bullet-point summary of the company's products from the scraped website HTML
2. **OpenAI pass** — combines the product summary with the enriched lead, product context, and target ICP, and produces the final qualification

**Input payload (built in Streamlit at `icp_profiling.py:65-71`):**

```python
data = {
    "enriched_lead":   row['enriched_lead'],       # full 10 fields from stage 1
    "domain":          row['company'].get('Company Domain')      # fallback chain
                    or row['company'].get('Company Website')
                    or row['enriched_lead'].get('Domain', ''),
    "product_context": text_area_input,            # QpiAI Pro + Agent Hive description
    "target_icp":      text_area_input             # ICP signals description
}
```

**Output schema (6 fields):**

| Field | Type | Notes |
|---|---|---|
| `Product Fit` | str | Which product (Pro or Hive) suits them |
| `ICP Score` | str/numeric | Fit score |
| `Prospect Level` | str | High / Medium / Low |
| `Engagement Readiness` | str | Ready to be contacted? |
| `Justification` | str | Reasoning for the score |
| `Use Case` | str | The concrete use case to pitch |

---

### 5.4 — Market Intelligence (`api-market-intelligence.json`)

**Endpoint:** `/api/v1/run/market-intelligence`
**Called from:** `sections/market_intelligence.py:48`

**Purpose:** Pull engagement signals and broader market posture for the company — what they're talking about, recent product news, PR, social activity.

**Component graph (parallel structure to Lead Enrichment):**

```
ChatInput  (json.dumps of enriched_lead minus Sources)
   ↓
CustomComponent "Research Agent"  ← calls http://34.58.1.42:8771/signals
                                    (note: /signals endpoint, NOT /research)
   ↓                                uses signals_prompt_templates.py
LanguageModelComponent  (default: gpt-4.1-nano-2025-04-14, cheaper than enrichment's gpt-4o)
   ↓
StructuredOutput  (7-field schema — the one in your screenshot)
   ↓
ChatOutput → ```json { Industry, Customer Segments, … } ```
```

**The key difference vs Lead Enrichment:** same deep-research-agent service, different endpoint (`/signals` vs `/research`), which switches to the **signals prompt templates** (`signals_prompt_templates.py:SIGNALS_CHAIN_OF_THOUGHT_QUERY_PROMPT`, `SIGNALS_SUMMARIZATION_PROMPT`, `SIGNALS_REFLECTION_PROMPT`, `SIGNALS_FINAL_REPORT_PROMPT`). Same iterative loop, different research focus.

**Output schema (7 fields — exactly the one in your screenshot):**

| Field | Type | Description |
|---|---|---|
| `Industry` | str | Sector/vertical |
| `Customer Segments` | str | Key buyer personas or end customers |
| `Business Model` | str | How the company makes money |
| `Geographic Presence` | str | Regions/countries |
| `Product Launches` | str | Names, dates, brief description |
| `Press & PR` | str | Recent announcements, features |
| `Social Media Activity` | str | Notable tweets, LinkedIn activity |

---

### 5.5 — Person Engagement Signal (`api - person engagement signal.json`)

**Endpoint:** *not yet exposed via the Streamlit UI*
**Purpose:** Per-person — scrape a contact's recent LinkedIn activity and extract their tone, themes, and the best personalization angle for outreach.

**Component graph:**

```
ChatInput  (LinkedIn URL of the person)
   ↓
LinkedInScraperConfig  (Apify config)
   ↓
ApifyActors  (executes a LinkedIn-profile-and-posts scraper actor)
   ↓
LinkedInPostProcessor  (cleans Apify raw output into a readable post list)
   ↓
Prompt-Sk9Kz  (analyze posts for engagement signals)
   ↓
GoogleGenerativeAIModel
   ↓
MarkdownJSONParser
   ↓
ChatOutput → JSON
```

**Verbatim prompt** (first ~200 chars from the JSON):

> You are an expert SDR assistant that analyzes recent LinkedIn activity of a person to extract a compact engagement signal. This helps generate personalized and high-converting outreach content. Focus on identifying: their core interests and values, their tone and writing style, timely or recurring themes in their posts, strong angles to personalize an outreach message.

**Output schema:**

```json
{
  "person_name": "<Name>",
  "engagement_signal_summary": {
    "core_themes": ["theme1", "theme2", "..."],
    "writing_style": "tone/voice description",
    "recent_focus": "current engagement topics",
    "engagement_trend": "activity consistency and resonance",
    "best_personalization_angle": "what message would resonate",
    "example_opening_line": "first-line for a cold email"
  }
}
```

**External dependency:** Apify (with an API token configured in the node). Apify LinkedIn scraper actors handle the login + profile/posts retrieval — there's no direct LinkedIn API.

**Where it fits in the pipeline:** stage 4, per-person. For each person in `row['people']`, call this flow with their `Linkedin` URL. Output gets attached as `row['people'][i]['engagement_signal']`.

---

### 5.6 — Champion Scoring (`api - champion scoring.json`)

**Endpoint:** *not yet exposed via the Streamlit UI*
**Purpose:** Score each contact on how good a "champion" they'd be for the deal — based on seniority, LinkedIn activity, and buying signals.

**Component graph:**

```
ChatInput  (person profile data — likely needs name + LinkedIn + company context)
   ↓
MarkdownJSONParser + ParserComponents  (extract fields)
   ↓
ApifyActors  (scrape extended LinkedIn / sales-nav data)
   ↓
ProfileNormalizerComponent  (standardize raw profile)
   ↓
DataToDataFrame → DataFrameToDataComponent  (normalize structure)
   ↓
Prompt + GoogleGenerativeAIModel  (apply scoring criteria)
   ↓
MarkdownJSONParser
   ↓
ChatOutput → JSON
```

**Inferred output schema** (verbatim prompt not fully extracted — flag for verification):

```json
{
  "champion_score": 0-100,
  "engagement_level": "High | Medium | Low",
  "seniority_tier":   "C-Suite | VP | Director | Manager",
  "buying_signals":   "string summary",
  "recommended_channel": "string",
  "personalization_hints": "string"
}
```

**Where it fits:** stage 5, per-person — distinguishes the *decision-maker* from other contacts at the same company. Output attached as `row['people'][i]['champion_score']`.

---

### 5.7 — Technographics Retrieval (`v3-technographics retreival.json`)

**Endpoint:** *not yet exposed via the Streamlit UI*
**Purpose:** Discover the technology stack a company uses — what software, tools, cloud providers, CRM, analytics platforms they have.

**Component graph (24 nodes):**

```
TextInput (company name) + TextInput (optional tech filter context)
   ↓
QPIAIKnowledgeBase  ← semantic search against an internal QpiAI KB
                      of company-to-tech-stack mappings
   ↓
CustomComponent "RAG Context Processor"  (ranks/dedupes results)
   ↓
ParserComponent
   ↓
Prompt + Gemini  (classify by category: cloud / CRM / analytics / security / …)
   ↓
MarkdownJSONParser
   ↓
CustomComponent "JSON Flattener"  (flattens nested categories)
   ↓
Gemini (2nd pass)  (enriches with version / context info)
   ↓
MarkdownJSONParser
   ↓
LoopComponent  (iterates over flattened tech items for final output)
```

**Inferred output schema:**

```json
{
  "company_name": "...",
  "technology_stack": [
    {
      "category": "Cloud Infrastructure | CRM | Analytics | …",
      "tools": [
        {"name": "AWS",       "confidence": "High",   "estimated_version": "...", "usage_context": "..."},
        {"name": "Salesforce","confidence": "Medium", "estimated_version": "...", "usage_context": "..."}
      ]
    }
  ]
}
```

**Key dependency:** the **QPIAI Knowledge Base** — an internal semantic DB. This is fed by:
- `v3- knowledge base ingestion.json` (the ingestion pipeline)
- `langflow - pre-filter using 500 char.json` (the 500-char text-chunker that prepares data for the KB)

**Where it fits:** stage 1b — runs in parallel with Lead Enrichment. Output attached as `row['tech_stack']`. Particularly useful for `Product Fit` decisions in ICP profiling (e.g., "they already use Salesforce → strong fit for our HubSpot competitor").

---

### 5.8 — Software List (`v3-software-list.json`)

**Endpoint:** *not yet exposed*
**Purpose:** Maintain and query a curated taxonomy of software categories. Acts as a reference dataset for the technographics flow.

**Component graph (small):**

```
ChatInput / TextInput  (category query)
   ↓
CustomComponent "ProductCategoryManager"
   ↓
Agent  (LLM orchestrator)
   ↓
ChatOutput → array of {category, softwares[], count}
```

**Where it fits:** offline / reference — not part of the main per-lead pipeline. Used to validate / categorize the output of the technographics flow.

---

### 5.9 — Knowledge Base Ingestion (`v3- knowledge base ingestion.json`)

**Endpoint:** *not yet exposed* (and not really a per-lead flow)
**Purpose:** Bulk-ingest product/company data into the QPIAI Knowledge Base.

**Component graph (no LLM — pure ETL):**

```
File upload (JSON / CSV)
   ↓
QPIAIKnowledgeBaseIngest
   ↓
ListDictParser → ProductDataFormatter
   ↓
LoopComponent  (batch persist each record)
```

**Where it fits:** offline maintenance. Run this whenever you add new product/company data to the KB that the technographics flow queries against.

---

### 5.10 — Pre-filter using 500 char (`langflow - pre-filter using 500 char.json`)

**Endpoint:** *not yet exposed* (utility flow)
**Purpose:** Fetches a URL, splits it into ≤500-char chunks for RAG ingestion.

**Component graph:**

```
URL input
   ↓
HTTP fetch + content extraction
   ↓
RecursiveCharacterTextSplitter (chunk_size=500)
   ↓
Output: array of {chunk_index, content, source_url, length}
```

**Where it fits:** offline preprocessing for the Knowledge Base. Pairs with the KB Ingestion flow.

---

### 5.11 — Email From CSV (`email-from-csv.json`)

**Endpoint:** *not yet exposed via the Streamlit UI — but this is the outreach flow you mentioned*
**Purpose:** Generate personalized cold-outreach emails from a CSV of leads, with HTML formatting and an injected brochure URL.

**Component graph (27 nodes — largest flow):**

```
CSVtoData  (Load CSV with Row Slicing)
   ↓
LoopComponent  (iterate one row at a time)
   ↓
DataGroupingComponent  (group/batch lead fields for prompt assembly)
   ↓
Prompt-oUq4F  ("write a personalized cold email")
   ↓
GoogleGenerativeAIModel  (drafts the email body)
   ↓
HiveProBothBrochure-2WCsq  ← *** THE BROCHURE COMPONENT ***
   ↓
MarkdownJSONParser  (parse drafted email into structured JSON)
   ↓
JSONFieldExtractor  (pull out subject/body/CTA/etc.)
   ↓
EmailTextFormatter  (plain-text version)
   ↓
BulletPointsHTMLGenerator  (HTML version)
   ↓
Prompt-x3wml + 4× ParserComponent  (HTML refinement + final field extraction)
   ↓
ChatOutput → per-lead email JSON
```

### 5.11.1 — The brochure component (`HiveProBothBrochure-2WCsq`)

> You explicitly asked about this — confirmed it exists.

- **Node ID:** `HiveProBothBrochure-2WCsq`
- **Display name:** "Brochure Switcher"
- **Component type:** `HiveProBothBrochure` (custom QpiAI component, not a stock Langflow node)
- **Role:** Given the company / product context for the email being generated, it **dynamically selects which brochure URL to attach** — likely QpiAI Pro brochure vs Agent Hive brochure vs both, based on the `Product Fit` decision (which would come from the ICP Profiling flow's output if these flows were chained).
- **Downstream consumer:** the HTML formatting prompt (`Prompt-x3wml`) reads the brochure URL from this component and embeds it as a link/attachment in the final email HTML.
- **Output field:** `brochure_url` in the final email JSON.

**Output schema (per email):**

```json
{
  "subject":         "Personalized subject line",
  "email_body":      "Plain text body",
  "email_html":      "HTML version with formatting",
  "call_to_action":  "CTA copy",
  "brochure_url":    "URL from HiveProBothBrochure"
}
```

**Where it fits:** stage 6 — the final output of the entire SDR pipeline. To wire it into the Streamlit app, we'd add `sections/email_outreach.py` that reads `enriched_lead + icp_analysis + market_intelligence + person_signals + champion_score` from each row and POSTs to this flow.

**Important note on the current flow:** the flow today loads **its own CSV** rather than accepting structured input from Streamlit's workflow data. To wire it cleanly we'd either (a) modify the flow to accept JSON input matching the Streamlit row shape, or (b) have Streamlit export the workflow data back to CSV and stream it to the flow. Option (a) is much cleaner.

---

## 6. The deep research agent — what it is and where it sits

The `deep-research-agent-sdr/` folder is the **source code** for the FastAPI service deployed at **`http://34.58.1.42:8771`**. The Lead Enrichment and Market Intelligence Langflow flows both call this service.

### 6.1 — The three endpoints

| Endpoint | Method | Body | Used by |
|---|---|---|---|
| `/research` | POST | `{topic, cycles, openai_api_key?, tavily_api_key?, openai_model?, ...prompt_overrides}` | Lead Enrichment flow |
| `/signals` | POST | same shape as `/research` | Market Intelligence flow |
| `/search` | POST | `{query, max_results}` | (Reserved for future use — single Tavily query, no LLM loop) |
| `/health` | GET | — | Healthcheck |

### 6.2 — The iterative research loop (`research_agent/research_controller.py:210`)

For each call to `/research` or `/signals`:

```
config.max_research_cycles (default 2 for Streamlit calls, 3 in the Dockerfile)
   │
   ├─► Cycle 1:
   │     1. generate_search_query()         ← LLM chain-of-thought
   │     2. perform_web_search()            ← Tavily, top N results
   │     3. scrape_search_results()         ← BeautifulSoup on top M URLs
   │     4. update_summary()                ← LLM summarization
   │     5. reflect_on_research()           ← LLM identifies gaps
   │
   ├─► Cycle 2: repeats with refined query informed by reflection
   │
   └─► generate_final_report()              ← LLM produces final markdown report
        + usage_summary (token counts)
```

### 6.3 — Prompt template variants

The same engine serves two purposes by swapping prompt sets:

| Template variant | Prompt module | Endpoint that loads it |
|---|---|---|
| Default (lead enrichment) | `research_agent/prompt_templates.py` | `/research` |
| Signals (market intelligence) | `research_agent/signals_prompt_templates.py` | `/signals` |

The signals templates ask the LLM to focus on recent events (product launches, PR, social), while the default templates ask for evergreen firmographic facts (size, revenue, funding).

### 6.4 — How the Langflow flow uses it

Inside `api-lead-enrichment.json` (and `api-market-intelligence.json`), the `CustomComponent` named "Research Agent" wraps a call to this service:

```python
# pseudocode for the custom component
def run(self, topic, cycles, endpoint):
    resp = requests.post(
        f"http://34.58.1.42:8771/{endpoint}",   # /research or /signals
        json={"topic": topic, "cycles": cycles},
        timeout=600
    )
    return resp.json()["final_report"]
```

The `final_report` markdown then flows into the LLM + StructuredOutput nodes of the Langflow flow, which constrain it into the 10-field (enrichment) or 7-field (intelligence) JSON schema returned to Streamlit.

### 6.5 — What changes if you point Langflow at your local agent

The Research Agent component has a "base URL" configured at `http://34.58.1.42:8771`. To redirect that to a local instance (e.g., for development) or to a new deployment, you'd:

1. Run your local agent (`docker compose up` in `deep-research-agent-sdr/` — port 8771)
2. Expose it publicly via `ngrok` or `cloudflared` (Langflow on `flow.agenthive.tech` can't reach `localhost`)
3. In the Agent Hive UI, open the lead-enrichment flow → click the Research Agent node → edit the URL field to your public URL → save the flow
4. Or use the runtime `tweaks` mechanism in the Streamlit payload to override the URL on a per-call basis (only works if the field name is exposed in the component template)

---

## 7. The end-to-end pipeline for a single lead

Putting it all together — what *should* happen to one prospect from upload to outreach (with current + future stages clearly marked):

```
┌──────────────────────────────────────────────────────────────────────┐
│ STAGE 0 — CSV UPLOAD                                                 │
│ sections/csv_converter.py                                            │
│ • User uploads a CSV (Company Name, Domain, Name, Email, LinkedIn…)  │
│ • Grouped by Company Name → list of {company, people} rows           │
│ • Saved to st.session_state.workflow_data                            │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  │  [if domain missing — FUTURE]
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STAGE 0.5 — DOMAIN RESOLUTION  (not wired yet)                       │
│ Calls: api-domain-finder.json (UUID c8656154-…)                      │
│ • For each row where company['Company Domain'] is empty              │
│ • Sends company name → gets back {"Company Domain": "..."}           │
│ • Fills the gap on row['company']['Company Domain']                  │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STAGE 1 — LEAD ENRICHMENT  (✅ wired)                                 │
│ sections/lead_enrichment.py → api-lead-enrichment                    │
│ Internally: Deep Research Agent (Tavily + LLM, 2 cycles)             │
│ Adds: row['enriched_lead'] = {Company, Overview, Size, Revenue,      │
│                               Domain, Funding…, Latest Funding…,     │
│                               Investors, LinkedIn URL, Sources}      │
└──────────┬──────────────────────────────────────┬────────────────────┘
           │                                      │ [PARALLEL — FUTURE]
           │                                      ▼
           │   ┌─────────────────────────────────────────────────────┐
           │   │ STAGE 1b — TECHNOGRAPHICS  (not wired yet)          │
           │   │ Calls: v3-technographics retreival.json             │
           │   │ Adds: row['tech_stack'] = {categories with tools}   │
           │   └─────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STAGE 2 — ICP PROFILING  (✅ wired)                                   │
│ sections/icp_profiling.py → api-icp-profiling                        │
│ Internally: scrape company site → Gemini product summary →            │
│             OpenAI ICP fit scoring                                   │
│ Input: enriched_lead + domain + product_context + target_icp         │
│ Adds: row['icp_analysis'] = {Product Fit, ICP Score, Prospect Level, │
│                              Engagement Readiness, Justification,    │
│                              Use Case}                               │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STAGE 3 — MARKET INTELLIGENCE  (✅ wired)                             │
│ sections/market_intelligence.py → api-market-intelligence            │
│ Internally: Deep Research Agent /signals endpoint                    │
│ Input: enriched_lead minus Sources                                   │
│ Adds: row['market_intelligence'] = {Industry, Customer Segments,     │
│                                     Business Model, Geographic       │
│                                     Presence, Product Launches,      │
│                                     Press & PR, Social Media}        │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  │ [PER PERSON IN row['people']] │
                  ▼                               ▼
   ┌─────────────────────────────┐  ┌──────────────────────────────┐
   │ STAGE 4 — PERSON ENGAGEMENT │  │ STAGE 5 — CHAMPION SCORING   │
   │     (not wired yet)         │  │     (not wired yet)          │
   │ Calls: api - person eng…    │  │ Calls: api - champion scoring│
   │ Apify LinkedIn scrape →     │  │ Apify scrape → normalize →   │
   │ Gemini themes/tone analysis │  │ Gemini scoring (seniority,   │
   │                             │  │ engagement, signals)         │
   │ Adds: people[i]['signals']  │  │ Adds: people[i]['champion']  │
   └──────────────┬──────────────┘  └─────────────┬────────────────┘
                  │                                │
                  └──────────────┬─────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STAGE 6 — OUTREACH EMAIL  (not wired yet)                            │
│ Calls: email-from-csv.json                                           │
│ Input: enriched_lead + icp_analysis + market_intelligence            │
│        + per-person {signals, champion_score}                        │
│ Internally: Gemini drafts email → HiveProBothBrochure picks brochure │
│             → HTML formatter → final JSON                            │
│ Adds: people[i]['outreach_email'] = {subject, body, html,            │
│                                       call_to_action, brochure_url}  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 8. Where the gaps are

To go from today's working app to a complete end-to-end SDR pipeline, the gaps are:

| Gap | Effort | Notes |
|---|---|---|
| **Wire up Domain Resolution** | ~1h | New `sections/domain_resolution.py`, call existing flow (UUID `c8656154-…`). Relax `config.py:36` to make Company Domain optional. |
| **Wire up Technographics** | ~2h | New `sections/technographics.py`. Optional but enriches Product Fit decisions in ICP. |
| **Wire up Person Engagement (per-person LinkedIn analysis)** | ~3h | New `sections/person_engagement.py`. First flow that operates on `row['people'][i]` not row-level. Need new UI patterns for per-person progress. |
| **Wire up Champion Scoring** | ~2h | Same per-person pattern as Person Engagement. |
| **Wire up Outreach Email + Brochure** | ~3h | New `sections/email_outreach.py`. The `email-from-csv.json` flow takes a CSV today — needs adjustment (Langflow side) to accept JSON workflow data. |
| **Cross-run dashboard** | ~4h | Persist runs to SQLite, new `sections/dashboard.py` with run history + status. |
| **Live component-level progress** | ~3h | Switch from blocking POST to Langflow's streaming endpoint, render with `st.status` per component. |
| **Human-in-the-loop gate** (best at ICP and Email) | ~3h per gate | Split a flow into "draft → human review → finalize" stages with a Streamlit form between them. |

---

## 9. Security notes (please fix before any further work)

While reading the flow JSONs, two credential exposures surfaced:

1. **`deep-research-agent-sdr/api-trial.py:5`** — hardcoded Agent Hive API key (`sk-4VY5n759o1R5BO4f8BQez4HwizEmggf-z5nyUViyiIQ`). Move to `.env`, **rotate the key on Agent Hive immediately**.
2. **`SDR workflows json/api-lead-enrichment.json`** — embedded OpenAI API key (`sk-proj-C9ReQ4879…`) and Tavily API key (`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`) in the exported flow config. These are exposed because Langflow exports include the actual values of fields marked as secrets. **Rotate both keys** and re-import the flow with empty key fields (or with environment-variable references) before sharing the JSONs anywhere.

These flows are sitting in a git repo. If this repo has ever been pushed publicly or shared, treat all four keys as compromised.

---

## 10. Quick reference — every endpoint, every field

### Endpoints
| Flow | Endpoint |
|---|---|
| Domain Finder | `POST https://flow.agenthive.tech/api/v1/run/c8656154-f3f0-44f3-b989-8f2a004bf56c` |
| Lead Enrichment | `POST https://flow.agenthive.tech/api/v1/run/lead-enrichment` |
| ICP Profiling | `POST https://flow.agenthive.tech/api/v1/run/icp-profiling` |
| Market Intelligence | `POST https://flow.agenthive.tech/api/v1/run/market-intelligence` |
| Person Engagement | (TBD — not yet exposed as a slug) |
| Champion Scoring | (TBD) |
| Technographics | (TBD) |
| Email From CSV | (TBD) |
| Deep Research Agent | `POST http://34.58.1.42:8771/research`, `/signals`, `/search` |

### Common request shape (for Langflow flows)
```json
{
  "output_type": "chat",
  "input_type":  "chat",
  "input_value": "<json-stringified flow input>",
  "tweaks":      { "<NodeId>": { "<field>": "<override>" } }  // optional
}
```
With header `x-api-key: $AGENT_HIVE_API_KEY`.

### Field-level data lineage (single source of truth)

| Field | Originates in | Used by |
|---|---|---|
| `company.*` | CSV upload | Lead Enrichment input, ICP domain fallback |
| `people[].Linkedin` | CSV upload | Person Engagement input (future), Champion Scoring (future) |
| `enriched_lead.Company` | Lead Enrichment flow | ICP input, MI input |
| `enriched_lead.Overview` | Lead Enrichment flow | ICP, MI |
| `enriched_lead.Size` | Lead Enrichment flow | ICP, MI |
| `enriched_lead.Revenue` | Lead Enrichment flow | ICP, MI |
| `enriched_lead.Domain` | Lead Enrichment flow | ICP (as fallback), MI |
| `enriched_lead.Funding Information` | Lead Enrichment flow | ICP, MI |
| `enriched_lead.Latest Funding Round` | Lead Enrichment flow | ICP, MI |
| `enriched_lead.Investors` | Lead Enrichment flow | ICP, MI |
| `enriched_lead.LinkedIn URL` | Lead Enrichment flow | ICP, MI |
| `enriched_lead.Sources` | Lead Enrichment flow | (stripped before MI), CSV export |
| `product_context` | UI text_area | ICP input only |
| `target_icp` | UI text_area | ICP input only |
| `icp_analysis.Product Fit` | ICP flow | Email outreach (brochure selection) — future |
| `icp_analysis.ICP Score` | ICP flow | CSV export, dashboard |
| `icp_analysis.Use Case` | ICP flow | Email outreach copy — future |
| `market_intelligence.Product Launches` | MI flow | Email outreach (trigger event) — future |
| `market_intelligence.Press & PR` | MI flow | Email outreach (timing) — future |
| `people[i].engagement_signal` | Person Eng. flow — future | Email outreach (per-contact personalization) |
| `people[i].champion_score` | Champion Scoring — future | Email priority + recipient selection |
| `email.brochure_url` | Email flow (HiveProBothBrochure node) | Final email HTML |

---

## Appendix A — Caveats & verified vs inferred

| Item | Verified | Inferred |
|---|---|---|
| Flow endpoints and slugs | ✅ verified in code | — |
| Lead Enrichment, ICP, MI output schemas | ✅ verified via CSV export mapping + sample payloads | — |
| Research Agent points at `34.58.1.42:8771` | ✅ verified in flow JSON | — |
| Embedded API keys in JSONs | ✅ verified | — |
| Person Engagement prompt + output | ✅ verbatim verified | — |
| Domain Finder Agent prompt | ✅ verbatim verified | — |
| Champion Scoring output schema | — | ⚠️ inferred from node types; verify against actual run |
| ICP Profiling output schema (6 fields) | ⚠️ partial — derived from `state_manager.py` export mapping | Some field names may differ slightly in flow internals |
| Technographics output schema | — | ⚠️ inferred from node types; verify against actual run |
| Brochure component logic | ✅ component exists | ⚠️ exact brochure URL selection logic not extracted from custom component code |
