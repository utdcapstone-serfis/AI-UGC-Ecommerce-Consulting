"""Tests for the guardrails (draft check, region, bounce breaker, one-touch cooldown, approve route, bounce parsing).

Run from the repo root:  python tests/test_guardrails.py
Every test uses a throwaway database in a temp folder; nothing touches output/leads.db and nothing is billed (Apify is mocked).
"""
import sys, tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # repo root
import config
tmp = Path(tempfile.mkdtemp())
config.OUTPUT_DIR = tmp
config.DB_PATH = tmp / "t.db"
config.GMAIL_ADDRESS = "x@example.com"; config.GMAIL_APP_PASSWORD = "x"; config.HAS_GMAIL = True
config.MAILING_ADDRESS = "1 Test St"
import storage
storage.init_db()
from agents import guardrails as g, send_agent
from models import Lead

passed = failed = 0
def ok(name, cond, detail=""):
    global passed, failed
    if cond: passed += 1; print("  PASS", name)
    else: failed += 1; print("  FAIL", name, detail)

GOOD_BODY = ("Hi Paul,\n\nI came across Tire Swing and really liked what you're building for affordable housing compliance teams.\n\n"
             "At Serfis AI, we create short-form video advertisements and social content designed for platforms including TikTok, Instagram, "
             "YouTube, Reddit, X, and Pinterest. Social media moves quickly, and staying on top of emerging trends can help brands remain "
             "relevant, capture attention, and create more opportunities to reach their target audience. We help businesses consistently "
             "produce fresh creative that fits the style and audience of each platform rather than relying on the same content everywhere.\n\n"
             "I had a few ideas for how Tire Swing could turn certification workflows into engaging social content. Would you be open to me "
             "sending over a couple of concepts?\n\nBest,\nAllison\nSerfis AI")
def mk(**kw):
    base = dict(company_name="Tire Swing", website="https://gettireswing.com", contact_name="Paul Witten", contact_email="paul@gettireswing.com",
                location="New York City, NY, USA", draft_email_subject="Short-form video ideas for Tire Swing", draft_email_body=GOOD_BODY,
                research_notes="Y Combinator Fall 2026, team of 2", approval_status="approved", email_status="published")
    base.update(kw); return Lead(**base)

print("1. DRAFT QUALITY")
ok("clean draft passes", g.check_draft(mk()) == [], g.check_draft(mk()))
ok("placeholder caught", any("placeholder" in i for i in g.check_draft(mk(draft_email_body=GOOD_BODY.replace("Tire Swing could", "[Company] could")))))
ok("NEEDS_ENRICHMENT caught", any("placeholder" in i for i in g.check_draft(mk(draft_email_body=GOOD_BODY + " NEEDS_ENRICHMENT"))))
ok("too short caught", any("words" in i for i in g.check_draft(mk(draft_email_body="Hi Paul, Tire Swing is great. Best, Allison"))))
ok("wrong first name caught", any("first name" in i for i in g.check_draft(mk(draft_email_body=GOOD_BODY.replace("Hi Paul", "Hi Sam")))))
ok("missing company caught", any("company by name" in i for i in g.check_draft(mk(draft_email_body=GOOD_BODY.replace("Tire Swing", "your company")))))
ok("call ask caught", any("meeting" in i or "call" in i for i in g.check_draft(mk(draft_email_body=GOOD_BODY.replace("sending over a couple of concepts", "hopping on a quick call")))))
ok("'aI native' garble caught", any("garbled" in i for i in g.check_draft(mk(draft_email_body=GOOD_BODY.replace("certification workflows", "aI native certification workflows")))))
ok("'Serfis AI' is NOT a false garble", not any("garbled" in i for i in g.check_draft(mk())))
ok("unsupported claim caught", any("claim" in i for i in g.check_draft(mk(draft_email_body=GOOD_BODY.replace("engaging social content", "content that boosts sales by 300%")))))
ok("supported claim allowed", not any("claim" in i for i in g.check_draft(mk(draft_email_body=GOOD_BODY.replace("engaging social content", "content that grows 300%"), research_notes="grew 300% last year"))))
ok("no draft caught", g.check_draft(mk(draft_email_subject="", draft_email_body="")) == ["there is no drafted email"])

print("4. REGION")
for loc, want in [("San Francisco, CA, USA", "us"), ("New York City, NY, USA", "us"), ("Austin, TX", "us"), ("Denmark, WI, USA", "us"),
                  ("Germany", "strict"), ("Paris, France", "strict"), ("London, UK", "strict"), ("Toronto, ON, Canada", "strict"),
                  ("San Francisco", "us"), ("New York City, NY", "us"), ("Bangalore, India", "other"), ("", "unknown")]:
    ok(f"region {loc!r} -> {want}", g.classify_region(loc) == want, g.classify_region(loc))
ok("strict region flagged", bool(g.region_issues(mk(location="Germany"))))
ok("US region clear", g.region_issues(mk()) == [])
ok("unknown location + .de site hints strict", "ends in .de" in " ".join(g.region_issues(mk(location="", website="https://x.de"))))

print("override logic")
l = mk(location="Germany")
ok("flagged lead is blocking", [c for c, _ in g.blocking(l)] == ["region"])
l.overrides = "region"
ok("acknowledged flag stops blocking", g.blocking(l) == [])
ok("summary says reviewed", g.summary(l)[0] == "reviewed")
ok("summary ok for clean", g.summary(mk())[0] == "ok")

print("2. BOUNCE BREAKER + KILL SWITCH")
ok("not paused initially", g.sending_block_reason() is None)
a = storage.save_lead(mk(company_name="A", website="https://a.com", contact_email="x@a.com"))
for i in range(10): storage.log_send(a.id, f"u{i}@c{i}.com", "s")
g.record_bounce("u0@c0.com", "test")
ok("one bounce does not trip (min count 2)", g.sending_block_reason() is None)
g.record_bounce("u1@c1.com", "test")
r = g.sending_block_reason()
ok("2 bounces of 10 sends (20%) trips", bool(r) and "paused" in r, r)
ok("pause flag file written", (tmp / "SENDING_PAUSED").exists())
ok("breaker stays tripped", g.sending_block_reason() is not None)
ok("bounced addresses suppressed", storage.is_suppressed("u0@c0.com"))
b = storage.save_lead(mk(company_name="B", website="https://b.com", contact_email="b@b.com"))
ok("blocker refuses while paused", "paused" in (send_agent.blocker(b) or ""), send_agent.blocker(b))
ok("send_approved refuses while paused", send_agent.send_approved(dry_run=True)["skipped"][0][0] == "ALL LEADS")
ok("resume works", g.resume() is True and g.pause_reason() is None)
ok("still trips again (numbers unchanged)", g.sending_block_reason() is not None)
g.resume()
# complaint
g.record_complaint("angry@x.com", "spam")
ok("complaint pauses sending", g.pause_reason() and "complaint" in g.pause_reason())
g.resume()

print("   manual kill switch")
g.pause("testing")
ok("manual pause blocks", "paused" in (g.sending_block_reason() or ""))
g.resume()

print("3. ONE TOUCH PER COMPANY")
# fresh DB state for breaker so it doesn't interfere
config.DB_PATH = tmp / "t2.db"; storage.init_db()
s1 = storage.save_lead(mk(company_name="Comena", website="https://comena.ai", contact_email="jiehua@comena.ai", location="Germany", overrides="region"))
s2 = storage.save_lead(mk(company_name="Comena Labs", website="https://comena.ai", contact_email="almo@comena.ai", location="Germany", overrides="region"))
ok("before any send: clear", g.company_cooldown(s2) is None)
storage.log_send(s1.id, "jiehua@comena.ai", "s")
c = g.company_cooldown(s2)
ok("second founder at same company blocked", bool(c) and "comena.ai" in c, c)
ok("same lead is not blocked by its own send", g.company_cooldown(s1) is None)
ok("blocker reports cooldown", "already emailed" in (send_agent.blocker(s2) or ""), send_agent.blocker(s2))
other = storage.save_lead(mk(company_name="Other", website="https://other.io", contact_email="o@other.io"))
ok("different company not blocked", g.company_cooldown(other) is None)
with storage.get_conn() as conn:    # age the send to 91 days ago
    conn.execute("UPDATE sent_log SET sent_at=?", ((datetime.now() - timedelta(days=91)).isoformat(),))
ok("after 90 days allowed again", g.company_cooldown(s2) is None)

print("blocker end-to-end")
good = storage.save_lead(mk(company_name="Good Co", website="https://good.io", contact_email="p@good.io", draft_email_body=GOOD_BODY.replace("Tire Swing", "Good Co"),
                            draft_email_subject="Short-form video ideas for Good Co"))
ok("clean, US, approved lead passes the blocker", send_agent.blocker(good) is None, send_agent.blocker(good))
bad = storage.save_lead(mk(company_name="Bad Co", website="https://bad.io", contact_email="p@bad.io", draft_email_body="Hi Paul [Company]"))
ok("flagged lead blocked at send time", "flagged by the draft check" in (send_agent.blocker(bad) or ""), send_agent.blocker(bad))
bad.overrides = "draft"
ok("acknowledged flag lets it through", send_agent.blocker(bad) is None, send_agent.blocker(bad))

print("DASHBOARD approve route")
import app as appmod
cl = appmod.app.test_client()
flagged = storage.save_lead(mk(company_name="Flag Co", website="https://flag.eu", contact_email="p@flag.eu", location="Paris, France", approval_status="pending_review",
                                draft_email_body=GOOD_BODY.replace("Tire Swing", "Flag Co"), draft_email_subject="Short-form video ideas for Flag Co"))
cl.post(f"/lead/{flagged.id}/approve")
ok("approve without override is refused", storage.get_lead(flagged.id).approval_status == "pending_review")
cl.post(f"/lead/{flagged.id}/approve", data={"override": "1"})
after = storage.get_lead(flagged.id)
ok("approve anyway works and records it", after.approval_status == "approved" and "region" in after.overrides, (after.approval_status, after.overrides))
page = cl.get(f"/lead/{flagged.id}").get_data(as_text=True)
ok("lead page shows guardrail panel", "Guardrail Checks" in page and "Reviewed" in page)
clean = storage.save_lead(mk(company_name="Clean Co", website="https://clean.io", contact_email="p@clean.io", approval_status="pending_review",
                             draft_email_body=GOOD_BODY.replace("Tire Swing", "Clean Co"), draft_email_subject="Short-form video ideas for Clean Co"))
cl.post(f"/lead/{clean.id}/approve")
ok("clean lead approves normally", storage.get_lead(clean.id).approval_status == "approved")
home = cl.get("/").get_data(as_text=True)
ok("list shows Checks column", "Checks" in home and ("Clear" in home or "Reviewed" in home))
g.pause("banner test")
ok("paused banner shows on list", "Sending is paused" in cl.get("/").get_data(as_text=True))
g.resume()

print("BOUNCE NOTICE PARSING (synthetic Gmail-style DSN)")
dsn = b"""From: Mail Delivery Subsystem <mailer-daemon@googlemail.com>
To: me@example.com
Subject: Delivery Status Notification (Failure)
MIME-Version: 1.0
Content-Type: multipart/report; report-type=delivery-status; boundary="b1"

--b1
Content-Type: text/plain; charset="UTF-8"

Address not found.

--b1
Content-Type: message/delivery-status

Reporting-MTA: dns; googlemail.com

Final-Recipient: rfc822; Nobody@Bounced-Co.com
Action: failed
Status: 5.1.1

--b1--
"""
ok("permanent failure parsed", g.parse_bounced_recipients(dsn) == ["nobody@bounced-co.com"], g.parse_bounced_recipients(dsn))
soft = dsn.replace(b"Status: 5.1.1", b"Status: 4.2.2")
ok("temporary failure ignored", g.parse_bounced_recipients(soft) == [])

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
