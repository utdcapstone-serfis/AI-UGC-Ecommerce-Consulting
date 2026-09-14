"""Step 3: decide whether the company is a strong potential customer for Serfis."""
import re

import config
from agents import llm
from models import Lead

SIZE_KEYWORDS_GOOD = ["1-10", "11-50", "51-200"]
FUNDING_KEYWORDS = ["seed", "series a", "series b", "pre-seed", "raised", "funding", "venture"]
SAAS_KEYWORDS = ["saas", "software", "platform", "subscription", "api", "app"]
ECOMM_KEYWORDS = ["e-commerce", "ecommerce", "shopify", "online store", "storefront"]

SYSTEM_PROMPT = """You score how well a company fits Serfis's ideal customer
profile. Serfis pitch: {pitch}

ICP: SaaS companies, small-to-medium size, newer startups with recent VC
funding, ideally with e-commerce/product-driven content needs.

Score 1-10 (10 = perfect fit) and give a 1-2 sentence reason grounded in the
specific facts given, not generic praise."""


class ScoringAgent:
    def score(self, lead: Lead) -> Lead:
        if config.HAS_CLAUDE:
            self._score_with_claude(lead)
        else:
            self._score_heuristic(lead)
        return lead

    def _score_with_claude(self, lead: Lead) -> None:
        user = (
            f"Company: {lead.company_name}\n"
            f"Industry: {lead.industry}\n"
            f"Size: {lead.company_size}\n"
            f"What they sell: {lead.what_they_sell}\n"
            f"Funding notes: {lead.funding_notes}\n\n"
            "Return JSON with keys: score (integer 1-10), reason (string)."
        )
        try:
            data = llm.ask_claude_json(SYSTEM_PROMPT.format(pitch=config.SERFIS_PITCH), user)
            lead.icp_fit_score = int(data["score"])
            lead.why_it_fits = data["reason"]
            return
        except Exception:
            pass
        self._score_heuristic(lead)

    def _score_heuristic(self, lead: Lead) -> None:
        text = " ".join([lead.industry, lead.what_they_sell, lead.funding_notes]).lower()
        score = 4
        reasons = []

        if any(k in text for k in SAAS_KEYWORDS):
            score += 2
            reasons.append("operates in software/SaaS")
        if any(k in text for k in ECOMM_KEYWORDS):
            score += 2
            reasons.append("has e-commerce/product content needs Serfis can automate")
        if lead.company_size and any(k in lead.company_size for k in SIZE_KEYWORDS_GOOD):
            score += 1
            reasons.append(f"SMB-sized team ({lead.company_size}) fits ICP")
        if any(k in text for k in FUNDING_KEYWORDS):
            score += 1
            reasons.append("shows signs of recent VC funding/growth stage")

        lead.icp_fit_score = min(score, 10)
        lead.why_it_fits = (
            "; ".join(reasons).capitalize() + "."
            if reasons
            else "Limited signal from available data; needs manual review."
        )
