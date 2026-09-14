"""Drafts a reply when a prospect responds to outreach.

Same human-approval model as agents/outreach_writer.py: this agent only ever
produces a DRAFT stored with approval_status='pending_review'. It never sends
anything, and nothing in this codebase calls it automatically - a human logs
the prospect's actual reply (pasted in via the dashboard, since there is no
live inbox connection yet - see README "Conversation / reply drafts") and
that action is what triggers a draft to be generated for review.
"""
import config
from agents import llm
from models import Lead

SYSTEM_PROMPT = """You write reply emails for Serfis, continuing an existing
outreach conversation with a prospect.

Serfis pitch: {pitch}

You will be given the original outreach email Serfis already sent, and the
prospect's reply to it. Write Serfis's next reply.

Rules:
- Directly address what the prospect actually asked or said - don't ignore it
  or pivot back to a generic pitch.
- Keep it honest: don't invent case studies, pricing, or commitments that
  aren't already implied by the Serfis pitch above.
- If the prospect asked a question you don't have a real answer for (specific
  pricing, contract terms, integration details), say a team member will
  follow up with specifics rather than guessing.
- This conversation stays entirely in email - Serfis does not call
  prospects. Never suggest or offer a phone call, meeting, or demo.
- Write like a person who works at Serfis, not like the product describing
  itself. Never describe Serfis as "an autonomous AI" or "an AI pipeline" -
  talk about the benefit to them, not how the system works internally.
- Plain, human tone, no hype words. Short - 50-100 words.
- Sign off as "The Serfis Team".

Return JSON with keys: subject (usually "Re: " + original subject), body (the
full reply including greeting and sign-off)."""


class ReplyDraftAgent:
    def draft_reply(self, lead: Lead, original_subject: str, original_body: str,
                     inbound_subject: str, inbound_body: str) -> tuple[str, str]:
        """Returns (subject, body) for a suggested reply. Callers are
        responsible for storing this as a pending_review draft - this
        function only generates text, it never touches the database."""
        if config.HAS_CLAUDE:
            result = self._draft_with_claude(
                lead, original_subject, original_body, inbound_subject, inbound_body
            )
            if result:
                return result
        return self._draft_template(lead, inbound_subject, inbound_body)

    def _draft_with_claude(self, lead, original_subject, original_body,
                            inbound_subject, inbound_body):
        user = (
            f"Company: {lead.company_name}\n"
            f"Contact: {lead.contact_name}, {lead.contact_title}\n\n"
            f"--- Original outreach Serfis sent ---\n"
            f"Subject: {original_subject}\n{original_body}\n\n"
            f"--- Prospect's reply ---\n"
            f"Subject: {inbound_subject}\n{inbound_body}\n"
        )
        try:
            data = llm.ask_claude_json(SYSTEM_PROMPT.format(pitch=config.SERFIS_PITCH), user)
            return data["subject"], data["body"]
        except Exception:
            return None

    def _draft_template(self, lead: Lead, inbound_subject: str, inbound_body: str):
        """No-LLM fallback so the pipeline still produces a usable draft."""
        first_name = (lead.contact_name or "there").split(" ")[0]
        subject = inbound_subject if inbound_subject.lower().startswith("re:") else f"Re: {inbound_subject}"
        body = (
            f"Hi {first_name},\n\n"
            f"Thanks for the reply - great question. Let me get you a precise "
            f"answer rather than guess; I'll have someone from the Serfis team "
            f"follow up over email with specifics shortly.\n\n"
            f"Happy to answer anything else here in the meantime.\n\n"
            f"The Serfis Team"
        )
        return subject, body
