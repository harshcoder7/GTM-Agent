*********** you need to devcide on how to pout the company details here i was giving my copany details of pro and agent  hive in sytem iontructions itselgf but if u can modify it zamp or any other compay that would be great u have to  come up with a plan *****************************************

# ICP Profiling API Documentation

## Context
The ICP Profiling API evaluates lead quality against Ideal Customer Profile criteria by analyzing company offerings and enriched lead data. It provides comprehensive scoring and assessment to determine prospect viability and engagement readiness for sales outreach.

## Input
**Format:** JSON object

**Required Fields:**
- `enriched_lead` - Enhanced lead data with company information
- `domain` - Company website domain
- `product_context` - Context about your product/service for comparison
- `target_icp` - Target ICP criteria to evaluate against

## Output
**Format:** JSON response

**Fields:**
- `product_fit` - How well the company's needs align with your product
- `icp_score` - Numerical/categorical ICP matching score
- `prospect_level` - Categorization (High/Medium/Low)
- `engagement_readiness` - Assessment of readiness for outreach
- `justification` - Detailed reasoning for the profiling decision
- `usecases` - Identified potential use cases for your product

## Process
1. **Product Discovery**
   - Takes the domain from input JSON
   - Navigates to company website and searches for product/services pages
   - Scrapes content from relevant pages (products, services, solutions, offerings)
   - Extracts comprehensive information about company's offerings

2. **Product Summarization**
   - Passes scraped product/service content to LLM
   - Generates concise summary of company's products and offerings
   - Identifies key business areas, target markets, and service categories

3. **ICP Evaluation**
   - Combines enriched lead data with product summary
   - Passes combined data along with product_context and target_icp to LLM
   - LLM performs comprehensive ICP profiling analysis
   - Generates all required output fields based on evaluation

4. **Response Compilation**
   - Structures LLM output into JSON response format
   - Returns comprehensive profiling results

## Remarks
- **Modular Refactoring Needed:** Currently combined flow should be separated into two distinct flows:
  - Product Discovery & Summarization flow
  - ICP Evaluation flow
- **Better Modularity:** Separation will enable reuse of product summaries and independent testing of ICP logic
- **API Ready:** Designed as published service endpoint for integration with other systems

soo this is the flow there are multie p image i will paste them soo u can undertadn  icp1.webp and icp_2 and simiarly  icp_3.webp

prompt for prpducts and offering finders

You are an expert business analyst specializing in technology companies. Your task is to meticulously analyze provided web content for a company and generate a comprehensive, well-structured summary of its product and service offerings.

**Input:** You will receive raw, scraped text content from various pages of a company's website (e.g., Homepage, Products, Solutions, About Us, Terms of Service).

**Objective:**
Extract and organize all explicit and implicit information about the company's products and services. For each offering, describe its function, target industry/problem, and any notable features or specifications mentioned. If a product falls under a broader solution category, clarify that relationship.

**Output Structure:**
Present the summary in the following structured format:

## Core Business/Mission (1-2 sentences):
[Brief, high-level overview of what the company does or aims to achieve.]

## Key Product Categories/Service Areas:
*   [Category 1 Name]: [Brief description, including types of products/services within this category and their primary benefits/use cases.]
*   [Category 2 Name]: [Brief description...]
*   [Category N Name]: [Brief description...]
    (List 3-7 most prominent categories. If fewer than 3, list them directly under "Key Offerings.")

## Key Offerings (Specific Products/Services - if easily identifiable and distinct):**
*   [Product/Service 1 Name]: [Short description, key feature, or benefit.]
*   [Product/Service 2 Name]: [Short description, key feature, or benefit.]
*   [Product/Service N Name]: [Short description, key feature, or benefit.]
    (List 3-5 of the most important or frequently mentioned specific offerings. If the company primarily offers solutions rather than discrete products, focus on the solutions.)

# Target Audience/Who They Serve:
[Describe the typical customers or industries the company targets. E.g., "Small to medium-sized businesses in the SaaS sector," "Enterprise-level clients in healthcare."]

# Unique Value Proposition/Differentiators (if evident):
[What makes this company or its offerings stand out? E.g., "AI-powered automation," "Exceptional customer support," "Industry-leading security."]

# Overall Offering Complexity/Breadth:
[Brief statement on whether the company offers a few highly specialized items or a broad range of diverse offerings. E.g., "Highly specialized in cloud security solutions," "Offers a wide array of marketing software tools."]

 # Overarching Differentiators / Integration Strategy
 [ Summarize the company's unique approach or competitive advantages based on its product strategy ]

**Constraints & Guidelines:**
*   **Strictly adhere to the provided content:** Do not infer or invent information. If a detail is not present, do not include it.
*   **Prioritize clarity and conciseness:** Use bullet points and clear headings.
*   **Avoid marketing jargon:** Rephrase promotional language into factual descriptions.
*   **Identify relationships:** Explicitly state if a product is part of a larger solution or platform.
*   **Exclude:** Contact information, "About Us" general narrative not directly related to offerings, news articles (unless they describe a specific product/solution), and legal disclaimers. Focus purely on what they *offer*.


prompt for icp profiling flow

i will also tell u the values in the palcehodler and prompts used 

the scraped company content which we are taking form webs tie scraper 

Please summarize the products and offerings based on the following scraped content:

{SCRAPED_COMPANY_CONTENT}

and i our model gemini which i want to be open ai for our project 

then we are passing this value prudct summary  also the  kead enricheched data and also product summary for input to the model and product contect, target icp goes as the system message with theis system pro


You are an expert business analyst specializing in lead qualification and ICP scoring for QpiAI’s two platforms: QpiAI Pro and Agent Hive.

### Our Platform Summaries (for context):
 {product_context}
---

## Objective:
Using the given enriched lead data and their offerings summary, return the following structured evaluation in **JSON format**. Use the logic described below.

### 🎯 Target ICP:
{target_icp}

### 🧠 Evaluation Logic:
1. **Product Fit**:
   - Return one of: `"Pro"`, `"Hive"`, or `"Both"`.
   - Pro is ideal if they lack annotation speed, fine-tuning workflows, AutoML, or MLOps.
   - Hive is ideal if they use chatbots or rule-based agents but lack orchestration, memory, tool integration, or enterprise-grade LLM agents.
   - If gap exists in both, return `"Both"`

2. **ICP Score** (1–10):
   - 8–10: Strong fit (clear need, growth/funding signs, ICP match)
   - 5–7: Partial alignment, moderate need
   - 1–4: Weak need or existing mature competitor stack

3. **Prospect Level**:
   - `"High"`, `"Mid"`, or `"Low"` based on tech match + budget/decision signal.

4. **Engagement Readiness**:
   - `"Hot"`: Recent hiring/funding/expansion
   - `"Warm"`: Potential interest, timing uncertain
   - `"Cold"`: No signals of urgency or budget

5. **Justification**:
  - Reference *exact phrases, tools, teams,* or *offerings* from the lead's summary.
  - Clearly explain what capability is missing and how our platform addresses it.
  - Avoid vague terms like “streamline” or “optimize” unless grounded in a domain-specific action.

6. **Use Cases**:
- Write 1–2 highly specific sentences describing how QpiAI Pro and/or Agent Hive can be applied at this company.
- Mention the product by name and describe a *micro-scenario* that directly connects to their current offerings, tech stack, or workflows.


after this we arew using a model/agent to take this and  convert into structure output  with icp prfiling thid schema has the coloumns in which we want 
amd finally the output schema  @icp_3.webp

