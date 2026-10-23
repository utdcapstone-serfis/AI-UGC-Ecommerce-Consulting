# Files to merge into main, per agent

Written 2026-10-11 from `git ls-files` on `alena-qc-distribution-agent` and the
imports in the code. Two ways to merge; the team picks one (see
`TEAM-MIGRATION.md`). Never include `.env` (already gitignored) or `drafts/`
(gitignored, holds videos).

## How the two agents depend on each other
- `distribution_agent/distribution_agent.py` imports
  `quality_control_agent.clearance`. Python runs the package's `__init__.py`
  first, which imports `intake`, `models`, `report` and `technical_quality`.
  So the whole `quality_control_agent/` package must be in `main` for
  distribution to run. `examples.py` is the only file there that nothing imports.
- `distribution_agent/adapters/__init__.py` imports every adapter, so all adapter
  files travel together.
- QC does not import anything from distribution.
- Both need `requirements.txt` (OpenCV is used by QC and by the Pinterest adapter).

## Option A: whole project (the current plan, one folder per project)
Everything under `qc-distribution-agent/`:

**QC Agent**
- `quality_control_agent/__init__.py`
- `quality_control_agent/intake.py`
- `quality_control_agent/clearance.py`
- `quality_control_agent/models.py`
- `quality_control_agent/report.py`
- `quality_control_agent/technical_quality.py`
- `quality_control_agent/examples.py`
- `QC_AGENT.md`

**Distribution Agent**
- `distribution_agent/__init__.py`, `config.py`, `distribution_agent.py`, `notifier.py`
- `distribution_agent/adapters/__init__.py`, `base.py`, `bluesky.py`, `facebook.py`,
  `instagram.py`, `linkedin.py`, `pinterest.py`, `reddit.py`, `threads.py`,
  `tiktok.py`, `uploadpost.py`, `x.py`, `youtube.py`
- `get_pinterest_token.py`, `get_tiktok_token.py`, `get_x_token.py`, `get_youtube_token.py`
- `DISTRIBUTION_AGENT.md`, `SETUP.md`

**Shared**
- `agent-prompts.md`, `SOP.md`, `CLAUDE.md`, `CURRENT_OBSTACLES.md`, `OPEN_QUESTIONS.md`
- `archive/HANDOFF.md` (old session brief, optional)
- `requirements.txt`, `.env.example`, `.gitignore`
- `test-assets/blank-test.mp4` (72 KB test video; optional)
- `TEAM-MIGRATION.md` and this file, if the team wants them in main

## Option B: only what other agents need to interact with
Smallest set that still runs. Other agents call two things: the QC gate
(`confirm_final_draft`, `clear_for_distribution`) and `distribute()`.

**Minimum for QC (the gate)**
- all of `quality_control_agent/` (required by the import chain above; `examples.py` may be left out)
- `requirements.txt`

**Minimum for distribution**
- `distribution_agent/__init__.py`, `config.py`, `distribution_agent.py`, `notifier.py`
- every file in `distribution_agent/adapters/`
- `.env.example` (so others know which credentials are needed)

**Docs to keep with it**
- `QC_AGENT.md`, `DISTRIBUTION_AGENT.md`, `SETUP.md`, `SOP.md`

**Safe to leave on the branch**
- `get_*_token.py` helper scripts
- `archive/HANDOFF.md`, `CURRENT_OBSTACLES.md`, `OPEN_QUESTIONS.md`, `agent-prompts.md`, `CLAUDE.md`
- `test-assets/`, `quality_control_agent/examples.py`

Risk with option B: anything left out that is imported somewhere breaks `main`.
After merging, run an import check (`python -c "import distribution_agent"`) on a
clean checkout of `main` before relying on it.
