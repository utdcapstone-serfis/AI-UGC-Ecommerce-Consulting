# Generation Log (append-only)

One entry per prompt delivered, plus one per video reviewed. Only entries written here are "saved". The agent appends new entries at delivery and fills results only after the user reports them.

## Entry template
```
### G-### · YYYY-MM-DD · <clip name>
- Model/mode: <e.g. Seedance 2.5 omni_reference, 7s, 9:16, 1080p>
- References: <@Image order and what each is>
- Prompt: <full text, or "not saved, see summary">
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
