# QC & Distribution Agent

Start with CURRENT_OBSTACLES.md for per-platform blockers and OPEN_QUESTIONS.md
for decisions still to make. SOP.md is the step-by-step procedure from final
draft to posted. archive/HANDOFF.md is the old session-start brief, kept for
reference only and no longer maintained.

Key rules:
- Never post, or submit a paid generation, without explicit approval of that exact item.
- Never read, print or paste credentials. The user edits .env. Never commit .env.
- Confirm before any git change or outward-facing action. Verify pushes with git ls-remote.
- Update the source-of-truth docs when things change.

Git rules (branch protection is not enforced, so these matter):
- Work and push only on your own branch (alena-qc-distribution-agent).
- Never push to main, never merge into main yourself, never force-push, never
  use git push --all or --mirror. Changes reach main later through pull requests.
- The team shares one GitHub login, so required approvals can't work.

Changes on main must stay revertable (added 2026-10-17):
- Merge into main only through a pull request, one purpose per pull request, so
  a bad merge can be undone in one step.
- Undo with `git revert` (or the Revert button on the merged pull request), which
  adds a new commit and keeps the history. Never rewind main with `git reset` and
  a force-push.
- Before merging, check the diff for tokens, passwords and .env contents. A secret
  that reached main stays in the history and in clones even after a revert, so
  rotate it, not just revert.
- A revert doesn't undo outside effects (deploys, posts, emails) or other people's
  copies; say so when proposing a merge that triggers any of them.

Windows PowerShell: use npm.cmd / npx.cmd (plain npm is blocked).
