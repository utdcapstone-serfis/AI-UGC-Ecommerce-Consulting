# Distribution Agent — Source of Truth

The single reference for what this agent actually does today. If this
file and the code ever disagree, **the code is right** — update this
file to match, not the reverse.

## Scope

Publishes a QC-approved video to one or more social platforms,
verifies it actually went live, and emails the client POC a
confirmation. Never runs on a video that hasn't already passed the
Quality Control Agent (see `QC_AGENT.md`).

## The one invariant: approval before posting

`distribute()` in `distribution_agent/distribution_agent.py` calls
`approve(platform, asset)` before every single upload. No approval
means no post — full stop:

- No flag or setting bypasses this.
- An unapproved platform is skipped entirely — its adapter is never
  even instantiated, so no credentials are touched and no API request
  is made for it.
- The default `cli_approval()` prompts on the terminal and **fails
  safe (denies)** on anything short of an explicit "y" — including a
  non-interactive terminal, silence, or EOF. It never crashes and
  never defaults to yes.
- To wire approval to something other than a terminal prompt (a
  dashboard button, a Slack confirmation), pass a custom
  `approve: (platform, asset) -> bool` callable to `distribute()`.

## Supported platforms

| Platform | Adapter | Credentials (env vars) | Setup effort | Expiry behavior |
|---|---|---|---|---|
| Bluesky | `adapters/bluesky.py` | `BLUESKY_IDENTIFIER`, `BLUESKY_APP_PASSWORD` | Simplest — one App Password, no dev app or review | App Passwords don't expire on a timer |
| Reddit | `adapters/reddit.py` | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`, `REDDIT_USER_AGENT`, `REDDIT_SUBREDDIT` | Register a "script" app, no review | Re-authenticates every run; watch for Reddit deprecating password-grant apps |
| YouTube | `adapters/youtube.py` | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | Google Cloud project + one-time OAuth consent | Refresh token is long-lived **only once the app is out of "Testing" mode** — just 7 days while still in Testing |
| Facebook | `adapters/facebook.py` | `FB_PAGE_ACCESS_TOKEN`, `FB_PAGE_ID` | Meta Developer App + Page access token | Page token is effectively permanent unless revoked |
| Instagram | `adapters/instagram.py` | `IG_ACCESS_TOKEN`, `IG_BUSINESS_ACCOUNT_ID` | Meta Developer App + Business/Creator account + linked Page — the most setup steps of the five | Long-lived token expires **~60 days** — must be refreshed before it lapses, or the OAuth consent flow has to be redone from scratch |

Full step-by-step credential setup for each platform:
`SETUP.md`.

## `VideoAsset` contract

Defined in `distribution_agent/adapters/base.py`:

- `local_path` — required by YouTube, Reddit, Bluesky (they upload the
  file directly).
- `public_url` — required by Instagram (the Graph API fetches the
  video server-side, it can't accept a local file); Facebook accepts
  either `local_path` or `public_url`.

## Output

One `DistributionRecord` per platform: `platform`, `approved`,
`post_id`, `url`, `is_live`, `poc_notified`. `is_live` is only set
after `verify_live()` re-fetches the post from the platform itself — a
successful upload response alone doesn't count as confirmation.

## Not yet built

Other platforms considered but not implemented, ranked easiest →
hardest to add next based on setup friction: Pinterest, Threads,
LinkedIn (gated behind a partner-approval process for posting as an
org page), Snapchat (built around the Ads API, not organic posting),
Twitter/X (meaningful write access needs a paid API tier), TikTok
(slowest — the Content Posting API requires a formal app audit that
can take days to weeks).

## Related files

- Prompt spec: `agent-prompts.md` (section 2)
- Implementation: `distribution_agent/`
- Credential setup walkthrough: `SETUP.md`
