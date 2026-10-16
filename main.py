"""CLI entrypoint.

Usage:
    python main.py run --limit 5          # run the pipeline, save to SQLite
    python main.py export                 # export current DB to Excel
    python main.py review                 # print pending leads for review
    python main.py approve <id> [--force] # approve a lead (refused if guardrails flag it; --force = approve anyway)
    python main.py audit-contacts [--repoint]   # re-verify every lead's contact (published email + LinkedIn role)
    python main.py checks                 # guardrail status: sending on/paused, bounce rate, flagged leads
    python main.py pause ["reason"]       # kill switch: stop all real sending
    python main.py resume                 # turn sending back on
    python main.py bounce <email>         # record a bounce (suppresses the address; may auto-pause sending)
    python main.py complaint <email>      # record a spam complaint (pauses sending)
    python main.py check-bounces [--days N] [--dry-run]   # scan the Gmail inbox for delivery-failure notices
    python main.py reject <id>            # mark a lead rejected
    python main.py send <id> --to a@b.com  # email an APPROVED lead's draft (test address)
    python main.py send <id>              # email an APPROVED lead's draft to the lead
    python main.py send-approved [--limit N] [--dry-run]   # email everything approved (daily cap)
    python main.py suppress <email>       # never email this address again
    python main.py seed-demo              # add one fictional sample lead (with analytics)
    python main.py reset                  # delete ALL leads and analytics (asks to confirm)
"""
import argparse
import sys

import config
import storage
from demo_seed import seed_demo_lead
from export_excel import export_to_excel
from orchestrator import LeadGenPipeline


def cmd_run(args):
    if config.DEMO_MODE:
        print("[demo mode] APIFY_API_TOKEN not set - using seed "
              "companies and marking contact fields NEEDS_ENRICHMENT.\n")
    pipeline = LeadGenPipeline()
    leads = pipeline.run(limit=args.limit, max_lookups=args.max_lookups)
    print(f"Processed {len(leads)} leads. Paid contact lookups this run: {pipeline.lookups}"
          + (" (lookup budget reached)" if pipeline.budget_hit else "") + ".")
    for note in getattr(pipeline.discovery, "notes", []):
        print(f"Note: {note}")
    if pipeline.rejected:
        print(f"Rejected {len(pipeline.rejected)} companies that don't meet the criteria (not saved):")
        for company, why in pipeline.rejected:
            print(f"  - {company}: {why}")
    if pipeline.lookup_failed:
        print(f"Contact not verified (or lookup failed) for {len(pipeline.lookup_failed)} companies - NOT saved as leads:")
        for msg in pipeline.lookup_failed:
            print(f"  - {msg}")
    if pipeline.dropped:
        print(f"Cancelled {len(pipeline.dropped)} companies with no decision-maker email found: "
              + ", ".join(pipeline.dropped))
    if len(leads) < args.limit and not config.DEMO_MODE:
        print(f"Only {len(leads)} of {args.limit} requested - ran out of candidates "
              f"({pipeline.candidates_seen} checked). Run again to search further.")
    print()
    for lead in leads:
        print(lead.print_block())
        print("-" * 60)
    path = export_to_excel()
    print(f"\nExported to {path}")


def cmd_export(args):
    path = export_to_excel()
    print(f"Exported to {path}")


def cmd_review(args):
    leads = storage.get_leads_by_status("pending_review")
    if not leads:
        print("No leads pending review.")
        return
    for lead in leads:
        print(lead.print_block())
        print(f"[id={lead.id}]  -> approve with: python main.py approve {lead.id}")
        print("-" * 60)


def cmd_approve(args):
    from agents import guardrails
    lead = storage.get_lead(args.lead_id)
    if lead is None:
        print(f"No lead with id {args.lead_id}.")
        return 1
    flagged = guardrails.blocking(lead)
    if flagged and not args.force:
        print(f"Not approved - {lead.company_name} has guardrail flags:")
        for category, issues in flagged:
            for issue in issues:
                print(f"  [{category}] {issue}")
        print(f"Fix it, or approve anyway with: python main.py approve {lead.id} --force")
        return 1
    if flagged:
        storage.set_overrides(lead.id, ",".join(sorted(guardrails.acknowledged(lead) | {c for c, _ in flagged})))
    storage.set_approval_status(args.lead_id, "approved")
    print(f"Lead {args.lead_id} approved" + (" (flags acknowledged)." if flagged else "."))


def cmd_checks(args):
    from agents import guardrails
    paused = guardrails.pause_reason()
    stats = guardrails.breaker_stats()
    print("SENDING:", f"PAUSED - {paused.split('  ', 1)[-1]}" if paused else "on")
    print(f"Last {config.BOUNCE_WINDOW_DAYS} days: {stats['sends']} sent, {stats['bounces']} bounced ({stats['rate']:.0%}); "
          f"complaints (30 days): {stats['complaints']}")
    print()
    for lead in storage.get_all_leads():
        if lead.source == "demo_sample":
            continue
        review = guardrails.review(lead)
        state = guardrails.summary(lead)[0]
        mark = {"ok": "clear   ", "flag": "REVIEW  ", "reviewed": "reviewed"}[state]
        print(f"[{lead.id:>3}] {mark} {lead.company_name}  ({lead.location or 'location unknown'})")
        for category, issues in review.items():
            for issue in issues:
                print(f"        - {category}: {issue}")


def cmd_audit_contacts(args):
    """Re-verify every lead's contact against the strict rule. Costs ~$0.004 per LinkedIn profile read."""
    from agents import linkedin, site_emails
    from agents.outreach_writer import OutreachWriterAgent
    verified = 0
    failing = []
    for lead in storage.get_all_leads():
        if lead.source == "demo_sample":
            continue
        problems, checks = [], []
        if lead.email_status not in config.VERIFIED_EMAIL_STATUSES:
            problems.append(f"email is '{lead.email_status or 'from a data provider'}' - not published by the company or confirmed")
        elif lead.email_status == "published":
            if lead.contact_email.lower() in site_emails.own_domain_emails(lead.website):
                checks.append("still published on the company site")
            else:
                problems.append("address is no longer on the company's website")
        details = {}
        if lead.email_status != "confirmed":
            ok, why, details = linkedin.check_contact(lead)
            (checks if ok else problems).append(f"LinkedIn: {why}")
        flag = "VERIFIED " if not problems else "NOT VERIFIED"
        print(f"[{lead.id:>3}] {flag} {lead.company_name} - {lead.contact_name} <{lead.contact_email}>")
        for c in checks: print(f"        + {c}")
        for p in problems: print(f"        - {p}")
        if not problems:
            verified += 1
            # keep the proof on the record so the dashboard can show how the contact was verified
            lead.contact_check = "; ".join(checks)
            if details.get("url"):
                lead.contact_profile_url = details["url"]
            if details.get("title"):
                lead.contact_title = details["title"]
            if not (lead.location or "").strip() and details.get("place"):
                lead.location = details["place"]
            storage.save_lead(lead)
            continue
        failing.append(lead)
        if args.repoint:
            alt = site_emails.find_published(lead.website, lead.founders)
            if alt and alt["email"].lower() != (lead.contact_email or "").lower():
                import copy
                trial = copy.copy(lead)
                trial.contact_name, trial.contact_title, trial.contact_email = alt["name"], alt["title"], alt["email"]
                trial.contact_profile_url = ""
                ok, why, d = linkedin.check_contact(trial)
                if ok:
                    lead.contact_name, lead.contact_title, lead.contact_email = alt["name"], alt["title"], alt["email"]
                    lead.email_status, lead.contact_profile_url = "published", d.get("url") or ""
                    lead.contact_check = f"email published on {storage.domain_of(lead.website)}; LinkedIn: {why}"
                    lead = OutreachWriterAgent().write_email(lead)
                    storage.save_lead(lead)
                    print(f"        -> switched to {alt['name']} <{alt['email']}> (published + {why}); draft rewritten")
                    verified += 1
                    failing.remove(lead) if lead in failing else None
                else:
                    print(f"        -> {alt['name']} <{alt['email']}> is published but fails LinkedIn: {why}")
            else:
                print("        -> no other published founder email on the site")
    print(f"\n{verified} verified, {len(failing)} not verified.")
    if failing and not args.repoint:
        print("Run again with --repoint to switch a failing lead to another founder whose email the company publishes.")


def cmd_pause(args):
    from agents import guardrails
    guardrails.pause(args.reason or "paused manually")
    print("Sending is PAUSED. Nothing will be emailed until you run: python main.py resume")


def cmd_resume(args):
    from agents import guardrails
    print("Sending resumed." if guardrails.resume() else "Sending was not paused.")
    stats = guardrails.breaker_stats()
    if stats["complaints"] or (stats["bounces"] >= config.BOUNCE_MIN_COUNT and stats["rate"] >= config.BOUNCE_RATE_PAUSE):
        print("Note: the bounce/complaint numbers still exceed the limit, so sending will pause itself again on the next send.")


def cmd_bounce(args):
    from agents import guardrails
    guardrails.record_bounce(args.email, args.reason or "reported manually")
    print(f"Recorded a bounce for {args.email} and added it to the do-not-contact list.")
    reason = guardrails.sending_block_reason()
    if reason:
        print(reason)


def cmd_complaint(args):
    from agents import guardrails
    guardrails.record_complaint(args.email, args.reason or "reported manually")
    print(f"Recorded a complaint from {args.email}. Sending is now PAUSED until you review it and run: python main.py resume")


def cmd_check_bounces(args):
    from agents import guardrails
    try:
        found = guardrails.check_bounces(days=args.days, dry_run=args.dry_run)
    except RuntimeError as exc:
        print(exc)
        return 1
    if not found:
        print("No bounce notices found for emails we sent.")
    for addr, known in found:
        print(f"  {addr}  ({'already recorded' if known else ('would record' if args.dry_run else 'recorded and suppressed')})")
    reason = guardrails.sending_block_reason()
    if reason:
        print(reason)


def cmd_confirm_email(args):
    lead = storage.get_lead(args.lead_id)
    if lead is None:
        print(f"No lead with id {args.lead_id}.")
        return 1
    if args.email:
        lead.contact_email = args.email.strip()
    lead.email_status = "confirmed"
    storage.save_lead(lead)
    print(f"Lead {lead.id} ({lead.company_name}): {lead.contact_email} marked confirmed.")


def cmd_reject(args):
    storage.set_approval_status(args.lead_id, "rejected")
    print(f"Lead {args.lead_id} rejected.")


def cmd_send(args):
    from agents.send_agent import send
    lead = storage.get_lead(args.lead_id)
    if lead is None:
        print(f"No lead with id {args.lead_id}.")
        return 1
    try:
        sent_to = send(lead, to_override=args.to)
    except Exception as exc:
        print(f"Send failed: {exc}")
        return 1
    print(f"Sent lead {lead.id} ({lead.company_name}) to {sent_to}.")


def cmd_send_approved(args):
    from agents.send_agent import send_approved
    try:
        result = send_approved(limit=args.limit, dry_run=args.dry_run)
    except RuntimeError as exc:
        print(f"Not sent: {exc}")
        return 1
    verb = "Would send" if args.dry_run else "Sent"
    print(f"{verb} {len(result['sent'])} email(s):")
    for company, to in result["sent"]:
        print(f"  {company} -> {to}")
    if result["skipped"]:
        print(f"Skipped {len(result['skipped'])}:")
        for company, why in result["skipped"]:
            print(f"  {company}: {why}")


def cmd_suppress(args):
    storage.add_suppression(args.email, args.reason)
    print(f"{args.email} added to the do-not-contact list.")


def cmd_seed_demo(args):
    lead = seed_demo_lead()
    print(f"Seeded sample converted lead: {lead.company_name} (id={lead.id})")
    print("This is fictional demo data (source='demo_sample') - not a real prospect.")


def cmd_reset(args):
    if not args.yes:
        confirm = input(
            "This deletes ALL leads and analytics in output/leads.db. Type 'yes' to continue: "
        )
        if confirm.strip().lower() != "yes":
            print("Aborted - no changes made.")
            return
    storage.reset_all_leads()
    print("All leads and analytics deleted. Database is now empty.")


def main():
    parser = argparse.ArgumentParser(description="Serfis lead-gen agent")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run the full discovery-to-draft pipeline")
    p_run.add_argument("--limit", type=int, default=5)
    p_run.add_argument("--max-lookups", type=int, default=None,
                       help="Cap on paid contact lookups this run (default: MAX_LOOKUPS_PER_RUN)")
    p_run.set_defaults(func=cmd_run)

    p_export = sub.add_parser("export", help="Export current leads to Excel")
    p_export.set_defaults(func=cmd_export)

    p_review = sub.add_parser("review", help="Print leads pending approval")
    p_review.set_defaults(func=cmd_review)

    p_approve = sub.add_parser("approve", help="Approve a lead by id (refuses if guardrails flag it)")
    p_approve.add_argument("lead_id", type=int)
    p_approve.add_argument("--force", action="store_true", help="Approve even though guardrails flagged it")
    p_approve.set_defaults(func=cmd_approve)

    p_audit = sub.add_parser("audit-contacts", help="Re-verify every lead's contact (published email + LinkedIn role); ~$0.004 each")
    p_audit.add_argument("--repoint", action="store_true", help="Switch a failing lead to another founder whose email the company publishes")
    p_audit.set_defaults(func=cmd_audit_contacts)
    p_checks = sub.add_parser("checks", help="Show guardrail status: sending on/paused, bounce rate, flagged leads")
    p_checks.set_defaults(func=cmd_checks)
    p_pause = sub.add_parser("pause", help="Kill switch: stop all real sending")
    p_pause.add_argument("reason", nargs="?", default="")
    p_pause.set_defaults(func=cmd_pause)
    p_resume = sub.add_parser("resume", help="Turn sending back on after a pause")
    p_resume.set_defaults(func=cmd_resume)
    p_bounce = sub.add_parser("bounce", help="Record that an email bounced (suppresses the address)")
    p_bounce.add_argument("email"); p_bounce.add_argument("--reason", default="")
    p_bounce.set_defaults(func=cmd_bounce)
    p_complaint = sub.add_parser("complaint", help="Record a spam complaint (suppresses the address and pauses sending)")
    p_complaint.add_argument("email"); p_complaint.add_argument("--reason", default="")
    p_complaint.set_defaults(func=cmd_complaint)
    p_cb = sub.add_parser("check-bounces", help="Scan the Gmail inbox (IMAP) for delivery-failure notices")
    p_cb.add_argument("--days", type=int, default=7); p_cb.add_argument("--dry-run", action="store_true")
    p_cb.set_defaults(func=cmd_check_bounces)

    p_confirm = sub.add_parser("confirm-email", help="Mark a guessed email as verified (optionally correct it)")
    p_confirm.add_argument("lead_id", type=int)
    p_confirm.add_argument("--email", help="Replace the address with this one")
    p_confirm.set_defaults(func=cmd_confirm_email)

    p_reject = sub.add_parser("reject", help="Reject a lead by id")
    p_reject.add_argument("lead_id", type=int)
    p_reject.set_defaults(func=cmd_reject)

    p_send = sub.add_parser("send", help="Email an approved lead's draft via Gmail")
    p_send.add_argument("lead_id", type=int)
    p_send.add_argument("--to", help="Send here instead of the lead's address (test send)")
    p_send.set_defaults(func=cmd_send)

    p_sa = sub.add_parser("send-approved", help="Email every approved, not-yet-contacted lead")
    p_sa.add_argument("--limit", type=int, help="Send at most this many")
    p_sa.add_argument("--dry-run", action="store_true", help="Show who would be emailed; send nothing")
    p_sa.set_defaults(func=cmd_send_approved)

    p_sup = sub.add_parser("suppress", help="Add an address to the do-not-contact list")
    p_sup.add_argument("email")
    p_sup.add_argument("--reason", default="manual")
    p_sup.set_defaults(func=cmd_suppress)

    p_seed_demo = sub.add_parser("seed-demo", help="Add one fictional sample lead with analytics")
    p_seed_demo.set_defaults(func=cmd_seed_demo)

    p_reset = sub.add_parser("reset", help="Delete ALL leads and analytics")
    p_reset.add_argument("--yes", action="store_true", help="Skip the confirmation prompt")
    p_reset.set_defaults(func=cmd_reset)

    args = parser.parse_args()
    storage.init_db()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
