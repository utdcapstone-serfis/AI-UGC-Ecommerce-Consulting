---
name: project-roma-ad-paused
description: Roma AI 30s fruit-character video ad is paused after Scene 4; lists locked assets and what remains
metadata:
  node_type: memory
  type: project
  originSessionId: 528d3730-76b1-471e-b993-d48272f6e383
  modified: 2026-10-02T19:57:29.993Z
---

The Roma AI comedic ad (strawberry girl + fruit teammates, 3D-cartoon style, script has 6 scenes) was paused by the user on 2026-10-02 ("put a pin in this").

**Done / approved (all in `content/`, untracked in git):**
- Locked characters: `roma_strawberry_MASTER.png`, `roma_banana_reference_v3.png`, `roma_orange_reference_v1.png`, `roma_apple_reference_v1.png`, plus watermelon/pineapple v1 as crowd filler.
- Locked backgrounds: `roma_bg_soccerfield_MASTER.png`, `roma_bg_dorm_MASTER.png` (empty, bed-framed), `roma_bg_stadium_MASTER.png`.
- Scene 1 `roma_scene1_v1.mp4`; Scene 2 `roma_scene2a_v1.mp4` + `roma_scene2b_v2.mp4`; Scene 3 `roma_scene3_v1.mp4`, `roma_scene3_aerial_v1.png`, hand-only still `roma_scene3_handonly_v5.png`; Scene 4 `roma_scene4_pan_v1.mp4` (worried face -> pan to phone press -> happy) was just delivered, not yet confirmed approved.
- `roma_app_mockup.png` is the PIL-built RomaAI phone screen (real text, used as an image reference so UI text stays legible).

**Remaining:** Scene 5 (practice montage + game sequence, plan was to consolidate into ~2 clips), Scene 6 (goal, team celebration, Roma logo end card). Dialogue is not generated: no Higgsfield model does scripted lip-sync, user planned sync.so or captions later. Music/SFX not yet added.

**Why:** User is cost-sensitive and sponsor requires Higgsfield. Spend so far is unknown; the Higgsfield MCP `balance` tool showed a different account (10 credits, no transactions) than the API key in `.env`, so only console.higgsfield.ai is authoritative.

**How to apply:** On resume, start at Scene 5, reuse the locked assets above, do not regenerate characters or backgrounds. Scene 4 acceptance should be confirmed first.
