# Campaign Profile: Start Again (fitness apparel)

Edit this file whenever the campaign changes; the skill reads it every time.

## Brand
- **Start Again**; emblem is a distinctive **metallic silver S** (use the user's brand reference image, never redraw it).
- Themes: discipline, determination, fitness, transformation, the decision to start again.
- Look: premium, powerful, modern, cinematic, emotionally engaging. Must read as a professional fitness commercial, not generic AI.

## Characters (identity comes from reference images, which outrank any text here)
- **Man A**: young, athletic, light-brown curly hair, clean-shaven.
- **Man B**: athletic, dark curly hair, short beard.
- Never change facial structure, hairstyle, skin tone, facial hair or body proportions between scenes.

## Wardrobe (apparel is the product)
- Premium black performance clothing, compression fit, visible stitching.
- Exact metallic silver S emblem on the chest of both; same placement, size and shape in every shot.
- Sweat darkens fabric naturally; fabric moves and creases realistically.

## Setting (keep identical across related clips)
Modern rooftop gym, golden hour: urban skyline, black rubber flooring, glass railings, warm sunset light, string lights, professional equipment, groups exercising, cinematic shadows.

## Workouts
1. Weighted squats, metallic silver dumbbells
2. Dumbbell lunges
3. High-intensity rooftop stationary-bike (spin) class
4. Group fitness
- Dumbbell scenes: each man holds one silver dumbbell in each hand unless told otherwise.
- Cycling: realistic stationary spin bikes, correct pedaling; camera first on both men's branded clothing, then smooth horizontal pan to reveal the class.

## Realism details to include
Individual sweat beads (forehead, temples), sweat running down skin, skin pores, muscle tension, heavy breathing, slight redness, sweat-darkened fabric, golden-hour highlights, shallow depth of field, natural motion blur, premium commercial lighting.

## Camera rules (hard)
- Human height on the rooftop. Preferred: close-ups, medium shots, controlled push-ins, lateral tracking, smooth horizontal pans across the class.
- NEVER (unless explicitly requested): drone shots, zoom-out from the building, aerial flyaways, cloud transitions, final logo reveal.

## Duration
Default clip = 7 seconds. Keep to one exercise, one camera move, at most 2–3 beats. Complex ideas become separate clips edited together.

## Reference assets (fill in as you create them)
| Name | File / Element name | Notes |
|---|---|---|
| Man A | (todo) | front-facing, sharp, neutral background |
| Man B | (todo) | same |
| Silver S emblem | (todo) | flat, front-on, high-res |
| Black apparel (front) | (todo) | showing S on chest |
| Rooftop | (todo) | 3/4 angle |
| Silver dumbbell | (todo) | |

## Prompt blocks (used by the templates in `prompt-templates.md`)

**LOCK (identity and wardrobe)**
Man A (@ManA reference): athletic man, light-brown curly hair, clean-shaven. Man B (@ManB reference): athletic man, dark curly hair, short beard. Faces, hair, skin tone and builds identical to the references throughout. Both wear fitted black performance athletic wear with the metallic silver S emblem centered on the chest exactly as in @Logo reference, same size and position in every frame.

**SET**
Modern rooftop gym at golden hour, black rubber flooring, glass railings, urban skyline behind, warm string lights, people exercising in the background.

**LOOK**
Warm low-sun key light with soft rim light on shoulders, shallow depth of field, natural motion blur, ARRI ALEXA aesthetic, 35mm film quality, 100% real-life shooting texture. Pore-level skin, individual sweat beads at the temples and forehead, sweat running down skin, sweat-darkened fabric, heavy breathing.

**CONSTRAINTS (positive wording, inside the prompt)**
Camera stays at human height on the rooftop, one continuous shot, no cuts. Each man holds exactly one silver dumbbell in each hand (four total). Emblem stays sharp and unchanged. Natural human anatomy and balance. No on-screen text, no subtitles, no watermark.

**NEGATIVE field (if the interface has one)**
drone shot, aerial view, zoom out from building, clouds, logo reveal, extra or missing dumbbells, distorted S logo, changing faces, extra limbs, warped hands, floating weights, text, subtitles, watermark

## Consistency specifics (moved from the shared guide)

### Anchors (starter set)
- Man A: light-brown curly hair, clean-shaven (avoid the word "young" in prompts; Seedance 2.5 guidance says age words hurt)
- Man B: dark curly hair, short beard
- Both: black compression top, metallic silver S centered on chest

### Dumbbell rule
Always write: "Man A holds one silver dumbbell in each hand; Man B holds one silver dumbbell in each hand; four dumbbells total, all identical." Keep both men in frame with both weights visible in frame 1. For close-ups of one man, still say "both hands hold dumbbells".

### Logo rule
Medium or close shots; avoid fast motion across the emblem; "emblem unchanged, sharp, same size on both men." If it warps, reduce motion and use a macro clip of the logo to cut in.

### Two-man blocking block (paste before the action in two-man shots)
Man A: left third, ~30% x, midground, three-quarter toward camera, feet shoulder-width on rubber floor, both hands gripping silver dumbbells, gaze forward.
Man B: right third, ~70% x, midground, three-quarter toward camera, same stance, both hands gripping silver dumbbells, gaze forward.
Distance ~1.5 m. Neither man crosses the center axis. Negative space: skyline behind between them.
