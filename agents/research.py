"""Step 6: research the company and identify 2-3 personalized observations
that can be used in outreach."""
import config
from agents import llm
from agents.scraper import fetch_site_text
from models import Lead

SYSTEM_PROMPT = """You are a sales researcher preparing outreach for Serfis, an
autonomous AI content pipeline for e-commerce/SaaS brands. Serfis pitch:
{pitch}

Given raw facts about a prospect company, produce 2-3 short, specific,
genuinely useful observations a rep could reference in a first-touch email -
things like a recent product launch, funding round, growth signal, content or
marketing gap, or stated goal. Avoid generic flattery ("great website!").
Each observation should be one sentence."""


class ResearchAgent:
    def research(self, lead: Lead) -> Lead:
        site_text = fetch_site_text(lead.website)

        if config.HAS_CLAUDE and (site_text or lead.what_they_sell):
            lead.research_notes = self._research_with_claude(lead, site_text)
        else:
            lead.research_notes = self._research_heuristic(lead)

        lead.research_sources = self._collect_sources(lead, site_text)

        if not lead.outreach_angle:
            lead.outreach_angle = self._default_angle(lead)
        return lead

    def _research_with_claude(self, lead: Lead, site_text: str) -> str:
        user = (
            f"Company: {lead.company_name}\n"
            f"Industry: {lead.industry}\n"
            f"What they sell: {lead.what_they_sell}\n"
            f"Funding notes: {lead.funding_notes}\n"
            f"Site text excerpt: {site_text[:3000]}\n\n"
            "List 2-3 observations, one per line, no numbering/bullets."
        )
        try:
            text = llm.ask_claude(SYSTEM_PROMPT.format(pitch=config.SERFIS_PITCH), user)
            return text
        except Exception:
            return self._research_heuristic(lead)

    def _research_heuristic(self, lead: Lead) -> str:
        notes = []
        if lead.funding_notes:
            notes.append(f"Discovery notes: {lead.funding_notes}.")
        if lead.what_they_sell:
            notes.append(f"Sells: {lead.what_they_sell[:150]}.")
        if not notes:
            notes.append("Limited public data found; recommend manual research before outreach.")
        return " ".join(notes)

    def _collect_sources(self, lead: Lead, site_text: str) -> str:
        """Track exactly what the research was drawn from, so a reviewer can
        verify claims instead of trusting an unlabeled LLM summary."""
        sources = []
        if site_text and lead.website:
            sources.append(f"Company website ({lead.website})")
        if lead.funding_notes:
            sources.append("Discovery-stage funding hint (unverified - confirm before citing in outreach)")
        if not sources:
            sources.append("No sources fetched - website unreachable or empty at research time")
        return "; ".join(sources)

    def _default_angle(self, lead: Lead) -> str:
        return (
            f"Position Serfis as the fastest way for {lead.company_name} to scale "
            f"content production without scaling headcount, and to A/B test "
            f"messaging automatically as they grow post-funding."
        )
