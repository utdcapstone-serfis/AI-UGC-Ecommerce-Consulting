"""Chains the agents together per company and persists after every step."""
import storage
from agents.contact_finder import ContactFinderAgent
from agents.discovery import DiscoveryAgent
from agents.enrichment import EnrichmentAgent
from agents.outreach_writer import OutreachWriterAgent
from agents.research import ResearchAgent
from agents.scoring import ScoringAgent
from models import Lead


class LeadGenPipeline:
    def __init__(self):
        self.discovery = DiscoveryAgent()
        self.enrichment = EnrichmentAgent()
        self.scoring = ScoringAgent()
        self.contact_finder = ContactFinderAgent()
        self.research = ResearchAgent()
        self.writer = OutreachWriterAgent()

    def run(self, limit: int = 5) -> list[Lead]:
        storage.init_db()
        companies = self.discovery.discover(limit=limit)
        leads = []
        for company in companies:
            lead = Lead(
                company_name=company.company_name,
                website=company.website,
                source=company.source,
            )
            lead = self.enrichment.enrich(lead, funding_hint=company.funding_hint)
            storage.save_lead(lead)

            lead = self.scoring.score(lead)
            storage.save_lead(lead)

            lead = self.contact_finder.find_contact(lead)
            storage.save_lead(lead)

            lead = self.research.research(lead)
            storage.save_lead(lead)

            lead = self.writer.write_email(lead)
            lead = storage.save_lead(lead)

            leads.append(lead)
        return leads
