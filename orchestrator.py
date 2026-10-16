"""Chains the agents together per company and persists after every step.

Order: enrichment (size, industry, YC facts) -> ICP guardrail -> contact-finding,
which uses size and industry to decide whose email to pull -> scoring -> research
-> outreach draft.

The ICP guardrail (agents/icp.py) runs BEFORE the paid contact lookup: a company
that doesn't meet the criteria (research-only comparable, infrastructure tooling,
established services firm, too large, or can't be verified as a fit) is never
saved, never emailed about, and costs nothing beyond its website fetch.

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
from agents import icp
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
        self.dropped: list[str] = []      # no decision-maker email found
        self.rejected: list[tuple] = []   # (company, reasons) - failed the ICP guardrail
        self.lookup_failed: list[str] = []  # email lookup errored (not the same as none found)
        self.candidates_seen = 0
        self.lookups = 0
        self.budget_hit = False

    def run(self, limit: int = 5, max_lookups: int = None) -> list[Lead]:
        storage.init_db()
        max_lookups = max_lookups if max_lookups is not None else config.MAX_LOOKUPS_PER_RUN
        self.lookups = 0
        require_email = not config.DEMO_MODE
        require_icp = not config.DEMO_MODE
        companies = self.discovery.discover(
            limit=max(limit * OVERFETCH, max_lookups * 2) if require_email else limit
        )
        self.dropped = []
        self.rejected = []
        self.lookup_failed = []
        self.candidates_seen = 0
        self.budget_hit = False
        leads = []
        for company in companies:
            if len(leads) >= limit:
                break
            self.candidates_seen += 1
            lead = Lead(
                company_name=company.company_name,
                website=company.website,
                source=company.source,
                priority=company.priority,
                category=company.category,
                market=company.market,
                what_they_sell=company.what_they_do,
                why_it_fits=company.why_serfis_fit,
                content_angle=company.content_angle,
                best_ad_type=company.best_ad_type,
                serfis_fit=company.serfis_fit,
                yc_profile_url=company.yc_profile_url,
                founders=company.founders,
                contact_name=company.contact_name, contact_title=company.contact_title,
                contact_email=company.contact_email,
                contact_profile_url=company.contact_linkedin,
                email_status=(company.contact_source or "published") if company.contact_email else "",
            )

            if require_email and config.PAID_LOOKUP_FALLBACK and self.contact_finder.paid_lookups >= max_lookups:
                self.budget_hit = True
                break
            lead = self.enrichment.enrich(lead, funding_hint=company.funding_hint)
            if require_icp:
                reasons = icp.rejection_reasons(lead, getattr(self.enrichment, "last_site_text", ""))
                if reasons:
                    self.rejected.append((company.company_name, "; ".join(reasons)))
                    continue

            errors_before = len(self.contact_finder.errors)
            paid_before = self.contact_finder.paid_lookups
            lead = self.contact_finder.find_contact(lead)
            self.lookups = self.contact_finder.paid_lookups
            outcome = self.contact_finder.last_outcome
            paid_now = self.contact_finder.paid_lookups > paid_before
            if require_email and outcome in ("hit", "miss", "unverified") and (outcome in ("hit", "unverified") or paid_now):
                # Feedback to discovery: remember the result so this company is never paid for
                # twice, and so the YC pool ranking learns which kinds of company yield emails.
                storage.record_lookup(lead.website, lead.company_name, outcome,
                                      batch=lead.yc_batch, size_band=lead.company_size, market=lead.market)
            if require_email and not lead.has_email():
                if len(self.contact_finder.errors) > errors_before:
                    self.lookup_failed.append(self.contact_finder.errors[-1])
                else:
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
