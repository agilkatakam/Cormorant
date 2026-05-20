"""High-fidelity strategic focus mandates for Cormorant's 30 frameworks."""

from __future__ import annotations

STRATEGIC_FOCUS_MAP: dict[str, str] = {
    # I. Business Strategy & Market Intelligence
    "industry_competitive_landscape": (
        "Focus on mapping the relative market shares of key competitors, identifying structural barriers "
        "to entry (such as capital requirements, regulatory hurdles, or proprietary technology), and "
        "diagnosing where profit pools sit within the value chain."
    ),
    "market_research_trend_forecasting": (
        "Focus on tracking historical and projected CAGR, identifying secular growth tailwinds vs. cyclical "
        "macroeconomic fluctuations, and detailing demographic or technological shifts driving future market demand."
    ),
    "gtm_strategy_development": (
        "Focus on defining the optimal customer acquisition channels, estimating CAC/LTV dynamics, mapping "
        "the partner ecosystem, and detailing a tactical, phased timeline for initial market entry."
    ),
    "feasibility_expansion_studies": (
        "Focus on regulatory compliance, localized operational or supply chain constraints, initial capital "
        "expenditure (CapEx) requirements, and assessing cultural or demographic product-market fit."
    ),
    "strategic_benchmarking_opportunity_mapping": (
        "Focus on comparing core capabilities against top-tier market leaders, identifying functional white-spaces "
        "or unserved niches, and creating a concrete action plan to exploit competitor weaknesses."
    ),

    # II. Research & Data Analytics
    "surveys_interviews_focus_groups": (
        "Focus on qualitative research methodologies, sampling strategy robustness, formulating neutral/unbiased "
        "interrogator questions, and extracting structured sentiment patterns from unstructured user responses."
    ),
    "consumer_behaviour_analysis": (
        "Focus on psychographic and demographic segmentation, identifying friction points in the user journey, "
        "isolating purchasing decision triggers, and tracking retention vs. churn cohort behaviors."
    ),
    "data_visualisation_dashboarding": (
        "Focus on defining high-signal dashboard metrics, user interaction flows, data pipeline latency "
        "requirements, and structuring clean, wireframe-grade wire layouts for automated business reporting."
    ),
    "business_insights_reporting": (
        "Focus on translating raw transactional or operational data into executive-level strategic decisions, "
        "isolating specific operational inefficiencies, and mapping data anomalies to real business impacts."
    ),
    "kpi_performance_tracking": (
        "Focus on establishing balanced scorecard metrics, defining leading vs. lagging performance indicators, "
        "setting realistic target thresholds, and structuring corporate accountability models."
    ),

    # III. Marketing & Growth Strategy
    "product_market_fit": (
        "Focus on defining the core value proposition, tracking the 'Sean Ellis' PMF metrics, isolating "
        "high-retention cohorts of power users, and detailing the product features driving organic word-of-mouth."
    ),
    "brand_positioning_messaging": (
        "Focus on defining the unique selling proposition (USP), crafting resonant messaging pillars for "
        "distinct buyer personas, mapping competitor positioning matrices, and tracking brand sentiment."
    ),
    "pricing_strategy_revenue_modeling": (
        "Focus on customer willingness-to-pay (WTP), comparing value-based vs. cost-plus pricing structures, "
        "defining optimal pricing tiers/packaging, and modeling revenue sensitivity curves (price elasticity)."
    ),
    "digital_marketing_social_media": (
        "Focus on multi-channel traffic attribution models, conversion rate optimization (CRO) at each funnel stage, "
        "ad spend efficiency metrics (ROAS, CPC), and organic search authority (SEO) growth."
    ),
    "influencer_campus_outreach": (
        "Focus on micro-influencer engagement rates, building campus brand-ambassador networks, establishing "
        "organic word-of-mouth referral loops, and tracking campaign attribution to acquisition."
    ),

    # IV. AI & Data Intelligence Consulting
    "ai_assisted_market_competitive_research": (
        "Focus on identifying standard generative and predictive AI tooling, assessing competitor LLM/SLM "
        "deployment strategies, and tracking open-source vs. proprietary software cost advantages."
    ),
    "predictive_trend_customer_analysis": (
        "Focus on machine learning models used for customer churn prediction, lifetime value forecasting, "
        "dynamic demand-pricing algorithms, and detailing the necessary data engineering pipelines."
    ),
    "ai_use_case_id": (
        "Focus on identifying low-hanging operational processes ripe for automation, estimating implementation "
        "costs vs. long-term ROI, and defining a phased rollout plan for MSMEs."
    ),
    "data_driven_decision_support": (
        "Focus on detailing data lakes/warehousing requirements, designing automated recommendation engines, "
        "and defining governance protocols for algorithmic decision-making."
    ),
    "ai_readiness_adoption_assessment": (
        "Focus on auditing current technical infrastructure (such as legacy databases), measuring employee "
        "skills gaps, assessing compute cost scalability, and identifying regulatory/compliance risks."
    ),

    # V. Operations & Process Excellence
    "workflow_process_optimisation": (
        "Focus on modeling current workflows, identifying structural bottlenecks (Theory of Constraints), "
        "calculating lead/cycle times, and detailing lean or Six Sigma waste reduction opportunities."
    ),
    "supply_chain_logistics": (
        "Focus on vendor dependency risks, inventory turnover metrics, freight/distribution costs, localized "
        "customs/regulatory constraints, and resilience strategies (such as dual sourcing)."
    ),
    "cost_reduction_efficiency": (
        "Focus on identifying redundant operational activities, automating manual steps, negotiating vendor "
        "pricing contracts, and modeling margin expansion from incremental cost-cuts."
    ),
    "sop_process_documentation": (
        "Focus on detailing step-by-step Standard Operating Procedures (SOPs), mapping responsibility "
        "matrices (RACI), identifying safety/compliance failure points, and onboarding protocols."
    ),
    "execution_roadmap_development": (
        "Focus on critical path scheduling (Gantt milestones), resource allocation matrixes, and risk "
        "mitigation strategies for complex consulting deployments."
    ),

    # VI. Policy, Ecosystem & Sector Research
    "sector_benchmarking_studies": (
        "Focus on broad sector indicators, structural growth trends, capital allocation efficiency across "
        "industries, and identifying key tailwinds."
    ),
    "policy_gap_analysis": (
        "Focus on comparing existing policy frameworks to best-in-class international standards, identifying "
        "regulatory enforcement gaps, and proposing legislative or regulatory amendments."
    ),
    "msme_startup_ecosystem_research": (
        "Focus on capital access barriers, public incubation infrastructure, talent retention challenges, "
        "and tax/regulatory burdens on early-stage enterprises."
    ),
    "economic_industry_opportunity_mapping": (
        "Focus on regional comparative advantages, talent hubs, local resource clusters, and fiscal incentives "
        "designed to attract industry investments."
    ),
    "implementation_roadmaps_kpi": (
        "Focus on defining public sector performance scorecards, community stakeholder alignment metrics, "
        "project milestone tracking, and long-term sustainability plans."
    )
}

def get_strategic_focus(framework_id: str) -> str:
    # 1. Check the standard map first
    if framework_id in STRATEGIC_FOCUS_MAP:
        return STRATEGIC_FOCUS_MAP[framework_id]
    # 2. Check if it's a custom framework with an embedded strategic_focus
    try:
        from cormorant.frameworks import FRAMEWORKS
        fw = FRAMEWORKS.get(framework_id, {})
        if fw.get("strategic_focus"):
            return fw["strategic_focus"]
    except Exception:
        pass
    # 3. Default fallback
    return "Focus on high-quality strategic consulting findings."
