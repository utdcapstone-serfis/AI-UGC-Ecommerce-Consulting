"""Sends APPROVED outreach through Gmail SMTP, with guardrails.

Never called by the discovery-to-draft pipeline. It runs only from
`python main.py send <id>` (one lead) or `python main.py send-approved`
(everything a human has approved), so a person always approves each email
first. Every email gets an opt-out line and the mailing address in its footer.

A real send is refused when: the lead isn't approved, was already contacted,
is on the do-not-contact list, has no usable address (or a reserved
.example/.test one), is demo data, the daily cap is reached, or
MAILING_ADDRESS isn't set. A test send (to_override) skips the per-lead and
cap checks, is not logged, and does not change the lead.
"""
import smtplib
import ssl
import time
from email.message import EmailMessage
from typing import Optional

import config
import storage
from agents import guardrails
from models import Lead

UNSUBSCRIBE_LINE = 'If you\'d rather not hear from me again, just reply "unsubscribe" and I\'ll take you off my list.'
RESERVED_DOMAINS = (".example", ".test", ".invalid", ".localhost")
OPT_OUT_PHRASES = ("unsubscribe", "remove me", "take me off", "stop emailing", "stop contacting",
                   "do not contact", "don't contact", "opt out", "opt-out")


def looks_like_opt_out(text: str) -> bool:
    """True if a reply is asking not to be emailed again."""
    lowered = (text or "").lower().replace("\u2019", "'")
    return any(p in lowered for p in OPT_OUT_PHRASES)


def footer() -> str:
    address = config.MAILING_ADDRESS or "[mailing address not set]"
    return f"\n\n--\n{UNSUBSCRIBE_LINE}\n{address}"


def blocker(lead: Lead) -> Optional[str]:
    """Why this lead must not get a REAL send right now, or None if it's clear."""
    if lead.approval_status != "approved":
        return f"approval_status is '{lead.approval_status}', not 'approved'"
    if lead.lead_status != "new":
        return f"lead_status is '{lead.lead_status}' (already handled)"
    if lead.source == "demo_sample":
        return "demo data"
    if not (lead.draft_email_subject and lead.draft_email_body):
        return "no drafted email"
    if not lead.has_email():
        return "no usable email address"
    if config.REQUIRE_VERIFIED_CONTACT and lead.email_status not in config.VERIFIED_EMAIL_STATUSES:
        return (f"contact is not verified (email status '{lead.email_status or 'from a data provider'}'): only an address the company "
                "or the founder published, or one a person confirmed, may be emailed")
    if lead.email_status == "guessed":
        return (f"email {lead.contact_email} is a guess from the founder's name, not confirmed - "
                f"verify it, then run: python main.py confirm-email {lead.id}")
    email = storage.normalize_email(lead.contact_email)
    if email.endswith(RESERVED_DOMAINS):
        return "reserved/example email domain"
    if storage.is_suppressed(email):
        return "on the do-not-contact list"
    paused = guardrails.sending_block_reason()
    if paused:
        return paused
    cooldown = guardrails.company_cooldown(lead)
    if cooldown:
        return cooldown
    for category, issues in guardrails.blocking(lead):
        return (f"flagged by the {category} check and not yet acknowledged: {issues[0]} "
                f"(open the lead in the dashboard and choose 'Approve anyway', or fix it)")
    return None


def send(lead: Lead, to_override: Optional[str] = None) -> str:
    """Send one lead's draft. Returns the address it was sent to."""
    if lead.approval_status != "approved":
        raise RuntimeError(
            f"Refusing to send lead {lead.id} ({lead.company_name}): "
            f"approval_status is '{lead.approval_status}', not 'approved'."
        )
    if not config.HAS_GMAIL:
        raise RuntimeError("GMAIL_ADDRESS / GMAIL_APP_PASSWORD are not set in .env.")
    if not (lead.draft_email_subject and lead.draft_email_body):
        raise RuntimeError(f"Lead {lead.id} has no drafted email.")

    if to_override:
        to = to_override.strip()
        if "@" not in to:
            raise RuntimeError(f"'{to}' is not an email address.")
    else:
        reason = blocker(lead)
        if reason:
            raise RuntimeError(f"Refusing to send lead {lead.id} ({lead.company_name}): {reason}.")
        if not config.MAILING_ADDRESS:
            raise RuntimeError(
                "MAILING_ADDRESS is not set in .env - a postal address is required in "
                "every outreach email (CAN-SPAM)."
            )
        if storage.count_sent_today() >= config.EMAIL_DAILY_CAP:
            raise RuntimeError(f"Daily cap of {config.EMAIL_DAILY_CAP} emails reached.")
        to = lead.contact_email.strip()

    msg = EmailMessage()
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = to
    msg["Subject"] = ("[TEST] " if to_override else "") + lead.draft_email_subject
    msg.set_content(lead.draft_email_body.rstrip() + footer())

    with smtplib.SMTP_SSL("smtp.gmail.com", 465,
                          context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        smtp.send_message(msg)

    if not to_override:
        storage.log_send(lead.id, to, lead.draft_email_subject)
        storage.set_lead_status(lead.id, "contacted")
    return to


def send_approved(limit: Optional[int] = None, dry_run: bool = False,
                  delay: Optional[int] = None) -> dict:
    """Sends every approved, not-yet-contacted lead, up to the daily cap (and
    `limit`), pausing between emails. Returns {"sent": [...], "skipped": [...]}
    where each entry is (company, address-or-reason)."""
    delay = config.EMAIL_SEND_DELAY_SECONDS if delay is None else delay
    sent, skipped = [], []
    paused = guardrails.sending_block_reason()
    if paused:                                   # kill switch / bounce breaker: nothing goes out
        return {"sent": [], "skipped": [("ALL LEADS", paused)]}
    room = config.EMAIL_DAILY_CAP - storage.count_sent_today()
    if limit is not None:
        room = min(room, limit)

    queue = []
    for lead in storage.get_all_leads():
        if lead.approval_status != "approved":
            continue
        reason = blocker(lead)
        if reason:
            skipped.append((lead.company_name, reason))
        else:
            queue.append(lead)

    if not dry_run and queue and not config.MAILING_ADDRESS:
        raise RuntimeError("MAILING_ADDRESS is not set in .env - required before real sends.")

    for i, lead in enumerate(queue):
        if room <= 0:
            skipped.append((lead.company_name, "daily cap / limit reached"))
            continue
        if dry_run:
            sent.append((lead.company_name, lead.contact_email))
            room -= 1
            continue
        try:
            to = send(lead)
        except (smtplib.SMTPAuthenticationError, smtplib.SMTPServerDisconnected) as exc:
            skipped.append((lead.company_name, f"stopped - Gmail login/connection failed: {exc}"))
            break
        except Exception as exc:
            skipped.append((lead.company_name, f"failed: {exc}"))
            continue
        sent.append((lead.company_name, to))
        room -= 1
        if i < len(queue) - 1 and room > 0 and delay:
            time.sleep(delay)
    return {"sent": sent, "skipped": skipped}
