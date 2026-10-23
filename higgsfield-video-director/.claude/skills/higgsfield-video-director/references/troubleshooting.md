# Troubleshooting Failed Generations

Process: (1) watch the whole clip; (2) name the exact flaw and timestamp; (3) classify cause: prompt / references / model limit / complexity; (4) change ONE thing; (5) keep what worked; (6) offer to log the lesson in `lessons-log.md`.

| Symptom | Likely cause | Fix |
|---|---|---|
| Faces change | weak/ignored references, face blocked, too many descriptors, drift late in clip | better front-facing refs; name refs in prompt; Elements/Soul ID; 3-5 anchors; shorter clip; start from approved still |
| Only one man has dumbbells | object count not explicit | state four total; mention both men's hands separately; show both weights in frame 1 |
| Impossible exercise motion | action vague or too fast | write phases and durations; one exercise; slower tempo; foot position and joint tracking stated |
| Clothing changes | wardrobe described loosely | wardrobe reference + LOCK block each clip |
| S emblem distorted | fast motion / small in frame | closer shot, less motion, logo reference, macro insert |
| Drone / zoom-out appears | model improvising camera | state "camera stays at human height, one continuous shot, no cuts"; remove words like "establishing", "reveal", "epic" |
| Too busy, glitchy | too many actions/camera moves | one exercise, one move, 2-3 beats; split into clips |
| Plastic skin | generic quality words | pore-level skin, natural imperfections, film-stock anchors |
| Extra people with warped faces | big crowd with many faces | soften background focus, fewer people |
| References ignored | no @ names in prompt | name every upload |
| Background bleed from reference | reference role unclear | "use for appearance only, ignore its background" |
| Hands/limbs warped | complex grip or fast motion | simpler grip, slower tempo, positive constraint "natural hands" |

Cost tip: test at lower resolution and without audio, upgrade once the prompt locks (community guidance; check current pricing).
