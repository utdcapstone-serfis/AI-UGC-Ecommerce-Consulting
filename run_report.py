"""Guardrail and kill-switch test report for a pipeline run, emailed to the Gmail account.

    python main.py report --label "Run 1" --before-id 123 --log output/run-logs/x.log --email

It audits every lead against the same checks the send agent enforces (as if the lead were approved),
flips the kill switch on and off against the real send path in dry-run mode (nothing is sent to anyone),
runs the test suites, and writes a plain-text summary. With --email it goes to the Gmail account's own
inbox. It never emails a prospect.
"""
import dataclasses
import re
import smtplib
import ssl
import subprocess
import sys
from collections import Counter
from email.message import EmailMessage
from pathlib import Path

import config
import storage
from agents import guardrails, send_agent

ROOT = Path(__file__).resolve().parent
LOG_KEEP = re.compile(r"^(processed|.*(candidates|cancelled|ran out|paid contact lookups|screened|eligible|exported))", re.I)


def _never_email_a_company(*_a, **_k):
    raise RuntimeError("run_report must never email a company")


# Hard guard: nothing in this module (or anything it calls) can send a prospect email.
send_agent.send = _never_email_a_company


def _as_approved(lead):
    return dataclasses.replace(lead, approval_status="approved", lead_status="new")


def audit(leads):
    """Run every lead through the send-time checks as if it had been approved (reads only, sends nothing)."""
    rows, reasons = [], Counter()
    for lead in leads:
        rev = guardrails.review(lead)
        verified = lead.email_status in config.VERIFIED_EMAIL_STATUSES
        block = send_agent.blocker(_as_approved(lead))
        if block:
            reasons[re.sub(r"\s*\(.*", "", block)[:80]] += 1
        rows.append({"name": lead.company_name, "verified": verified, "draft": rev["draft"], "region": rev["region"],
                     "cooldown": guardrails.company_cooldown(lead), "suppressed": storage.is_suppressed(storage.normalize_email(lead.contact_email)),
                     "block": block, "approval": lead.approval_status})
    return rows, reasons


def killswitch(leads):
    """Pause, prove nothing can go out, resume, restore the original state. Dry-run only: no email is sent."""
    real = [l for l in leads if l.source != "demo_sample"]
    sim = _as_approved(real[0]) if real else None
    prior = guardrails.pause_reason()
    steps = []
    try:
        guardrails.resume()
        before = send_agent.blocker(sim) if sim else None
        steps.append(("switch OFF, approved lead checked", "not blocked by pause" if not before or "paused" not in before else f"BLOCKED: {before}", not before or "paused" not in before))
        guardrails.pause("kill-switch test (run_report): safe to ignore")
        after = send_agent.blocker(sim) if sim else None
        steps.append(("kill switch ON: single-lead check", after or "NOT BLOCKED", bool(after and "paused" in after)))
        bulk = send_agent.send_approved(dry_run=True)
        first = (bulk["skipped"][0][1] if bulk["skipped"] else "")
        steps.append(("kill switch ON: send-approved (dry run)", f"sent {len(bulk['sent'])}; {first[:90]}" if first else f"sent {len(bulk['sent'])}", not bulk["sent"] and "paused" in first))
        guardrails.resume()
        resumed = send_agent.blocker(sim) if sim else None
        steps.append(("kill switch OFF again", "sending allowed again" if not resumed or "paused" not in resumed else f"STILL PAUSED: {resumed}", not resumed or "paused" not in resumed))
    finally:
        guardrails.resume()
        if prior:
            guardrails.pause(prior.split("  ", 1)[-1])
    stats = guardrails.breaker_stats()
    return steps, stats, prior


def tests():
    out = []
    for name in ("test_guardrails.py", "test_verified.py"):
        path = ROOT / "tests" / name
        if not path.exists():
            out.append((name, "not found"))
            continue
        r = subprocess.run([sys.executable, "-W", "ignore", str(path)], capture_output=True, text=True, cwd=ROOT, timeout=300)
        last = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
        out.append((name, last))
    return out


def _log_lines(path):
    if not path or not Path(path).exists():
        return []
    keep = [ln.strip() for ln in Path(path).read_text(errors="ignore").splitlines() if LOG_KEEP.search(ln) and "warn" not in ln.lower()]
    return keep[-14:]


def build(label, before_id=0, log_path=None):
    leads = storage.get_all_leads()
    new = [l for l in leads if l.id > before_id]
    rows, reasons = audit(leads)
    ks, stats, prior = killswitch(leads)
    suite = tests()
    seen, dupes = {}, []
    for l in leads:
        for key in (("name", re.sub(r"\W+", "", l.company_name.lower())), ("site", storage.domain_of(l.website))):
            if key[1] and seen.setdefault(key, l.company_name) != l.company_name:
                dupes.append(f"{l.company_name} / {seen[key]}")
    emails = [storage.normalize_email(l.contact_email) for l in leads if l.has_email()]
    dup_emails = len(emails) - len(set(emails))
    unver = [r["name"] for r in rows if not r["verified"] and r["name"] != "Serfis Sample"]
    lines = [f"SERFIS LEAD-GEN TEST: {label}", "=" * 46, "",
             f"Leads in the database: {len(leads)} ({len(new)} new this run, {len(leads) - len(new)} existing)",
             f"Approval: " + ", ".join(f"{v} {k}" for k, v in Counter(l.approval_status for l in leads).items()),
             f"Contact status: " + ", ".join(f"{v} {k or 'provider/none'}" for k, v in Counter(l.email_status for l in leads).items()), ""]
    if new:
        lines.append(f"NEW LEADS THIS RUN ({len(new)})")
        for l in new:
            lines.append(f"  - {l.company_name} | {l.contact_name or '-'} ({l.contact_title or '-'}) | {l.email_status or 'unverified'} | score {l.icp_fit_score}")
        lines.append("")
    run_lines = _log_lines(log_path)
    if run_lines:
        lines += ["RUN LOG (key lines)"] + [f"  {ln[:150]}" for ln in run_lines] + [""]
    flagged = [r for r in rows if r["draft"] or r["region"]]
    lines += ["GUARDRAIL CHECKS (every lead tested as if approved)",
              f"  verified contact: {sum(r['verified'] for r in rows)} of {len(rows)}" + (f" (not verified: {', '.join(unver)})" if unver else ""),
              f"  draft check flags: {sum(bool(r['draft']) for r in rows)} | location flags: {sum(bool(r['region']) for r in rows)} | on the do-not-contact list: {sum(r['suppressed'] for r in rows)} | company cooldown: {sum(bool(r['cooldown']) for r in rows)}",
              f"  would a send be blocked today if approved: {sum(bool(r['block']) for r in rows)} of {len(rows)}"]
    for reason, n in reasons.most_common():
        lines.append(f"      {n} x {reason}")
    for r in flagged:
        lines.append(f"  flagged: {r['name']}: " + "; ".join((r['draft'] + r['region'])[:2]))
    lines += [f"  duplicate protection: {len(dupes)} duplicate companies/websites, {dup_emails} duplicate contact emails across {len(leads)} leads (one touch per company)"]
    lines += ["", "KILL SWITCH TEST (dry run: no email was sent to anyone)"]
    for name, result, passed in ks:
        lines.append(f"  [{'PASS' if passed else 'FAIL'}] {name}: {result}")
    lines.append(f"  bounce breaker today: {stats['sends']} sends, {stats['bounces']} bounces, {stats['complaints']} complaints; trips at {config.BOUNCE_RATE_PAUSE:.0%} bounces (min {config.BOUNCE_MIN_COUNT}) or 1 complaint")
    lines.append(f"  state restored: sending is {'PAUSED (as before)' if prior else 'ON'}")
    lines += ["", "TEST SUITES (throwaway database, no cost)"] + [f"  {n}: {res}" for n, res in suite]
    lines += ["", "Nothing was sent to any prospect. Mailing address for the footer is "
              + ("set." if getattr(config, "MAILING_ADDRESS", "") else "NOT set, so real sends are refused until it is."), ""]
    return "\n".join(lines)


def send_email(subject, body):
    if not config.HAS_GMAIL:
        raise RuntimeError("Gmail is not configured (GMAIL_ADDRESS / GMAIL_APP_PASSWORD)")
    msg = EmailMessage()
    msg["From"] = msg["To"] = config.GMAIL_ADDRESS     # only ever the connected Gmail account itself
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        smtp.send_message(msg)
    return config.GMAIL_ADDRESS
