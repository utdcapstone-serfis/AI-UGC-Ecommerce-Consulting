"""Step 6: research the company and identify 2-3 personalized observations
that can be used in outreach."""
import config
from agents import icp, yc
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
        icp.classify(lead, site_text)       # no-op when the tracker already supplied these
        profile = yc.fetch_profile(lead.yc_profile_url) if lead.yc_profile_url else None

        if config.HAS_CLAUDE and (site_text or lead.what_they_sell):
            lead.research_notes = self._research_with_claude(lead, site_text, profile)
        else:
            lead.research_notes = self._research_heuristic(lead, profile)

        lead.research_sources = self._collect_sources(lead, site_text, profile)

        if not lead.outreach_angle:
            lead.outreach_angle = lead.content_angle or self._default_angle(lead)
        return lead

    def _context(self, lead: Lead, profile) -> str:
        """Everything already known about the company, for the model and the notes."""
        parts = []
        if profile:
            facts = [f"Y Combinator {profile['batch']}", f"team of {profile['team_size']}" if profile["team_size"] else "",
                     profile["location"]]
            parts.append(", ".join(x for x in facts if x) + ".")
            if profile["long_description"]:
                parts.append(profile["long_description"][:400].rstrip() + ("..." if len(profile["long_description"]) > 400 else ""))
        if lead.founders:
            parts.append("Founders: " + "; ".join(lead.founders.splitlines()) + ".")
        if lead.category or lead.market:
            parts.append(f"Category: {lead.category or '-'} ({lead.market or 'market unknown'}).")
        if lead.content_angle:
            parts.append(f"Suggested content angle: {lead.content_angle}")
        if lead.best_ad_type:
            parts.append(f"Best ad type: {lead.best_ad_type}.")
        return " ".join(parts)

    def _research_with_claude(self, lead: Lead, site_text: str, profile=None) -> str:
        user = (
            f"Company: {lead.company_name}\n"
            f"Industry: {lead.industry}\n"
            f"What they sell: {lead.what_they_sell}\n"
            f"Funding notes: {lead.funding_notes}\n"
            f"Already known: {self._context(lead, profile)}\n"
            f"Site text excerpt: {site_text[:3000]}\n\n"
            "List 2-3 observations, one per line, no numbering/bullets."
        )
        try:
            text = llm.ask_claude(SYSTEM_PROMPT.format(pitch=config.SERFIS_PITCH), user)
            return text
        except Exception:
            return self._research_heuristic(lead, profile)

    def _research_heuristic(self, lead: Lead, profile=None) -> str:
        notes = []
        context = self._context(lead, profile)
        if context:
            notes.append(context)
        elif lead.funding_notes:
            notes.append(f"Discovery notes: {lead.funding_notes}.")
        if lead.what_they_sell:
            notes.append(f"Sells: {lead.what_they_sell[:150]}.")
        if not notes:
            notes.append("Limited public data found; recommend manual research before outreach.")
        return " ".join(notes)

    def _collect_sources(self, lead: Lead, site_text: str, profile=None) -> str:
        """Track exactly what the research was drawn from, so a reviewer can
        verify claims instead of trusting an unlabeled LLM summary."""
        sources = []
        if site_text and lead.website:
            sources.append(f"Company website ({lead.website})")
        if profile:
            sources.append(f"Y Combinator company profile ({lead.yc_profile_url})")
        if lead.priority and lead.source == "prospect_tracker":
            sources.append("Serfis YC F26 prospect tracker (priority, category, fit, content angle)")
        if lead.funding_notes and not profile:
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
