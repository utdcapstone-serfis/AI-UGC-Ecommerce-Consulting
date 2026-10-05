# Handoff: QC & Distribution Agent (as of 2026-10-05)

Read this first, then CURRENT_OBSTACLES.md (platform blockers, with dates and
reasoning), DISTRIBUTION_AGENT.md, QC_AGENT.md and SETUP.md.

## What this project is
A QC Agent scores short-form video. A Distribution Agent posts approved videos
to 10 platforms (Instagram, Facebook, Threads, YouTube, Reddit, Bluesky,
Pinterest, X, LinkedIn, TikTok). Every post needs explicit human approval.

## Where the repo stands
- Working copy: C:\Users\alena\work\AI-UGC-Ecommerce-Consulting\qc-distribution-agent\
  on branch alena-qc-distribution-agent (outside OneDrive). Open sessions in
  this folder so .env and CLAUDE.md are found.
- New shared repo (GitHub): utdcapstone-serfis/AI-UGC-Ecommerce-Consulting.
  main = README only. alena-history = full old commit history (212ce7d).
  alena-qc-distribution-agent = this project snapshot (4d4ad2a) plus later commits.
- Old repo: utdcapstone-serfis/aivideo, branch Alena, up to date at 212ce7d.
  Old Desktop folder "Distribution Quality Control Agent" is a backup.
- To do: copy .env into qc-distribution-agent/ (user does this), read-only
  test from the new folder, then archive aivideo LAST, after everyone has moved.
- Not merged into main yet. Team still has to agree on main's layout (one
  folder per project) and merge one project at a time via pull requests.
- Branch protection is NOT enforced: GitHub says rulesets don't apply to a
  private repo on the current plan. Rely on team rules: nobody pushes to main,
  everything goes through pull requests, never force-push, never use
  git push --all or --mirror, push only your own branch. Check main with
  git ls-remote before and after each merge. The team shares one GitHub login,
  so required approvals can't work either.

## Platform status
- Working, verified live: YouTube, Bluesky, X, Instagram, Facebook.
- TikTok: verified in Sandbox only (private account, SELF_ONLY). Open decision:
  stay in Sandbox vs Production audit vs other posting approach.
- LinkedIn: native adapter written, never tested live. Blocked on Page
  requirement and ID verification decision.
- Reddit: adapter untested, no credentials. Devvit checked and ruled out (no
  way to supply a video). Commercial-use ticket pending since 2026-10-01.
  Support form is drafted but NOT submitted yet. developers.reddit.com/
  app-registration on hold (nothing entered). Only Reddit account: SerfisAI2026.
  No API use until Reddit gives written approval.
- Pinterest: new app waiting on Trial access. App secret is hidden until
  approved. PINTEREST_BOARD_ID lookup deferred until a real token exists.
- Threads: serfisai2026 permanently banned. A test with a second Meta app
  (threads-test) is on hold. A brand-new test account is high risk.

## Rules (from the user)
- Never post, or submit a paid generation, without explicit approval of that
  exact post/generation.
- Never read, print or paste secrets. The user puts credentials in .env.
  Never commit .env.
- Confirm before any git change or anything outward-facing. Verify pushes
  with git ls-remote.
- Keep the source-of-truth docs current as things change.
- Windows PowerShell: use npm.cmd / npx.cmd (plain npm is blocked).
