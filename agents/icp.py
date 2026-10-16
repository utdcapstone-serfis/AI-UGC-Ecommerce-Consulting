"""Who Serfis wants as a lead, and the guardrail that keeps everyone else out.

The criteria come from the YC F26 prospect tracker: Serfis sells short-form
video ads and social content to early-stage tech startups. Consumer and prosumer
AI products with a demo-able story are the best fit (P1); B2B workflow products
with a visual before/after are secondary (P2); infrastructure and developer
tools are research comparables, never outreach targets (P3).

`rejection_reasons(lead)` is the guardrail. An empty list means the company
passes; anything else is why it must NOT become a lead. It fails closed: if the
criteria can't be verified for a company that isn't on the watchlist, it does
not pass.
"""
import re

import config

FIT_RANK = {"very high": 5, "high": 4, "medium-high": 3, "medium": 2, "strategic comparable": 0}
FIT_SCORE = {"very high": 10, "high": 8, "medium-high": 7, "medium": 6, "strategic comparable": 3}
PRIORITY_OK = {"P1", "P2"}

# Wording that marks a company as one of each kind. Checked in this order.
INFRA_SIGNALS = ["infrastructure", "developer platform", "for developers", "sdk", "open source",
                 "devops", "observability", "sandbox", "kubernetes", "benchmark", "evaluations",
                 "inference", "gpu", "llm ops", "agent framework", "testing for ai agents"]
CONSUMER_SIGNALS = ["app", "download", "your life", "personal", "daily", "students", "travel", "dating",
                    "fitness", "wearable", "ring", "earphones", "consumer", "habit", "for everyone",
                    "mobile", "creators", "your phone"]
B2B_SIGNALS = ["teams", "enterprise", "workflow", "automate", "brokers", "operations", "sales",
               "compliance", "customers", "crm", "b2b", "platform for", "businesses", "carriers", "advisors"]
STARTUP_SIGNALS = ["y combinator", "yc ", "backed by", "pre-seed", "seed round", "series a", "series b",
                   "startup", "start-up", "founded in 2019", "founded in 202"]
# Unambiguous developer-tooling wording: when present the company is infrastructure,
# however consumer-sounding the rest of the text ("mobile SDK for in-app purchases").
STRONG_INFRA = ["sdk", "for developers", "developer platform", "developer tools", "open source", "open-source",
                "infrastructure", "api for", "apis for", "dev tool", "devtool"]
SERVICES_INDUSTRIES = ("IT Services / Dev Agency", "Marketing / Agency", "HR / Recruiting")


def _hits(signals: list[str], text: str) -> int:
    return sum(1 for s in signals if re.search(rf"(?<![a-z]){re.escape(s)}(?![a-z])", text))


def fit_rank(fit: str) -> int:
    return FIT_RANK.get((fit or "").strip().lower(), -1)


def priority_for(fit: str) -> str:
    rank = fit_rank(fit)
    return "" if rank < 0 else "P1" if rank >= 4 else "P2" if rank >= 2 else "P3"


def classify(lead, text: str = "") -> None:
    """Fills market / best_ad_type / serfis_fit / priority / why / content angle for
    a company that is NOT on the watchlist, from its own wording. Leaves the
    fields blank when nothing in the text supports an answer - and never
    overwrites anything already set (watchlist values are authoritative)."""
    if lead.market and lead.serfis_fit:
        return
    blob = " ".join([lead.category, lead.industry, lead.what_they_sell, text]).lower()
    infra, consumer, b2b = _hits(INFRA_SIGNALS, blob), _hits(CONSUMER_SIGNALS, blob), _hits(B2B_SIGNALS, blob)
    if _hits(STRONG_INFRA, blob) or (infra >= 1 and infra >= consumer):
        market, fit, ad = "B2B Infrastructure", "Strategic Comparable", "Technical Demo"
        why = "Infrastructure / developer tooling - useful as a comparable, not a buyer of video ads."
        angle = ""
    elif consumer >= 2 and consumer >= b2b:
        market, fit, ad = "B2C", "High", "UGC + Screen Demo"
        why = ("Consumer-facing product with a demo-able story; suits short-form UGC and screen-demo "
               "content with many personas for rapid creative testing. (Rule-based - review.)")
        angle = "Day-in-the-life demo; before/after of the core pain point; screen recording of the main feature."
    elif b2b >= 2:
        market, fit, ad = "B2B", "Medium", "B2B Explainer / LinkedIn"
        why = ("Workflow product with a visual before/after; suits targeted explainer and LinkedIn "
               "content. (Rule-based - review.)")
        angle = "Manual process vs. automated; time-saved story; short founder-led explainer."
    else:
        return
    lead.market = lead.market or market
    lead.serfis_fit = lead.serfis_fit or fit
    lead.best_ad_type = lead.best_ad_type or ad
    lead.priority = lead.priority or priority_for(lead.serfis_fit)
    lead.why_it_fits = lead.why_it_fits or why
    lead.content_angle = lead.content_angle or angle


def _max_team(lead) -> int:
    nums = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", lead.company_size or "")]
    return max(nums) if nums else 0


def rejection_reasons(lead, text: str = "") -> list[str]:
    """Why this company must not become a lead. Empty list = it passes."""
    reasons = []
    max_team = config.ICP_MAX_TEAM_SIZE
    if _max_team(lead) > max_team:
        reasons.append(f"too large for an early-stage startup (team size {lead.company_size}, limit {max_team})")

    if lead.source == "prospect_tracker":                # on the tracker: its review is authoritative
        if lead.priority not in PRIORITY_OK:
            kind = "research-only comparable" if lead.priority == "P3" else "not reviewed yet"
            reasons.append(f"priority {lead.priority or 'none'} - {kind}, not an outreach target")
        if fit_rank(lead.serfis_fit) < fit_rank(config.ICP_MIN_FIT):
            reasons.append(f"fit rating '{lead.serfis_fit or 'none'}' is below '{config.ICP_MIN_FIT}'")
        if "infrastructure" in (lead.market or "").lower():
            reasons.append("B2B infrastructure / developer tooling is not a video-ad buyer")
        return reasons

    # Not on the tracker: it has to prove it fits.
    if lead.industry in SERVICES_INDUSTRIES:
        reasons.append(f"{lead.industry} - an established services firm, not a startup")
    blob = " ".join([lead.industry, lead.what_they_sell, lead.funding_notes, text]).lower()
    known_small = 0 < _max_team(lead) <= max_team
    if not (lead.yc_profile_url or known_small or _hits(STARTUP_SIGNALS, blob)):
        reasons.append("no evidence it is an early-stage startup (not YC, no small team size, no funding signal)")
    if not lead.market:
        reasons.append("could not tell whether the product is a consumer app or a B2B workflow tool")
    else:
        if "infrastructure" in lead.market.lower():
            reasons.append("looks like infrastructure / developer tooling, not a video-ad buyer")
        if fit_rank(lead.serfis_fit) < fit_rank(config.ICP_MIN_FIT):
            reasons.append(f"fit rating '{lead.serfis_fit or 'none'}' is below '{config.ICP_MIN_FIT}'")
    return reasons
