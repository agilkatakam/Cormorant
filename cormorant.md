# Cormorant: The Synthetic Research Team

Cormorant is a high-depth, agentic research orchestrator designed for MBA-level case competitions, strategic consulting, and academic-grade research. It leverages Gemini's massive context window and high RPM to execute a "Synthetic Research Team" workflow.

---

## 1. Core Philosophy: Framework-First "Partner Mode"
Cormorant operates on a **Lossless High-Depth** architecture. Rather than performing simple summaries, it subjects data to a rigorous consulting pipeline built around **30 specialized framework templates** and user-defined custom frameworks:
- **Framework-First Scoping**: Users select exactly one targeted consulting framework from an interactive menu before starting the conversational interrogation, aligning the research strategy with professional methodologies.
- **`cormorant custom` Bespoke Synth**: Create a custom 8-angle DAG research framework for any unique niche. Gemini Flash synthesises the framework, validates it for cyclical dependencies, and registers it to the system natively.
- **Strategic Focus Mandates**: Every framework features a custom strategic focus prompt, acting as a research "North Star" across all scoping, planning, search, and drafting pipelines to prevent general encyclopedic drift.
- **Atomic Data Retention**: Every source is read individually in triplet batches to ensure zero information loss.
- **Adversarial Integrity**: The agent actively searches for evidence that *challenges* its current thesis, auditing its findings for gaps.
- **Citation Grounding**: Source domain metadata is preserved end-to-end from extraction through to drafting. The drafting model is only ever given real, scraped domains for inline citations — hallucinated sources are structurally impossible.
- **Active Truth Engine (Closed-Loop Self-Correction)**: After every section is synthesized, an automated `citation_validator` cross-references claims against raw cached source text. If hallucinations are detected, a corrective rewrite call fires immediately — the flawed draft never reaches the final report.
- **The Visual Forge**: Automatically synthesises and injects high-fidelity inline Mermaid.js diagrams (structural market maps, value chains, etc.) during synthesis.
- **Passive Citation Audit (Appendix)**: At the end of compilation, a second-pass audit produces a `## Citation Integrity Audit` appendix with an overall Hallucination Risk Score for full transparency.
- **Multi-Persona Critique**: Every section is peer-reviewed by a Skeptical Investor, a Technical Expert, and a Strategic Partner.
- **Lead Partner Synthesis**: A final synthesis stage adjudicates feedback to maintain a bold, action-oriented tone. The synthesizer is strictly forbidden from introducing new unverified figures.
- **Visually Dynamic Report Output**: Prompts are engineered to produce McKinsey/BCG-style scannable reports with `**bold**` key stats, `### sub-headings` for logical breaks, `> **Key Metric:**` callout blocks, and structured bullet evidence lists.

---

## 2. System Architecture

### Phase 1: Scoping (Two-Sub-Phase Interrogation)
- **Phase 1a: Framework Selection**: The user chooses from 6 major corporate domains (or the "Custom Frameworks" tab) and locks in **exactly one** framework.
- **Phase 1b: Tailored Conversational Scoping**:
  - **Engine**: Gemini 2.5 Flash Lite (fallback to Gemma 4 31B).
  - **Goal**: Conversational scoping where the model's system prompt and first question are dynamically customized to the selected framework and strategic focus mandate to identify the **Topic**, **Decision**, and **Audience**.
  - **Output**: `case_brief.json` (contains the dynamic strategic focus mandate, validated against schemas to ensure execution safety).

### Phase 2: Strategy (Planning)
- **Engine**: Gemini 3.1 Flash Lite.
- **Goal**: Generate a non-linear 8-angle research plan with custom interpolated search seeds.
- **Output**: `plan.json` and initialization of the `living_brief.md`.

### Phase 3: The Research Loop (Execution)
Every angle follows a modular pipeline (up to 22 calls per angle):
1.  **Query Generation**: Generates targeted search queries tuned to the angle and strategic focus.
2.  **Search & Fetch**: Executes multi-engine search cascade across DuckDuckGo → Brave → SearXNG.
3.  **Triplet Batch Extraction**: Reads sources in batches of 3, extracting atomic facts with source URL metadata.
4.  **Consolidation**: Merges atoms into a `Fact Pool`, de-duplicating and ranking by importance.
5.  **Gap Analysis**: Identifies missing data and generates **Adversarial Search** queries.
6.  **Recursive Research**: Executes follow-up searches for missing/challenging data.
7.  **Data Forge**: Synthesises structured Markdown tables from the raw fact pool.
8.  **Drafting**: Writes a high-SNR section using only top-ranked facts. Source domain names are injected alongside each claim to enable grounded inline citations.
9.  **Peer Review Suite**: 3 parallel critique calls (Skeptic, Expert, Partner).
10. **Lead Partner Synthesis**: Integrates reviews. Strictly forbidden from introducing new unverified figures.
11. **Active Truth Engine**: Cross-references the synthesized section against raw cached source text. Any `UNVERIFIED_RISK` claims trigger an immediate **Self-Correction Rewrite** call. Corroborated sections pass through untouched.
12. **Brief Update**: Updates the `Living Brief` with new "Foundational" facts and checks for **Strategic Pivots**.

### Phase 4: Compilation (Synthesis)
- **Goal**: Merges 8 deep-dive sections into a coherent, professional report.
- **Stages**: 
  1. Executive Summary (structured sub-headings, bold key stats, bullet evidence)
  2. Key Findings (bold headline + evidence body format for each finding)
  3. **The Visual Forge** (synthesises structural Mermaid.js diagrams to map market landscapes)
  4. Section Transitions
  5. Conclusion / So What (watchlist format + bold non-negotiable action)
  6. Risks & Limitations
  7. **Passive Citation Audit** (second-pass `## Citation Integrity Audit` appendix with overall LOW/MEDIUM/HIGH Hallucination Risk Score)
  8. Final Read-through (`_final_readthrough` processes content in sections to avoid large-report truncation)

---

## 3. Supported Consulting Frameworks
Cormorant features **30 standard frameworks** organized across **6 core advisory divisions**, plus a dynamic category for custom frameworks:

### I. Business Strategy & Market Intelligence
*   **`industry_competitive_landscape`**: Industry & Competitive Landscape Analysis
*   **`market_research_trend_forecasting`**: Market Research & Trend Forecasting
*   **`gtm_strategy_development`**: Go-To-Market Strategy Development
*   **`feasibility_expansion_studies`**: Feasibility & Expansion Studies
*   **`strategic_benchmarking_opportunity_mapping`**: Strategic Benchmarking & Opportunity Mapping

### II. Research & Data Analytics
*   **`surveys_interviews_focus_groups`**: Surveys, Interviews & Focus Groups
*   **`consumer_behaviour_analysis`**: Consumer Behaviour Analysis
*   **`data_visualisation_dashboarding`**: Data Visualisation & Dashboarding
*   **`business_insights_reporting`**: Business Insights & Reporting
*   **`kpi_performance_tracking`**: KPI & Performance Tracking Frameworks

### III. Marketing & Growth Strategy
*   **`product_market_fit`**: Product-Market Fit Analysis
*   **`brand_positioning_messaging`**: Brand Positioning & Messaging
*   **`pricing_strategy_revenue_modeling`**: Pricing Strategy & Revenue Modeling
*   **`digital_marketing_social_media`**: Digital Marketing & Social Media Strategy
*   **`influencer_campus_outreach`**: Influencer & Campus Outreach Strategy

### IV. AI & Data Intelligence Consulting
*   **`ai_assisted_market_competitive_research`**: AI-Assisted Market & Competitive Research
*   **`predictive_trend_customer_analysis`**: Predictive Trend & Customer Analysis
*   **`ai_use_case_id`**: AI Use-Case ID for Startups & MSMEs
*   **`data_driven_decision_support`**: Data-Driven Decision Support Systems
*   **`ai_readiness_adoption_assessment`**: AI Readiness & Adoption Assessment

### V. Operations & Process Excellence
*   **`workflow_process_optimisation`**: Workflow & Process Optimisation
*   **`supply_chain_logistics`**: Supply Chain & Logistics Analysis
*   **`cost_reduction_efficiency`**: Cost Reduction & Efficiency Enhancement
*   **`sop_process_documentation`**: SOP & Process Documentation
*   **`execution_roadmap_development`**: Execution Roadmap Development

### VI. Policy, Ecosystem & Sector Research
*   **`sector_benchmarking_studies`**: Sector Benchmarking Studies
*   **`policy_gap_analysis`**: Policy Gap Analysis
*   **`msme_startup_ecosystem_research`**: MSME & Startup Ecosystem Research
*   **`economic_industry_opportunity_mapping`**: Economic & Industry Opportunity Mapping
*   **`implementation_roadmaps_kpi`**: Implementation Roadmaps & KPI Frameworks

### VII. Custom Frameworks (Dynamic Category)
*   *Bespoke research templates designed on-demand via the CLI, loaded natively at runtime from `~/.cormorant/custom_frameworks.json`.*

---

## 4. Technical Constraints & Quota

- **Interrogator**: `gemini-2.5-flash-lite` (Fallback: `gemma-4-31b-it`)
- **Research Engine**: `gemini-3.1-flash-lite`
- **RPM (Requests Per Minute)**: 15 (Managed by a `RateGate` self-throttle).
- **RPD (Requests Per Day)**: 500 (Free Tier).
- **Project Budget**: 250 calls (approx. 180 for research, 40 for compilation, 30 for planning/interrogation).

---

## 5. Directory Structure
```text
/Cormorant/
├── cormorant/
│   ├── agent.py         # Top-level Orchestrator
│   ├── researcher.py    # Deep-dive 20-call pipeline
│   ├── memory.py        # Living Brief & Token Management
│   ├── llm.py           # API Client & Rate Throttling
│   ├── search.py        # Search, Anti-Bot scraper & AMP Fallback
│   ├── compiler.py      # Stitches sections & executes final readthroughs
│   ├── frameworks.py    # Registers templates, categories & domain tiers
│   ├── framework_focus.py # High-fidelity strategic focus mandates
│   ├── prompts/         # 20+ specialized prompt templates (including Visual Forge & Citation Validator)
│   └── schemas/         # JSON validation schemas
├── projects/            # Individual research projects
│   └── [slug]_[date]/
│       ├── cache/       # Scraped HTML raw texts populated during execution
│       ├── living_brief.md
│       ├── case_brief.json
│       ├── plan.json
│       ├── session.json
│       └── sections/    # Final .md chapters (S01 - S08)
└── report_final.md      # The final output (with Strategic Market Map & Citation Integrity Audit)
```

---

## 6. Commands
- `cormorant custom`: **[NEW]** Launch the interactive bespoke framework synthesis. Gemini Flash designs a targeted, cyclic-safe, 8-angle consulting framework based on your topic description. Registers it to Category VII for instant selection.
- `cormorant new`: Start a fresh project. First prompts category selection (including Custom), then framework selection, and launches the scoping chat.
- `cormorant resume`: Pick up where you left off.
- `cormorant status`: Check current project progress and usage.
- `cormorant quota`: View daily model usage.
- `cormorant dig [id]`: Specifically deepen research on one section.

### Interrogation (Phase 1) Slash Commands
- `/skip`: Force the model to generate a plan now.
- `/brief`: Preview the draft research brief.
- `/topic <text>`: Refine or change the topic.
- `/reset`: Restart the scoping conversation.
- `/help`: Show all slash commands.

---

## 7. Hardened Anti-Bot Search & Elite Terminal UI

Cormorant features a state-of-the-art scraping and interactive interface layer to ensure uninterrupted, high-fidelity research execution:

### I. Three-Tier Search Cascade & Evasion
* **Engine Fallback Cascade**: If the primary scraper (DuckDuckGo) fails or blocks, the pipeline automatically cascades through Brave Search and SearXNG HTML scraper (shuffling public instances) to guarantee data collection under any circumstances.
* **Dynamic Header Fingerprinting**: The `_get_headers(engine, url)` generator dynamically crafts browser-perfect request headers. It automatically synthesizes `sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`, `Sec-Fetch-*`, and connection properties, matching the specific target referrer to evade advanced firewalls.
* **Human-Mimic Pacing**: Randomized pacing intervals of **`6.0s - 12.0s`** combined with supplementary cooling-off delays completely neutralize automated traffic signatures.
* **Native Proxy Integration**: Automatically respects standard environment variables (`HTTP_PROXY` and `HTTPS_PROXY`) through the `httpx` engine.

### II. Elite Cyan-to-Indigo Terminal Dashboard
* **Overall Completion Progress**: Displays a single, beautiful **80-character horizontal progress bar** representing your absolute project progress (0% to 100%) slowly climbing across all 160 execution steps of your 8 research angles.
* **Cyan-to-Indigo Gradient Fade**: The dashboard and bar display a smooth, premium glowing gradient transitioning from deep indigo (`#312e81` $\rightarrow$ `#4f46e5`) to electric cyan (`#22d3ee`).
* **Custom Vertical Gradient Startup Logo**: Displays a stylized, cropped Cormorant ASCII art startup logo featuring a dynamic vertical gradient fading from cyan (`#22d3ee`) down to deep indigo (`#4f46e5`).
* **Emoji-Free Strategy Presentation**: Strictly adheres to a minimalist corporate advisory aesthetic—completely free of emojis, utilizing clean, high-contrast hyphens (`-`) for extracted facts feeds.

