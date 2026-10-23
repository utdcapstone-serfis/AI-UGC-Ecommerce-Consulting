# Generation Log (append-only)

One entry per prompt delivered, plus one per video reviewed. Only entries written here are "saved". The agent appends new entries at delivery and fills results only after the user reports them.

## Entry template
```
### G-### · YYYY-MM-DD · <clip name>
- Campaign: <profile name, or "none (new brand)">
- Model/mode: <e.g. Seedance 2.5 omni_reference, 7s, 9:16, 1080p>
- References: <@Image order and what each is>
- Prompt: <the FULL prompt text in a code block; never "not saved". Diagnosis needs it to compare against the video>
- Techniques applied: <names, matching technique-scorecard.md>
- Sources fetched: <repo/path list>
- Prediction: <what should look right, and the main risk>
- Result: not reported | success | partial | failed   (date, who reported)
- Defects [SEEN/USER]: <time · what · severity>
- Cause + evidence: <class from diagnosis-protocol.md, with labels>
- Next change: <the ONE variable changed in G-###+1>
```

## Entries

### G-001 · 2026-10-16 · Two-man dumbbell squat, 7 s
- Model/mode: Seedance 2.5 omni_reference, 7 s, 9:16, 1080p
- References: @Image 1 Man A, @Image 2 Man B, @Image 3 black top with S, @Image 4 rooftop, @Image 5 dumbbell
- Prompt: not saved (delivered in chat; re-create from `prompt-templates.md` #1 plus the role and positioning blocks)
- Techniques applied: reference role sentences with exclusions; two-man positioning block; explicit dumbbell and hand counts; one dolly-in with named end frame; faint-sweat exertion cues; diegetic audio; short AVOID line
- Sources fetched: OSM seedance-2-5, multi-character-anchor, FAILURE-MODES, camera, motion, facs, omni-reference-2-5
- Prediction: both men keep four dumbbells and distinct faces; main risk is face drift and logo warp
- Result: not reported

### G-002 · 2026-10-16 · Two-man cycling, apparel then pan, 7 s
- Model/mode: Seedance 2.5 omni_reference, 7 s, 9:16, 1080p
- References: @Image 1 Man A, @Image 2 Man B, @Image 3 black top with S, @Image 4 rooftop with bike row
- Prompt: not saved (delivered in chat)
- Techniques applied: hold-then-pan timed beats; chin-down chest framing for the first 3 s; garment "one identical" emblem lock; pedaling as an ordered physics chain at 90 rpm; background riders as a separate soft-focus block
- Sources fetched: LRN sports-extreme, LRN fashion-lookbook, ZER commercial-use-cases (+ cached OSM camera, seedance-2-5)
- Prediction: emblem stays sharp for 0-3 s; pedals turn in full circles; risk is class faces warping and pedal mechanics
- Result: not reported

### G-003 · 2026-10-21 · Coffee brand pour, 7 s (placeholder brand)
- Model/mode: Seedance 2.5 omni_reference, 7 s, 9:16, 1080p
- References: @Image 1 cup with brand mark, @Image 2 optional counter
- Prompt: not saved (delivered in chat)
- Techniques applied: timed beats one action per step; scope fence "Espresso only"; no hands; one dolly-in; diegetic audio with `[AUDIO: Xs]`
- Sources fetched: LRN food-asmr, OSM 02-product-ugc-showcase, OSM higgsfield-audio
- Prediction: crema forms and holds; risk is liquid physics (no source covers coffee) and the brand mark
- Result: not reported

### R-001 · 2026-10-16 · Reviewed video: combined_final.mp4 (~30 s, 496x864, 24 fps, stereo audio)
- Evidence: 30 frames at 1 fps viewed on two contact sheets; audio not reviewed
- Prompt: unknown; the file is an edit of about five separate clips
- Defects [SEEN]:
  - ~0-12 s tuxedo bar scene, ~13-16 s gym with dumbbell curls: not the rooftop campaign setting
  - ~17-23 s rooftop cycling: a man in a black tee with a silver S on the chest; the S looks consistent across close-ups here
  - ~23-26 s both men leap above the skyline and fly into clouds; ~26-30 s a large metallic S in clouds with text "START AGAIN - WHERE DISCIPLINE MEETS DESIGN": violates the no-aerial, no-cloud-transition, no-logo-reveal rules
  - Men's faces and apparel differ between segments (gym tee/tank vs black tee)
- Cause + evidence: segments came from separate generations with different setups `[INFERRED]`; the rule violations match prompts that asked for those moves `[INFERRED]`
- Next change: regenerate the cycling clip (G-002) and drop the flight and cloud segments

### G-004 · 2026-10-23 · DEMO (step 0 test) - two-man squat
- Campaign: Start Again
- Model/mode: Seedance 2.5 omni_reference, 7 s, 9:16, 1080p (DEMO: not submitted)
- References: @Image 1 Man A, @Image 2 Man B, @Image 3 black top with silver S, @Image 4 rooftop, @Image 5 silver dumbbell
- Prompt:
```
7-second vertical 9:16 photorealistic commercial clip, one continuous shot, no cuts. Not a 3D render.
REFERENCE ROLES: Man A corresponds to @Image 1; use only his appearance, hairstyle and clothing. Man B corresponds to @Image 2; use only his appearance, hairstyle and clothing. Do not interchange their appearances, clothing, actions or positions. The S emblem is exactly as in @Image 3, one identical emblem on both chests. The rooftop uses only the spatial layout, architecture and lighting of @Image 4; do not use people from it. Dumbbells look like @Image 5.
POSITIONING: Man A: left third (~30% x), midground, three-quarter toward camera, feet shoulder-width on black rubber floor, gaze forward. Man B: right third (~70% x), midground, same stance and orientation, gaze forward. About 1.5 m apart, neither crosses the center axis, neither drifts more than ~1 m; skyline visible between them. Man A holds one silver dumbbell in each hand; Man B holds one silver dumbbell in each hand; four dumbbells total, all identical, all four visible in frame 1 and throughout.
ACTION (one exercise, both men in sync): 0-2s stand, weight mid-foot, dumbbells hang at sides. 2-4s descend slowly, knees tracking over toes, spine neutral. 4-5s brief pause, thighs near parallel. 5-7s drive up through heels and exhale, ending standing tall.
CAMERA: human height, one slow smooth push-in from medium two-shot (both men full to knees) to a tighter chest-up two-shot by 7s, camera otherwise steady.
LOOK: modern rooftop gym at golden hour, glass railings, urban skyline behind, warm string lights, soft background exercisers. Single warm low-sun key with soft rim light on shoulders, shallow depth of field, natural motion blur, ARRI ALEXA look, 35mm film texture.
DETAIL: both in fitted black compression tops with visible stitching, silver S sharp and unchanged, same size and position. Faint sweat beads at temples and forehead, one visible breath at the drive-up, jaw tightening, slight flush, fabric darkening with sweat.
AUDIO: diegetic only: footfalls on rubber, dumbbell weight shifting, steady exhale at 5-7s, distant city ambience. No music.
AVOID: drone or aerial shot, clouds, logo reveal, extra or missing dumbbells, distorted S, changing faces, extra limbs, floating weights, mirrors or reflections of the men, on-screen text, subtitles, watermark.
```
- Techniques applied: reference role sentences with exclusions; two-man positioning block; explicit dumbbell and hand counts; one camera move with named end frame; faint-sweat exertion cues; short positive AVOID line
- Sources fetched: OSM worked-example-two-character, OSM ENGINE-RULES, OSM global-style-prefix (+ cached OSM seedance-2-5, multi-character-anchor, camera, facs, omni-reference-2-5)
- Prediction: both men keep four dumbbells and distinct faces; main risk is face drift and S logo warp during descent
- Result: not reported (demo, no generation)
