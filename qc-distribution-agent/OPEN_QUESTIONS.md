# Important questions to answer

Decisions the team still has to make. Add new ones at the end of the Open list.
When one is decided, move it to "Decided" with the date and the answer.

## Open

### 1. Will the final pipeline keep a human approval step before posting?
Added 2026-10-11.

Today (development): `distribute()` shows the user the list of target platforms,
all preselected. The user presses Enter to post to all, or narrows the list
(numbers or names, or a leading dash to leave some out). No answer means no post.
This is a development-time step, because the final pipeline is planned to be
automated, so this may not be a feature of the finished product.

**Part A: if a human keeps approving (as now)**
- Pinterest: probably satisfied. Its Developer Guidelines say that if an app lets
  users schedule pins, "the end user must choose each Pin to be published". Showing
  the user the list and getting a confirmation is a deliberate human choice for this
  video. It is a lighter form of choosing than a yes/no for each platform, and
  whether Pinterest accepts it is our reading, not Pinterest's stated position. The
  safest approach is to leave Pinterest out of the list unless the user wants this
  video on Pinterest.
- TikTok: approval alone is not enough, automated or not. Direct Post requires a
  real interface (creator nickname, a privacy dropdown with no default, unchecked
  comment/duet/stitch boxes, a commercial-content toggle, a preview, and consent
  before each upload), which a terminal list cannot provide. This only applies if the
  app leaves Sandbox and goes through TikTok's review. Details and options are in
  `CURRENT_OBSTACLES.md`.

**Part B: if the pipeline becomes fully automated**
- Pinterest: the "user chooses each Pin" rule could not be met, so Pinterest would
  need to keep a human step, or be left out of automation.
- TikTok: the missing interface and per-upload consent become a bigger problem.
- Other platforms: no specific platform rule found yet, but a bad caption, a wrong
  platform or a duplicate post would go out unchecked. QC clearance only guarantees
  the video passed QC.
- What could replace the human gate: a posting limit per day or per client, a short
  delay before posting with a chance to cancel, an allowed-platforms list per
  client, human approval only for first posts or new clients.
- Who is accountable when an automated post goes wrong, especially for LinkedIn
  (posts appear under a personal profile).

Where it lives in code: `cli_approval()` and the `approve` argument of
`distribute()` in `distribution_agent/distribution_agent.py`. A custom `approve`
function can already replace the terminal prompt.

Note on the current default: pressing Enter approves every platform. That is an
explicit action after the list is shown, and silence or no terminal still approves
nothing. If accidental Enter ever becomes a risk, the safer default is to require
typing "y" or "all".

Source of the platform rules: Pinterest's Developer Guidelines
(policy.pinterest.com/en/developer-guidelines) and TikTok's Content Sharing
Guidelines (developers.tiktok.com/doc/content-sharing-guidelines/), as recorded in
`CURRENT_OBSTACLES.md` on 2026-09-29 and 2026-10-02. Not re-checked since; policies
change, so re-read them before relying on them.

### 2. Will the pipeline serve other clients later, and what should we prepare now?
Added 2026-10-11.

Today the pipeline is built for a single company. A future expansion to other
clients is possible, not decided. This is not a reason to build multi-client
support now, but several choices are cheaper to make well early.

What gets harder with more than one client:
- Credentials: `.env` holds one set of credentials for one person on one machine.
  Each client needs their own accounts, tokens and refresh schedules, kept
  separate, never shared or mixed. See the credentials section of
  `CURRENT_OBSTACLES.md`.
- Reddit: posting for clients is treated as commercial use and needs Reddit's
  explicit written approval. Agency use is the clearest case.
- TikTok: the platform prohibits tools limited to internal or private use, which
  matters more once outside clients are served.
- UploadPost (if used for LinkedIn or TikTok): pricing scales with the number of
  connected profiles, so each client adds cost.
- LinkedIn: posts go out under a personal profile, so each client needs an
  authorized person who is personally responsible for the content.
- QC rubric: brand rules (colors, logo, voice) differ per client, and the rubric
  assumes one brand. The dashboard has a 5,000-document cap and no per-client view.
- Approval: the approver may be each client's own contact, not the operator.

Cheap to do now:
- Keep client-specific values (accounts, brand rules, contact emails) in settings,
  not in code.
- Put a client name on every QC evaluation and distribution record.

Example, YouTube (added 2026-10-11): the Google OAuth app is External and in
Testing. It was switched to Internal on 2026-10-11, which only lets accounts
in the `serfis.ai` organization authorize it. That covers the company's own channel
and nothing else, and it can be switched back. Routes for client channels later,
none built or tested:
1. Switch the app to External and publish it. Each client authorizes it once and we
   store their refresh token. `youtube.upload` is a sensitive permission, so Google
   verification is needed (privacy policy, demo video, review); until then there is an
   unverified-app warning and a 100-user cap.
2. Keep the internal app for the company's channel and create a second Google Cloud
   project for clients (External, verified).
3. Each client creates their own credentials. More work for them, separate credential
   sets for us.
Also unverified: YouTube may lock uploads from an unaudited API project to private,
which could apply to client channels too. The same pattern (our own accounts now,
client accounts through a different path later) applies to Meta, LinkedIn, TikTok
and the other platforms.

To decide:
- Is expansion a real goal, or a possibility to keep in mind?
- If it is, who owns each client's platform accounts and approvals?
- Does the Reddit and TikTok position (single company vs agency) change what we
  apply for, and when?

## Decided
(none yet)

Other open decisions are tracked in `CURRENT_OBSTACLES.md` (TikTok Sandbox vs Production,
Reddit, LinkedIn).
