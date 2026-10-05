"""CLI entrypoint.

Usage:
    python main.py run --limit 5          # run the pipeline, save to SQLite
    python main.py export                 # export current DB to Excel
    python main.py review                 # print pending leads for review
    python main.py approve <id>           # mark a lead approved
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
    leads = pipeline.run(limit=args.limit)
    print(f"Processed {len(leads)} leads.")
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
    storage.set_approval_status(args.lead_id, "approved")
    print(f"Lead {args.lead_id} approved.")


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
    p_run.set_defaults(func=cmd_run)

    p_export = sub.add_parser("export", help="Export current leads to Excel")
    p_export.set_defaults(func=cmd_export)

    p_review = sub.add_parser("review", help="Print leads pending approval")
    p_review.set_defaults(func=cmd_review)

    p_approve = sub.add_parser("approve", help="Approve a lead by id")
    p_approve.add_argument("lead_id", type=int)
    p_approve.set_defaults(func=cmd_approve)

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
