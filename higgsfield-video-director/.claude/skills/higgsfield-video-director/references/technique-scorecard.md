# Technique Scorecard

Which techniques actually work for THIS campaign, from our own generations. Read it before writing a prompt: prefer `proven` and `promising`, use `untested` with a note, avoid `failed` unless the failure was a misuse.

## Status rules
- `untested`: 0 results.
- `promising`: 1 clear success, no failures.
- `proven`: 2+ successes in different scenes and no unexplained failures.
- `failed`: 2 failures where the technique was applied correctly (evidence: frames), or 1 failure plus a matching known limit in a source.
- A result counts only when the user reported it or shared the video (log the Prompt ID). One result never makes a technique `proven`.
- Moving a technique to `failed` needs a note on how it was applied, so misuse isn't blamed on the technique.

## Scorecard (updated 2026-10-23; zero generations reported so far)
| Technique | Source | Tried | Worked | Failed | Status | Evidence |
|---|---|---|---|---|---|---|
| Reference role sentences with "use only…" + "do not interchange" | OSM omni-reference-2-5 | 0 | 0 | 0 | untested | G-001, G-002 |
| Two-man positioning block (thirds, depth, contact points, no-crossing rule) | OSM multi-character-anchor | 0 | 0 | 0 | untested | G-001 |
| Explicit dumbbell and hand counts ("four total, two hands per man") | OSM FAILURE-MODES, our rule | 0 | 0 | 0 | untested | G-001 |
| One camera move with named end frame | OSM camera | 0 | 0 | 0 | untested | G-001, G-002, G-003 |
| Hold-then-pan as timed beats | OSM camera, our template | 0 | 0 | 0 | untested | G-002 |
| Chin-down chest framing to limit face drift in apparel beats | ours | 0 | 0 | 0 | untested | G-002 |
| Garment + emblem "one identical" lock line | LRN fashion-lookbook (extended to logo) | 0 | 0 | 0 | untested | G-001, G-002 |
| Pedaling as ordered chain, ~90 rpm, contact-triggered motion | LRN sports-extreme | 0 | 0 | 0 | untested | G-002 |
| Background riders as separate soft-focus block | LRN sports-extreme | 0 | 0 | 0 | untested | G-002 |
| Exertion cues with qualifiers ("faint sweat beads") | OSM facs | 0 | 0 | 0 | untested | G-001, G-002 |
| Short positive AVOID line instead of a long negative list | OSM seedance-2-5 | 0 | 0 | 0 | untested | G-001, G-002, G-003 |
| Diegetic-only audio with `[AUDIO: Xs]` timestamps | OSM higgsfield-audio | 0 | 0 | 0 | untested | G-003 |
| No hands in product macro shots | LRN food-asmr | 0 | 0 | 0 | untested | G-003 |
| Scope fence ("Espresso only") | LRN food-asmr | 0 | 0 | 0 | untested | G-003 |

## How to update
After a result: for each technique applied in that entry, +1 to Tried; +1 to Worked or Failed depending on whether the defect list implicates it; recompute Status; add the entry ID to Evidence. If a defect has no technique to blame, don't invent one; log it in `generation-log.md` as `Unknown` and design a test.
