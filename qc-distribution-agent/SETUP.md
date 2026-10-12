# Distribution Agent — Platform Setup

Each platform requires you to obtain credentials yourself (OAuth
consent has to be granted by a logged-in human — this can't be
scripted). Once you have them, put them in `.env` (copy from
`.env.example`) and never commit that file.

## Instagram

1. Convert the target account to a **Business or Creator** account
   (Instagram app → Settings → Account type).
2. Link it to a **Facebook Page** (any minimal Page works).
3. Create a Meta Developer App at https://developers.facebook.com,
   add the **Instagram Graph API** product.
4. Run the OAuth flow yourself (Graph API Explorer or your app's login
   flow) granting `instagram_basic` and `instagram_content_publish`,
   then exchange for a **long-lived token**
   (`GET /oauth/access_token?grant_type=fb_exchange_token...`).
5. Fill in `IG_ACCESS_TOKEN` and `IG_BUSINESS_ACCOUNT_ID`.

Note: `InstagramAdapter.upload()` needs a **publicly reachable video
URL** (`VideoAsset.public_url`), not a local file — the Graph API
fetches the video from that URL itself.

## Facebook

1. Same Meta Developer App as above.
2. Get a **long-lived Page access token** (steps below). A token made the quick
   way, by picking the Page directly in Graph API Explorer, comes from a
   short-lived user token and stops working within hours (error 190, "the session
   is invalid because the user logged out").
3. Fill in `FB_PAGE_ACCESS_TOKEN` and `FB_PAGE_ID`. Edit `.env` in your editor.
   Never paste tokens or the app secret into chat, screenshots or the repo.

`FacebookAdapter.upload()` accepts either `VideoAsset.local_path` or
`VideoAsset.public_url`.

### Getting a long-lived Page token

The app can stay in Development mode. You need a role on the app (admin,
developer or tester) and admin access to the Page. Run the commands in your own
PowerShell window, in any folder.

1. **Short-lived user token.** Open developers.facebook.com/tools/explorer, choose
   the app, and in the "User or Page" dropdown choose **Get User Access Token**
   (not the Page entry). Make sure these permissions are listed:
   `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`. Click
   **Generate Access Token**, sign in, and tick the Page when asked which Pages to
   allow. The token appears in the Access Token box and lasts about an hour.
2. **Long-lived user token (about 60 days).** The app ID and app secret are in
   App settings, Basic. This copies the token to the clipboard without printing it:
   ```powershell
   $appId = Read-Host "App ID"
   $secret = Read-Host "App secret"
   $short = Read-Host "Short-lived token"
   $r = Invoke-RestMethod "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=$appId&client_secret=$secret&fb_exchange_token=$short"
   $r.access_token | Set-Clipboard
   "Copied. Length: " + $r.access_token.Length
   ```
   Do not print the token to the screen: PowerShell cuts long values off with
   "...", and a cut-off token does not work.
3. **Page token (does not expire on a timer).** Paste the long-lived token when asked:
   ```powershell
   $long = Read-Host "Long-lived user token (paste from clipboard)"
   $pages = (Invoke-RestMethod "https://graph.facebook.com/v19.0/me/accounts?access_token=$long").data
   $pages | ForEach-Object { $_.name + "  id=" + $_.id }
   $p = $pages | Where-Object { $_.name -eq "Serfis" }   # change to your Page's name
   $p.access_token | Set-Clipboard
   "Copied. Length: " + $p.access_token.Length
   ```
   The printed `id` is `FB_PAGE_ID`; the clipboard holds `FB_PAGE_ACCESS_TOKEN`. An
   empty list means the Page wasn't ticked in step 1, so repeat it.
4. **Check it.** Paste the Page token into the Access Token Debugger
   (developers.facebook.com/tools/debug/accesstoken). It should show **Type: Page**,
   **Expires: Never** and the three scopes. A date means it came from a short-lived
   token.

A Page token can still stop working if the user logs out everywhere, changes their
password, or removes the app from their account, so "never expires" means no timer,
not permanent. If the app ever goes Live, Meta's App Review and the app icon, privacy
policy URL and category fields apply; for posting to your own Page in Development
mode they are not needed.

## Threads

1. Same Meta Developer App as Facebook/Instagram — add the **Threads API** product to it.
2. Run the OAuth flow yourself, granting `threads_basic` and `threads_content_publish`.
3. Fill in `THREADS_ACCESS_TOKEN` and `THREADS_USER_ID` — this is a **separate id from the Instagram Business Account ID**, even though it's tied to the same underlying account.

Like Instagram, `ThreadsAdapter.upload()` needs a **publicly reachable video URL** (`VideoAsset.public_url`), not a local file. A container that isn't published within 24 hours expires and has to be recreated — not a concern for normal use, but worth knowing if a post gets stuck for other reasons.

## YouTube

1. Create a Google Cloud project, enable **YouTube Data API v3**.
2. Create an OAuth 2.0 Client ID (Desktop app type is simplest).
3. Run the OAuth consent flow once, locally, with scope
   `https://www.googleapis.com/auth/youtube.upload`, to get a
   **refresh token** (e.g. via `google-auth-oauthlib`'s
   `InstalledAppFlow.run_local_server()`).
4. Fill in `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

New Google Cloud projects start in **testing mode** with a small quota
— request production access before relying on this for real traffic.

## Reddit

1. Register an app at https://www.reddit.com/prefs/apps (type:
   "script").
2. Fill in `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`,
   `REDDIT_USERNAME`, `REDDIT_PASSWORD`, `REDDIT_USER_AGENT`,
   `REDDIT_SUBREDDIT`.

Reddit has been tightening password-grant OAuth for third-party apps —
if `RedditAdapter` stops authenticating, check current Reddit API docs
and switch to the web-app OAuth code flow.

## Bluesky

The simplest of the bunch — no developer app, no review process.

1. In the Bluesky app: **Settings → App Passwords → Add App Password**.
2. Fill in `BLUESKY_IDENTIFIER` (your handle, e.g. `you.bsky.social`, or the email on the account) and `BLUESKY_APP_PASSWORD`.
3. **Confirm the account's email** (Settings → Email) if you haven't already. Video upload specifically fails with a 401 `unconfirmed_email` otherwise — found by actually running this against a real account, not documented anywhere obvious up front.

`BLUESKY_SERVICE` is optional — only set it if you're on a self-hosted Personal Data Server instead of the default `bsky.social`.

Note: video posting on AT Protocol requires the video to finish server-side processing before it can be attached to a post — `BlueskyAdapter.upload()` handles the upload-then-poll flow internally, but it does mean a Bluesky post can take a little longer to go through than the other platforms.

## Pinterest

1. Create a Pinterest Developer app at https://developers.pinterest.com.
2. Run the OAuth flow yourself, granting `pins:write` and `boards:read`.
3. Find the target board's id (`GET /v5/boards`, or from the board's URL) and fill in `PINTEREST_ACCESS_TOKEN` and `PINTEREST_BOARD_ID`.
4. **Submit the app to Pinterest for review before relying on it beyond initial testing.** Their Developer Terms require review and approval "prior to distribution to End Users or commencement of use" — this isn't optional for production use, even for posting to a single business's own account. See `CURRENT_OBSTACLES.md` for the full note; this step wasn't in earlier versions of this walkthrough and is a real gap, not a formality to skip.

`PinterestAdapter.upload()` requires `VideoAsset.local_path` — it uploads the file directly and generates the required cover image itself (the video's own first frame) rather than needing you to host a separate thumbnail.

## X (Twitter)

Native, not via UploadPost — X has no approval gate at all (unlike LinkedIn/TikTok), just a real per-request cost. See `CURRENT_OBSTACLES.md` for the full pricing breakdown and why native won out over UploadPost for this one.

1. Go to **developer.x.com**, create a **confidential client** ("Web App, Automated App or Bot" type — needs both a Client ID and Client Secret, unlike a "public" client which only gets an ID).
2. Fund a credit balance for the app (pay-per-usage — no subscription, but posting won't work with a zero balance).
3. Set the app's callback/redirect URL to exactly `http://localhost:8766/callback`.
4. Fill in `X_CLIENT_ID` and `X_CLIENT_SECRET` in `.env`.
5. Run `python get_x_token.py` yourself — same pattern as YouTube/Pinterest: it opens your browser, you approve, and it prints a refresh token in your own terminal for you to copy into `.env` as `X_REFRESH_TOKEN`.

Note: X's docs don't say whether refresh tokens rotate (a new one issued each time the old one's used, invalidating it). `XAdapter` handles this defensively — if a refresh ever returns a new token, it's written back into `.env` automatically, so this shouldn't silently break even if rotation turns out to be real.

`XAdapter.upload()` requires `VideoAsset.local_path` — it does a full chunked upload (INIT/APPEND/FINALIZE) directly to X, then polls for video processing before posting.

## LinkedIn

Native, as of 2026-10-01. Posts to a **personal profile**, not a Company Page — see `CURRENT_OBSTACLES.md` for why (Company Page creation needs a connections/profile-strength threshold on the account that wasn't met, and a LinkedIn developer app can't even be created without a Page attached either way).

1. Go to **linkedin.com/developers/apps**, click "Create app." It requires a LinkedIn Page even for member-scope posting — attach whichever one the app is associated with.
2. Under the app's **Products**, add **"Share on LinkedIn"** — this is self-serve, no partner review needed (confirmed via `developer.linkedin.com/documents/share-api`).
3. Run the OAuth 2.0 three-legged consent flow yourself, granting `w_member_social`.
4. Fill in `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_ACCESS_TOKEN`, and `LINKEDIN_PERSON_ID` (your own numeric LinkedIn member ID — build the `urn:li:person:{id}` yourself if you only have the raw ID).

Note: access tokens from this flow last ~60 days. `LinkedInAdapter` doesn't refresh them automatically — LinkedIn's refresh-token support is a separate product requiring its own approval, not assumed granted here — so expiry means redoing step 3 manually.

`LinkedInAdapter.upload()` requires `VideoAsset.local_path` — it uploads via LinkedIn's Videos API (chunked, capturing each part's ETag) then creates the post via the Posts API referencing the uploaded video.

## TikTok

Native, as of 2026-10-01, via the Content Posting API's Direct Post flow.

1. Create an organization and app at **developers.tiktok.com**.
2. Add the **Content Posting API** product with **Direct Post** enabled. Note: TikTok requires the **Login Kit** product too, as a platform-enforced dependency — even though we're only posting to our own account, Content Posting API's OAuth flow runs through Login Kit.
3. Fill in the app's required URLs — Terms of Service, Privacy Policy, and Web/Desktop URL — all pointing at a real site you control (TikTok verifies domain ownership via a signature file; `localhost` is explicitly **not** accepted as a redirect URI, even in Sandbox).
4. Run the OAuth flow yourself (scopes: `user.info.basic`, `video.publish`, `video.upload`) and fill in `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_ACCESS_TOKEN`.
5. **Before this works for real posting**, the app needs to pass TikTok's formal review — which requires uploading a demo video showing the complete integration working end-to-end against the **Sandbox** environment (a separate target-user setup from Production). See `CURRENT_OBSTACLES.md` for the exact requirements; this is a real audit, not a toggle.

`TikTokAdapter.upload()` requires `VideoAsset.local_path` — it does a chunked upload (`init` → `PUT` to the returned upload URL → poll `status/fetch` until `PUBLISH_COMPLETE`). Privacy level defaults to `SELF_ONLY`, since TikTok restricts unaudited apps to private/self-visible posts regardless of what's requested — don't change this until the app is actually approved.

## LinkedIn and TikTok — UploadPost.com fallback (superseded)

Both platforms were originally routed through [UploadPost.com](https://upload-post.com) to avoid each platform's own approval process, before switching to native above. `UploadPostAdapter` (in `adapters/uploadpost.py`) still exists as a fallback — it's just not registered in `ADAPTERS` by default anymore. If either native integration ends up blocked long-term, instantiate `UploadPostAdapter("linkedin")` or `UploadPostAdapter("tiktok")` directly rather than resurrecting a dedicated subclass.

1. Create an UploadPost account and grab your API key from their dashboard.
2. In the UploadPost dashboard, click **Connect** for LinkedIn and/or TikTok and approve the permissions in the popup that opens — no app of your own to create, no waiting on either platform's review.
3. Fill in `UPLOADPOST_API_KEY` and `UPLOADPOST_USER` (the profile username shown in their dashboard once connected).

Note: `UploadPostAdapter.verify_live()` can only trust the upload response itself — UploadPost's docs don't expose a separate get-post/status endpoint, so this is a genuinely weaker live-confirmation guarantee than the native adapters, which always re-check the post via the platform's own API. Also note the endpoint/field names here were taken from UploadPost's docs but not exercised against a live account in this codebase — confirm against their current docs before relying on this in production.

Free tier: UploadPost's $0 plan excludes TikTok entirely and caps at 10 uploads/month. The Basic plan (~$16–24/mo) is needed for TikTok and unlimited uploads.

## Email notifications

Standard SMTP — `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`,
`SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`. Any provider works (Gmail app
password, SendGrid SMTP relay, etc.).

### Summary email draft (video attached)

After `distribute()`, build one summary email listing every platform the video
is live on, with the video attached. It only creates a draft; nothing is sent
and no SMTP settings are needed.

```python
from distribution_agent.notifier import draft_distribution_email, save_draft

message = draft_distribution_email(
    records, asset, poc_email="client@example.com",
    video_title="Spring Launch", qc_score=evaluation.composite_score(),
)
path = save_draft(message)  # writes drafts/<timestamp>-<subject>.eml; open it in a mail app to review and send
```

- Only platforms confirmed live are listed. It raises `ValueError` if none are.
- The video must be at most 20 MB to attach (`ValueError` otherwise). Pass
  `attach_video=False` to send links only.
- `drafts/` is gitignored because the draft holds the video.
- Sending is a separate step the user does themselves from the mail app.

## Usage

```python
from pathlib import Path
from distribution_agent import distribute
from distribution_agent.adapters.base import VideoAsset
from quality_control_agent import confirm_final_draft, clear_for_distribution

draft = confirm_final_draft("video.mp4", title="New product")  # asks: is this the FINAL draft?
# ... run QC on `draft`, building a QCEvaluation named `evaluation` ...
clearance = clear_for_distribution(draft, evaluation)  # raises unless QC passed

asset = VideoAsset(
    caption="Check out our new product!",
    local_path=Path("video.mp4"),      # needed for YouTube, Reddit, Bluesky, Pinterest, X, LinkedIn, TikTok
    public_url="https://cdn.example.com/video.mp4",  # needed for Instagram and Threads, optional for Facebook
)

records = distribute(
    asset,
    platforms=["youtube", "instagram"],
    poc_email="client@example.com",
    clearance=clearance,  # required: proof this exact file passed QC
)
for r in records:
    print(r)
```

`clearance` is required and is checked against `local_path`, so set
`local_path` even for Instagram and Threads. Only a confirmed final draft
that passed the Quality Control Agent can get one (see `QC_AGENT.md`).

### Approval gate

`distribute()` never posts without asking first. By default it prints
the full list of platforms with all of them preselected:

```
Video: "Spring"
Post to these platforms:
  1. instagram
  2. youtube
  3. x
Press Enter to post to ALL, type numbers or names for only those ("1 3"), "-2" to leave one out, or "n" to cancel:
```

Enter approves every listed platform. Anything not approved is skipped
(`approved=False` in the returned record). With no terminal, EOF, or an
answer it can't understand three times, nothing is approved, so an
unattended run can't accidentally post.

To wire approval to something other than a terminal prompt — a
dashboard button, a Slack confirmation — pass your own `approve`
callback: it receives `(platforms, asset)` and must return the list of
platforms to post to. Returning a bool raises `TypeError`.

```python
def approve_from_dashboard(platforms: list[str], asset) -> list[str]:
    return get_human_selection(platforms, asset.caption)  # your own approval UI

records = distribute(asset, platforms=["youtube"], approve=approve_from_dashboard, clearance=clearance)
```
