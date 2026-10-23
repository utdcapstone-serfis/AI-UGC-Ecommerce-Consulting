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

SYSTEM_PROMPT = """You write reply emails for Serfis AI, continuing an existing
outreach conversation with a prospect.

What Serfis offers: {offer}

This is the approved outreach message Serfis sends. Match its voice, its
wording about what Serfis does, and its closing ask:
---
{reference}
---

You will be given the original outreach email already sent and the prospect's
reply to it. Write the next reply.

Rules:
- Answer what the prospect actually said or asked FIRST. Never ignore it or
  paste the reference message back.
- When the prospect asks what Serfis does, or shows interest, explain it using
  the reference wording (short-form video ads and social content for TikTok,
  Instagram, YouTube, Reddit, X and Pinterest, innovative advertisements per platform).
- Never use the phrase "fresh creative" (it reads oddly). Say "innovative advertisements".
- Where it fits, close with the same low-key ask: would they be open to a
  couple of concepts sent over email. If they already said yes, confirm the
  concepts will follow by email instead of asking again.
- Be honest: don't invent case studies, results, pricing or turnaround times.
  If they ask something you can't answer (pricing, contracts, specifics), say
  a team member will follow up over email with specifics.
- This conversation stays entirely in email. Never suggest or offer a phone
  call, meeting or demo.
- "Serfis AI" is the company name and is fine to use. Never describe the
  system as "an autonomous AI" or "an AI pipeline" or explain how it works
  internally - talk about the benefit to them.
- Plain text only (no markdown, no bold, no bullets). Human tone, no hype
  words. 60-120 words.
- Sign off exactly as:
{signoff}

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
            data = llm.ask_claude_json(SYSTEM_PROMPT.format(
                offer=config.EMAIL_OFFER.strip(),
                reference=config.EMAIL_REFERENCE,
                signoff=config.EMAIL_SIGNOFF,
            ), user)
            return data["subject"], data["body"]
        except Exception:
            return None

    def _draft_template(self, lead: Lead, inbound_subject: str, inbound_body: str):
        """No-LLM fallback so the pipeline still produces a usable draft."""
        first_name = lead.first_name()
        subject = inbound_subject if inbound_subject.lower().startswith("re:") else f"Re: {inbound_subject}"
        what = lead.product_phrase()
        ideas = (
            f"turn {what} into engaging social content"
            if what else "turn what you do into engaging social content"
        )
        body = (
            f"Hi {first_name},\n\n"
            f"Thanks for getting back to me. For context, at Serfis AI we create "
            f"short-form video advertisements and social content for TikTok, Instagram, "
            f"YouTube, Reddit, X, and Pinterest - innovative advertisements that fit the style and "
            f"audience of each platform instead of the same content everywhere.\n\n"
            f"I had a few ideas for how {lead.company_name} could {ideas}. Would you be "
            f"open to me sending over a couple of concepts? If you had a specific question, "
            f"I'll have someone from the team follow up over email with specifics.\n\n"
            f"{config.EMAIL_SIGNOFF}"
        )
        return subject, body
