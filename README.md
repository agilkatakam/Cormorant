# Cormorant

**A high-depth, agentic research system. Runs on free APIs.**

Cormorant is a fully autonomous research agent that lives in your terminal and produces boardroom-grade consulting reports. It doesn't browse the web and summarize. It runs a synthetic research team — extracting atomic facts, consolidating contradictions, filing adversarial gap searches, self-correcting hallucinations in real time, and delivering structured strategic reports that read like McKinsey work.

> **Heads up**: This is a passion project, shared as-is. I built it because I kept needing high-depth market research for case competitions and nothing out there did it without hallucinating half the data. Fork it, break it, make it your own — but don't expect active maintenance or support.

---

## What Cormorant Actually Does

Cormorant isn't a search wrapper. It's a 12-phase research pipeline with schema validation, closed-loop fact-checking, and multi-persona peer review.

**It picks a framework before it researches.** Before a single search query fires, you choose from 30 professional consulting frameworks — market entry, pricing strategy, competitive benchmarking, policy gap analysis, and more. The entire pipeline — from the search queries it generates to the tone it writes in — is governed by a Strategic Focus Mandate tied to your chosen framework. There is no encyclopedic drift.

**It preserves citations end-to-end.** Every scraped domain is tracked from extraction through to the final draft. The drafting model is only ever given real, verified domains to cite. Hallucinated sources like `[internal-report.org, 2024]` are structurally impossible.

**It catches its own hallucinations.** After every section is written and peer-reviewed, the Active Truth Engine cross-references every statistical claim in the draft against the raw cached source text. If unverified claims are found, a self-correction rewrite fires immediately. The flawed draft never reaches the output file.

**It doesn't pad the word count.** Section lengths are proportional to the actual evidence. If a research angle only yielded 6 solid facts, the section is 400 words, not 1,200 words of speculative filler.

**It audits itself twice.** Once mid-pipeline per section (active), and once at compilation across the whole report (passive). The final report includes a `## Citation Integrity Audit` appendix with a `🟢 LOW / 🟡 MEDIUM / 🔴 HIGH` Hallucination Risk Score and a full table of every claim's verification status.

**It reads like a consultant wrote it.** Report output uses `### sub-headings` for logical breaks, `> **Key Metric:**` callout blocks for standout statistics, and `**bold**` on the single most critical data point per paragraph. The Key Findings section uses a `**Bold Headline**: evidence body` format. The conclusion uses a **Watch for:** watchlist + **The Non-Negotiable:** action call.

---

## Architecture

```
cormorant/
├── main.py              # CLI entry point, command routing
├── agent.py             # Top-level orchestrator — sequences all 4 phases
├── interrogator.py      # Phase 1: Framework-first conversational scoping
├── planner.py           # Phase 2: 8-angle non-linear research plan generation
├── researcher.py        # Phase 3: Per-angle 22-call research pipeline
├── compiler.py          # Phase 4: Report compilation, Visual Forge, Truth Engine
├── search.py            # Three-tier search cascade, anti-bot headers, scraper
├── memory.py            # Living Brief, source registry, atomic file writes
├── llm.py               # API client, RateGate throttle, call tracking
├── frameworks.py        # 30 framework templates, domain tiers, category registry
├── framework_focus.py   # Strategic Focus Mandates per framework
├── sessions.py          # Session persistence, section saving, status tracking
├── ui.py                # Cyan-to-indigo terminal dashboard, progress bars
└── prompts/             # 27 specialized prompt templates
    ├── atomic_extraction.txt
    ├── fact_consolidation.txt
    ├── gap_analysis.txt
    ├── section_draft.txt
    ├── section_redraft.txt   # Active self-correction rewrite prompt
    ├── citation_validator.txt
    ├── final_synthesis.txt
    ├── visual_forge.txt
    └── ...
```

### The Research Loop (Phase 3)

`researcher.py` runs a 12-step modular pipeline per research angle. The key insight is that the pipeline is **closed-loop** — it doesn't just write a draft and move on. After the Lead Partner Synthesis call, the Active Truth Engine fires a citation audit. If hallucinations are detected, a corrective rewrite call runs and replaces the section before it's ever saved to disk.

```
Query Generation
      ↓
Search & Fetch (DuckDuckGo → Brave → SearXNG cascade)
      ↓
Triplet Batch Extraction  ← source URLs preserved here
      ↓
Consolidation + Contradiction Detection
      ↓
Gap Analysis + Adversarial Search Queries
      ↓
Recursive Research (fills the gaps)
      ↓
Data Forge (synthesizes markdown tables)
      ↓
Section Draft  ← verified domains injected per claim
      ↓
Peer Review ×3 (Skeptic · Expert · Partner)
      ↓
Lead Partner Synthesis
      ↓
Active Truth Engine Audit
      ↓  hallucinations found?
      ├── YES → Self-Correction Rewrite → final_section
      └── NO  → final_section (unchanged)
      ↓
Living Brief Update + Strategic Pivot Check
```

### Citation Grounding

The fact consolidation schema tracks `sources: [url, url]` on every consolidated fact. Before the draft call, `researcher.py` parses these URLs, extracts the domain names, and appends `[Verified Sources: bain.com, statista.com]` to every claim in the prompt. The model can only cite what it's been given.

### Three-Tier Search Cascade

If DuckDuckGo gets rate-limited or blocked, the pipeline automatically falls through to Brave Search, then to SearXNG (with shuffled public instances). Dynamic browser-fingerprint headers are generated per-request to evade anti-bot heuristics. Randomized 6–12 second pacing neutralizes automated traffic signatures.

### The Living Brief

Every completed research angle updates a `living_brief.md` with foundational facts, open contradictions, completed section one-liners, and any strategic pivot flags. The brief is injected into every subsequent prompt as running context — later sections build on earlier ones instead of starting blind.

### Visual Forge

At compilation, a dedicated prompt synthesizes a Mermaid.js diagram from the consolidated research — a structural market map, value chain, or competitive flow — and injects it into the report as an interactive `\`\`\`mermaid\`\`\`` block.

---

## 30 Consulting Frameworks

Cormorant ships with 30 professional frameworks across 6 advisory divisions, each with a unique Strategic Focus Mandate that shapes every prompt in the pipeline.

| Division | Frameworks |
|----------|-----------|
| **Business Strategy & Market Intelligence** | Industry & Competitive Landscape, Market Research & Trend Forecasting, Go-To-Market Strategy, Feasibility & Expansion Studies, Strategic Benchmarking |
| **Research & Data Analytics** | Surveys & Interviews, Consumer Behaviour Analysis, Data Visualisation & Dashboarding, Business Insights Reporting, KPI & Performance Tracking |
| **Marketing & Growth Strategy** | Product-Market Fit, Brand Positioning & Messaging, Pricing Strategy & Revenue Modeling, Digital Marketing Strategy, Influencer & Campus Outreach |
| **AI & Data Intelligence** | AI-Assisted Market Research, Predictive Trend Analysis, AI Use-Case ID for Startups, Data-Driven Decision Support, AI Readiness Assessment |
| **Operations & Process Excellence** | Workflow Optimisation, Supply Chain Analysis, Cost Reduction, SOP Documentation, Execution Roadmap Development |
| **Policy, Ecosystem & Sector Research** | Sector Benchmarking, Policy Gap Analysis, MSME & Startup Ecosystem Research, Economic Opportunity Mapping, Implementation Roadmaps & KPIs |
| **Custom Frameworks** | Design any bespoke 8-angle framework on-demand via `cormorant custom` |

---

## Install & Run

```bash
pip install git+https://github.com/agilkatakam/Cormorant.git
```

Get a free API key from [Google AI Studio](https://aistudio.google.com). Cormorant runs entirely on `gemini-2.5-flash-lite` and `gemini-3.1-flash-lite` — both free tier.

```bash
export GEMINI_API_KEY="your_key_here"
cormorant new
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `cormorant new` | Start a new project — picks framework, scopes the topic, kicks off research |
| `cormorant custom` | Design a bespoke 8-angle framework for any niche — synthesized by Gemini, registered natively |
| `cormorant resume` | Resume your last project exactly where you left off |
| `cormorant status` | Current project progress, phase, and call count |
| `cormorant quota` | Daily API call usage across all models |
| `cormorant dig [id]` | Deep-dive specifically on one section (e.g. `cormorant dig S03`) |

### Interrogation Slash Commands

During the Phase 1 scoping conversation:

| Command | What it does |
|---------|-------------|
| `/skip` | Force the model to generate the research plan now |
| `/brief` | Preview the current draft research brief |
| `/topic <text>` | Refine or change the research topic mid-conversation |
| `/reset` | Restart the scoping conversation from the beginning |
| `/help` | Show all slash commands |

---

## Report Output Format

Cormorant reports are engineered to be skimmable. Not wall-of-text. Not a Wikipedia summary.

- **Executive Summary** — structured `### sub-sections` per strategic pillar, `*` bullet evidence lists, bold key stats, **Final Verdict** closing sentence
- **Key Findings** — `**Bold Headline**: evidence body [citation]` format per finding
- **Strategic Market Map** — auto-generated Mermaid.js diagram injected inline
- **Research Sections** — `### sub-headings` for logical breaks, `> **Key Metric:**` blockquote callouts, inline `[domain.com, YYYY-MM]` citations grounded to real scraped sources
- **Conclusion / So What** — **Watch for:** watchlist bullets + **The Non-Negotiable:** closing action
- **Citation Integrity Audit** — per-section hallucination audit table with `✅ VERIFIED / 🟡 PARTIALLY_SUPPORTED / ❌ UNVERIFIED_RISK` status on every sampled claim

---

## Configuration

```toml
# ~/.cormorant/config.toml

[llm]
api_key = "YOUR_KEY"

[behavior]
research_engine = "gemini-3.1-flash-lite"
interrogator = "gemini-2.5-flash-lite"
rpm_limit = 15
```

---

## Technical Constraints (Free Tier)

| Parameter | Value |
|-----------|-------|
| Research Engine | `gemini-3.1-flash-lite` |
| Interrogator | `gemini-2.5-flash-lite` (fallback: `gemma-4-31b-it`) |
| RPM | 15 (managed by `RateGate` self-throttle) |
| RPD | 500 (free tier) |
| Calls per project | ~250 (180 research · 40 compilation · 30 planning/scoping) |

---

## Terminal UI

The dashboard uses a cyan-to-indigo gradient theme (`#22d3ee` → `#4f46e5`). During research, it shows a single 80-character progress bar climbing across all execution steps, a live feed of extracted atomic facts as they're found, and the current pipeline step. No emoji. No spinners. Just clean, high-contrast terminal output.

---

## License

MIT
