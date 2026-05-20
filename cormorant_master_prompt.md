# Master Prompt — Build Cormorant

> Pass this entire document to Claude Code as the build specification.

---

## 0. Project Identity

**Name:** Cormorant
**Tagline:** Deep research. Consulting grade. Runs while you sleep.
**License:** MIT
**Distribution:** `pip install git+https://github.com/<user>/Cormorant.git`
**Entry point:** `cormorant` (terminal command)

Cormorant is a terminal-based autonomous deep research agent that produces consulting-grade reports of ~5,000 words on any topic the user asks about. It runs on Google's free Gemini API tier. The user starts it, optionally closes the terminal, and returns 2-4 hours later to a finished markdown report structured like a real consulting deliverable.

**Target users:** Consultants, consulting candidates (MBA, case interview prep), market analysts, founders doing competitive research, anyone who needs case-study depth.

Cormorant is the sibling project to **Toucan** (a coding agent built by the same developer). Same DNA: terminal-first, opinionated, free-API-powered, atomic writes, session persistence, beautiful UX. Different domain.

---

## 1. What Cormorant Does (End-to-End User Experience)

1. User runs `cormorant` in a terminal.
2. Animated banner appears. Cormorant greets and asks what to research.
3. **Gemma-powered interrogation** — a conversational back-and-forth (5-8 turns) that extracts: the real decision being informed, the audience, the appropriate consulting framework, scope, depth, and emphasis areas.
4. Gemma proposes **8 research angles** structured around the chosen framework. User confirms or edits via natural language ("add something about Chinese competition").
5. Once locked, the **autonomous research loop** begins:
   - 1 Flash Lite call locks in the plan
   - 8 angles × ~10 Flash Lite calls each = ~80 calls of research
   - 12 Flash Lite calls compile the final report
   - 57 Flash Lite calls held as buffer for retries and deep-dives
6. User can close the terminal. State persists to disk. `cormorant status` from any terminal shows live progress.
7. Hours later: `report_final.md` is sitting in the project folder, ~5,000 words, ~13 pages, structured as a consulting brief with executive summary, key findings, 8 sections, risks/limitations, conclusion, and tiered bibliography.
8. User can run `cormorant dig S02` to spend remaining buffer calls going deeper on a specific section.

---

## 2. Critical Architectural Principles

These are non-negotiable. Every design decision flows from them.

### 2.1 Sequential execution, not parallel
One Flash Lite call at a time. Predictable, debuggable, easy to rate-limit-manage. The user has hours to wait — there's no reason to parallelize.

### 2.2 Write to disk immediately
Every claim, every section draft, every Living Brief update — written to disk the moment it's produced. If the process dies at call 87 of 150, the user has 86 calls of progress recoverable. Use atomic writes (temp file + `os.replace`).

### 2.3 The Living Brief is the cohesion mechanism
Not stitching at the end. A 2K-token document that every Flash Lite call reads and updates. It threads context through every call so Section 5 naturally references findings from Sections 1-4 without needing their full text in context. This is the single most important architectural decision.

### 2.4 The case brief is immutable
Original user intent never gets overwritten by evolving research. The Living Brief sits alongside the case brief, not replacing it. Flash Lite always sees both — the original north star and the evolving understanding. If evidence overturns the thesis, that surfaces in the conclusion as a finding, not silent drift mid-loop.

### 2.5 Trafilatura, not LLM, parses HTML
Web scraping is solved by the `trafilatura` library locally. Zero API calls for HTML cleanup. LLM only ever sees clean article text.

### 2.6 Explicit output schemas in every Flash Lite call
Either strict JSON with a schema or markdown with a strict section structure. Python validates output before writing to disk. Malformed output triggers retry with a stricter prompt (consumes a buffer call but never silently produces bad output).

### 2.7 No premium model calls, ever
The free tier provides Gemma and Flash Lite. The user does not have access to Gemini Pro, Flash 2.5, or any premium model. Architecture assumes Flash Lite for all reasoning. Quality comes from structure (Living Brief, multi-round per-angle, devil's advocate), not from smarter models.

---

## 3. API Configuration

The agent uses Google's Gemini API via the official `google-generativeai` Python SDK.

```python
MODELS = {
    "gemma": {
        "name": "gemma-3-27b-it",       # use latest available Gemma model
        "rpm": 15,
        "rpd": 1500,
        "tpm": "unlimited",
        "role": "interrogation only — Phase 1"
    },
    "flash_lite": {
        "name": "gemini-3.1-flash-lite",  # use latest Flash Lite
        "rpm": 15,
        "rpd": 500,
        "tpm": 250000,
        "role": "everything after interrogation — Phases 2-4"
    }
}
```

### Per-project budget
- **Flash Lite:** 150 calls maximum per research project
- **Gemma:** 10 calls maximum for interrogation
- Typical user pattern: 1-2 deep research projects per day

### API key
Loaded from (in priority order):
1. `~/.cormorant/config.toml`
2. Environment variable `GEMINI_API_KEY`
3. Prompt user on first run, save to config

Get keys from Google AI Studio (https://aistudio.google.com).

### Rate limit handling
```python
def call_with_retry(model, prompt, max_wait=300):
    while True:
        try:
            return client.generate(model, prompt)
        except RateLimitError:
            log("Rate limited. Sleeping 60s.")
            time.sleep(60)
        except QuotaExceededError:
            raise  # daily quota — surface to user, don't retry
```

Track RPM locally to self-throttle before hitting the API ceiling. Deque of timestamps for the last 60 seconds; if length >= 15, sleep before next call.

---

## 4. Project Structure

```
cormorant/
├── pyproject.toml              # packaging, dependencies
├── README.md
├── LICENSE                     # MIT
├── cormorant/
│   ├── __init__.py
│   ├── main.py                 # REPL, slash commands, CLI entry
│   ├── agent.py                # Orchestrator — the research loop
│   ├── interrogator.py         # Gemma-powered conversational scoping
│   ├── planner.py              # Angle generation from framework
│   ├── researcher.py           # Per-angle 10-call research pipeline
│   ├── compiler.py             # Final report assembly
│   ├── memory.py               # Living Brief + source registry
│   ├── llm.py                  # Gemini API client, rate limiting
│   ├── search.py               # DDG + httpx + trafilatura pipeline
│   ├── sessions.py             # Project persistence, resume
│   ├── frameworks.py           # Consulting framework templates
│   ├── ui.py                   # Banner, progress bars, formatting
│   ├── prompts/                # Prompt templates (one per call type)
│   │   ├── interrogator_system.txt
│   │   ├── planning.txt
│   │   ├── query_generation.txt
│   │   ├── extraction.txt
│   │   ├── contradiction_analysis.txt
│   │   ├── section_draft.txt
│   │   ├── devils_advocate.txt
│   │   ├── integration.txt
│   │   ├── brief_update.txt
│   │   ├── executive_summary.txt
│   │   ├── key_findings.txt
│   │   ├── transitions.txt
│   │   ├── conclusion.txt
│   │   ├── risks_limitations.txt
│   │   ├── bibliography.txt
│   │   └── final_readthrough.txt
│   └── schemas/                # JSON schemas for output validation
│       ├── case_brief.json
│       ├── plan.json
│       ├── claims.json
│       └── contradictions.json
└── tests/
    ├── test_search.py
    ├── test_memory.py
    ├── test_rate_gate.py
    └── test_schemas.py
```

---

## 5. The Call Budget — Exact Allocation

```
PHASE 1 — Gemma interrogation:          ~6 Gemma calls   (separate budget)
─────────────────────────────────────────────────────────────────────────
PHASE 2 — Planning:                       1 Flash Lite call
PHASE 3 — Research loop:                 80 Flash Lite calls (8 × 10)
PHASE 4 — Compilation:                   12 Flash Lite calls
PHASE 5 — Buffer (retries, dig deeper): 57 Flash Lite calls
─────────────────────────────────────────────────────────────────────────
TOTAL Flash Lite:                       150 calls
```

### Token math (verify rate limit headroom)
- Typical Flash Lite call: ~7,400 tokens in + ~1,500 tokens out = ~9,000 tokens
- Sequential execution: max 4 calls/minute realistically
- Per-minute usage: ~36,000 tokens
- Limit: 250,000 TPM
- Utilization: ~14% of limit — comfortable headroom

The TPM limit will never be the binding constraint. The 15 RPM limit is. Self-throttling handles it.

---

## 6. Phase 1 — Gemma Interrogation (`interrogator.py`)

A conversational loop. Gemma asks one question at a time, builds understanding turn by turn. **One question per turn, not a five-question dump.**

### What the interrogation must extract

1. **The decision being informed.** Not "what to research" but "what decision does this research support, and who is making it." This is the difference between a summary tool and a consulting tool.
2. **The audience.** Board, internal team, case study prep, personal learning. Affects depth and tone.
3. **The framework.** Identify which consulting framework fits (see Section 9).
4. **Geographic and time scope.**
5. **Any exclusions or specific angles the user wants emphasized.**

### Interrogation flow example

```
Cormorant: What market are you investigating, and who's making
           a decision based on this?

User: Semiconductor industry, investment angle for AI chips.

Cormorant: Is this for portfolio allocation, a specific
           position, or general thesis development?

User: Portfolio allocation for a mid-size PE fund.

Cormorant: Public markets only or also private? Time horizon?

User: Public, 6-12 months forward looking.

Cormorant: Geographic focus — US/Taiwan/China/Korea, or global?

User: Global, but emphasize US-China dynamics.

Cormorant: Depth — exec summary, analyst brief, or full deep dive?

User: Full deep dive.

Cormorant: Got it. Here's how I understand this:

  DECISION:   AI semiconductor allocation for mid-size PE
              fund, 6-12 month horizon
  FRAMEWORK:  Investment thesis validation
  EMPHASIS:   US-China dynamics, AI chip segment
  EXCLUDE:    Private companies, consumer electronics

The report will move through 8 angles:
  S01  Demand drivers and durability
  S02  Competitive structure and moats
  S03  Supply chain and capacity constraints
  S04  Geopolitical and regulatory risk
  S05  Valuation and timing
  S06  Bull case — what has to be true
  S07  Bear case — what breaks the thesis
  S08  So what — positioning implications

The report will argue one of three things by the end:
  A) Thesis valid — here's how to position
  B) Thesis valid but timing wrong
  C) Thesis overhyped — here's the real story

Does this framing match what you need?

User: Yes, but add something about ASML / picks-and-shovels.

Cormorant: Folded into S02. Starting research.
```

### Output of Phase 1

`case_brief.json`:

```json
{
  "topic": "AI Semiconductor Investment Landscape",
  "decision": "Portfolio allocation for mid-size PE fund, 6-12mo horizon",
  "audience": "internal investment team",
  "framework": "investment_thesis",
  "thesis_hypothesis": "AI semiconductor demand is durable but concentrated; picks-and-shovels (ASML, TSMC) may be more asymmetric than direct chip plays",
  "narrative_arc": [
    "Thesis valid — here's how to position",
    "Thesis valid but timing wrong",
    "Thesis overhyped — here's the real story"
  ],
  "scope": {
    "geography": "global, emphasis on US-China",
    "time_horizon": "6-12 months forward",
    "depth": "full"
  },
  "emphasis": ["US-China dynamics", "picks-and-shovels (ASML/TSMC)"],
  "exclude": ["private companies", "consumer electronics"],
  "created_at": "2026-05-14T09:00:00"
}
```

### Initial Living Brief seeded

The Living Brief is initialized with the case brief's hypothesis as its initial THESIS section. Everything else (CONFIRMED, CONTRADICTIONS, SECTIONS COMPLETE, OPEN ANGLES) starts empty.

### Gemma calls used
Typically 5-8, hard cap at 10. If interrogation hits 10 without convergence, force a summary and confirm with user.

---

## 7. Phase 2 — Planning (`planner.py`)

A single Flash Lite call. Reads `case_brief.json`. Locks in the 8 angles with full structure.

### Output: `plan.json`

```json
{
  "angles": [
    {
      "id": "S01",
      "title": "Demand drivers and durability",
      "key_questions": [
        "What is actually driving AI chip demand — training vs inference?",
        "How durable is the demand curve through 2027?",
        "Which end markets are growing and which are saturating?"
      ],
      "search_seeds": [
        "AI chip demand forecast 2025 2026",
        "data center capex AI infrastructure",
        "inference vs training compute demand"
      ],
      "priority": 10,
      "depends_on": []
    },
    {
      "id": "S02",
      "title": "Competitive structure and moats",
      "key_questions": ["..."],
      "search_seeds": ["..."],
      "priority": 9,
      "depends_on": ["S01"]
    }
    // ... S03-S08
  ],
  "execution_order": ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08"]
}
```

### Dependency handling
Use Kahn's algorithm (topological sort) for execution order. Most angles depend on S01 (demand context). Bull case (S06) and bear case (S07) depend on all prior angles being complete.

### User edit window
After planning call completes, show the plan and prompt: `Edit plan? [y/N]`. If yes, user can edit `plan.json` directly or via natural language commands. Then `cormorant go` starts Phase 3.

---

## 8. Phase 3 — Research Loop (`researcher.py` + `agent.py`)

For each angle in execution order, run the **10-call pipeline**.

### Call 1 — Query Generation
- **Input:** angle (title, key questions, search seeds) + Living Brief + case brief + previous section one-liners
- **Output:** 5 targeted search queries, each attacking a different facet
- **Constraint:** queries must be diverse, not variations of each other

### Search Phase (no API calls — pure Python)
1. Hit DuckDuckGo HTML endpoint (`https://html.duckduckgo.com/html/`) for each query
2. Collect ~25 URLs total, deduplicate
3. Score by domain tier (see Section 11) + snippet relevance (simple keyword overlap)
4. Take top 8 URLs
5. Fetch with `httpx` (timeout=10s, follow redirects, set realistic User-Agent)
6. Pass through `trafilatura.extract()` for clean text
7. **Fallback for JS-rendered pages:** if trafilatura returns <300 chars, try AMP cache via `https://amp.google.com/v/s/<url>`
8. **Mark as paywalled** if both attempts fail
9. Chunk clean text at paragraph boundaries, max ~1500 tokens per chunk
10. Cache raw + clean content to `cache/<angle_id>_raw/`
11. Register all successful sources in `sources.json`

### Call 2 — First Source Extraction
- **Input:** angle context + chunks from URLs 1-4 + case brief (compressed to 300 tokens)
- **Output:** strict JSON (see schema in Section 12)
- **Validation:** Python validates JSON structure before writing. On failure, retry with stricter prompt (consumes a buffer call).

### Call 3 — Second Source Extraction
- **Input:** angle context + chunks from URLs 5-8 + case brief
- **Output:** same JSON structure

### Call 4 — Contradiction and Gap Analysis
- **Input:** all claims from Calls 2+3 + Living Brief
- **Output:** confirmed claims, contradictions with resolutions, remaining gaps, **evidence quality verdict** (`strong | adequate | thin | paywalled`)
- **Trigger:** if verdict is `thin` or `paywalled`, run targeted re-search with specific query types: SEC filings (`site:sec.gov`), government sources, PDFs (`filetype:pdf`), earnings call transcripts. Re-search consumes buffer calls but uses the same extraction call structure.

### Call 5 — Section First Draft
- **Input:** confirmed claims + contradictions + Living Brief + case brief + previous section one-liners
- **Output:** 400-600 word section using **exact structure**:

```markdown
## [Section Title]

[Opening claim — one assertive sentence.]

[Evidence paragraph 1 — with inline citations like [reuters.com, 2024-04].]

[Evidence paragraph 2 — building the argument.]

[Counterargument acknowledged in one paragraph.]

[Implication for thesis — one sentence.]

**Sources used:** reuters.com, ft.com, semianalysis.com, sec.gov
```

### Call 6 — Devil's Advocate
- **Input:** section draft + all contradicting evidence + thesis
- **Output:** strongest counterargument + reasoning for whether primary argument still holds
- **Critical instruction in prompt:** "Do NOT both-sides. State the counterargument clearly, then explain why the primary argument still holds given evidence weight, OR explicitly flag that thesis needs revision."

### Call 7 — Integration
- **Input:** original draft + devil's advocate output
- **Output:** revised section that acknowledges the counterargument honestly **without diluting assertion**. Consulting writing is assertive — it acknowledges counterarguments and dispatches them with reasoning, not balanced both-siding.

### Call 8 — Living Brief Update
- **Input:** finalized section + current Living Brief
- **Output:** delta updates only:
  ```json
  {
    "confirmed_add": ["new fact 1", "new fact 2"],
    "confirmed_drop": ["oldest fact to remove if list >10"],
    "thesis_nuance": "added nuance, not replacement",
    "contradictions_add": [],
    "contradictions_resolved": [],
    "section_complete": {
      "id": "S01",
      "one_liner": "Demand real and durable, pace slower than 2022 hype, 2030 horizon solid."
    },
    "new_angles_discovered": []
  }
  ```
- Python applies the delta to `living_brief.md` atomically.

### Calls 9-10 — Buffer (per angle)
- Reserved for: rate limit retries, format validation retries, thin evidence re-runs
- **Banked if unused** — roll into project-level buffer

### Section output written atomically
After Call 8, the angle is complete. `sections/S0X_<slug>.md` is written. `living_brief.md` is updated. `session.json` records progress.

---

## 9. Consulting Frameworks (`frameworks.py`)

Hard-coded framework templates. Gemma's interrogation chooses one. Each defines the 8 angles.

### `investment_thesis`
1. Demand drivers and durability
2. Competitive structure and moats
3. Supply chain and capacity constraints
4. Geopolitical and regulatory risk
5. Valuation and timing
6. Bull case — what has to be true
7. Bear case — what breaks the thesis
8. So what — positioning implications

### `market_entry`
1. Market size and growth
2. Customer segments and jobs-to-be-done
3. Competitive landscape
4. Regulatory environment
5. Go-to-market routes
6. Unit economics benchmarks
7. Key risks and mitigants
8. Entry recommendation and sequencing

### `industry_landscape`
1. Market structure and key players
2. Value chain analysis
3. Demand and growth drivers
4. Disruption vectors
5. Regulatory environment
6. Capital flows and M&A activity
7. Geographic dynamics
8. Forward outlook

### `competitive_analysis`
1. Competitive set definition
2. Market share and positioning
3. Business model comparison
4. Capability and moat analysis
5. Pricing dynamics
6. Strategic moves and signals
7. Threats to incumbent
8. Strategic implications

### `strategic_options`
1. Current state diagnosis
2. Forces driving change
3. Option A — detailed
4. Option B — detailed
5. Option C — detailed
6. Comparative evaluation
7. Risks and dependencies
8. Recommended path

### `due_diligence`
1. Business model and revenue quality
2. Market position and competition
3. Financial performance and trends
4. Operational and capability assessment
5. Management and governance
6. Risk factors
7. Growth opportunities
8. Investment recommendation

Each framework has its angles, default search seeds per angle, and stylistic notes (e.g., DD writing is more cautious; strategic options writing is more decisive).

---

## 10. Phase 4 — Compilation (`compiler.py`)

12 Flash Lite calls to assemble the final report.

### Compilation Call 1 — Executive Summary
- **Input:** all 8 section one-liners + Living Brief + case brief
- **Output:** 180-word executive summary
- **Constraint:** states findings directly. Does NOT preview the conclusion. Ends with a one-sentence verdict.

### Compilation Call 2 — Key Findings Bullets
- **Input:** Living Brief
- **Output:** 5-7 bullet points, each ~25 words, most important factual findings with inline citations

### Compilation Call 3 — Section Transitions
- **Input:** opening sentence of each section
- **Output:** one transition sentence between each pair of sections (7 transitions total)

### Compilation Calls 4-6 — Conclusion / So-What (up to 3 calls)
- **Input:** full Living Brief + case brief + executive summary (to avoid repetition)
- **Output:** 250-word forward-looking conclusion focused on implications, not findings
- **Constraint:** pure implication. Forward-looking only. References specific findings without repeating them.
- Calls 5-6 used only if Call 4 output fails quality check (e.g., repeats exec summary content)

### Compilation Calls 7-8 — Risks and Limitations (up to 2 calls)
- **Input:** all `evidence_quality` scores from extraction + all flagged gaps + unresolved contradictions + paywalled source count
- **Output:** honest limitations section. This is what makes the report trustworthy. Lists thin evidence areas, unresolved contradictions, paywalled blind spots.

### Compilation Call 9 — Bibliography
- **Input:** `sources.json` registry
- **Output:** deduplicated sources sorted by tier (Tier 1 first), then by frequency of use. Format:
  ```
  [Tier 1] reuters.com — "Title here" — 2024-04 — https://...
  ```

### Compilation Calls 10-12 — Final Read-Through (up to 3 calls)
- **Input:** complete assembled report
- **Output:** list of specific line edits only — no full rewrites. Flags:
  - Cross-section factual contradictions
  - Broken "as noted above" references
  - Awkward transitions
  - Repetition between exec summary and conclusion
- Python applies edits via simple string replacement
- Calls 11-12 used only if Call 10 surfaces edits that, when applied, create new issues

### Final report structure

```
# [Topic] — [Decision Framing]

## Executive Summary
[180 words]

## Key Findings
- [Bullet 1]
- [Bullet 2]
- ...

## S01 [Title]
[Section content with transitions]

## S02 [Title]
...

## S08 [Title]
...

## Risks and Limitations
[200 words — honest assessment of evidence weaknesses]

## So What
[250 words — forward-looking implications]

## Sources
[Tiered bibliography]

---
*Generated by Cormorant on [date]. Calls used: 134/150.*
```

---

## 11. Source Quality — Domain Tiers

`frameworks.py` includes:

```python
DOMAIN_TIERS = {
    # Tier 1 — primary sources, regulators, top-tier financial press
    "sec.gov": 1, "federalreserve.gov": 1, "europa.eu": 1,
    "imf.org": 1, "worldbank.org": 1, "oecd.org": 1, "bis.org": 1,
    "reuters.com": 1, "ft.com": 1, "wsj.com": 1, "economist.com": 1,
    "bloomberg.com": 1, "nikkei.com": 1,

    # Tier 2 — established analyst/specialist sources
    "semianalysis.com": 2, "stratechery.com": 2,
    "hbr.org": 2, "mckinsey.com": 2, "bain.com": 2, "bcg.com": 2,
    "techcrunch.com": 2, "theinformation.com": 2,
    "barrons.com": 2, "morningstar.com": 2,

    # Tier 3 — usable, treat with care
    "seekingalpha.com": 3, "businessinsider.com": 3,
    "cnbc.com": 3, "marketwatch.com": 3,
    "medium.com": 3, "substack.com": 3,

    # Tier 4 — only for sentiment / community signal
    "reddit.com": 4, "twitter.com": 4, "x.com": 4,
    "ycombinator.com": 4,
}
DEFAULT_TIER = 3  # unknown domains
```

### Trust score for synthesis
When two sources contradict, the lower-tier number wins (Tier 1 > Tier 2 > Tier 3). When tiers are equal, more recent source wins. Both scoring rules surface in the contradiction analysis prompt.

---

## 12. Output Schemas

### `case_brief.json`
See Section 6 for structure.

### `plan.json`
See Section 7 for structure.

### Extraction output schema (Calls 2, 3 of each angle)
```json
{
  "claims": [
    {
      "claim": "string — the factual assertion",
      "source_url": "string — full URL",
      "source_date": "YYYY-MM or 'unknown'",
      "confidence": "high | medium | low",
      "supports_thesis": true,
      "quote": "optional verbatim quote ≤25 words for citation"
    }
  ],
  "evidence_quality": "strong | adequate | thin | paywalled",
  "gaps": ["string — what's missing"]
}
```

`supports_thesis` can be `true`, `false`, or `null` (for facts that are relevant but neither support nor contradict).

### Contradiction analysis output schema (Call 4)
```json
{
  "confirmed_claims": ["string"],
  "contradictions": [
    {
      "claim_a": "string",
      "claim_b": "string",
      "source_a_tier": 1,
      "source_b_tier": 2,
      "resolution": "string — how this resolves",
      "is_real_contradiction": true
    }
  ],
  "gaps": ["string"],
  "evidence_quality": "strong | adequate | thin | paywalled",
  "re_search_needed": false,
  "re_search_suggestions": ["specific query types if re-search needed"]
}
```

### Living Brief delta schema (Call 8)
See Section 8 (Call 8 description) for structure.

### All schemas validated via `jsonschema` library before writing to disk. Validation failure triggers retry with stricter prompt.

---

## 13. The Living Brief — Detailed Spec

File: `living_brief.md` in project root. **Hard cap: 2,000 tokens.** Enforced by truncating CONFIRMED list when full (drop oldest).

```markdown
# LIVING BRIEF — [Topic]

## THESIS
[Single paragraph, ~100 words. Evolves with nuance only — never overwritten.]

## CONFIRMED
- [Fact 1 with inline source domain]
- [Fact 2 with inline source domain]
... (max 10 items, oldest dropped)

## CONTRADICTIONS LIVE
- [Source A says X, Source B says Y — current status: unresolved/resolved]
... (cleared when resolved)

## SECTIONS COMPLETE
- S01 [Title]: [one-line conclusion]
- S02 [Title]: [one-line conclusion]
...

## OPEN ANGLES
- [Angle discovered during research not in original plan]
```

### Read pattern
Every Flash Lite call (except Phase 2 Call 1 and some compilation calls) reads the full Living Brief as part of its prompt.

### Write pattern
Only `memory.py` writes to it. Updates are deltas applied atomically:
1. Read current brief
2. Apply delta from Call 8 output
3. Validate total token count ≤ 2000 (truncate CONFIRMED if needed)
4. Write to temp file
5. `os.replace()` to final path

---

## 14. Search Pipeline (`search.py`)

### Function: `search_and_fetch(queries: list[str], angle_id: str) -> list[Source]`

```python
def search_and_fetch(queries, angle_id):
    """
    1. For each query: hit DDG HTML, collect URLs + snippets
    2. Dedupe URLs globally (check sources.json — if already fetched, reuse cache)
    3. Score URLs: domain_tier_weight + snippet_relevance
    4. Take top 8 by score
    5. Fetch with httpx (10s timeout, realistic UA, follow redirects)
    6. Pass HTML to trafilatura.extract()
    7. If clean text < 300 chars, try AMP cache fallback
    8. If still < 300 chars, mark as paywalled
    9. Chunk successful clean text at paragraph boundaries (~1500 tokens)
    10. Write raw + clean + chunks to cache/<angle_id>_raw/
    11. Register sources in sources.json
    12. Return list of Source objects with chunks ready for LLM
    """
```

### DuckDuckGo scraping
- Endpoint: `https://html.duckduckgo.com/html/?q=<query>`
- Parse with BeautifulSoup, extract result blocks (`.result__body`)
- Each result: title, snippet, URL
- Rate limit: 1 search/second (be polite, DDG blocks fast scrapers)

### Fallback search engine
If DDG returns no results or starts rate limiting, fall back to a SearXNG public instance. Maintain a list of instances in config. Rotate on failure.

### httpx config
```python
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}
timeout = httpx.Timeout(10.0, connect=5.0)
client = httpx.Client(headers=headers, timeout=timeout, follow_redirects=True)
```

### Trafilatura config
```python
import trafilatura
text = trafilatura.extract(
    html,
    include_comments=False,
    include_tables=True,
    favor_precision=True,
    deduplicate=True
)
```

### AMP cache fallback
```python
def amp_fallback(url):
    # Strip protocol from URL
    stripped = url.replace("https://", "").replace("http://", "")
    amp_url = f"https://amp.google.com/v/s/{stripped}"
    try:
        html = client.get(amp_url).text
        return trafilatura.extract(html, favor_precision=True)
    except Exception:
        return None
```

### Source caching
- Path: `cache/<angle_id>_raw/<domain>_<hash>.txt` (clean text)
- Also save `<domain>_<hash>.html` (raw, for debugging)
- Before fetching any URL, check `sources.json` — if previously fetched, read from cache instead of re-fetching
- This makes re-runs and `dig` operations fast and source-consistent

---

## 15. LLM Wrapper (`llm.py`)

```python
class LLMClient:
    def __init__(self, config):
        self.config = config
        self.flash_gate = RateGate(rpm=15)
        self.gemma_gate = RateGate(rpm=15)
        self.daily_usage = self._load_daily_usage()  # tracks RPD

    def call_flash(self, prompt, schema=None, max_retries=2):
        """
        - Self-throttle via rate gate
        - Make call
        - On RateLimitError: sleep 60s, retry indefinitely (with logging)
        - On QuotaExceededError: raise (surface to user)
        - On schema validation failure: retry with stricter prompt, max 2x
        - Track call against daily budget
        """

    def call_gemma(self, prompt, max_retries=2):
        """Same pattern, Gemma model"""

class RateGate:
    def __init__(self, rpm):
        self.rpm = rpm
        self.calls = deque()

    def wait_if_needed(self):
        now = time.time()
        while self.calls and self.calls[0] < now - 60:
            self.calls.popleft()
        if len(self.calls) >= self.rpm:
            sleep_for = 60 - (now - self.calls[0]) + 0.5
            log(f"Self-throttle: sleeping {sleep_for:.1f}s")
            time.sleep(sleep_for)
        self.calls.append(time.time())
```

### Logging
Every call logged to `quota.log` in the project directory:
```
2026-05-14T09:23:11  flash_lite  Q07_extract_2  in=7320  out=1450  ok
2026-05-14T09:24:02  flash_lite  Q07_section    in=8100  out=1820  ok
2026-05-14T09:24:55  flash_lite  Q07_devils     in=6900  out=980   rate_limited_60s
```

---

## 16. Session Management (`sessions.py`)

### Project directory structure

```
~/.cormorant/projects/<topic_slug>_<YYYYMMDD>/
├── case_brief.json
├── living_brief.md
├── plan.json
├── sources.json
├── session.json              # progress state for resume
├── quota.log                 # call-by-call audit
├── sections/
│   ├── S01_demand.md
│   ├── S02_competition.md
│   ├── ...
│   └── S08_recommendation.md
├── cache/
│   ├── S01_raw/
│   │   ├── reuters_a1b2.txt
│   │   ├── reuters_a1b2.html
│   │   ├── ft_c3d4.txt
│   │   └── chunks/
│   │       ├── reuters_a1b2_chunk1.txt
│   │       └── ...
│   └── S02_raw/...
├── report_draft.md           # live-assembled during compilation
└── report_final.md           # post final read-through
```

### `session.json`
```json
{
  "project_id": "ai_semis_20260514",
  "topic": "AI Semiconductor Investment Landscape",
  "created_at": "2026-05-14T09:00:00",
  "current_phase": "research_loop",
  "current_angle": "S04",
  "current_call": 6,
  "calls_used": 47,
  "calls_remaining": 103,
  "completed_angles": ["S01", "S02", "S03"],
  "status": "running | paused | complete | error"
}
```

### Resume
On `cormorant resume`, read `session.json`, pick up at `current_angle` and `current_call`. All prior outputs read from disk. Living Brief, sources, completed sections already there.

---

## 17. CLI Surface (`main.py`)

### Top-level commands

```
cormorant                    # start REPL — prompts for new project or resume
cormorant new                # force new project
cormorant resume             # resume most recent project
cormorant resume <slug>      # resume specific project
cormorant status             # show progress of currently running project
cormorant sessions           # list all projects
cormorant dig <section_id>   # spend buffer calls deepening a section
cormorant export <slug>      # export final report (md, pdf, docx)
cormorant config             # edit config / API key
cormorant quota              # show today's API usage
```

### REPL slash commands (inside Gemma interrogation)

```
/skip       — skip remaining clarifying questions, use what's gathered
/edit       — edit the case brief draft directly
/framework  — manually override framework choice
/go         — confirm and start research
/cancel     — abort
```

### REPL slash commands (after research starts)

```
/status     — current progress
/pause      — halt after current call
/quota      — calls used / remaining
/brief      — open living_brief.md
/findings   — list completed sections
/log        — tail quota.log
```

### Progress display

```
$ cormorant status

  Project: AI Semiconductor Investment Landscape
  Started: 09:14 AM (3h 22m ago)

  [████████████████░░░░] 7/8 angles complete

    ✓ S01 Demand Drivers              (12 sources, 540 words)
    ✓ S02 Competitive Moats           (14 sources, 580 words)
    ✓ S03 Supply Chain                (11 sources, 510 words)
    ✓ S04 Geopolitical Risk           (16 sources, 620 words)
    ✓ S05 Valuation Context           (9 sources, 490 words)
    ✓ S06 Bull Case                   (10 sources, 530 words)
    ✓ S07 Bear Case                   (12 sources, 550 words)
    ⟳ S08 Recommendation              in progress... (Call 6 of 10)

  Flash Lite calls today:  118 / 150
  Rate limit pauses:        4  (last: 12 min ago, slept 47s)
  Sources gathered:         84
  ETA to completion:        ~28 minutes

  Output: ~/.cormorant/projects/ai_semis_20260514/report_final.md
```

---

## 18. UI / UX (`ui.py`)

### Banner

```
   ░░░░░  ░░░░░  ░░░░░  ░░   ░░  ░░░░░  ░░░░░   ░░░░  ░░   ░░ ░░░░░░░
  ██      ██  ██ ██  ██ ███ ███ ██  ██ ██  ██ ██  ██ ███  ██    ██
  ██      ██  ██ ██████ ████████ ██  ██ ██████ ██████ ████ ██    ██
  ██      ██  ██ ██  ██ ██ █  ██ ██  ██ ██  ██ ██  ██ ██ ████    ██
   ░░░░░  ░░░░░  ░░  ░░ ░░    ░░  ░░░░  ░░  ░░ ░░  ░░ ░░   ░░    ░░

   deep research. consulting grade. runs while you sleep.
```

### Color palette
- Primary: cyan (`#00d4ff`)
- Accent: warm orange (`#ff8a3d`) — for warnings and highlights
- Muted: gray (`#6b7280`) — secondary text
- Success: green (`#22c55e`)
- Error: red (`#ef4444`)

### Output formatting
- Use `rich` library for everything: progress bars, tables, syntax-highlighted markdown, status panels
- Live status updates via `rich.live.Live`
- Banner uses `rich.console` with carefully chosen Unicode box-drawing characters

### Progress indicators
- Spinner during Flash Lite calls
- Progress bar across angles
- Counter for sources fetched
- Live token usage estimate

### Output is calm and confident
- No emojis unless user uses them
- No fake excitement
- Status messages factual: "S03 complete. 14 sources used." not "🎉 S03 done!"

---

## 19. Dependencies

`pyproject.toml`:

```toml
[project]
name = "cormorant"
version = "0.1.0"
description = "Deep research. Consulting grade. Runs while you sleep."
license = "MIT"
requires-python = ">=3.10"
dependencies = [
    "google-generativeai>=0.8.0",
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "trafilatura>=1.12.0",
    "rich>=13.7.0",
    "tomli>=2.0.0",
    "tomli-w>=1.0.0",
    "jsonschema>=4.21.0",
    "tiktoken>=0.7.0",  # for token counting
]

[project.scripts]
cormorant = "cormorant.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## 20. Edge Cases and Failure Modes

### 20.1 Process crashes mid-run
- Every artifact written atomically (temp file + `os.replace`)
- `session.json` updated after every successful call
- `cormorant resume` reads session state and continues exactly where left off
- Cached HTML/clean text means resume doesn't re-fetch URLs

### 20.2 All search results paywalled or JS-rendered
- Triggered after a single angle's search phase returns mostly empty trafilatura output
- Re-search with `site:sec.gov`, `filetype:pdf`, `site:europa.eu`, etc.
- If still empty, write the section honestly noting evidence limitations
- Surface in Risks and Limitations section

### 20.3 Daily quota exhausted mid-project
- `QuotaExceededError` raised
- Agent saves state, writes partial report from completed sections, surfaces clear message:
  ```
  Daily Flash Lite quota exhausted (500/500).
  Project paused at S05 of 8.
  Resume tomorrow with: cormorant resume
  ```
- Partial report exists in `report_draft.md` from completed angles

### 20.4 Schema validation fails
- Up to 2 retries with stricter prompt ("Output ONLY valid JSON matching this schema. No prose. No code fences. Begin with `{` and end with `}`.")
- If still fails, log the bad output to `cache/validation_failures/`, skip that extraction, continue
- Flag in Risks section if it happens repeatedly

### 20.5 Living Brief drifts from case brief
- Cross-check after every brief update: does the THESIS still address the case brief's `decision`?
- If a delta would substantially change the thesis direction, flag for user notification in status output
- User can `/redirect` to manually course-correct

### 20.6 Thin evidence on a critical angle
- After re-search, if evidence still thin: write the section honestly
- Section explicitly states "Evidence on this angle was limited because..."
- Section is shorter (~300 words instead of 520) — don't pad
- Surfaced prominently in Risks section

### 20.7 Two sections contradict each other (caught in final read-through)
- Final read-through call flags this
- Apply edit: add a sentence to the later section acknowledging the apparent tension and resolving it (or noting that it remains unresolved)
- If unresolvable, surface in Risks section

### 20.8 User runs `dig` with no buffer calls remaining
- Reject with clear message: "Buffer exhausted. Try again tomorrow or start a new project."

### 20.9 DuckDuckGo blocks scraping
- Detect (empty results from queries that should return many)
- Rotate to SearXNG fallback instances
- If all fall, surface to user clearly — don't silently fail

---

## 21. Testing Strategy

### Unit tests (`tests/`)
- `test_search.py` — mock HTTP, test trafilatura extraction, AMP fallback, chunking
- `test_memory.py` — Living Brief updates, token cap enforcement, atomic writes
- `test_rate_gate.py` — self-throttling logic, deque-based RPM tracking
- `test_schemas.py` — JSON schema validation against known good/bad outputs

### Integration test
- A single end-to-end run on a simple topic with mocked LLM responses
- Validates that all files get created, structure matches spec, session.json updates correctly

### Manual test plan
- Real run on "DTC mattress market in the US"
- Validate report is ~5,000 words, has all sections, sources are real and cited, Living Brief is coherent

---

## 22. Build Order (For Claude Code)

Build in this order, testing each component before moving to the next:

1. **`llm.py`** — API client + rate gate + retry logic. Test with simple prompts.
2. **`search.py`** — DDG scraping + trafilatura + AMP fallback. Test on real URLs.
3. **`memory.py`** — Living Brief read/write, source registry. Unit tested.
4. **`sessions.py`** — project directory layout, session.json, resume capability.
5. **`frameworks.py`** — framework templates and domain tiers (static data, no logic).
6. **`prompts/`** — write all prompt templates as separate `.txt` files. Each template includes its schema and explicit format constraints.
7. **`interrogator.py`** — Phase 1 Gemma conversation loop. Test interactively.
8. **`planner.py`** — Phase 2 single Flash Lite call. Test against case brief.
9. **`researcher.py`** — Phase 3 10-call pipeline. The biggest component. Test on a single angle first, then full 8-angle run.
10. **`compiler.py`** — Phase 4 final assembly. Test against pre-built section files.
11. **`agent.py`** — Top-level orchestrator stitching all phases together.
12. **`ui.py`** — banner, progress bars, status display.
13. **`main.py`** — CLI entry point, REPL, slash command handlers.
14. **Tests** — unit + integration.
15. **`README.md`** — user-facing documentation.

---

## 23. Style and Tone (For Generated Output)

The reports Cormorant produces must read like consulting work, not like an AI summary. Bake this into every section-writing prompt:

- **Assertive, not hedging.** "Demand is durable" not "Demand appears to potentially be durable."
- **Specific, not generic.** "NVIDIA's data center segment grew 154% YoY in fiscal 2024" not "NVIDIA grew significantly."
- **Claims have citations.** Every factual assertion is followed by `[domain.com, YYYY-MM]`.
- **Counterarguments are dispatched, not balanced.** Acknowledge then explain why the primary argument still holds.
- **No filler phrases.** Banned in prompts: "It is worth noting that," "In today's rapidly evolving landscape," "It is important to consider," "Various factors contribute to."
- **Lead with the point, then evidence.** Each paragraph: claim sentence first, evidence after.
- **End each section with a forward link.** "This raises the question of [next section's topic]."

The terminal UX (status messages, banner, etc.) is calm and confident — not chatty, no emojis unless user uses them, no fake enthusiasm.

---

## 24. Stretch Features (Out of Scope for v0.1, Document for Roadmap)

- PDF export with proper formatting via `weasyprint`
- DOCX export via `python-docx`
- Multi-language support (research in non-English sources)
- Inline charts/tables (would need a different output approach)
- Comparison mode (compare two topics in one report)
- Notion/Obsidian export with backlinks
- Web UI mirror of the terminal experience

---

## 25. Success Criteria

The build is complete when:

1. `pip install` works on a clean Python 3.10+ environment
2. `cormorant` launches with the banner and prompts for input
3. A full end-to-end run on a real topic produces a `report_final.md` of 4,000-6,000 words within 4 hours
4. The report has: executive summary, key findings, 8 sections, risks/limitations, conclusion, bibliography
5. Every factual claim in the report has an inline citation
6. The Living Brief stayed under 2K tokens throughout
7. Closing the terminal and running `cormorant resume` picks up exactly where it left off
8. Total Flash Lite calls used is ≤ 150 for a normal-depth project
9. The report reads like consulting writing, not AI slop — assertive, specific, structured

---

End of master prompt. Build accordingly.
