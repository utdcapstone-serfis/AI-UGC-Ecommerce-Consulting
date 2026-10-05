"""Step 2: collect basic company info - industry, size, location, what they sell."""
import config
from agents import llm
from agents import classify
from agents.scraper import fetch_company_text
from models import Lead

SYSTEM_PROMPT = """You are a B2B research analyst. Given raw text scraped from a
company's website, extract structured facts. Only state what is reasonably
supported by the text; if something isn't mentioned, use an empty string
rather than guessing. Keep every field short (a phrase, not a paragraph)."""


class EnrichmentAgent:
    def enrich(self, lead: Lead, funding_hint: str = "") -> Lead:
        site_text = fetch_company_text(lead.website)
        lead.funding_notes = funding_hint

        if site_text and config.HAS_CLAUDE:
            self._enrich_with_claude(lead, site_text)
        elif site_text:
            self._enrich_heuristic(lead, site_text)
        # else: leave fields for manual entry - we don't fabricate company facts.
        return lead

    def _enrich_with_claude(self, lead: Lead, site_text: str) -> None:
        user = (
            f"Company: {lead.company_name}\nWebsite: {lead.website}\n\n"
            f"Scraped site text:\n{site_text}\n\n"
            "Return JSON with keys: industry, company_size, location, "
            "what_they_sell.\n"
            f"industry: pick exactly one of {list(classify.INDUSTRIES)} or ''.\n"
            f"company_size: pick exactly one employee band of {classify.SIZE_BANDS} "
            "only if the text states or clearly implies headcount (e.g. 'team of "
            "40', '300+ employees', a Fortune 500 company); otherwise ''. Do not "
            "guess from how polished the site looks."
        )
        try:
            data = llm.ask_claude_json(SYSTEM_PROMPT, user)
        except Exception:
            self._enrich_heuristic(lead, site_text)
            return
        lead.industry = data.get("industry", "") or lead.industry
        lead.company_size = data.get("company_size", "") or lead.company_size
        lead.location = data.get("location", "") or lead.location
        lead.what_they_sell = data.get("what_they_sell", "") or lead.what_they_sell

    def _enrich_heuristic(self, lead: Lead, site_text: str) -> None:
        """No-LLM fallback: keyword and pattern rules (see agents/classify.py).
        Leaves industry/size blank when the text doesn't support an answer."""
        lead.industry = lead.industry or classify.classify_industry(site_text)
        lead.company_size = lead.company_size or classify.estimate_size_label(site_text)
        lead.what_they_sell = lead.what_they_sell or site_text[:200]
