"""Chains the agents together per company and persists after every step.

Order: enrichment (company size and industry) -> contact-finding, which uses
them to decide whose email to pull -> scoring -> research -> outreach draft.

If contact-finding can't produce a decision maker's email (it only ever
returns decision makers), that company is cancelled right there: it is never
scored, researched, drafted or saved, and the pipeline moves on to the next
candidate. Discovery is asked for extra candidates up front so there are
replacements to draw on.

DEMO_MODE is exempt: with no provider keys the contact finder can never return
an email by design, so dropping on "no email" would drop every lead.
"""
import config
import storage
from agents.contact_finder import ContactFinderAgent
from agents.discovery import DiscoveryAgent
from agents.enrichment import EnrichmentAgent
from agents.outreach_writer import OutreachWriterAgent
from agents.research import ResearchAgent
from agents.scoring import ScoringAgent
from models import Lead

# Candidates requested from discovery per lead wanted, to cover the ones that
# get cancelled for having no email.
OVERFETCH = 3


class LeadGenPipeline:
    def __init__(self):
        self.discovery = DiscoveryAgent()
        self.enrichment = EnrichmentAgent()
        self.scoring = ScoringAgent()
        self.contact_finder = ContactFinderAgent()
        self.research = ResearchAgent()
        self.writer = OutreachWriterAgent()
        self.dropped: list[str] = []
        self.candidates_seen = 0

    def run(self, limit: int = 5) -> list[Lead]:
        storage.init_db()
        require_email = not config.DEMO_MODE
        companies = self.discovery.discover(
            limit=limit * OVERFETCH if require_email else limit
        )
        self.dropped = []
        self.candidates_seen = 0
        leads = []
        for company in companies:
            if len(leads) >= limit:
                break
            self.candidates_seen += 1
            lead = Lead(
                company_name=company.company_name,
                website=company.website,
                source=company.source,
            )

            lead = self.enrichment.enrich(lead, funding_hint=company.funding_hint)

            lead = self.contact_finder.find_contact(lead)
            if require_email and not lead.has_email():
                self.dropped.append(company.company_name)
                continue
            storage.save_lead(lead)

            lead = self.scoring.score(lead)
            storage.save_lead(lead)

            lead = self.research.research(lead)
            storage.save_lead(lead)

            lead = self.writer.write_email(lead)
            lead = storage.save_lead(lead)

            leads.append(lead)
        return leads
