# Character, Clothing and Object Consistency

## Reference kit (build once, reuse forever)
1. **Per man**: 1 sharp front-facing, evenly lit portrait on neutral grey, plus 1 full-body front. Add a 3/4 face if available. Real photos or locked AI renders only.
2. **Wardrobe**: front view of the black top with the S emblem visible and sharp.
3. **Logo**: flat, front-on, high-res S emblem on plain background.
4. **Rooftop**: one 3/4-angle still.
5. **Dumbbell**: one clean product shot.
Fix the *image* before the prompt: reference quality is the biggest lever (community guidance).

## Recommended order of options (use what the selected model/interface supports)
1. **Reference/Elements** (Higgsfield): save Man A, Man B, Logo, Rooftop, Dumbbell as named Elements; reference by exact name.
2. **Image-to-video from a starting frame** where both men already look right: generate the still first (image model), approve it, then animate.
3. **Soul ID** for each man if you have real consenting-subject photos (20+).
4. **Text anchors**: 3–5 per man, repeated every prompt.
Test whether the model accepts your human-face references; if it blocks or ignores them, escalate to 2/3.

## Procedure per clip
1. Attach references in a fixed order (Man A, Man B, Logo, Rooftop).
2. Name each in the prompt.
3. Paste the LOCK block verbatim.
4. State counts: "two men", "four dumbbells total", "one emblem on each chest".
5. One variable change per iteration.
6. Watch the full clip, not just frame 1 (drift often appears at 5–8s).

## Anchors (starter set)
- Man A: light-brown curly hair, clean-shaven (avoid the word "young" in prompts; Seedance 2.5 guidance says age words hurt)
- Man B: dark curly hair, short beard
- Both: black compression top, metallic silver S centered on chest

## Separate states
Dry and sweaty versions of each man should be separate references/Elements, rather than asking for "make him sweaty" (community guidance).

## Dumbbell rule
Always write: "Man A holds one silver dumbbell in each hand; Man B holds one silver dumbbell in each hand; four dumbbells total, all identical." Keep both men in frame with both weights visible in frame 1. For close-ups of one man, still say "both hands hold dumbbells".

## Logo rule
Medium or close shots; avoid fast motion across the emblem; "emblem unchanged, sharp, same size on both men." If it warps, reduce motion and use a macro clip of the logo to cut in.

## Two-man blocking block (paste before the action in two-man shots)
Man A: left third, ~30% x, midground, three-quarter toward camera, feet shoulder-width on rubber floor, both hands gripping silver dumbbells, gaze forward.
Man B: right third, ~70% x, midground, three-quarter toward camera, same stance, both hands gripping silver dumbbells, gaze forward.
Distance ~1.5 m. Neither man crosses the center axis. Negative space: skyline behind between them.
