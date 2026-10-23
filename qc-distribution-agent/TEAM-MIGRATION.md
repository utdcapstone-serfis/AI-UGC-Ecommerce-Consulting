# Team migration: moving projects into the shared repo

Written 2026-10-05. Two ready-to-paste texts: a message for teammates and a
prompt for their Claude agents. Fill in the `<angle bracket>` fields for each
person (`<yourname>`, `<topic>`, `<your-project-folder>`, `<your-repo>`,
`<your-old-branch>`, `<path to shared-repo clone>`, `<short-id>`).

Example of a finished move: branch `alena-qc-distribution-agent`, with the
project inside a `qc-distribution-agent/` folder, plus `alena-history` holding
the old commit-by-commit history.

Notes for whoever coordinates:
- Everyone's old project is in its own separate repo. Nobody should delete or
  archive their old repo until the whole team has confirmed their move.
- Branch protection is NOT enforced (GitHub does not apply rulesets to a
  private repo on the current plan), so the ground rules below matter.
- The team shares one GitHub login. If someone pushes under a different
  GitHub account, they must be added under the shared repo's Settings >
  Collaborators.
- Nothing merges into main until the team agrees on main's layout (one folder
  per project) and merges one project at a time through pull requests.

---

## Message for teammates

```
Hi all, we're moving our projects into one shared repo. Your current repo stays exactly as it is for now. Please don't delete or archive it until the whole team has confirmed their move.

Shared repo: https://github.com/utdcapstone-serfis/AI-UGC-Ecommerce-Consulting
(Example of a finished move: branch alena-qc-distribution-agent, with my project inside a qc-distribution-agent/ folder.)

What to do (your original repo and folder stay untouched):

1. Before you start, make sure all your work is committed and pushed to your own repo (git status should show nothing uncommitted). The snapshot only copies committed files, so anything uncommitted would be left behind.
2. Clone the shared repo into a NEW folder, separate from your current project folder:
   git clone https://github.com/utdcapstone-serfis/AI-UGC-Ecommerce-Consulting.git
   cd AI-UGC-Ecommerce-Consulting
3. Create your own branch from main, named <yourname>-<topic>:
   git checkout -b <yourname>-<topic> origin/main
4. Copy ONLY your project's committed files into a folder named for your project (not .env, not .git):
   - Make the destination folder first.
   - In your ORIGINAL project folder (Git Bash): git archive HEAD | tar -x -C "<path to shared-repo clone>/<your-project-folder>"
   - PowerShell can corrupt this pipe, so use Git Bash, or copy the files by hand and skip .env and .git.
5. Check the copy has no secrets (no .env, no tokens or passwords in any file).
6. Commit with a message that says where it came from: "Snapshot from <your-repo>, branch <branch>, commit <short-id>".
7. Push YOUR branch only:
   git push -u origin <yourname>-<topic>
8. Optional, to keep your old commit history: from your ORIGINAL folder run
   git remote add new https://github.com/utdcapstone-serfis/AI-UGC-Ecommerce-Consulting.git
   git push new <your-old-branch>:<yourname>-history
9. Tell me the branch names when done.

If git says you don't have permission to push, tell me. I need to add your GitHub account to the shared repo.

Ground rules (branch protection isn't enforced on our plan, so these matter):
- Never push straight to main. Everything reaches main through a pull request. Nothing is merged yet; we'll merge one project at a time once we agree on main's layout.
- Never force-push, and never use git push --all or --mirror.
- Never commit .env, tokens, or passwords. Keep your .env inside your own project folder, never at the top level of the repo.
- Unique branch names. Set your own name and email in git so commits show who made them.
- Check main hasn't changed with git ls-remote before and after.
```

---

## Prompt for their Claude agents

```
You are helping move my project into a shared GitHub repo. Follow these rules exactly.

Target repo: https://github.com/utdcapstone-serfis/AI-UGC-Ecommerce-Consulting
My branch name: <yourname>-<topic>. My project folder inside the repo: <your-project-folder>/.
My source project is in my own separate repo and folder, not in the target repo.

Task: first check that my source repo has no uncommitted changes (git status). If it does, tell me and stop. Don't commit for me. Then clone the target repo into a NEW folder (not my current project folder), create my branch from origin/main, copy only my project's tracked files into <your-project-folder>/ (use git archive of my source repo's HEAD, never copy .env or .git), commit with a message naming my source repo, branch and commit ID, and push my branch.

Rules:
1. Before EVERY push, tell me exactly: which GitHub repo, which branch, which local folder it comes from, the commit before and after, and what it will NOT touch (main, other people's branches, my source repo). Then wait for my yes.
2. Never push to main. Never force-push. Never use git push --all or --mirror. Never merge into main yourself; merging happens later through a pull request that I approve.
3. Never read, print, paste or commit secrets (.env, tokens, passwords). Before committing, scan the files being added for secret-like strings, and report only file names.
4. Don't change my source repo or folder. Don't archive or delete anything on GitHub, including my own old repo.
5. Confirm before any git change, and verify every push afterward with git ls-remote.
6. If a commit fails because git has no author set, copy user.name and user.email from my source repo into the new clone only. Never change global git config.
7. Don't open a pull request or merge anything for now. We'll agree on the layout of main first, and I'll tell you when it's time to open the pull request.
8. If a push is refused for permissions, stop and tell me. Don't try other credentials.
9. Report what you did and what's left at the end.
```
