"""Tests for the verified-contact rule (LinkedIn role check, explicit-email extraction, enforcement, error handling).

Run from the repo root:  python tests/test_verified.py
Every test uses a throwaway database in a temp folder; nothing touches output/leads.db and nothing is billed (Apify is mocked).
"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # repo root
import config
tmp = Path(tempfile.mkdtemp()); config.OUTPUT_DIR = tmp; config.DB_PATH = tmp / "t.db"
config.DEMO_MODE = False; config.APIFY_API_TOKEN = "x"
import storage; storage.init_db()
from agents import linkedin, site_emails, contact_finder as cf
from models import Lead

passed = failed = 0
def ok(name, cond, detail=""):
    global passed, failed
    if cond: passed += 1; print("  PASS", name)
    else: failed += 1; print("  FAIL", name, detail)

def profile(**kw):
    p = {"firstName": "Paul", "lastName": "Witten", "headline": "Cofounder/CEO at Tire Swing", "linkedinUrl": "https://www.linkedin.com/in/paul-witten",
         "currentPosition": [{"position": "Founder/CEO", "companyName": "Tire Swing", "companyUniversalName": "tire-swing", "endDate": {"text": "Present"}}],
         "location": {"countryCode": "US", "parsed": {"text": "New York City, NY, United States"}}, "emails": [], "about": "", "experience": []}
    p.update(kw); return p
lead = Lead(company_name="Tire Swing", website="https://gettireswing.com", contact_name="Paul Witten", contact_title="Founder/CEO")

print("EXPLICIT EMAIL on the LinkedIn page")
ok("email written in About is found", linkedin.explicit_emails(profile(about="Say hi: paul@gettireswing.com")) == ["paul@gettireswing.com"])
ok("obfuscated 'name [at] domain' is found", linkedin.explicit_emails(profile(about="paul [at] gettireswing.com")) == ["paul@gettireswing.com"])
ok("email in a role description is found", linkedin.explicit_emails(profile(experience=[{"description": "reach me at paul@x.io"}])) == ["paul@x.io"])
ok("generic hello@ ignored", linkedin.explicit_emails(profile(about="hello@gettireswing.com")) == [])
ok("the tool's own 'emails' field is NEVER used (that is its guesser)",
   linkedin.explicit_emails(profile(emails=[{"email": "paul.witten@gettireswing.com", "status": "risky"}])) == [])
ok("no email anywhere -> nothing", linkedin.explicit_emails(profile()) == [])

print("ROLE CHECK")
ok("current founder at the company passes", linkedin.verify_role(profile(), lead)[0])
ok("company slug 'tire-swing' matches domain 'gettireswing'", linkedin.verify_role(profile(currentPosition=[{"position": "CEO", "companyName": "Something Else", "companyUniversalName": "tire-swing"}]), lead)[0])
ok("left the company (end date) fails", not linkedin.verify_role(profile(currentPosition=[{"position": "CEO", "companyName": "Tire Swing", "endDate": {"text": "Mar 2026"}}]), lead)[0])
ok("works elsewhere fails", not linkedin.verify_role(profile(currentPosition=[{"position": "CEO", "companyName": "Acme", "endDate": {"text": "Present"}}]), lead)[0])
ok("non-decision title fails", not linkedin.verify_role(profile(currentPosition=[{"position": "Marketing Associate", "companyName": "Tire Swing", "endDate": {"text": "Present"}}]), lead)[0])
ok("wrong person fails", not linkedin.verify_role(profile(firstName="Zed", lastName="Quark"), lead)[0])
ok("empty profile fails", not linkedin.verify_role(None, lead)[0])
ok("nickname spelling (Sirsho/Sirsha) tolerated", linkedin.verify_role(profile(firstName="Sirsha", lastName="Chakraborty"),
   Lead(company_name="Tire Swing", website="https://gettireswing.com", contact_name="Sirsho Chakraborty"))[0])

print("ENFORCEMENT in the contact finder (LinkedIn mocked, no spend)")
agent = cf.ContactFinderAgent()
_real_check_contact = linkedin.check_contact
def L(status, **kw):
    return Lead(company_name="Tire Swing", website="https://gettireswing.com", contact_name="Paul Witten", contact_title="Founder/CEO",
                contact_email="paul@gettireswing.com", email_status=status, yc_profile_url="", **kw)
linkedin.check_contact = lambda l: (True, "confirmed Founder/CEO at Tire Swing (current)", {"title": "Founder/CEO", "url": "https://www.linkedin.com/in/paul-witten", "place": "New York City, NY, United States"})
r = agent._enforce(L("published"))
ok("published + LinkedIn ok -> kept", r.has_email() and "published on gettireswing.com" in r.contact_check and "LinkedIn" in r.contact_check, r.contact_check)
ok("LinkedIn profile URL saved", r.contact_profile_url.endswith("paul-witten"))
ok("blank location filled from LinkedIn", r.location.startswith("New York"))
r = agent._enforce(L("linkedin"))
ok("email from LinkedIn page -> kept and labelled", r.has_email() and "LinkedIn profile" in r.contact_check, r.contact_check)
for bad in ("found", "guessed", ""):
    r = agent._enforce(L(bad))
    ok(f"status {bad or 'blank'!r} (provider / guess) -> rejected", not r.has_email() and agent.last_outcome == "unverified")
linkedin.check_contact = lambda l: (False, "LinkedIn does not show a current role at Tire Swing", {})
r = agent._enforce(L("published"))
ok("published but LinkedIn role fails -> rejected", not r.has_email() and "LinkedIn" in agent.errors[-1], agent.errors[-1])
linkedin.check_contact = lambda l: (_ for _ in ()).throw(AssertionError("must not call LinkedIn for human-confirmed"))
r = agent._enforce(L("confirmed"))
ok("human-confirmed contact is kept without a paid check", r.has_email() and "confirmed by a person" in r.contact_check)

linkedin.check_contact = _real_check_contact
print("CACHE: a profile is never paid for twice")
calls = []
import agents.linkedin as li
li.run_actor = lambda actor, inp, max_charge_usd=None: calls.append(inp.get("username") or inp.get("urls")) or [{"basic_info": {"first_name": "Paul", "last_name": "Witten", "headline": "CEO", "about": "mail me paul@gettireswing.com", "profile_url": "https://linkedin.com/in/paul-witten", "location": {"country_code": "US", "full": "New York, New York, United States"}, "email": "guess@x.com"}, "experience": [{"title": "Founder/CEO", "company": "Tire Swing", "is_current": True, "description": ""}]}]
li._CACHE.clear(); li.paid_reads = 0
li.fetch_profile("https://www.linkedin.com/in/paul-witten"); li.fetch_profile("https://www.linkedin.com/in/paul-witten/")
ok("second read of the same profile is free", len(calls) == 1 and li.paid_reads == 1, (calls, li.paid_reads))
ok("actor runs in the no-email mode", config.LINKEDIN_MODE.startswith("Profile details no email"))
ok("username parsed from the profile URL", li._username("https://www.linkedin.com/in/paul-witten/?x=1") == "paul-witten")
prof = li.fetch_profile("https://www.linkedin.com/in/paul-witten")
ok("apimaestro profile normalised (name, current role, country)", prof["firstName"] == "Paul" and prof["currentPosition"][0]["companyName"] == "Tire Swing" and prof["location"]["countryCode"] == "US")
ok("role check works on the normalised profile", li.verify_role(prof, lead)[0])
ok("email written in About is read from the normalised profile", li.explicit_emails(prof) == ["paul@gettireswing.com"])
ok("actor's own basic_info.email guess is never used", "guess@x.com" not in li.explicit_emails(prof))
print("ERROR HANDLING")
li._CACHE.clear(); li._blocked = ""
li.run_actor = lambda actor, inp, max_charge_usd=None: [{"error": "Free users are limited to 50 runs. Please upgrade to a paid plan to run more."}]
ok_, why, _ = li.check_contact(Lead(company_name="Tire Swing", website="https://gettireswing.com", contact_name="Paul Witten", contact_profile_url="https://www.linkedin.com/in/paul-witten"))
ok("plan-limit error is reported as such (not 'no profile')", (not ok_) and "limited to 50 runs" in why, why)
n = li.paid_reads
li.check_contact(Lead(company_name="X", website="https://x.com", contact_name="A B", contact_profile_url="https://www.linkedin.com/in/ab"))
ok("after a plan limit, the actor is not called again", li.paid_reads == n)
li._blocked = ""
li._CACHE.clear()
li.run_actor = lambda actor, inp, max_charge_usd=None: [{"profile_input": "x", "message": "Daily free-tier limit of 20 profiles reached. Upgrade your Apify plan or wait until tomorrow."}]
ok_, why, det = li.check_contact(Lead(company_name="Fort", website="https://fort.com", contact_name="A B", contact_profile_url="https://www.linkedin.com/in/ab"))
ok("a daily-limit 'message' is reported as the real cause and marked transient", (not ok_) and "Daily free-tier limit" in why and det.get("transient"), (why, det))
ok("empty profile is transient (not a verdict on the company)", li.verify_role(None, lead)[2].get("transient"))
li._blocked = ""
print(f"\n{passed} passed, {failed} failed"); sys.exit(1 if failed else 0)
