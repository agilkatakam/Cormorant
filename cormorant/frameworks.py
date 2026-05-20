"""Consulting framework templates and domain tier registry."""

from __future__ import annotations

import json
from pathlib import Path

DOMAIN_TIERS: dict[str, int] = {
    "sec.gov": 1, "federalreserve.gov": 1, "europa.eu": 1,
    "imf.org": 1, "worldbank.org": 1, "oecd.org": 1, "bis.org": 1,
    "reuters.com": 1, "ft.com": 1, "wsj.com": 1, "economist.com": 1,
    "bloomberg.com": 1, "nikkei.com": 1, "apnews.com": 1, "bbc.com": 1, "bbc.co.uk": 1,
    "semianalysis.com": 2, "stratechery.com": 2, "hbr.org": 2, "mckinsey.com": 2, "bain.com": 2, "bcg.com": 2,
    "techcrunch.com": 2, "theinformation.com": 2, "barrons.com": 2, "morningstar.com": 2,
    "statista.com": 2, "pitchbook.com": 2, "crunchbase.com": 2,
    "seekingalpha.com": 3, "businessinsider.com": 3, "cnbc.com": 3, "marketwatch.com": 3,
    "medium.com": 3, "substack.com": 3, "forbes.com": 3, "fortune.com": 3, "wired.com": 3,
    "venturebeat.com": 3, "zdnet.com": 3,
    "reddit.com": 4, "twitter.com": 4, "x.com": 4, "ycombinator.com": 4, "news.ycombinator.com": 4,
}
DEFAULT_TIER = 3

def get_domain_tier(domain: str) -> int:
    return DOMAIN_TIERS.get(domain.lstrip("www."), DEFAULT_TIER)

def fill_search_seeds(seeds: list[str], topic: str, year: str = "2025") -> list[str]:
    return [s.format(topic=topic, year=year) for s in seeds]


_CUSTOM_FW_PATH = Path.home() / ".cormorant" / "custom_frameworks.json"
_CUSTOM_CATEGORY = "Custom Frameworks"


def _load_custom_frameworks() -> dict[str, dict]:
    """Load user-defined frameworks from ~/.cormorant/custom_frameworks.json."""
    if not _CUSTOM_FW_PATH.exists():
        return {}
    try:
        return json.loads(_CUSTOM_FW_PATH.read_text())
    except Exception:
        return {}


def _save_custom_frameworks(data: dict[str, dict]) -> None:
    """Persist custom frameworks atomically."""
    _CUSTOM_FW_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CUSTOM_FW_PATH.write_text(json.dumps(data, indent=2))


def register_custom_framework(fw_id: str, fw_data: dict) -> None:
    """Register a new custom framework and merge it into the live registries."""
    existing = _load_custom_frameworks()
    existing[fw_id] = fw_data
    _save_custom_frameworks(existing)
    # Live-inject into module-level registries so the running session picks it up
    FRAMEWORKS[fw_id] = fw_data
    cat_list = CATEGORIES.setdefault(_CUSTOM_CATEGORY, [])
    if fw_id not in cat_list:  # prevent duplicates on overwrite
        cat_list.append(fw_id)


def validate_custom_framework(fw: dict) -> list[str]:
    """Validate a synthesised framework dict. Returns list of error strings."""
    errors: list[str] = []
    angles = fw.get("angles", [])
    if len(angles) != 8:
        errors.append(f"Expected exactly 8 angles, got {len(angles)}.")
    ids = {a.get("id") for a in angles}
    for a in angles:
        for dep in a.get("depends_on", []):
            if dep not in ids:
                errors.append(f"Angle {a['id']} has unknown dependency '{dep}'.")
    # Check for cycles via DFS
    graph: dict[str, list[str]] = {a["id"]: a.get("depends_on", []) for a in angles}
    visited: set[str] = set()
    rec_stack: set[str] = set()

    def _has_cycle(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)
        for neighbour in graph.get(node, []):
            if neighbour not in visited:
                if _has_cycle(neighbour):
                    return True
            elif neighbour in rec_stack:
                return True
        rec_stack.discard(node)
        return False

    for node in graph:
        if node not in visited:
            if _has_cycle(node):
                errors.append("Dependency cycle detected in framework angles.")
                break
    return errors


CATEGORIES: dict[str, list[str]] = {
    "Business Strategy & Market Intelligence": [
        "industry_competitive_landscape",
        "market_research_trend_forecasting",
        "gtm_strategy_development",
        "feasibility_expansion_studies",
        "strategic_benchmarking_opportunity_mapping",
    ],
    "Research & Data Analytics": [
        "surveys_interviews_focus_groups",
        "consumer_behaviour_analysis",
        "data_visualisation_dashboarding",
        "business_insights_reporting",
        "kpi_performance_tracking",
    ],
    "Marketing & Growth Strategy": [
        "product_market_fit",
        "brand_positioning_messaging",
        "pricing_strategy_revenue_modeling",
        "digital_marketing_social_media",
        "influencer_campus_outreach",
    ],
    "AI & Data Intelligence Consulting": [
        "ai_assisted_market_competitive_research",
        "predictive_trend_customer_analysis",
        "ai_use_case_id",
        "data_driven_decision_support",
        "ai_readiness_adoption_assessment",
    ],
    "Operations & Process Excellence": [
        "workflow_process_optimisation",
        "supply_chain_logistics",
        "cost_reduction_efficiency",
        "sop_process_documentation",
        "execution_roadmap_development",
    ],
    "Policy, Ecosystem & Sector Research": [
        "sector_benchmarking_studies",
        "policy_gap_analysis",
        "msme_startup_ecosystem_research",
        "economic_industry_opportunity_mapping",
        "implementation_roadmaps_kpi",
    ],
}

FRAMEWORKS: dict[str, dict] = {
    "industry_competitive_landscape": {
        "name": "Industry & Competitive Landscape Analysis",
        "description": "Comprehensive sector overview and rival benchmarking",
        "angles": [
            {
                        "id": "S01",
                        "title": "Market Definition & TAM",
                        "key_questions": [
                                    "What is the total addressable market?",
                                    "What defines the boundaries of this space?"
                        ],
                        "search_seeds": [
                                    "{topic} market size TAM",
                                    "{topic} industry definition scope"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Value Chain & Profit Pools",
                        "key_questions": [
                                    "Where is value created?",
                                    "Who captures the margins?"
                        ],
                        "search_seeds": [
                                    "{topic} value chain profit pool",
                                    "{topic} industry margins economics"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Competitive Landscape",
                        "key_questions": [
                                    "Who are the major players?",
                                    "What is the market share distribution?"
                        ],
                        "search_seeds": [
                                    "{topic} competitive landscape players",
                                    "{topic} market share distribution"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S04",
                        "title": "Growth Drivers & Tailwinds",
                        "key_questions": [
                                    "What structural forces drive growth?",
                                    "What are the macroeconomic tailwinds?"
                        ],
                        "search_seeds": [
                                    "{topic} growth drivers tailwinds",
                                    "{topic} market expansion catalyst"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Regulatory & Risk Factors",
                        "key_questions": [
                                    "What policy changes affect this space?",
                                    "What are the major operational risks?"
                        ],
                        "search_seeds": [
                                    "{topic} regulatory environment policy",
                                    "{topic} industry risks headwinds"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S06",
                        "title": "Disruption & Innovation",
                        "key_questions": [
                                    "What technologies threaten the status quo?",
                                    "Who are the emerging challengers?"
                        ],
                        "search_seeds": [
                                    "{topic} technology disruption innovation",
                                    "{topic} emerging startups threat"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Strategic Benchmarking",
                        "key_questions": [
                                    "How do leaders differentiate?",
                                    "What are the best-in-class capabilities?"
                        ],
                        "search_seeds": [
                                    "{topic} strategic benchmarking best practices",
                                    "{topic} competitive differentiation advantage"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Forward Outlook & Scenarios",
                        "key_questions": [
                                    "What is the 3-5 year outlook?",
                                    "What strategic scenarios are plausible?"
                        ],
                        "search_seeds": [
                                    "{topic} future outlook scenarios {year}",
                                    "{topic} market forecast projection"
                        ],
                        "depends_on": [
                                    "S04",
                                    "S06"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "market_research_trend_forecasting": {
        "name": "Market Research & Trend Forecasting",
        "description": "Deep-dive market scoping, CAGR, and future trend shifts",
        "angles": [
            {
                        "id": "S01",
                        "title": "Market Definition & TAM",
                        "key_questions": [
                                    "What is the total addressable market?",
                                    "What defines the boundaries of this space?"
                        ],
                        "search_seeds": [
                                    "{topic} market size TAM",
                                    "{topic} industry definition scope"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Value Chain & Profit Pools",
                        "key_questions": [
                                    "Where is value created?",
                                    "Who captures the margins?"
                        ],
                        "search_seeds": [
                                    "{topic} value chain profit pool",
                                    "{topic} industry margins economics"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Competitive Landscape",
                        "key_questions": [
                                    "Who are the major players?",
                                    "What is the market share distribution?"
                        ],
                        "search_seeds": [
                                    "{topic} competitive landscape players",
                                    "{topic} market share distribution"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S04",
                        "title": "Growth Drivers & Tailwinds",
                        "key_questions": [
                                    "What structural forces drive growth?",
                                    "What are the macroeconomic tailwinds?"
                        ],
                        "search_seeds": [
                                    "{topic} growth drivers tailwinds",
                                    "{topic} market expansion catalyst"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Regulatory & Risk Factors",
                        "key_questions": [
                                    "What policy changes affect this space?",
                                    "What are the major operational risks?"
                        ],
                        "search_seeds": [
                                    "{topic} regulatory environment policy",
                                    "{topic} industry risks headwinds"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S06",
                        "title": "Disruption & Innovation",
                        "key_questions": [
                                    "What technologies threaten the status quo?",
                                    "Who are the emerging challengers?"
                        ],
                        "search_seeds": [
                                    "{topic} technology disruption innovation",
                                    "{topic} emerging startups threat"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Strategic Benchmarking",
                        "key_questions": [
                                    "How do leaders differentiate?",
                                    "What are the best-in-class capabilities?"
                        ],
                        "search_seeds": [
                                    "{topic} strategic benchmarking best practices",
                                    "{topic} competitive differentiation advantage"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Forward Outlook & Scenarios",
                        "key_questions": [
                                    "What is the 3-5 year outlook?",
                                    "What strategic scenarios are plausible?"
                        ],
                        "search_seeds": [
                                    "{topic} future outlook scenarios {year}",
                                    "{topic} market forecast projection"
                        ],
                        "depends_on": [
                                    "S04",
                                    "S06"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "gtm_strategy_development": {
        "name": "Go-To-Market Strategy Development",
        "description": "Evaluating entry strategies, channel selection, and launch plans",
        "angles": [
            {
                        "id": "S01",
                        "title": "Market Definition & TAM",
                        "key_questions": [
                                    "What is the total addressable market?",
                                    "What defines the boundaries of this space?"
                        ],
                        "search_seeds": [
                                    "{topic} market size TAM",
                                    "{topic} industry definition scope"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Value Chain & Profit Pools",
                        "key_questions": [
                                    "Where is value created?",
                                    "Who captures the margins?"
                        ],
                        "search_seeds": [
                                    "{topic} value chain profit pool",
                                    "{topic} industry margins economics"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Competitive Landscape",
                        "key_questions": [
                                    "Who are the major players?",
                                    "What is the market share distribution?"
                        ],
                        "search_seeds": [
                                    "{topic} competitive landscape players",
                                    "{topic} market share distribution"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S04",
                        "title": "Growth Drivers & Tailwinds",
                        "key_questions": [
                                    "What structural forces drive growth?",
                                    "What are the macroeconomic tailwinds?"
                        ],
                        "search_seeds": [
                                    "{topic} growth drivers tailwinds",
                                    "{topic} market expansion catalyst"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Regulatory & Risk Factors",
                        "key_questions": [
                                    "What policy changes affect this space?",
                                    "What are the major operational risks?"
                        ],
                        "search_seeds": [
                                    "{topic} regulatory environment policy",
                                    "{topic} industry risks headwinds"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S06",
                        "title": "Disruption & Innovation",
                        "key_questions": [
                                    "What technologies threaten the status quo?",
                                    "Who are the emerging challengers?"
                        ],
                        "search_seeds": [
                                    "{topic} technology disruption innovation",
                                    "{topic} emerging startups threat"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Strategic Benchmarking",
                        "key_questions": [
                                    "How do leaders differentiate?",
                                    "What are the best-in-class capabilities?"
                        ],
                        "search_seeds": [
                                    "{topic} strategic benchmarking best practices",
                                    "{topic} competitive differentiation advantage"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Forward Outlook & Scenarios",
                        "key_questions": [
                                    "What is the 3-5 year outlook?",
                                    "What strategic scenarios are plausible?"
                        ],
                        "search_seeds": [
                                    "{topic} future outlook scenarios {year}",
                                    "{topic} market forecast projection"
                        ],
                        "depends_on": [
                                    "S04",
                                    "S06"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "feasibility_expansion_studies": {
        "name": "Feasibility & Expansion Studies",
        "description": "Assessing the viability of new ventures or geographic expansions",
        "angles": [
            {
                        "id": "S01",
                        "title": "Market Definition & TAM",
                        "key_questions": [
                                    "What is the total addressable market?",
                                    "What defines the boundaries of this space?"
                        ],
                        "search_seeds": [
                                    "{topic} market size TAM",
                                    "{topic} industry definition scope"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Value Chain & Profit Pools",
                        "key_questions": [
                                    "Where is value created?",
                                    "Who captures the margins?"
                        ],
                        "search_seeds": [
                                    "{topic} value chain profit pool",
                                    "{topic} industry margins economics"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Competitive Landscape",
                        "key_questions": [
                                    "Who are the major players?",
                                    "What is the market share distribution?"
                        ],
                        "search_seeds": [
                                    "{topic} competitive landscape players",
                                    "{topic} market share distribution"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S04",
                        "title": "Growth Drivers & Tailwinds",
                        "key_questions": [
                                    "What structural forces drive growth?",
                                    "What are the macroeconomic tailwinds?"
                        ],
                        "search_seeds": [
                                    "{topic} growth drivers tailwinds",
                                    "{topic} market expansion catalyst"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Regulatory & Risk Factors",
                        "key_questions": [
                                    "What policy changes affect this space?",
                                    "What are the major operational risks?"
                        ],
                        "search_seeds": [
                                    "{topic} regulatory environment policy",
                                    "{topic} industry risks headwinds"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S06",
                        "title": "Disruption & Innovation",
                        "key_questions": [
                                    "What technologies threaten the status quo?",
                                    "Who are the emerging challengers?"
                        ],
                        "search_seeds": [
                                    "{topic} technology disruption innovation",
                                    "{topic} emerging startups threat"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Strategic Benchmarking",
                        "key_questions": [
                                    "How do leaders differentiate?",
                                    "What are the best-in-class capabilities?"
                        ],
                        "search_seeds": [
                                    "{topic} strategic benchmarking best practices",
                                    "{topic} competitive differentiation advantage"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Forward Outlook & Scenarios",
                        "key_questions": [
                                    "What is the 3-5 year outlook?",
                                    "What strategic scenarios are plausible?"
                        ],
                        "search_seeds": [
                                    "{topic} future outlook scenarios {year}",
                                    "{topic} market forecast projection"
                        ],
                        "depends_on": [
                                    "S04",
                                    "S06"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "strategic_benchmarking_opportunity_mapping": {
        "name": "Strategic Benchmarking & Opportunity Mapping",
        "description": "Identifying white-spaces and comparing capabilities against peers",
        "angles": [
            {
                        "id": "S01",
                        "title": "Market Definition & TAM",
                        "key_questions": [
                                    "What is the total addressable market?",
                                    "What defines the boundaries of this space?"
                        ],
                        "search_seeds": [
                                    "{topic} market size TAM",
                                    "{topic} industry definition scope"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Value Chain & Profit Pools",
                        "key_questions": [
                                    "Where is value created?",
                                    "Who captures the margins?"
                        ],
                        "search_seeds": [
                                    "{topic} value chain profit pool",
                                    "{topic} industry margins economics"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Competitive Landscape",
                        "key_questions": [
                                    "Who are the major players?",
                                    "What is the market share distribution?"
                        ],
                        "search_seeds": [
                                    "{topic} competitive landscape players",
                                    "{topic} market share distribution"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S04",
                        "title": "Growth Drivers & Tailwinds",
                        "key_questions": [
                                    "What structural forces drive growth?",
                                    "What are the macroeconomic tailwinds?"
                        ],
                        "search_seeds": [
                                    "{topic} growth drivers tailwinds",
                                    "{topic} market expansion catalyst"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Regulatory & Risk Factors",
                        "key_questions": [
                                    "What policy changes affect this space?",
                                    "What are the major operational risks?"
                        ],
                        "search_seeds": [
                                    "{topic} regulatory environment policy",
                                    "{topic} industry risks headwinds"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S06",
                        "title": "Disruption & Innovation",
                        "key_questions": [
                                    "What technologies threaten the status quo?",
                                    "Who are the emerging challengers?"
                        ],
                        "search_seeds": [
                                    "{topic} technology disruption innovation",
                                    "{topic} emerging startups threat"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Strategic Benchmarking",
                        "key_questions": [
                                    "How do leaders differentiate?",
                                    "What are the best-in-class capabilities?"
                        ],
                        "search_seeds": [
                                    "{topic} strategic benchmarking best practices",
                                    "{topic} competitive differentiation advantage"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Forward Outlook & Scenarios",
                        "key_questions": [
                                    "What is the 3-5 year outlook?",
                                    "What strategic scenarios are plausible?"
                        ],
                        "search_seeds": [
                                    "{topic} future outlook scenarios {year}",
                                    "{topic} market forecast projection"
                        ],
                        "depends_on": [
                                    "S04",
                                    "S06"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "surveys_interviews_focus_groups": {
        "name": "Surveys, Interviews & Focus Groups",
        "description": "Research methodologies and qualitative data gathering best practices",
        "angles": [
            {
                        "id": "S01",
                        "title": "Methodology Landscape",
                        "key_questions": [
                                    "What are the standard research methodologies used?",
                                    "How is data typically sourced?"
                        ],
                        "search_seeds": [
                                    "{topic} research methodology approach",
                                    "{topic} data collection standards"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Key Metrics & Indicators",
                        "key_questions": [
                                    "What are the defining KPIs?",
                                    "How is success measured quantitatively?"
                        ],
                        "search_seeds": [
                                    "{topic} key metrics KPI indicators",
                                    "{topic} measurement frameworks"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Behavioral & Segmentation Patterns",
                        "key_questions": [
                                    "How is the target audience segmented?",
                                    "What are the core behavioral drivers?"
                        ],
                        "search_seeds": [
                                    "{topic} behavioral patterns segmentation",
                                    "{topic} audience demographics psychographics"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S04",
                        "title": "Data Infrastructure & Tooling",
                        "key_questions": [
                                    "What tech stack is required?",
                                    "Which platforms dominate this analytics space?"
                        ],
                        "search_seeds": [
                                    "{topic} data infrastructure platforms",
                                    "{topic} analytics tools software"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S05",
                        "title": "Quantitative Trends",
                        "key_questions": [
                                    "What do the numbers indicate?",
                                    "Are there statistically significant shifts?"
                        ],
                        "search_seeds": [
                                    "{topic} quantitative trends statistics",
                                    "{topic} data analysis results"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Qualitative Insights",
                        "key_questions": [
                                    "What is the underlying sentiment?",
                                    "What nuanced feedback is emerging?"
                        ],
                        "search_seeds": [
                                    "{topic} qualitative insights sentiment",
                                    "{topic} unstructured feedback analysis"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Privacy & Compliance",
                        "key_questions": [
                                    "What are the data privacy constraints?",
                                    "How does regulation impact data gathering?"
                        ],
                        "search_seeds": [
                                    "{topic} data privacy compliance GDPR",
                                    "{topic} regulation analytics tracking"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S08",
                        "title": "Synthesized Intelligence",
                        "key_questions": [
                                    "How does this data translate to business strategy?",
                                    "What are the actionable takeaways?"
                        ],
                        "search_seeds": [
                                    "{topic} actionable insights strategy",
                                    "{topic} business intelligence applications"
                        ],
                        "depends_on": [
                                    "S05",
                                    "S06"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "consumer_behaviour_analysis": {
        "name": "Consumer Behaviour Analysis",
        "description": "Analyzing purchasing habits, psychological drivers, and demographics",
        "angles": [
            {
                        "id": "S01",
                        "title": "Methodology Landscape",
                        "key_questions": [
                                    "What are the standard research methodologies used?",
                                    "How is data typically sourced?"
                        ],
                        "search_seeds": [
                                    "{topic} research methodology approach",
                                    "{topic} data collection standards"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Key Metrics & Indicators",
                        "key_questions": [
                                    "What are the defining KPIs?",
                                    "How is success measured quantitatively?"
                        ],
                        "search_seeds": [
                                    "{topic} key metrics KPI indicators",
                                    "{topic} measurement frameworks"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Behavioral & Segmentation Patterns",
                        "key_questions": [
                                    "How is the target audience segmented?",
                                    "What are the core behavioral drivers?"
                        ],
                        "search_seeds": [
                                    "{topic} behavioral patterns segmentation",
                                    "{topic} audience demographics psychographics"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S04",
                        "title": "Data Infrastructure & Tooling",
                        "key_questions": [
                                    "What tech stack is required?",
                                    "Which platforms dominate this analytics space?"
                        ],
                        "search_seeds": [
                                    "{topic} data infrastructure platforms",
                                    "{topic} analytics tools software"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S05",
                        "title": "Quantitative Trends",
                        "key_questions": [
                                    "What do the numbers indicate?",
                                    "Are there statistically significant shifts?"
                        ],
                        "search_seeds": [
                                    "{topic} quantitative trends statistics",
                                    "{topic} data analysis results"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Qualitative Insights",
                        "key_questions": [
                                    "What is the underlying sentiment?",
                                    "What nuanced feedback is emerging?"
                        ],
                        "search_seeds": [
                                    "{topic} qualitative insights sentiment",
                                    "{topic} unstructured feedback analysis"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Privacy & Compliance",
                        "key_questions": [
                                    "What are the data privacy constraints?",
                                    "How does regulation impact data gathering?"
                        ],
                        "search_seeds": [
                                    "{topic} data privacy compliance GDPR",
                                    "{topic} regulation analytics tracking"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S08",
                        "title": "Synthesized Intelligence",
                        "key_questions": [
                                    "How does this data translate to business strategy?",
                                    "What are the actionable takeaways?"
                        ],
                        "search_seeds": [
                                    "{topic} actionable insights strategy",
                                    "{topic} business intelligence applications"
                        ],
                        "depends_on": [
                                    "S05",
                                    "S06"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "data_visualisation_dashboarding": {
        "name": "Data Visualisation & Dashboarding",
        "description": "Best practices and tooling for data presentation and executive dashboards",
        "angles": [
            {
                        "id": "S01",
                        "title": "Methodology Landscape",
                        "key_questions": [
                                    "What are the standard research methodologies used?",
                                    "How is data typically sourced?"
                        ],
                        "search_seeds": [
                                    "{topic} research methodology approach",
                                    "{topic} data collection standards"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Key Metrics & Indicators",
                        "key_questions": [
                                    "What are the defining KPIs?",
                                    "How is success measured quantitatively?"
                        ],
                        "search_seeds": [
                                    "{topic} key metrics KPI indicators",
                                    "{topic} measurement frameworks"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Behavioral & Segmentation Patterns",
                        "key_questions": [
                                    "How is the target audience segmented?",
                                    "What are the core behavioral drivers?"
                        ],
                        "search_seeds": [
                                    "{topic} behavioral patterns segmentation",
                                    "{topic} audience demographics psychographics"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S04",
                        "title": "Data Infrastructure & Tooling",
                        "key_questions": [
                                    "What tech stack is required?",
                                    "Which platforms dominate this analytics space?"
                        ],
                        "search_seeds": [
                                    "{topic} data infrastructure platforms",
                                    "{topic} analytics tools software"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S05",
                        "title": "Quantitative Trends",
                        "key_questions": [
                                    "What do the numbers indicate?",
                                    "Are there statistically significant shifts?"
                        ],
                        "search_seeds": [
                                    "{topic} quantitative trends statistics",
                                    "{topic} data analysis results"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Qualitative Insights",
                        "key_questions": [
                                    "What is the underlying sentiment?",
                                    "What nuanced feedback is emerging?"
                        ],
                        "search_seeds": [
                                    "{topic} qualitative insights sentiment",
                                    "{topic} unstructured feedback analysis"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Privacy & Compliance",
                        "key_questions": [
                                    "What are the data privacy constraints?",
                                    "How does regulation impact data gathering?"
                        ],
                        "search_seeds": [
                                    "{topic} data privacy compliance GDPR",
                                    "{topic} regulation analytics tracking"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S08",
                        "title": "Synthesized Intelligence",
                        "key_questions": [
                                    "How does this data translate to business strategy?",
                                    "What are the actionable takeaways?"
                        ],
                        "search_seeds": [
                                    "{topic} actionable insights strategy",
                                    "{topic} business intelligence applications"
                        ],
                        "depends_on": [
                                    "S05",
                                    "S06"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "business_insights_reporting": {
        "name": "Business Insights & Reporting",
        "description": "Frameworks for converting raw data into strategic intelligence",
        "angles": [
            {
                        "id": "S01",
                        "title": "Methodology Landscape",
                        "key_questions": [
                                    "What are the standard research methodologies used?",
                                    "How is data typically sourced?"
                        ],
                        "search_seeds": [
                                    "{topic} research methodology approach",
                                    "{topic} data collection standards"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Key Metrics & Indicators",
                        "key_questions": [
                                    "What are the defining KPIs?",
                                    "How is success measured quantitatively?"
                        ],
                        "search_seeds": [
                                    "{topic} key metrics KPI indicators",
                                    "{topic} measurement frameworks"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Behavioral & Segmentation Patterns",
                        "key_questions": [
                                    "How is the target audience segmented?",
                                    "What are the core behavioral drivers?"
                        ],
                        "search_seeds": [
                                    "{topic} behavioral patterns segmentation",
                                    "{topic} audience demographics psychographics"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S04",
                        "title": "Data Infrastructure & Tooling",
                        "key_questions": [
                                    "What tech stack is required?",
                                    "Which platforms dominate this analytics space?"
                        ],
                        "search_seeds": [
                                    "{topic} data infrastructure platforms",
                                    "{topic} analytics tools software"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S05",
                        "title": "Quantitative Trends",
                        "key_questions": [
                                    "What do the numbers indicate?",
                                    "Are there statistically significant shifts?"
                        ],
                        "search_seeds": [
                                    "{topic} quantitative trends statistics",
                                    "{topic} data analysis results"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Qualitative Insights",
                        "key_questions": [
                                    "What is the underlying sentiment?",
                                    "What nuanced feedback is emerging?"
                        ],
                        "search_seeds": [
                                    "{topic} qualitative insights sentiment",
                                    "{topic} unstructured feedback analysis"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Privacy & Compliance",
                        "key_questions": [
                                    "What are the data privacy constraints?",
                                    "How does regulation impact data gathering?"
                        ],
                        "search_seeds": [
                                    "{topic} data privacy compliance GDPR",
                                    "{topic} regulation analytics tracking"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S08",
                        "title": "Synthesized Intelligence",
                        "key_questions": [
                                    "How does this data translate to business strategy?",
                                    "What are the actionable takeaways?"
                        ],
                        "search_seeds": [
                                    "{topic} actionable insights strategy",
                                    "{topic} business intelligence applications"
                        ],
                        "depends_on": [
                                    "S05",
                                    "S06"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "kpi_performance_tracking": {
        "name": "KPI & Performance Tracking Frameworks",
        "description": "Defining OKRs, lagging/leading indicators, and performance measurement",
        "angles": [
            {
                        "id": "S01",
                        "title": "Methodology Landscape",
                        "key_questions": [
                                    "What are the standard research methodologies used?",
                                    "How is data typically sourced?"
                        ],
                        "search_seeds": [
                                    "{topic} research methodology approach",
                                    "{topic} data collection standards"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Key Metrics & Indicators",
                        "key_questions": [
                                    "What are the defining KPIs?",
                                    "How is success measured quantitatively?"
                        ],
                        "search_seeds": [
                                    "{topic} key metrics KPI indicators",
                                    "{topic} measurement frameworks"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Behavioral & Segmentation Patterns",
                        "key_questions": [
                                    "How is the target audience segmented?",
                                    "What are the core behavioral drivers?"
                        ],
                        "search_seeds": [
                                    "{topic} behavioral patterns segmentation",
                                    "{topic} audience demographics psychographics"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S04",
                        "title": "Data Infrastructure & Tooling",
                        "key_questions": [
                                    "What tech stack is required?",
                                    "Which platforms dominate this analytics space?"
                        ],
                        "search_seeds": [
                                    "{topic} data infrastructure platforms",
                                    "{topic} analytics tools software"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S05",
                        "title": "Quantitative Trends",
                        "key_questions": [
                                    "What do the numbers indicate?",
                                    "Are there statistically significant shifts?"
                        ],
                        "search_seeds": [
                                    "{topic} quantitative trends statistics",
                                    "{topic} data analysis results"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Qualitative Insights",
                        "key_questions": [
                                    "What is the underlying sentiment?",
                                    "What nuanced feedback is emerging?"
                        ],
                        "search_seeds": [
                                    "{topic} qualitative insights sentiment",
                                    "{topic} unstructured feedback analysis"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Privacy & Compliance",
                        "key_questions": [
                                    "What are the data privacy constraints?",
                                    "How does regulation impact data gathering?"
                        ],
                        "search_seeds": [
                                    "{topic} data privacy compliance GDPR",
                                    "{topic} regulation analytics tracking"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S08",
                        "title": "Synthesized Intelligence",
                        "key_questions": [
                                    "How does this data translate to business strategy?",
                                    "What are the actionable takeaways?"
                        ],
                        "search_seeds": [
                                    "{topic} actionable insights strategy",
                                    "{topic} business intelligence applications"
                        ],
                        "depends_on": [
                                    "S05",
                                    "S06"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "product_market_fit": {
        "name": "Product-Market Fit Analysis",
        "description": "Assessing traction, value propositions, and market readiness",
        "angles": [
            {
                        "id": "S01",
                        "title": "Target Audience Definition",
                        "key_questions": [
                                    "Who is the exact buyer persona?",
                                    "What is the ICP (Ideal Customer Profile)?"
                        ],
                        "search_seeds": [
                                    "{topic} target audience persona ICP",
                                    "{topic} customer profile demographics"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Value Proposition & Messaging",
                        "key_questions": [
                                    "What is the core message?",
                                    "How is value communicated?"
                        ],
                        "search_seeds": [
                                    "{topic} value proposition messaging",
                                    "{topic} brand positioning statement"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Channel Strategy",
                        "key_questions": [
                                    "Which channels yield the best CAC?",
                                    "Where does the audience aggregate?"
                        ],
                        "search_seeds": [
                                    "{topic} marketing channels strategy",
                                    "{topic} customer acquisition channels"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S04",
                        "title": "Pricing & Monetization",
                        "key_questions": [
                                    "What is the pricing strategy?",
                                    "How elastic is demand?"
                        ],
                        "search_seeds": [
                                    "{topic} pricing strategy elasticity",
                                    "{topic} monetization models revenue"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Competitive Positioning",
                        "key_questions": [
                                    "How do competitors market?",
                                    "What is our differentiation?"
                        ],
                        "search_seeds": [
                                    "{topic} competitive positioning marketing",
                                    "{topic} competitor messaging differentiation"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Campaign Economics",
                        "key_questions": [
                                    "What are the benchmark CAC and LTV figures?",
                                    "How is ROI measured?"
                        ],
                        "search_seeds": [
                                    "{topic} CAC LTV benchmark economics",
                                    "{topic} marketing ROI campaign metrics"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Emerging Growth Tactics",
                        "key_questions": [
                                    "What new growth hacks or channels are emerging?",
                                    "How is social media shifting?"
                        ],
                        "search_seeds": [
                                    "{topic} growth hacking emerging channels",
                                    "{topic} digital marketing trends social"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Go-to-Market Execution",
                        "key_questions": [
                                    "What is the phased rollout plan?",
                                    "How do we execute the strategy?"
                        ],
                        "search_seeds": [
                                    "{topic} GTM go to market execution",
                                    "{topic} marketing rollout plan strategy"
                        ],
                        "depends_on": [
                                    "S04",
                                    "S06"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "brand_positioning_messaging": {
        "name": "Brand Positioning & Messaging",
        "description": "Crafting brand identity, core narratives, and competitive differentiation",
        "angles": [
            {
                        "id": "S01",
                        "title": "Target Audience Definition",
                        "key_questions": [
                                    "Who is the exact buyer persona?",
                                    "What is the ICP (Ideal Customer Profile)?"
                        ],
                        "search_seeds": [
                                    "{topic} target audience persona ICP",
                                    "{topic} customer profile demographics"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Value Proposition & Messaging",
                        "key_questions": [
                                    "What is the core message?",
                                    "How is value communicated?"
                        ],
                        "search_seeds": [
                                    "{topic} value proposition messaging",
                                    "{topic} brand positioning statement"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Channel Strategy",
                        "key_questions": [
                                    "Which channels yield the best CAC?",
                                    "Where does the audience aggregate?"
                        ],
                        "search_seeds": [
                                    "{topic} marketing channels strategy",
                                    "{topic} customer acquisition channels"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S04",
                        "title": "Pricing & Monetization",
                        "key_questions": [
                                    "What is the pricing strategy?",
                                    "How elastic is demand?"
                        ],
                        "search_seeds": [
                                    "{topic} pricing strategy elasticity",
                                    "{topic} monetization models revenue"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Competitive Positioning",
                        "key_questions": [
                                    "How do competitors market?",
                                    "What is our differentiation?"
                        ],
                        "search_seeds": [
                                    "{topic} competitive positioning marketing",
                                    "{topic} competitor messaging differentiation"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Campaign Economics",
                        "key_questions": [
                                    "What are the benchmark CAC and LTV figures?",
                                    "How is ROI measured?"
                        ],
                        "search_seeds": [
                                    "{topic} CAC LTV benchmark economics",
                                    "{topic} marketing ROI campaign metrics"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Emerging Growth Tactics",
                        "key_questions": [
                                    "What new growth hacks or channels are emerging?",
                                    "How is social media shifting?"
                        ],
                        "search_seeds": [
                                    "{topic} growth hacking emerging channels",
                                    "{topic} digital marketing trends social"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Go-to-Market Execution",
                        "key_questions": [
                                    "What is the phased rollout plan?",
                                    "How do we execute the strategy?"
                        ],
                        "search_seeds": [
                                    "{topic} GTM go to market execution",
                                    "{topic} marketing rollout plan strategy"
                        ],
                        "depends_on": [
                                    "S04",
                                    "S06"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "pricing_strategy_revenue_modeling": {
        "name": "Pricing Strategy & Revenue Modeling",
        "description": "Evaluating elasticity, willingness-to-pay, and monetization models",
        "angles": [
            {
                        "id": "S01",
                        "title": "Target Audience Definition",
                        "key_questions": [
                                    "Who is the exact buyer persona?",
                                    "What is the ICP (Ideal Customer Profile)?"
                        ],
                        "search_seeds": [
                                    "{topic} target audience persona ICP",
                                    "{topic} customer profile demographics"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Value Proposition & Messaging",
                        "key_questions": [
                                    "What is the core message?",
                                    "How is value communicated?"
                        ],
                        "search_seeds": [
                                    "{topic} value proposition messaging",
                                    "{topic} brand positioning statement"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Channel Strategy",
                        "key_questions": [
                                    "Which channels yield the best CAC?",
                                    "Where does the audience aggregate?"
                        ],
                        "search_seeds": [
                                    "{topic} marketing channels strategy",
                                    "{topic} customer acquisition channels"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S04",
                        "title": "Pricing & Monetization",
                        "key_questions": [
                                    "What is the pricing strategy?",
                                    "How elastic is demand?"
                        ],
                        "search_seeds": [
                                    "{topic} pricing strategy elasticity",
                                    "{topic} monetization models revenue"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Competitive Positioning",
                        "key_questions": [
                                    "How do competitors market?",
                                    "What is our differentiation?"
                        ],
                        "search_seeds": [
                                    "{topic} competitive positioning marketing",
                                    "{topic} competitor messaging differentiation"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Campaign Economics",
                        "key_questions": [
                                    "What are the benchmark CAC and LTV figures?",
                                    "How is ROI measured?"
                        ],
                        "search_seeds": [
                                    "{topic} CAC LTV benchmark economics",
                                    "{topic} marketing ROI campaign metrics"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Emerging Growth Tactics",
                        "key_questions": [
                                    "What new growth hacks or channels are emerging?",
                                    "How is social media shifting?"
                        ],
                        "search_seeds": [
                                    "{topic} growth hacking emerging channels",
                                    "{topic} digital marketing trends social"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Go-to-Market Execution",
                        "key_questions": [
                                    "What is the phased rollout plan?",
                                    "How do we execute the strategy?"
                        ],
                        "search_seeds": [
                                    "{topic} GTM go to market execution",
                                    "{topic} marketing rollout plan strategy"
                        ],
                        "depends_on": [
                                    "S04",
                                    "S06"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "digital_marketing_social_media": {
        "name": "Digital Marketing & Social Media Strategy",
        "description": "Analyzing digital acquisition channels, ROI, and social campaigns",
        "angles": [
            {
                        "id": "S01",
                        "title": "Target Audience Definition",
                        "key_questions": [
                                    "Who is the exact buyer persona?",
                                    "What is the ICP (Ideal Customer Profile)?"
                        ],
                        "search_seeds": [
                                    "{topic} target audience persona ICP",
                                    "{topic} customer profile demographics"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Value Proposition & Messaging",
                        "key_questions": [
                                    "What is the core message?",
                                    "How is value communicated?"
                        ],
                        "search_seeds": [
                                    "{topic} value proposition messaging",
                                    "{topic} brand positioning statement"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Channel Strategy",
                        "key_questions": [
                                    "Which channels yield the best CAC?",
                                    "Where does the audience aggregate?"
                        ],
                        "search_seeds": [
                                    "{topic} marketing channels strategy",
                                    "{topic} customer acquisition channels"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S04",
                        "title": "Pricing & Monetization",
                        "key_questions": [
                                    "What is the pricing strategy?",
                                    "How elastic is demand?"
                        ],
                        "search_seeds": [
                                    "{topic} pricing strategy elasticity",
                                    "{topic} monetization models revenue"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Competitive Positioning",
                        "key_questions": [
                                    "How do competitors market?",
                                    "What is our differentiation?"
                        ],
                        "search_seeds": [
                                    "{topic} competitive positioning marketing",
                                    "{topic} competitor messaging differentiation"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Campaign Economics",
                        "key_questions": [
                                    "What are the benchmark CAC and LTV figures?",
                                    "How is ROI measured?"
                        ],
                        "search_seeds": [
                                    "{topic} CAC LTV benchmark economics",
                                    "{topic} marketing ROI campaign metrics"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Emerging Growth Tactics",
                        "key_questions": [
                                    "What new growth hacks or channels are emerging?",
                                    "How is social media shifting?"
                        ],
                        "search_seeds": [
                                    "{topic} growth hacking emerging channels",
                                    "{topic} digital marketing trends social"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Go-to-Market Execution",
                        "key_questions": [
                                    "What is the phased rollout plan?",
                                    "How do we execute the strategy?"
                        ],
                        "search_seeds": [
                                    "{topic} GTM go to market execution",
                                    "{topic} marketing rollout plan strategy"
                        ],
                        "depends_on": [
                                    "S04",
                                    "S06"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "influencer_campus_outreach": {
        "name": "Influencer & Campus Outreach Strategy",
        "description": "Mapping creator ecosystems, affiliate networks, and grassroots marketing",
        "angles": [
            {
                        "id": "S01",
                        "title": "Target Audience Definition",
                        "key_questions": [
                                    "Who is the exact buyer persona?",
                                    "What is the ICP (Ideal Customer Profile)?"
                        ],
                        "search_seeds": [
                                    "{topic} target audience persona ICP",
                                    "{topic} customer profile demographics"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Value Proposition & Messaging",
                        "key_questions": [
                                    "What is the core message?",
                                    "How is value communicated?"
                        ],
                        "search_seeds": [
                                    "{topic} value proposition messaging",
                                    "{topic} brand positioning statement"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Channel Strategy",
                        "key_questions": [
                                    "Which channels yield the best CAC?",
                                    "Where does the audience aggregate?"
                        ],
                        "search_seeds": [
                                    "{topic} marketing channels strategy",
                                    "{topic} customer acquisition channels"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S04",
                        "title": "Pricing & Monetization",
                        "key_questions": [
                                    "What is the pricing strategy?",
                                    "How elastic is demand?"
                        ],
                        "search_seeds": [
                                    "{topic} pricing strategy elasticity",
                                    "{topic} monetization models revenue"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Competitive Positioning",
                        "key_questions": [
                                    "How do competitors market?",
                                    "What is our differentiation?"
                        ],
                        "search_seeds": [
                                    "{topic} competitive positioning marketing",
                                    "{topic} competitor messaging differentiation"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Campaign Economics",
                        "key_questions": [
                                    "What are the benchmark CAC and LTV figures?",
                                    "How is ROI measured?"
                        ],
                        "search_seeds": [
                                    "{topic} CAC LTV benchmark economics",
                                    "{topic} marketing ROI campaign metrics"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Emerging Growth Tactics",
                        "key_questions": [
                                    "What new growth hacks or channels are emerging?",
                                    "How is social media shifting?"
                        ],
                        "search_seeds": [
                                    "{topic} growth hacking emerging channels",
                                    "{topic} digital marketing trends social"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Go-to-Market Execution",
                        "key_questions": [
                                    "What is the phased rollout plan?",
                                    "How do we execute the strategy?"
                        ],
                        "search_seeds": [
                                    "{topic} GTM go to market execution",
                                    "{topic} marketing rollout plan strategy"
                        ],
                        "depends_on": [
                                    "S04",
                                    "S06"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "ai_assisted_market_competitive_research": {
        "name": "AI-Assisted Market & Competitive Research",
        "description": "Using AI to scrape, analyze, and map market landscapes",
        "angles": [
            {
                        "id": "S01",
                        "title": "Technological Readiness",
                        "key_questions": [
                                    "What is the state of the art?",
                                    "Is the technology mature enough?"
                        ],
                        "search_seeds": [
                                    "{topic} technological maturity state of art",
                                    "{topic} AI readiness technology stack"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "High-ROI Use Cases",
                        "key_questions": [
                                    "Where are the highest ROI applications?",
                                    "Which workflows are prime for automation?"
                        ],
                        "search_seeds": [
                                    "{topic} AI use cases ROI",
                                    "{topic} automation opportunities workflows"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Vendor & Ecosystem Landscape",
                        "key_questions": [
                                    "Who are the foundational model providers?",
                                    "What tools exist in the ecosystem?"
                        ],
                        "search_seeds": [
                                    "{topic} vendor landscape AI ecosystem",
                                    "{topic} foundational models tools platform"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S04",
                        "title": "Data Architecture Requirements",
                        "key_questions": [
                                    "What data infrastructure is necessary?",
                                    "How are data silos resolved?"
                        ],
                        "search_seeds": [
                                    "{topic} data architecture requirements",
                                    "{topic} infrastructure data pipelines"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Security & Governance",
                        "key_questions": [
                                    "How is data secured?",
                                    "What are the ethical/compliance risks?"
                        ],
                        "search_seeds": [
                                    "{topic} AI security governance",
                                    "{topic} ethical AI compliance risks"
                        ],
                        "depends_on": [
                                    "S04"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Implementation Challenges",
                        "key_questions": [
                                    "What are the common failure modes?",
                                    "Why do data projects fail?"
                        ],
                        "search_seeds": [
                                    "{topic} implementation challenges failure modes",
                                    "{topic} AI adoption barriers"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Cost & ROI Modeling",
                        "key_questions": [
                                    "What is the cost of inference/compute?",
                                    "How is ROI calculated?"
                        ],
                        "search_seeds": [
                                    "{topic} AI compute costs inference",
                                    "{topic} ROI modeling data intelligence"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Adoption Roadmap",
                        "key_questions": [
                                    "How should this be rolled out?",
                                    "What is the 90-day integration plan?"
                        ],
                        "search_seeds": [
                                    "{topic} adoption roadmap integration",
                                    "{topic} phased implementation plan AI"
                        ],
                        "depends_on": [
                                    "S06",
                                    "S07"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "predictive_trend_customer_analysis": {
        "name": "Predictive Trend & Customer Analysis",
        "description": "Machine learning applications for forecasting and segmentation",
        "angles": [
            {
                        "id": "S01",
                        "title": "Technological Readiness",
                        "key_questions": [
                                    "What is the state of the art?",
                                    "Is the technology mature enough?"
                        ],
                        "search_seeds": [
                                    "{topic} technological maturity state of art",
                                    "{topic} AI readiness technology stack"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "High-ROI Use Cases",
                        "key_questions": [
                                    "Where are the highest ROI applications?",
                                    "Which workflows are prime for automation?"
                        ],
                        "search_seeds": [
                                    "{topic} AI use cases ROI",
                                    "{topic} automation opportunities workflows"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Vendor & Ecosystem Landscape",
                        "key_questions": [
                                    "Who are the foundational model providers?",
                                    "What tools exist in the ecosystem?"
                        ],
                        "search_seeds": [
                                    "{topic} vendor landscape AI ecosystem",
                                    "{topic} foundational models tools platform"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S04",
                        "title": "Data Architecture Requirements",
                        "key_questions": [
                                    "What data infrastructure is necessary?",
                                    "How are data silos resolved?"
                        ],
                        "search_seeds": [
                                    "{topic} data architecture requirements",
                                    "{topic} infrastructure data pipelines"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Security & Governance",
                        "key_questions": [
                                    "How is data secured?",
                                    "What are the ethical/compliance risks?"
                        ],
                        "search_seeds": [
                                    "{topic} AI security governance",
                                    "{topic} ethical AI compliance risks"
                        ],
                        "depends_on": [
                                    "S04"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Implementation Challenges",
                        "key_questions": [
                                    "What are the common failure modes?",
                                    "Why do data projects fail?"
                        ],
                        "search_seeds": [
                                    "{topic} implementation challenges failure modes",
                                    "{topic} AI adoption barriers"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Cost & ROI Modeling",
                        "key_questions": [
                                    "What is the cost of inference/compute?",
                                    "How is ROI calculated?"
                        ],
                        "search_seeds": [
                                    "{topic} AI compute costs inference",
                                    "{topic} ROI modeling data intelligence"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Adoption Roadmap",
                        "key_questions": [
                                    "How should this be rolled out?",
                                    "What is the 90-day integration plan?"
                        ],
                        "search_seeds": [
                                    "{topic} adoption roadmap integration",
                                    "{topic} phased implementation plan AI"
                        ],
                        "depends_on": [
                                    "S06",
                                    "S07"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "ai_use_case_id": {
        "name": "AI Use-Case ID for Startups & MSMEs",
        "description": "Identifying high-ROI artificial intelligence implementations for businesses",
        "angles": [
            {
                        "id": "S01",
                        "title": "Technological Readiness",
                        "key_questions": [
                                    "What is the state of the art?",
                                    "Is the technology mature enough?"
                        ],
                        "search_seeds": [
                                    "{topic} technological maturity state of art",
                                    "{topic} AI readiness technology stack"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "High-ROI Use Cases",
                        "key_questions": [
                                    "Where are the highest ROI applications?",
                                    "Which workflows are prime for automation?"
                        ],
                        "search_seeds": [
                                    "{topic} AI use cases ROI",
                                    "{topic} automation opportunities workflows"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Vendor & Ecosystem Landscape",
                        "key_questions": [
                                    "Who are the foundational model providers?",
                                    "What tools exist in the ecosystem?"
                        ],
                        "search_seeds": [
                                    "{topic} vendor landscape AI ecosystem",
                                    "{topic} foundational models tools platform"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S04",
                        "title": "Data Architecture Requirements",
                        "key_questions": [
                                    "What data infrastructure is necessary?",
                                    "How are data silos resolved?"
                        ],
                        "search_seeds": [
                                    "{topic} data architecture requirements",
                                    "{topic} infrastructure data pipelines"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Security & Governance",
                        "key_questions": [
                                    "How is data secured?",
                                    "What are the ethical/compliance risks?"
                        ],
                        "search_seeds": [
                                    "{topic} AI security governance",
                                    "{topic} ethical AI compliance risks"
                        ],
                        "depends_on": [
                                    "S04"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Implementation Challenges",
                        "key_questions": [
                                    "What are the common failure modes?",
                                    "Why do data projects fail?"
                        ],
                        "search_seeds": [
                                    "{topic} implementation challenges failure modes",
                                    "{topic} AI adoption barriers"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Cost & ROI Modeling",
                        "key_questions": [
                                    "What is the cost of inference/compute?",
                                    "How is ROI calculated?"
                        ],
                        "search_seeds": [
                                    "{topic} AI compute costs inference",
                                    "{topic} ROI modeling data intelligence"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Adoption Roadmap",
                        "key_questions": [
                                    "How should this be rolled out?",
                                    "What is the 90-day integration plan?"
                        ],
                        "search_seeds": [
                                    "{topic} adoption roadmap integration",
                                    "{topic} phased implementation plan AI"
                        ],
                        "depends_on": [
                                    "S06",
                                    "S07"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "data_driven_decision_support": {
        "name": "Data-Driven Decision Support Systems",
        "description": "Architecting systems that convert intelligence into automated decisions",
        "angles": [
            {
                        "id": "S01",
                        "title": "Technological Readiness",
                        "key_questions": [
                                    "What is the state of the art?",
                                    "Is the technology mature enough?"
                        ],
                        "search_seeds": [
                                    "{topic} technological maturity state of art",
                                    "{topic} AI readiness technology stack"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "High-ROI Use Cases",
                        "key_questions": [
                                    "Where are the highest ROI applications?",
                                    "Which workflows are prime for automation?"
                        ],
                        "search_seeds": [
                                    "{topic} AI use cases ROI",
                                    "{topic} automation opportunities workflows"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Vendor & Ecosystem Landscape",
                        "key_questions": [
                                    "Who are the foundational model providers?",
                                    "What tools exist in the ecosystem?"
                        ],
                        "search_seeds": [
                                    "{topic} vendor landscape AI ecosystem",
                                    "{topic} foundational models tools platform"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S04",
                        "title": "Data Architecture Requirements",
                        "key_questions": [
                                    "What data infrastructure is necessary?",
                                    "How are data silos resolved?"
                        ],
                        "search_seeds": [
                                    "{topic} data architecture requirements",
                                    "{topic} infrastructure data pipelines"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Security & Governance",
                        "key_questions": [
                                    "How is data secured?",
                                    "What are the ethical/compliance risks?"
                        ],
                        "search_seeds": [
                                    "{topic} AI security governance",
                                    "{topic} ethical AI compliance risks"
                        ],
                        "depends_on": [
                                    "S04"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Implementation Challenges",
                        "key_questions": [
                                    "What are the common failure modes?",
                                    "Why do data projects fail?"
                        ],
                        "search_seeds": [
                                    "{topic} implementation challenges failure modes",
                                    "{topic} AI adoption barriers"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Cost & ROI Modeling",
                        "key_questions": [
                                    "What is the cost of inference/compute?",
                                    "How is ROI calculated?"
                        ],
                        "search_seeds": [
                                    "{topic} AI compute costs inference",
                                    "{topic} ROI modeling data intelligence"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Adoption Roadmap",
                        "key_questions": [
                                    "How should this be rolled out?",
                                    "What is the 90-day integration plan?"
                        ],
                        "search_seeds": [
                                    "{topic} adoption roadmap integration",
                                    "{topic} phased implementation plan AI"
                        ],
                        "depends_on": [
                                    "S06",
                                    "S07"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "ai_readiness_adoption_assessment": {
        "name": "AI Readiness & Adoption Assessment",
        "description": "Evaluating organizational maturity, data silos, and tech-stack readiness",
        "angles": [
            {
                        "id": "S01",
                        "title": "Technological Readiness",
                        "key_questions": [
                                    "What is the state of the art?",
                                    "Is the technology mature enough?"
                        ],
                        "search_seeds": [
                                    "{topic} technological maturity state of art",
                                    "{topic} AI readiness technology stack"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "High-ROI Use Cases",
                        "key_questions": [
                                    "Where are the highest ROI applications?",
                                    "Which workflows are prime for automation?"
                        ],
                        "search_seeds": [
                                    "{topic} AI use cases ROI",
                                    "{topic} automation opportunities workflows"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Vendor & Ecosystem Landscape",
                        "key_questions": [
                                    "Who are the foundational model providers?",
                                    "What tools exist in the ecosystem?"
                        ],
                        "search_seeds": [
                                    "{topic} vendor landscape AI ecosystem",
                                    "{topic} foundational models tools platform"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S04",
                        "title": "Data Architecture Requirements",
                        "key_questions": [
                                    "What data infrastructure is necessary?",
                                    "How are data silos resolved?"
                        ],
                        "search_seeds": [
                                    "{topic} data architecture requirements",
                                    "{topic} infrastructure data pipelines"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Security & Governance",
                        "key_questions": [
                                    "How is data secured?",
                                    "What are the ethical/compliance risks?"
                        ],
                        "search_seeds": [
                                    "{topic} AI security governance",
                                    "{topic} ethical AI compliance risks"
                        ],
                        "depends_on": [
                                    "S04"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Implementation Challenges",
                        "key_questions": [
                                    "What are the common failure modes?",
                                    "Why do data projects fail?"
                        ],
                        "search_seeds": [
                                    "{topic} implementation challenges failure modes",
                                    "{topic} AI adoption barriers"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Cost & ROI Modeling",
                        "key_questions": [
                                    "What is the cost of inference/compute?",
                                    "How is ROI calculated?"
                        ],
                        "search_seeds": [
                                    "{topic} AI compute costs inference",
                                    "{topic} ROI modeling data intelligence"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Adoption Roadmap",
                        "key_questions": [
                                    "How should this be rolled out?",
                                    "What is the 90-day integration plan?"
                        ],
                        "search_seeds": [
                                    "{topic} adoption roadmap integration",
                                    "{topic} phased implementation plan AI"
                        ],
                        "depends_on": [
                                    "S06",
                                    "S07"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "workflow_process_optimisation": {
        "name": "Workflow & Process Optimisation",
        "description": "Mapping operations, identifying bottlenecks, and leaning processes",
        "angles": [
            {
                        "id": "S01",
                        "title": "Current Process Baseline",
                        "key_questions": [
                                    "What does the current operation look like?",
                                    "What are the baseline metrics?"
                        ],
                        "search_seeds": [
                                    "{topic} current process baseline metrics",
                                    "{topic} standard operating procedures status"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Bottleneck Identification",
                        "key_questions": [
                                    "Where are the constraints?",
                                    "What slows down the workflow?"
                        ],
                        "search_seeds": [
                                    "{topic} process bottlenecks constraints",
                                    "{topic} operational inefficiencies slow down"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Supply Chain mapping",
                        "key_questions": [
                                    "What does the upstream/downstream look like?",
                                    "Where is supplier concentration high?"
                        ],
                        "search_seeds": [
                                    "{topic} supply chain mapping structure",
                                    "{topic} supplier concentration logistics"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S04",
                        "title": "Cost Drivers & Waste",
                        "key_questions": [
                                    "Where is capital being wasted?",
                                    "What are the primary cost centers?"
                        ],
                        "search_seeds": [
                                    "{topic} cost drivers waste reduction",
                                    "{topic} operational cost centers"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Automation & Technology Levers",
                        "key_questions": [
                                    "How can tech optimize this?",
                                    "What automation tools apply?"
                        ],
                        "search_seeds": [
                                    "{topic} process automation technology",
                                    "{topic} operations software optimization"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Quality & Compliance Control",
                        "key_questions": [
                                    "How is quality assured?",
                                    "Are there regulatory compliance steps?"
                        ],
                        "search_seeds": [
                                    "{topic} quality control assurance",
                                    "{topic} compliance regulatory operations"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Best-in-Class Benchmarks",
                        "key_questions": [
                                    "What do industry leaders do?",
                                    "What are the benchmark efficiency ratios?"
                        ],
                        "search_seeds": [
                                    "{topic} operational benchmarking leaders",
                                    "{topic} efficiency ratios benchmark"
                        ],
                        "depends_on": [
                                    "S04"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Execution & Restructuring Plan",
                        "key_questions": [
                                    "How do we implement changes?",
                                    "What is the change management strategy?"
                        ],
                        "search_seeds": [
                                    "{topic} execution plan restructuring",
                                    "{topic} change management implementation"
                        ],
                        "depends_on": [
                                    "S05",
                                    "S07"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "supply_chain_logistics": {
        "name": "Supply Chain & Logistics Analysis",
        "description": "Auditing supplier networks, freight, inventory, and fulfillment models",
        "angles": [
            {
                        "id": "S01",
                        "title": "Current Process Baseline",
                        "key_questions": [
                                    "What does the current operation look like?",
                                    "What are the baseline metrics?"
                        ],
                        "search_seeds": [
                                    "{topic} current process baseline metrics",
                                    "{topic} standard operating procedures status"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Bottleneck Identification",
                        "key_questions": [
                                    "Where are the constraints?",
                                    "What slows down the workflow?"
                        ],
                        "search_seeds": [
                                    "{topic} process bottlenecks constraints",
                                    "{topic} operational inefficiencies slow down"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Supply Chain mapping",
                        "key_questions": [
                                    "What does the upstream/downstream look like?",
                                    "Where is supplier concentration high?"
                        ],
                        "search_seeds": [
                                    "{topic} supply chain mapping structure",
                                    "{topic} supplier concentration logistics"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S04",
                        "title": "Cost Drivers & Waste",
                        "key_questions": [
                                    "Where is capital being wasted?",
                                    "What are the primary cost centers?"
                        ],
                        "search_seeds": [
                                    "{topic} cost drivers waste reduction",
                                    "{topic} operational cost centers"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Automation & Technology Levers",
                        "key_questions": [
                                    "How can tech optimize this?",
                                    "What automation tools apply?"
                        ],
                        "search_seeds": [
                                    "{topic} process automation technology",
                                    "{topic} operations software optimization"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Quality & Compliance Control",
                        "key_questions": [
                                    "How is quality assured?",
                                    "Are there regulatory compliance steps?"
                        ],
                        "search_seeds": [
                                    "{topic} quality control assurance",
                                    "{topic} compliance regulatory operations"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Best-in-Class Benchmarks",
                        "key_questions": [
                                    "What do industry leaders do?",
                                    "What are the benchmark efficiency ratios?"
                        ],
                        "search_seeds": [
                                    "{topic} operational benchmarking leaders",
                                    "{topic} efficiency ratios benchmark"
                        ],
                        "depends_on": [
                                    "S04"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Execution & Restructuring Plan",
                        "key_questions": [
                                    "How do we implement changes?",
                                    "What is the change management strategy?"
                        ],
                        "search_seeds": [
                                    "{topic} execution plan restructuring",
                                    "{topic} change management implementation"
                        ],
                        "depends_on": [
                                    "S05",
                                    "S07"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "cost_reduction_efficiency": {
        "name": "Cost Reduction & Efficiency Enhancement",
        "description": "Identifying operational bloat, margin improvement, and zero-based budgeting",
        "angles": [
            {
                        "id": "S01",
                        "title": "Current Process Baseline",
                        "key_questions": [
                                    "What does the current operation look like?",
                                    "What are the baseline metrics?"
                        ],
                        "search_seeds": [
                                    "{topic} current process baseline metrics",
                                    "{topic} standard operating procedures status"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Bottleneck Identification",
                        "key_questions": [
                                    "Where are the constraints?",
                                    "What slows down the workflow?"
                        ],
                        "search_seeds": [
                                    "{topic} process bottlenecks constraints",
                                    "{topic} operational inefficiencies slow down"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Supply Chain mapping",
                        "key_questions": [
                                    "What does the upstream/downstream look like?",
                                    "Where is supplier concentration high?"
                        ],
                        "search_seeds": [
                                    "{topic} supply chain mapping structure",
                                    "{topic} supplier concentration logistics"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S04",
                        "title": "Cost Drivers & Waste",
                        "key_questions": [
                                    "Where is capital being wasted?",
                                    "What are the primary cost centers?"
                        ],
                        "search_seeds": [
                                    "{topic} cost drivers waste reduction",
                                    "{topic} operational cost centers"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Automation & Technology Levers",
                        "key_questions": [
                                    "How can tech optimize this?",
                                    "What automation tools apply?"
                        ],
                        "search_seeds": [
                                    "{topic} process automation technology",
                                    "{topic} operations software optimization"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Quality & Compliance Control",
                        "key_questions": [
                                    "How is quality assured?",
                                    "Are there regulatory compliance steps?"
                        ],
                        "search_seeds": [
                                    "{topic} quality control assurance",
                                    "{topic} compliance regulatory operations"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Best-in-Class Benchmarks",
                        "key_questions": [
                                    "What do industry leaders do?",
                                    "What are the benchmark efficiency ratios?"
                        ],
                        "search_seeds": [
                                    "{topic} operational benchmarking leaders",
                                    "{topic} efficiency ratios benchmark"
                        ],
                        "depends_on": [
                                    "S04"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Execution & Restructuring Plan",
                        "key_questions": [
                                    "How do we implement changes?",
                                    "What is the change management strategy?"
                        ],
                        "search_seeds": [
                                    "{topic} execution plan restructuring",
                                    "{topic} change management implementation"
                        ],
                        "depends_on": [
                                    "S05",
                                    "S07"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "sop_process_documentation": {
        "name": "SOP & Process Documentation",
        "description": "Establishing standard operating procedures and institutional knowledge",
        "angles": [
            {
                        "id": "S01",
                        "title": "Current Process Baseline",
                        "key_questions": [
                                    "What does the current operation look like?",
                                    "What are the baseline metrics?"
                        ],
                        "search_seeds": [
                                    "{topic} current process baseline metrics",
                                    "{topic} standard operating procedures status"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Bottleneck Identification",
                        "key_questions": [
                                    "Where are the constraints?",
                                    "What slows down the workflow?"
                        ],
                        "search_seeds": [
                                    "{topic} process bottlenecks constraints",
                                    "{topic} operational inefficiencies slow down"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Supply Chain mapping",
                        "key_questions": [
                                    "What does the upstream/downstream look like?",
                                    "Where is supplier concentration high?"
                        ],
                        "search_seeds": [
                                    "{topic} supply chain mapping structure",
                                    "{topic} supplier concentration logistics"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S04",
                        "title": "Cost Drivers & Waste",
                        "key_questions": [
                                    "Where is capital being wasted?",
                                    "What are the primary cost centers?"
                        ],
                        "search_seeds": [
                                    "{topic} cost drivers waste reduction",
                                    "{topic} operational cost centers"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Automation & Technology Levers",
                        "key_questions": [
                                    "How can tech optimize this?",
                                    "What automation tools apply?"
                        ],
                        "search_seeds": [
                                    "{topic} process automation technology",
                                    "{topic} operations software optimization"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Quality & Compliance Control",
                        "key_questions": [
                                    "How is quality assured?",
                                    "Are there regulatory compliance steps?"
                        ],
                        "search_seeds": [
                                    "{topic} quality control assurance",
                                    "{topic} compliance regulatory operations"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Best-in-Class Benchmarks",
                        "key_questions": [
                                    "What do industry leaders do?",
                                    "What are the benchmark efficiency ratios?"
                        ],
                        "search_seeds": [
                                    "{topic} operational benchmarking leaders",
                                    "{topic} efficiency ratios benchmark"
                        ],
                        "depends_on": [
                                    "S04"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Execution & Restructuring Plan",
                        "key_questions": [
                                    "How do we implement changes?",
                                    "What is the change management strategy?"
                        ],
                        "search_seeds": [
                                    "{topic} execution plan restructuring",
                                    "{topic} change management implementation"
                        ],
                        "depends_on": [
                                    "S05",
                                    "S07"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "execution_roadmap_development": {
        "name": "Execution Roadmap Development",
        "description": "Translating strategy into 90-day actionable sprint plans and milestones",
        "angles": [
            {
                        "id": "S01",
                        "title": "Current Process Baseline",
                        "key_questions": [
                                    "What does the current operation look like?",
                                    "What are the baseline metrics?"
                        ],
                        "search_seeds": [
                                    "{topic} current process baseline metrics",
                                    "{topic} standard operating procedures status"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Bottleneck Identification",
                        "key_questions": [
                                    "Where are the constraints?",
                                    "What slows down the workflow?"
                        ],
                        "search_seeds": [
                                    "{topic} process bottlenecks constraints",
                                    "{topic} operational inefficiencies slow down"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Supply Chain mapping",
                        "key_questions": [
                                    "What does the upstream/downstream look like?",
                                    "Where is supplier concentration high?"
                        ],
                        "search_seeds": [
                                    "{topic} supply chain mapping structure",
                                    "{topic} supplier concentration logistics"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S04",
                        "title": "Cost Drivers & Waste",
                        "key_questions": [
                                    "Where is capital being wasted?",
                                    "What are the primary cost centers?"
                        ],
                        "search_seeds": [
                                    "{topic} cost drivers waste reduction",
                                    "{topic} operational cost centers"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Automation & Technology Levers",
                        "key_questions": [
                                    "How can tech optimize this?",
                                    "What automation tools apply?"
                        ],
                        "search_seeds": [
                                    "{topic} process automation technology",
                                    "{topic} operations software optimization"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Quality & Compliance Control",
                        "key_questions": [
                                    "How is quality assured?",
                                    "Are there regulatory compliance steps?"
                        ],
                        "search_seeds": [
                                    "{topic} quality control assurance",
                                    "{topic} compliance regulatory operations"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Best-in-Class Benchmarks",
                        "key_questions": [
                                    "What do industry leaders do?",
                                    "What are the benchmark efficiency ratios?"
                        ],
                        "search_seeds": [
                                    "{topic} operational benchmarking leaders",
                                    "{topic} efficiency ratios benchmark"
                        ],
                        "depends_on": [
                                    "S04"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Execution & Restructuring Plan",
                        "key_questions": [
                                    "How do we implement changes?",
                                    "What is the change management strategy?"
                        ],
                        "search_seeds": [
                                    "{topic} execution plan restructuring",
                                    "{topic} change management implementation"
                        ],
                        "depends_on": [
                                    "S05",
                                    "S07"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "sector_benchmarking_studies": {
        "name": "Sector Benchmarking Studies",
        "description": "Macro-level evaluation of entire industries against global standards",
        "angles": [
            {
                        "id": "S01",
                        "title": "Macroeconomic & Policy Backdrop",
                        "key_questions": [
                                    "What is the current policy environment?",
                                    "What macroeconomic forces are at play?"
                        ],
                        "search_seeds": [
                                    "{topic} policy environment macroeconomic",
                                    "{topic} government regulations backdrop"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Ecosystem Mapping",
                        "key_questions": [
                                    "Who are the key stakeholders?",
                                    "How do the nodes interact?"
                        ],
                        "search_seeds": [
                                    "{topic} ecosystem mapping stakeholders",
                                    "{topic} sector participants network"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Regulatory Gaps & Opportunities",
                        "key_questions": [
                                    "Where does policy fall short?",
                                    "What subsidies or incentives exist?"
                        ],
                        "search_seeds": [
                                    "{topic} policy gap analysis shortcomings",
                                    "{topic} government incentives subsidies"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S04",
                        "title": "Capital & Funding Flows",
                        "key_questions": [
                                    "Where is investment coming from?",
                                    "How are MSMEs/startups funded?"
                        ],
                        "search_seeds": [
                                    "{topic} capital flows funding sources",
                                    "{topic} venture capital MSME funding"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Socio-Economic Impact",
                        "key_questions": [
                                    "What is the broader societal impact?",
                                    "How does this affect employment/GDP?"
                        ],
                        "search_seeds": [
                                    "{topic} socio economic impact employment",
                                    "{topic} GDP contribution sector"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Global Benchmarking",
                        "key_questions": [
                                    "How does this ecosystem compare globally?",
                                    "What can be learned from other regions?"
                        ],
                        "search_seeds": [
                                    "{topic} global benchmarking sector",
                                    "{topic} international comparison ecosystem"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Structural Headwinds",
                        "key_questions": [
                                    "What prevents further growth?",
                                    "What are the structural risks?"
                        ],
                        "search_seeds": [
                                    "{topic} structural headwinds barriers",
                                    "{topic} systemic risks sector"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Policy Recommendations",
                        "key_questions": [
                                    "What should policymakers do?",
                                    "What is the roadmap for ecosystem growth?"
                        ],
                        "search_seeds": [
                                    "{topic} policy recommendations roadmap",
                                    "{topic} ecosystem growth initiatives"
                        ],
                        "depends_on": [
                                    "S06",
                                    "S07"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "policy_gap_analysis": {
        "name": "Policy Gap Analysis",
        "description": "Analyzing regulatory frameworks, subsidies, and compliance shortcomings",
        "angles": [
            {
                        "id": "S01",
                        "title": "Macroeconomic & Policy Backdrop",
                        "key_questions": [
                                    "What is the current policy environment?",
                                    "What macroeconomic forces are at play?"
                        ],
                        "search_seeds": [
                                    "{topic} policy environment macroeconomic",
                                    "{topic} government regulations backdrop"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Ecosystem Mapping",
                        "key_questions": [
                                    "Who are the key stakeholders?",
                                    "How do the nodes interact?"
                        ],
                        "search_seeds": [
                                    "{topic} ecosystem mapping stakeholders",
                                    "{topic} sector participants network"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Regulatory Gaps & Opportunities",
                        "key_questions": [
                                    "Where does policy fall short?",
                                    "What subsidies or incentives exist?"
                        ],
                        "search_seeds": [
                                    "{topic} policy gap analysis shortcomings",
                                    "{topic} government incentives subsidies"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S04",
                        "title": "Capital & Funding Flows",
                        "key_questions": [
                                    "Where is investment coming from?",
                                    "How are MSMEs/startups funded?"
                        ],
                        "search_seeds": [
                                    "{topic} capital flows funding sources",
                                    "{topic} venture capital MSME funding"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Socio-Economic Impact",
                        "key_questions": [
                                    "What is the broader societal impact?",
                                    "How does this affect employment/GDP?"
                        ],
                        "search_seeds": [
                                    "{topic} socio economic impact employment",
                                    "{topic} GDP contribution sector"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Global Benchmarking",
                        "key_questions": [
                                    "How does this ecosystem compare globally?",
                                    "What can be learned from other regions?"
                        ],
                        "search_seeds": [
                                    "{topic} global benchmarking sector",
                                    "{topic} international comparison ecosystem"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Structural Headwinds",
                        "key_questions": [
                                    "What prevents further growth?",
                                    "What are the structural risks?"
                        ],
                        "search_seeds": [
                                    "{topic} structural headwinds barriers",
                                    "{topic} systemic risks sector"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Policy Recommendations",
                        "key_questions": [
                                    "What should policymakers do?",
                                    "What is the roadmap for ecosystem growth?"
                        ],
                        "search_seeds": [
                                    "{topic} policy recommendations roadmap",
                                    "{topic} ecosystem growth initiatives"
                        ],
                        "depends_on": [
                                    "S06",
                                    "S07"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "msme_startup_ecosystem_research": {
        "name": "MSME & Startup Ecosystem Research",
        "description": "Mapping startup hubs, incubator effectiveness, and venture capital flows",
        "angles": [
            {
                        "id": "S01",
                        "title": "Macroeconomic & Policy Backdrop",
                        "key_questions": [
                                    "What is the current policy environment?",
                                    "What macroeconomic forces are at play?"
                        ],
                        "search_seeds": [
                                    "{topic} policy environment macroeconomic",
                                    "{topic} government regulations backdrop"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Ecosystem Mapping",
                        "key_questions": [
                                    "Who are the key stakeholders?",
                                    "How do the nodes interact?"
                        ],
                        "search_seeds": [
                                    "{topic} ecosystem mapping stakeholders",
                                    "{topic} sector participants network"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Regulatory Gaps & Opportunities",
                        "key_questions": [
                                    "Where does policy fall short?",
                                    "What subsidies or incentives exist?"
                        ],
                        "search_seeds": [
                                    "{topic} policy gap analysis shortcomings",
                                    "{topic} government incentives subsidies"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S04",
                        "title": "Capital & Funding Flows",
                        "key_questions": [
                                    "Where is investment coming from?",
                                    "How are MSMEs/startups funded?"
                        ],
                        "search_seeds": [
                                    "{topic} capital flows funding sources",
                                    "{topic} venture capital MSME funding"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Socio-Economic Impact",
                        "key_questions": [
                                    "What is the broader societal impact?",
                                    "How does this affect employment/GDP?"
                        ],
                        "search_seeds": [
                                    "{topic} socio economic impact employment",
                                    "{topic} GDP contribution sector"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Global Benchmarking",
                        "key_questions": [
                                    "How does this ecosystem compare globally?",
                                    "What can be learned from other regions?"
                        ],
                        "search_seeds": [
                                    "{topic} global benchmarking sector",
                                    "{topic} international comparison ecosystem"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Structural Headwinds",
                        "key_questions": [
                                    "What prevents further growth?",
                                    "What are the structural risks?"
                        ],
                        "search_seeds": [
                                    "{topic} structural headwinds barriers",
                                    "{topic} systemic risks sector"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Policy Recommendations",
                        "key_questions": [
                                    "What should policymakers do?",
                                    "What is the roadmap for ecosystem growth?"
                        ],
                        "search_seeds": [
                                    "{topic} policy recommendations roadmap",
                                    "{topic} ecosystem growth initiatives"
                        ],
                        "depends_on": [
                                    "S06",
                                    "S07"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "economic_industry_opportunity_mapping": {
        "name": "Economic & Industry Opportunity Mapping",
        "description": "Identifying macroeconomic tailwinds and broad capital allocation targets",
        "angles": [
            {
                        "id": "S01",
                        "title": "Macroeconomic & Policy Backdrop",
                        "key_questions": [
                                    "What is the current policy environment?",
                                    "What macroeconomic forces are at play?"
                        ],
                        "search_seeds": [
                                    "{topic} policy environment macroeconomic",
                                    "{topic} government regulations backdrop"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Ecosystem Mapping",
                        "key_questions": [
                                    "Who are the key stakeholders?",
                                    "How do the nodes interact?"
                        ],
                        "search_seeds": [
                                    "{topic} ecosystem mapping stakeholders",
                                    "{topic} sector participants network"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Regulatory Gaps & Opportunities",
                        "key_questions": [
                                    "Where does policy fall short?",
                                    "What subsidies or incentives exist?"
                        ],
                        "search_seeds": [
                                    "{topic} policy gap analysis shortcomings",
                                    "{topic} government incentives subsidies"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S04",
                        "title": "Capital & Funding Flows",
                        "key_questions": [
                                    "Where is investment coming from?",
                                    "How are MSMEs/startups funded?"
                        ],
                        "search_seeds": [
                                    "{topic} capital flows funding sources",
                                    "{topic} venture capital MSME funding"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Socio-Economic Impact",
                        "key_questions": [
                                    "What is the broader societal impact?",
                                    "How does this affect employment/GDP?"
                        ],
                        "search_seeds": [
                                    "{topic} socio economic impact employment",
                                    "{topic} GDP contribution sector"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Global Benchmarking",
                        "key_questions": [
                                    "How does this ecosystem compare globally?",
                                    "What can be learned from other regions?"
                        ],
                        "search_seeds": [
                                    "{topic} global benchmarking sector",
                                    "{topic} international comparison ecosystem"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Structural Headwinds",
                        "key_questions": [
                                    "What prevents further growth?",
                                    "What are the structural risks?"
                        ],
                        "search_seeds": [
                                    "{topic} structural headwinds barriers",
                                    "{topic} systemic risks sector"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Policy Recommendations",
                        "key_questions": [
                                    "What should policymakers do?",
                                    "What is the roadmap for ecosystem growth?"
                        ],
                        "search_seeds": [
                                    "{topic} policy recommendations roadmap",
                                    "{topic} ecosystem growth initiatives"
                        ],
                        "depends_on": [
                                    "S06",
                                    "S07"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
    "implementation_roadmaps_kpi": {
        "name": "Implementation Roadmaps & KPI Frameworks",
        "description": "Tracking large-scale governmental or sector-wide policy rollouts",
        "angles": [
            {
                        "id": "S01",
                        "title": "Macroeconomic & Policy Backdrop",
                        "key_questions": [
                                    "What is the current policy environment?",
                                    "What macroeconomic forces are at play?"
                        ],
                        "search_seeds": [
                                    "{topic} policy environment macroeconomic",
                                    "{topic} government regulations backdrop"
                        ],
                        "depends_on": []
            },
            {
                        "id": "S02",
                        "title": "Ecosystem Mapping",
                        "key_questions": [
                                    "Who are the key stakeholders?",
                                    "How do the nodes interact?"
                        ],
                        "search_seeds": [
                                    "{topic} ecosystem mapping stakeholders",
                                    "{topic} sector participants network"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S03",
                        "title": "Regulatory Gaps & Opportunities",
                        "key_questions": [
                                    "Where does policy fall short?",
                                    "What subsidies or incentives exist?"
                        ],
                        "search_seeds": [
                                    "{topic} policy gap analysis shortcomings",
                                    "{topic} government incentives subsidies"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S04",
                        "title": "Capital & Funding Flows",
                        "key_questions": [
                                    "Where is investment coming from?",
                                    "How are MSMEs/startups funded?"
                        ],
                        "search_seeds": [
                                    "{topic} capital flows funding sources",
                                    "{topic} venture capital MSME funding"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S05",
                        "title": "Socio-Economic Impact",
                        "key_questions": [
                                    "What is the broader societal impact?",
                                    "How does this affect employment/GDP?"
                        ],
                        "search_seeds": [
                                    "{topic} socio economic impact employment",
                                    "{topic} GDP contribution sector"
                        ],
                        "depends_on": [
                                    "S01"
                        ]
            },
            {
                        "id": "S06",
                        "title": "Global Benchmarking",
                        "key_questions": [
                                    "How does this ecosystem compare globally?",
                                    "What can be learned from other regions?"
                        ],
                        "search_seeds": [
                                    "{topic} global benchmarking sector",
                                    "{topic} international comparison ecosystem"
                        ],
                        "depends_on": [
                                    "S02"
                        ]
            },
            {
                        "id": "S07",
                        "title": "Structural Headwinds",
                        "key_questions": [
                                    "What prevents further growth?",
                                    "What are the structural risks?"
                        ],
                        "search_seeds": [
                                    "{topic} structural headwinds barriers",
                                    "{topic} systemic risks sector"
                        ],
                        "depends_on": [
                                    "S03"
                        ]
            },
            {
                        "id": "S08",
                        "title": "Policy Recommendations",
                        "key_questions": [
                                    "What should policymakers do?",
                                    "What is the roadmap for ecosystem growth?"
                        ],
                        "search_seeds": [
                                    "{topic} policy recommendations roadmap",
                                    "{topic} ecosystem growth initiatives"
                        ],
                        "depends_on": [
                                    "S06",
                                    "S07"
                        ]
            }
],
        "style_notes": "Professional, analytical, and heavily structured.",
    },
}


def get_framework(framework_id: str) -> dict:
    from cormorant.framework_focus import get_strategic_focus
    fw = FRAMEWORKS.get(framework_id, list(FRAMEWORKS.values())[0])
    fw_copy = dict(fw)
    fw_copy["strategic_focus"] = get_strategic_focus(framework_id)
    return fw_copy


def list_categories() -> dict[str, list[tuple[str, str, str]]]:
    """Returns a dict mapping Category Name -> List of (framework_id, name, description)."""
    result = {}
    for cat, keys in CATEGORIES.items():
        entries = []
        for k in keys:
            fw = FRAMEWORKS.get(k)
            if fw is None:
                continue
            entries.append((k, fw.get("name", k), fw.get("description", "")))
        result[cat] = entries
    return result


def list_frameworks() -> list[tuple[str, str]]:
    return [(k, v["name"]) for k, v in FRAMEWORKS.items()]


# ── Load custom frameworks at module import time ──────────────────────────────
_custom = _load_custom_frameworks()
for _fw_id, _fw_data in _custom.items():
    if _fw_id not in FRAMEWORKS:
        FRAMEWORKS[_fw_id] = _fw_data
        CATEGORIES.setdefault(_CUSTOM_CATEGORY, []).append(_fw_id)
