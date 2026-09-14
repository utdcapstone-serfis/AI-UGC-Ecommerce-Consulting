# Session Log - Serfis Lead Dashboard & Website Setup

A running record of what was built, decided, and fixed in this working session, for your own reference and for anyone else picking this project up.

## What this session covered

1. **Git organization.** Moved the project from a temporary scratch folder to
   `~/Documents/serfis-leadgen` (permanent). Initialized git, wrote a
   `.gitignore` (keeps out `venv/`, `.env`, generated `output/*.db` and
   `*.xlsx`), and committed the working MVP as the baseline. Created two
   branches, `agents-development` and `website-development`, both starting
   from that same baseline commit; `main` stays untouched until you're ready
   for Phase 3 integration.

2. **Real API integrations.**
   - Set up a real **Apollo.io** API key ("Serfis Lead Gen v2", master key
     scope). Fixed three real bugs in the existing code along the way:
     Apollo now requires the key in an `X-Api-Key` header (not the request
     body); one endpoint was renamed (`mixed_people/search` ->
     `mixed_people/api_search`); and getting a real email requires a second
     "enrichment" call (`people/match` with `reveal_personal_emails`), which
     spends an Apollo credit. Discovery and contact-finding both now return
     real companies, names, titles, emails, and LinkedIn URLs.
   - Looked at **Anthropic** (Claude API) setup too. Account created, but no
     credits purchased yet (that step needs your card info, which I can't
     enter on your behalf) - so `ANTHROPIC_API_KEY` is still unset and the
     pipeline runs on its template-based fallback logic instead of
     Claude-written content. Nothing is blocked by this; quality is just
     lower until/unless you add credits.
   - Decided **Hunter.io isn't needed** - it's only a fallback for when
     Apollo can't find a contact, and Apollo alone is already working well.

3. **New feature: Reply drafts / Conversation thread.** You asked for
   ongoing email conversation support. I declined to build it as "fully
   autonomous" (would mean sending/replying to real prospects with no human
   checking each message - conflicts with the human-approval requirement
   this whole project was built around, plus real legal/reputational risk).
   Built instead: `ReplyDraftAgent` (`agents/reply_writer.py`) drafts a
   suggested reply once a human logs what a prospect actually wrote (pasted
   in via the dashboard - no live inbox connection yet). That draft sits at
   `pending_review` in a new `messages` table until a human clicks Approve
   or Reject, on the lead detail page under "Conversation." Nothing is ever
   sent automatically.

4. **Tone/wording fixes**, applied to both the first-touch email and reply
   drafts, in both the Claude prompts and the no-LLM template fallbacks:
   - No phone calls, meetings, or demos suggested anywhere - email-only.
   - No self-description as "an autonomous AI" or "an AI pipeline" - reads
     as robotic. Rewritten to sound like a person at Serfis, focused on the
     benefit to the prospect.
   - Closes on a warm "reply if you have questions" note instead of a hard
     ask.

## A mistake worth flagging

Mid-session, while trying to clear out some test conversation messages, I
accidentally ran a full database reset that deleted 9 real leads we'd found
via Apollo (including 3 with real contacts: Jobgether, avua, Crossing
Hurdles). That data wasn't recoverable (no backup, not in git - it's
runtime-generated data, correctly gitignored). It's fully regenerable by
re-running the pipeline, but the specific companies/contacts from that
batch are gone. I'm noting it here so it's not a surprise later.

## Current state of the database (as of this log)

Run `python main.py review` or open the dashboard to see current leads -
this file won't stay in sync with that, it's a snapshot of decisions, not
live data.

## What's still open / not built

- Live inbox connection (Gmail API or IMAP) to auto-detect prospect replies,
  instead of pasting them in manually.
- Actually sending anything (`agents/send_agent.py` is still an intentional,
  unwired stub).
- Anthropic credits not yet purchased - pipeline runs on template fallbacks.
- `main` branch integration (Phase 3) - hasn't happened yet, by design.

## Where things live

- Project folder: `~/Documents/serfis-leadgen`
- Run the pipeline: `python main.py run --limit N`
- Run the dashboard: `python app.py`, then open `http://localhost:5050`
- Full technical detail on every feature: see `README.md` in this folder.
