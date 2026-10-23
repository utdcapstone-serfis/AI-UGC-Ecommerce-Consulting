# Evidence-Based Diagnosis Protocol

Use when the user shares a generated video, a screenshot, or says a clip "came out wrong". Goal: find the actual cause from evidence, change one thing, predict the result, then check the prediction.

## Evidence labels (use them in every diagnosis)
- `[SEEN]` visible in frames you extracted and viewed (cite frame/time)
- `[USER]` the user told you; not verified by you
- `[SOURCE repo/path]` from a repo file you fetched this session or a dated cache entry
- `[OURS n/m]` our own results from the scorecard: worked n of m tries
- `[INFERRED]` your reasoning; no direct evidence
- `[UNTESTED]` a fix or technique with no result on record

Never diagnose from the prompt text alone when a video exists. A claim with only `[INFERRED]` must be said as a guess.

## Steps
1. **Identify the generation.** Find the Prompt ID in `generation-log.md` (ask the user for the ID, or match by text). If it isn't logged, ask for the exact prompt, model, mode and references used, and log it as a new entry.
2. **Get the frames.** Run `scripts/extract_frames.sh "<video>" "<outdir>" 1` (use fps 4 around a flaw). `<outdir>` = the session scratchpad or a temp folder, never inside the repo. Read the contact sheets, then individual frames for each suspected defect. Audio can't be judged from frames: say so, and ask the user about audio problems.
3. **List defects.** Table: time · what is visible `[SEEN]` · what the prompt asked for · severity (blocks use / fixable in post / minor). Include what WORKED, and keep it in the next prompt.
4. **Classify the cause**, with the evidence that points to it:
   | Cause | Evidence that points to it |
   |---|---|
   | Prompt | The prompt was missing, vague on, or contradictory about the flaw; or the model did exactly what was written |
   | References | The flaw is in identity/logo/clothing and the reference image is weak, off-angle, or was not named in the prompt |
   | Model limit | The same flaw appears across two or more different wordings, or in repo `FAILURE-MODES` as a known limit |
   | Complexity | More than one action or camera move; flaw appears late in the clip or only when several things happen at once |
   | Unknown | Evidence doesn't separate the causes: say so and design a test |
5. **Research the symptom** (only for flaws not already explained): fetch `skills/higgsfield-seedance/FAILURE-MODES.md` and `skills/higgsfield-troubleshoot/SKILL.md` (OSM), then follow `repo-sources.md` for any other library that fits. Look for the symptom, the mechanism, and the counter. Label each finding with its source. One community source = `[SOURCE]` only. Two independent sources agreeing = stronger, still not proven.
6. **Hypothesis and test.** Write: "If the cause is X, changing ONLY Y should make Z disappear at time T." Change one variable. Keep every element that worked, byte for byte.
7. **Deliver**: defect table, cause with evidence labels, the one change (as a before/after diff of the prompt), the prediction, and the revised prompt in the usual six-part format.
8. **Close the loop** when the user reports the next result: compare it to the prediction; update `generation-log.md` and `technique-scorecard.md` (see below). A wrong prediction is a result: record it and revise the hypothesis.

## Escalation rules
- Same flaw after two different wording fixes → stop rewording. Change the workflow: approved still + image-to-video, separate clip per element, or different reference images.
- Identity drift only late in the clip → shorten the clip or end earlier and cut; do not add more face description.
- Logo distorts only in motion → macro insert clip for the logo, cut in during edit.
- A flaw you can't see at 1 fps → re-extract at 4 fps for that window before concluding.

## Limits (say these when they matter)
- Frame review can miss small artifacts; ask the user to confirm the key defects you cite.
- Low-resolution files limit logo and skin judgments.
- One generation is one sample; a single success or failure is not proof about a technique.
- Never claim you reviewed the audio, or the whole video, if you only sampled frames.

## Updating the evidence (what the agent may write)
- Always, at delivery: append the new prompt to `generation-log.md` and say so.
- Only after the user reports an outcome (or shares the video): fill that entry's result, defects and cause, and update `technique-scorecard.md` counts.
- Status changes on the scorecard follow its rules; one result never makes a technique "proven".
- Never edit `campaign-start-again.md` on your own. If evidence suggests a campaign rule should change, propose the edit and wait for the user.
