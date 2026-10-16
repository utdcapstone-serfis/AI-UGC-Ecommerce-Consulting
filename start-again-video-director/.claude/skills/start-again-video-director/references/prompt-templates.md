# Prompt Templates (7-second clips, human-height camera)

Fill the [brackets]. Keep each clip to ONE exercise and ONE camera move. Attach references first; name them in the prompt.

## Shared blocks (paste into every prompt)

**LOCK (identity and wardrobe)**
Man A (@ManA reference): young athletic man, light-brown curly hair, clean-shaven. Man B (@ManB reference): athletic man, dark curly hair, short beard. Faces, hair, skin tone and builds identical to the references throughout. Both wear fitted black performance athletic wear with the metallic silver S emblem centered on the chest exactly as in @Logo reference, same size and position in every frame.

**SET**
Modern rooftop gym at golden hour, black rubber flooring, glass railings, urban skyline behind, warm string lights, people exercising in the background.

**LOOK**
Warm low-sun key light with soft rim light on shoulders, shallow depth of field, natural motion blur, ARRI ALEXA aesthetic, 35mm film quality, 100% real-life shooting texture. Pore-level skin, individual sweat beads at the temples and forehead, sweat running down skin, sweat-darkened fabric, heavy breathing.

**CONSTRAINTS (positive wording, inside the prompt)**
Camera stays at human height on the rooftop, one continuous shot, no cuts. Each man holds exactly one silver dumbbell in each hand (four total). Emblem stays sharp and unchanged. Natural human anatomy and balance. No on-screen text, no subtitles, no watermark.

**NEGATIVE field (if the interface has one)**
drone shot, aerial view, zoom out from building, clouds, logo reveal, extra or missing dumbbells, distorted S logo, changing faces, extra limbs, warped hands, floating weights, text, subtitles, watermark

---

## 1. Weighted squats (two men, dumbbells)
[LOCK] [SET] Side by side, both men perform slow goblet-free weighted squats, one silver dumbbell in each hand held at the sides. Beats: 0-2s stand, weight mid-foot, feet shoulder width; 2-4s descend with knees tracking over toes, neutral spine; 4-5s brief pause thighs near parallel; 5-7s drive up through heels, exhale. Camera: controlled slow push-in from medium shot to chest-level close-up, smooth and continuous. [LOOK] [CONSTRAINTS]

## 2. Dumbbell lunges
[LOCK] [SET] Both men step forward into alternating lunges, silver dumbbell in each hand, front shin vertical, back knee lowering toward the floor, torso upright, then push back to standing. One lunge per leg. Camera: smooth lateral tracking shot at waist height, matching their pace. [LOOK] [CONSTRAINTS]

## 3. Rooftop cycling class (apparel focus + pan)
[LOCK] [SET] Man A and Man B ride realistic stationary spin bikes in front, hands on handlebars, feet clipped in, pedaling steadily at about 90 rpm with correct pedal circles, shoulders low, sweat visible. Rows of riders behind them. Shot: 0-3s medium close-up on both men's chests and the silver S emblems, shallow focus; 3-7s smooth horizontal pan left to right revealing the rest of the class. [LOOK] [CONSTRAINTS]

## 4. Cinematic fitness commercial (hero beat)
[LOCK] [SET] One man mid-exercise, determination in his eyes, a single drop of sweat falling from his chin. Camera: slow push-in to a close-up, then hold. [LOOK] Mood: discipline and the decision to start again.

## 5. High-intensity workout scene
Use #1 or #3, then raise intensity in words: "faster tempo, jaw set, veins in forearms, chest rising with each breath", but keep the same movement and camera.

## 6. Luxury athletic apparel ad (garment hero)
[LOCK] [SET] Man A pauses between reps, chest rising, the silver S emblem catching golden-hour light. Camera: locked-off medium close-up, then slow push-in to the emblem and fabric weave. Visible stitching, compression seams, fabric stretching over shoulders, sweat darkening the collar. [LOOK] [CONSTRAINTS]

## 7. Product close-up (macro)
Macro of the metallic silver S emblem on black performance fabric, stitching and weave visible, warm sunset glare sliding across the metal, a few sweat beads on the fabric, shallow depth of field, slow subtle push-in. Emblem shape exactly as @Logo, no warping, no extra letters.

## 8. Character-focused scene
[LOCK for ONE man] [SET] Tight medium close-up on [Man A / Man B] between sets, breathing hard, eyes forward, sweat at temples, subtle flush. Camera: locked-off with a very slow push-in. Hold the face unchanged.

## 9. Group fitness
[LOCK] [SET] Man A and Man B lead in the front row, a class of 8-10 people in matching black apparel follow the same movement [exercise] in sync behind them. Camera: smooth horizontal pan across the class at chest height. Keep background faces soft (shallow focus) to reduce drift.

## 10. Realistic action sequence
Choose ONE movement phase only (e.g. the drive-up of a squat) and write beats with durations. Do not combine exercises.

## 11. Multi-shot sequence (build from separate clips)
Do not put multiple shots in one prompt unless the model's docs say it handles cuts well. Generate:
- 1a: wide-medium class, pan
- 1b: close-up of Man A (squat)
- 1c: macro S emblem
- 1d: Man B face, between reps
Reuse the same LOCK/SET/LOOK text verbatim and the same references. Edit together in post.

## 12. Cinematic transitions
Default: hard cut or match cut in editing. In-prompt transitions only if asked. Allowed ideas: match cut on a repeated motion (dumbbell rise to dumbbell rise), whip-pan across the class. Never cloud/aerial transitions.
