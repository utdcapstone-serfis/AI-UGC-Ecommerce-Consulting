# Skills Library — what to apply, and where it came from

## Provenance (be honest about this)
- **Community**: https://github.com/Abteeeen/higgsfield-prompting-skill — I read the full repo (README, SKILL.md, text/multimedia/advanced/elements/format playbooks, both knowledge bases). It calls itself "official" but sits under an individual account (1 star, no LICENSE file seen), so treat it as a third-party compilation. Its `elements_and_consistency.md` says it was compiled from Higgsfield blog posts, which I did not independently open.
- **Official**: Higgsfield API docs (docs.higgsfield.ai) — authoritative for model fields and limits; use the `higgsfield` skill to check before each new model.
- **Official-org, MIT**: https://github.com/higgsfield-ai/skills — sits under the `higgsfield-ai` org (the page doesn't literally say "official"; confirm on higgsfield.ai). I read only the README, not each SKILL.md. It is a tooling/CLI skill set (generate, soul-id, product-photoshoot, brandkit...), with NO Seedance prompting craft and no troubleshooting. Useful facts: default video model `seedance_2_5`; image-to-video via `--mode omni_reference --start-image`; character identity via `higgsfield-soul-id` (5-20 photos, then `--soul-id`). `higgsfield-product-photoshoot` has a virtual try-on mode that may help apparel stills.
- **Community, MIT**: https://github.com/OSideMedia/higgsfield-ai-prompt-skill — ~32 sub-skills. I read its README, `skills/higgsfield-seedance-2-5/SKILL.md` and `templates/seedance/multi-character-anchor.md`. I did NOT read its 15-mode FAILURE-MODES doc (path 404'd), `higgsfield-troubleshoot`, camera, motion or audio skills. Read those next if a failure persists.
- Limits quoted below (9 images / 3 videos / 3 audio, etc.) are from the community wiki; confirm in the live model page.

## Selected techniques (grouped by need)

### Prompt structure (Seedance)
- 6-part formula: Subject + Action + Environment + Camera + Style + Constraints. Describe camera and subject in separate sentences. (community)
- ONE primary camera instruction per clip. Rhythmic words ("slow", "smooth", "continuous") beat lens/ISO specs. (community)
- Timestamp shot script, e.g. `[00:00-00:03]`, for anything over ~5s. (community)
- Use numbers over adjectives ("pedaling at about 90 rpm"). (community)
- Include "no cuts" if you want one continuous shot, otherwise Seedance may cut. (community)

### Reference / consistency
- Image-to-video beats text-to-video for specific people. (community)
- Name every reference in the prompt with its `@` anchor or it may be ignored. (community)
- Elements (Higgsfield): save character/product/location once; reference by exact name. Separate Elements for states (dry vs sweaty). (community, from Higgsfield blog)
- Soul ID: trained persistent face from 20+ photos; usable across models. Needs real photos of consenting people. (community; verify availability/pricing)
- 3–5 visual anchors per character, no more. (community)
- Grey-background sheets; erase duplicate faces on multi-view sheets. (community)
- Change one variable at a time between clips. (community)
- Caution: the wiki notes Seedance may block realistic human faces in uploaded images. If your references are rejected or ignored, test Elements/Soul ID or another model. (unverified; test it)

### Clothing, logo, product
- Describe the emblem geometrically ("metallic silver S, centered on chest, ~8 cm") and attach the logo reference. Keep the logo in medium/close shots, avoid hard fast motion on it.
- Lock wardrobe in a "positive lock" line repeated in every clip.
- Product ads: macro close-ups on fabric, stitching, emblem catching golden-hour highlights.

### Motion and anatomy
- Beat-by-beat choreography beats "he squats". Write phases (descend 2s, pause, drive up). (community)
- State physics: weight on mid-foot, knees track over toes, neutral spine, gravity respected. (community "physics" header idea)

### Camera and look
- Allowed for this campaign: push-in, lateral tracking, horizontal pan, locked-off close-up, shallow DOF.
- Lighting: golden hour, warm key from low sun, rim light on shoulders, soft highlight rolloff. Film anchors: "ARRI ALEXA aesthetic", "35mm film quality", "natural imperfections". (community)
- Avoid vague hype words ("epic", "beautiful").

### Skin and texture
- "Pore-level skin realism, capillary flush, sweat beads at temples" (community style header). Name where sweat is.

### Audio
- Diegetic only in generation (breathing, bike whirr, dumbbell clink, distant city); add music in post. Prototype without audio to save credits. (community)

### Shot sequencing
- Separate clips per exercise/angle; plan match cuts (end one clip on a pose the next begins with); first/last frame control if the model supports it. Name clips 1a, 1b, 2a.

### Troubleshooting
- See `troubleshooting.md` (built from the community failure/fix table plus your recurring issues).

## Seedance 2.5 specifics (community, OSideMedia; verify on the live model page)
- Modes: `t2v`, `omni_reference` (references plus start/end frames), `video_edit`, `video_extension`. Duration 4-30s, 480/720/1080p. Don't write duration/resolution/aspect into the prompt text.
- Declare each reference's job: "@Image 1 defines Man A's face and hair. Do not use its background." Every role gets an exclusion. Say when several views are one subject. Never reference a handle in a shot where that subject is absent. Pick one handle spelling per project (`@Image 1` vs `@image1`).
- Fidelity grade per reference: full-preserve (logo, wardrobe), partial-preserve, attribute-transfer, loose-guide (mood).
- Avoid age words ("young") in prompts; describe build, hair, clothing, action. Avoid stacked buzzwords and long negative lists (treated as scene description): prefer positive locks plus a short "avoid" line. Pair emotion with 2-4 observable cues.
- No more than one action per second. Split physics from performance into separate clips.
- Audio brackets: `()` music, `<>` SFX, `{}` dialogue. Timestamps are approximate. Text/logo accuracy is not guaranteed, so plan a post-production or macro-insert fix.
- Multi-character blocking (adapted from the community template, written for 2.0): before the action, lock for each man: screen third + approx % position, depth layer, body orientation, pose, gaze, contact points (hands on dumbbells, feet on floor); then relationship: distance, eyeline, crossing rule (neither crosses the center axis), negative space.

## Not selected (and why)
Transformations/orbs/POV/fight/anime playbooks, VFX source-lock for video-to-video, JSON prompt format, speed ramping, monetization and K-pop sections: not relevant to realistic rooftop workout ads. Speed ramping may be reconsidered for slow-motion hero shots.
