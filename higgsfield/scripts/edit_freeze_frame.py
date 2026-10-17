"""Edit the approved freeze frame with Grok Imagine Image 2.0 (image 1 = the frame, image 2 = identity reference).

Usage:  python edit_freeze_frame.py background-standing   -> ad_scene1_freeze_v2.png  (he stays seated)
        python edit_freeze_frame.py all-standing          -> ad_scene1_freeze_v3.png  (everyone stands)
Lessons: an edit keeps the scene but not every detail; v3 left the left-hand couple seated because the
low round table stayed in the picture. Say what should change AND what must stay.
"""
import sys

from hf_common import ROOT, collect, submit, upload

DIR = ROOT / "media" / "scene1-bar"
VARIANTS = {
    "background-standing": ("ad_scene1_freeze_v2.png", """Edit the first image. Keep everything exactly as it is: the man in the foreground (same face, wavy light-brown hair, black suit, white shirt, black tie, seated pose on the black leather barstool, forearm on the counter, crystal tumbler of amber liquor in his hand), the bar, the marble counter, the brass pendant lights, the windows and city skyline, the warm lighting, the camera angle and the vertical framing.
Change only the background people: every person in the background is now standing upright on their feet, none seated. The men and the woman on the left stand around the high-top table holding their drinks, the man and woman in the middle stand close together chatting, and the bartender stands behind the counter pouring a drink. Keep the same people, outfits, hair and positions as far as possible, only upright and standing, with natural relaxed standing posture and independent small gestures. Nobody looks at the camera and nobody notices the man in the foreground. Photorealistic, same cinematic grade. No logos, no brand marks, no readable text."""),
    "all-standing": ("ad_scene1_freeze_v3.png", """Edit the first image. Keep exactly the same: the bar, the black marble counter, the brass pendant lights, the windows and city skyline, the warm cinematic lighting, the camera angle slightly oblique along the bar, and the vertical 9:16 framing. Keep the man's identity exactly (same face, wavy light-brown hair, black two-piece suit, white shirt, black tie) and keep the crystal tumbler of amber liquor in his hand.
Change the poses so that EVERYONE is standing upright on their feet and nobody is seated; the barstools are empty. The man now stands at the marble counter, slightly left of center, torso angled slightly toward the bar, one forearm resting on the counter and the other hand holding the tumbler, relaxed but quietly withdrawn posture, calm thoughtful expression. Medium shot from about the hips up. Leave open empty space on the right side of the frame.
In the background everyone stands too: the men and the woman on the left stand around the high-top table holding drinks, the man and woman in the middle stand close together chatting, and the bartender stands behind the counter pouring a drink. Keep the same people, outfits, hair and positions as far as possible, only standing, with natural relaxed standing posture and small independent gestures. Nobody looks at the camera and nobody notices the man in the foreground. Photorealistic, same cinematic grade. No logos, no brand marks, no readable text."""),
}
name = sys.argv[1] if len(sys.argv) > 1 else "all-standing"
out_name, prompt = VARIANTS[name]
base = upload(DIR / "ad_scene1_freeze_v1.png", "image/png")
ref = upload(DIR / "references" / "ref_front_head.png", "image/png")
body = {"prompt": prompt, "image_urls": [base, ref], "resolution": "1k", "aspect_ratio": "9:16", "quality": "medium"}
collect(submit("xai/grok-imagine-image-2.0", body, f"scene1_edit_{name}"), DIR / out_name, "images")
