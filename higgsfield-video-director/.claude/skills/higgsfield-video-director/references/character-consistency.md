# Subject, Wardrobe, Logo and Object Consistency (general)

Brand-specific anchors, object counts and logo rules live in the campaign profile (`campaigns/<name>.md`). This file holds the general method.

## Reference kit (build once, reuse forever)
1. **Per person**: 1 sharp front-facing, evenly lit portrait on neutral grey, plus 1 full-body front. Add a 3/4 face if available. Real photos or locked AI renders only.
2. **Wardrobe or product**: a front view with the logo or label visible and sharp.
3. **Logo**: flat, front-on, high-res on a plain background.
4. **Location**: one clean 3/4-angle still, with no people if possible.
5. **Key props**: one clean product shot each.
Fix the *image* before the prompt: reference quality is the biggest lever (community guidance).

## Recommended order of options (use what the selected model/interface supports)
1. **Reference/Elements** (Higgsfield): save each subject, logo, location and prop as named Elements; reference by exact name.
2. **Image-to-video from a starting frame** where everything already looks right: generate the still first (image model), approve it, then animate.
3. **Soul ID** for each person if you have real consenting-subject photos (20+).
4. **Text anchors**: 3-5 per subject, repeated every prompt.
Test whether the model accepts your human-face references; if it blocks or ignores them, escalate to 2 or 3.

## Procedure per clip
1. Attach references in a fixed order and name each in the prompt with a role sentence ("use only ...", "do not interchange ...").
2. Paste the campaign's LOCK block verbatim.
3. State counts: people, objects, logos ("one emblem on each chest", "four cups total").
4. One variable change per iteration.
5. Watch the full clip, not just frame 1 (drift often appears late in the clip).

## Separate states
Dry and sweaty (or clean and used) versions of a subject should be separate references/Elements, rather than asking for "make him sweaty" (community guidance).

## Logos and labels
Use medium or close shots; avoid fast motion across the mark; lock it as a hero item ("one identical ..., sharp, same size and placement"). If it warps, reduce motion and use a macro clip of the mark to cut in. On-screen text is unreliable: add names and slogans in post.

## Multi-person blocking
For two or more people, lock each person's screen third and approximate position, depth layer, orientation, pose, gaze and contact points, plus distance, eyeline and a no-crossing rule, before the action text. A worked example is in the Start Again profile.
