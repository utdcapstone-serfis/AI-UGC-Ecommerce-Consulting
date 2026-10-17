"""Scene 1 ("The Bar"): one 1k 9:16 still of the opening frame, built from character reference crops.

Grok Imagine Image 2.0 (xai/grok-imagine-image-2.0), generate-with-references. ~1 paid image.
Put 2-3 crops of the character sheet in media/scene1-bar/references/ (ref_front_head.png,
ref_34left_head.png, ref_front_body.png). Output: media/scene1-bar/ad_scene1_freeze_v1.png
"""
from hf_common import ROOT, collect, resume, submit, upload, wants_resume

REF = ROOT / "media" / "scene1-bar" / "references"
OUT = ROOT / "media" / "scene1-bar" / "ad_scene1_freeze_v1.png"

PROMPT = """Photorealistic cinematic still frame from a premium luxury lifestyle commercial, vertical 9:16, shot on a 35mm cinema lens with shallow depth of field and natural optical falloff.
Setting: an upscale cocktail bar in an American city at night. Dark walnut wood, polished black marble counter, brushed brass accents, black leather barstools, elegant pendant lights, floor-to-ceiling windows with a softly lit city skyline behind, warm golden reflections on glassware, small candle-like table lights. Palette: charcoal, black, walnut brown, muted gold, warm amber, cream highlights; not oversaturated orange.
Foreground: the exact man from the reference images (same face, same light-brown tousled wavy hair, clean-shaven, defined angular jaw, athletic build), about 28 years old, wearing a tailored black two-piece suit, crisp white dress shirt and a neatly tied black necktie. He sits alone on a black leather barstool at the marble counter, positioned slightly left of center, torso angled slightly toward the bar, one forearm resting naturally on the counter, the other hand holding a short heavy crystal tumbler with a little amber liquor and partly melted ice cubes. Relaxed but quietly withdrawn posture, shoulders slightly lowered, calm thoughtful neutral expression, eyes looking down toward his drink. Medium shot from the waist up, camera slightly oblique along the bar so the counter leads diagonally into the background. Leave open empty space on the right side of the frame.
Background, soft focus but clearly alive: two well-dressed men talking quietly at the bar behind him, a man and woman across a high-top table with cocktails, a bartender in a dark shirt and black apron pouring a drink at the far end of the counter, three friends chatting in a loose semicircle, more patrons in small groups by the windows. About 12 to 18 adults in believable evening attire, natural independent poses, nobody looking at the camera, nobody noticing him.
Lighting: warm amber key light from the pendant lamps on one side of his face, cooler window fill preserving shadow detail, subtle warm rim light separating the dark suit from the background. Real skin texture with visible pores, individual hair strands, black suit fabric showing weave and tailoring, white shirt not overexposed, believable refraction and highlights in the crystal glass, restrained marble reflections.
No logos, no brand marks, no readable text or captions anywhere; bottle and glass labels are blank."""

if wants_resume():
    resume("scene1_freeze_v1", OUT, "images")
else:
    refs = [upload(REF / f"{n}.png", "image/png") for n in ("ref_front_head", "ref_34left_head", "ref_front_body")]
    body = {"prompt": PROMPT, "image_urls": refs, "resolution": "1k", "aspect_ratio": "9:16", "quality": "medium"}
    collect(submit("xai/grok-imagine-image-2.0", body, "scene1_freeze_v1"), OUT, "images")
