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

Windows PowerShell: use npm.cmd / npx.cmd (plain npm is blocked).
