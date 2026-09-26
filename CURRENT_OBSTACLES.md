# Current Obstacles

Open risks and blockers that need a human decision or real-world action — not code bugs (those live in `QC_AGENT.md` / `DISTRIBUTION_AGENT.md` as "known gaps"). This is a running list; update it as items get resolved or new ones surface.

## Snapchat: not viable — resolved, no action needed

**Closed, not open** — included here for the record since it looked like a normal "not yet built" gap until checked. Verified against Snap's current docs (2026-09-25): there is no way for an unattended backend to post organic content to Snapchat, full stop.

- **Marketing/Ads API** is exclusively for paid ad campaigns — no organic posting endpoint exists.
- **Creative Kit** (Snap Kit) — the other candidate — is client-side only. It opens the Snapchat app on a real person's own device with content pre-filled, and that person has to manually review and hit send themselves inside the app. It cannot be triggered unattended from a server.
- UploadPost's 22+ supported platforms don't include Snapchat either — independent confirmation this isn't just hard to find.

Unlike X or the other platforms on the "not yet built" list, this isn't something more setup work or a different adapter pattern would fix — there's no programmatic surface to build against. Not pursuing Snapchat further unless Snap changes their platform offering.

## Reddit: commercial API terms and content-policy risk

Reddit's Data API Terms distinguish commercial from non-commercial use, and the distinction is about whether the API is used in connection with a business at all — not specifically whether you're serving third-party clients. Two scenarios, both relevant to how this tool might be used:

- **Agency use (posting on behalf of clients)** — plausibly commercial use under Reddit's terms as currently understood. The `SETUP.md` "script app" registration is the free/self-serve path; genuinely commercial use is meant to go through a different arrangement with Reddit. Not yet resolved which category this actually falls into — needs a firsthand read of Reddit's current terms (`redditinc.com/policies/data-api-terms` — this environment is blocked from fetching Reddit's own domains directly, so it hasn't been verified against the live text in this session).
- **Own-company use (posting your own content only)** — still technically business use of the API, but a much smaller volume/risk profile than agency use. Reddit's actual enforcement has historically been volume/rate-driven (aimed at heavy scraping), so low-volume posting for one company likely stays within free-tier limits even though it's not strictly "personal" use.

**Separate from API tier entirely**: Reddit's content policy and individual subreddit rules (commonly known as something like a "10% rule" against self-promotion) apply identically regardless of API commercial classification. An account posting marketing/client video content without genuine community participation risks being removed or banned by subreddit moderators — this is a moderation risk, not an API terms-of-service risk, and it's arguably the more likely thing to actually bite in practice. It applies the same whether the content is a client's or the operating company's own.

**Action needed:** read Reddit's current terms directly, decide honestly which use case applies, and treat Reddit as a platform that needs more human judgment per-post (genuine community fit, not just QC-pass) than the others in this pipeline.

## Pinterest: requires a business account, mandatory app review, and terms worth reading

Pinterest's Developer API (v5, what `PinterestAdapter` uses) requires the connected account to be a **Business account**, not a personal one — same pattern as Instagram's Business/Creator requirement. Conversion is free and instant (Settings → Account settings → Convert to business account), not an approval process, but it's a real prerequisite: a personal account won't authenticate through the OAuth flow in `SETUP.md`/`get_pinterest_token.py`. Not yet verified firsthand against a live account in this session — confirm by just running the OAuth flow, which will either work or prompt for conversion.

Separately: Pinterest access tokens expire (historically ~30 days), and `PinterestAdapter` doesn't currently handle refresh — `get_pinterest_token.py` has to be rerun manually to get a new token when it lapses. Same category of issue as Instagram's 60-day token expiry, just not yet automated for either.

**Mandatory app review — a real gap the original walkthrough missed.** Pinterest's Developer and API Terms of Service, Section 2.3: *"You must submit your application, integration, or interface to Pinterest for review and approval prior to distribution to End Users **or commencement of use**."* Unlike Instagram/Facebook (where review is only required for apps requesting access beyond your own account/Page), this phrasing applies to commencing use at all, not just public distribution. Getting an access token via `get_pinterest_token.py` will work technically; using it beyond initial testing without submitting for Pinterest's review would be a real ToS violation, not just a formality. `SETUP.md` now flags this — actually submitting for review hasn't been done.

**One thing worth knowing, not a problem**: Pinterest's Developer Guidelines explicitly prohibit blanket auto-posting — *"if your app allows end users to schedule Pin publishing, the end user must choose each Pin to be published."* This is a real compliance requirement, and it's already satisfied: the approval gate in `distribute()` (see `DISTRIBUTION_AGENT.md`) requires exactly this — explicit per-post human confirmation, never a blanket auto-approve. Built before this was known to be a Pinterest requirement specifically, not because of it, but it happens to be exactly what Pinterest's terms demand.

Lower relevance for this use case: the data-privacy/CCPA/deletion obligations (Section 4 of their terms) govern *pulling* Pinterest Data (analytics, audience data) back out — since this pipeline only posts, never reads Pinterest Data, these mostly don't apply unless a future Pinterest analytics feature gets added. Same with the "publishing content" linking-back rules, which govern apps that *display* Pinterest content elsewhere, not apps that post content *into* Pinterest.

## X (Twitter): not yet built, real pricing found, decision pending

X isn't implemented yet (no `XAdapter`, native or UploadPost-backed). Initial assumption going in — that X needed an expensive paid subscription tier like the old Free/Basic/Pro system — turned out to be stale. Confirmed via X's current docs (`docs.x.com`) and a pasted excerpt of their live pricing page:

- **X now uses pay-per-usage credits, not subscriptions.** No monthly minimum, no approval process to get write access at all (unlike LinkedIn/TikTok). Fund a credit balance, pay per request.
- **Post: Create costs $0.015/post** (jumps to $0.200 if the post text includes a URL). Other read/interaction operations are fractions of a cent.
- **Unconfirmed**: whether attaching video specifically adds a separate media-upload charge beyond the base per-post cost — the pricing sheet only documents the tweet-creation charge itself.

**Cost comparison, UploadPost vs. native**, depends entirely on whether UploadPost is already in use for LinkedIn/TikTok:
- **Already paying UploadPost's Basic tier (~$16–24/mo) for LinkedIn/TikTok** → adding X there is **$0 marginal cost** (paid tiers include all supported platforms). Native X would mean standing up a second, separate billing relationship with no actual savings.
- **X as the only reason to use UploadPost** → UploadPost's Free tier ($0, but capped at 10 uploads/month *total across all platforms on the account*) vs. native X (~$0.015/post, uncapped, but its own developer account + funded payment method to set up). Native is cheaper in absolute terms at any real volume; UploadPost is simpler/free at very low volume.

**Decision status:** not made — asked the user twice (native vs. UploadPost) and both times the question was dismissed without an answer, so this is genuinely open rather than defaulted. Given LinkedIn/TikTok already route through UploadPost in this codebase, routing X there too is the practical recommendation, but nothing's been built pending an actual decision.

## `.env` / credentials management

Current state: each machine running this code needs its own `.env`, created locally from `.env.example` and filled in by hand (never committed — `.gitignore` covers it, and `distribution_agent/__init__.py` auto-loads it via `load_dotenv()` as of 2026-09-24). This works for a single person on a single machine, but doesn't yet have an answer for:

- **Another teammate's machine** — they'd repeat the same manual setup with their own credentials, or need the same production credentials shared through a password manager (never via git, Slack, or email in plaintext).
- **A real deployment target** (a server, a scheduled job, a PaaS, CI) — `.env` as a file is a local-dev convenience only. A production deployment should set real environment variables through whatever mechanism that platform provides (a cloud secrets manager, a PaaS's config-vars dashboard, GitHub Actions Secrets, `docker run --env-file`, etc.) rather than shipping a `.env` file to that environment at all.
- **No shared secrets vault yet** — if the team ends up needing the same production credentials across multiple people/machines, that's the point where a proper secrets manager (1Password, Doppler, Vault) becomes worth setting up rather than ad hoc file copies.

Nothing broken today, but this is unresolved for any use beyond "one person, one machine."

## Scaling

Several parts of the current design assume low volume and a single human operator; none of this is broken, but each is a real ceiling if usage grows:

- **The approval gate is a hard per-post, per-platform human checkpoint.** That's a deliberate safety choice (see `DISTRIBUTION_AGENT.md`), but it means throughput is bounded by how fast a human can say yes — there's no batch-approval mechanism today. Scaling to many videos/day across many clients would need a real approval UI (a dashboard, a queue), not just a custom `approve` callback.
- **QC scoring is human-in-the-loop (Claude doing visual review), not automated CV**, for hook, branding, safe zone, pacing, and CTA — only duration, resolution, loudness, and technical quality (blur/noise/blockiness) are actually measured by code. Higher video throughput would bottleneck on review time unless those remaining metrics get automated.
- **Per-platform rate limits and token lifecycles get harder to manage at volume** — Instagram's ~60-day token refresh and YouTube's 7-day Testing-mode window are manageable manually for one account each; multiplied across many client accounts (the agency use case), this becomes real operational overhead without an automated refresh job.
- **UploadPost's pricing scales with connected "profiles"** — the free tier caps at 2 profiles and 10 uploads/month; serving multiple clients through UploadPost (LinkedIn/TikTok) means paying for a higher tier as the client count grows (see `SETUP.md` for current pricing).
- **The QC Review Desk dashboard's database has a hard cap of 5,000 documents total** (an artifact database platform limit, not something this project controls) — fine for the current handful of logged evaluations, worth remembering if evaluation volume grows substantially; would need pruning/archiving old evaluations rather than keeping every one forever.
- **No retry/queue infrastructure** — `distribute()` is a synchronous, in-process call with no resumption if the process dies mid-run. Fine for manual/interactive use; not fine for an unattended high-volume pipeline.

None of these need solving now — they're the natural next set of problems once this moves from "one person testing manually" to "a team running this regularly at real volume."
