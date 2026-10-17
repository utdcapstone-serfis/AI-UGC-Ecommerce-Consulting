"""Backgrounds for the Serfis deck, drawn from the site's CSS: a near-black violet ground,
soft violet/blue pools of light, film grain; plus the lavender 'CTA band' gradient."""
from pathlib import Path

import numpy as np
from PIL import Image

W, H = 1920, 1080
OUT = str(Path(__file__).resolve().parent / "bg")
import os
os.makedirs(OUT, exist_ok=True)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
rng = np.random.default_rng(7)


def hexc(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32)


def base(color="#06030F"):
    img = np.ones((H, W, 3), np.float32) * hexc(color)
    return img


def glow(img, color, cx, cy, rx, ry, alpha):
    """Radial pool of colour: opaque `alpha` at the centre fading to 0 at the ellipse edge."""
    d = np.sqrt(((xx - cx * W) / (rx * W)) ** 2 + ((yy - cy * H) / (ry * H)) ** 2)
    a = np.clip(1 - d, 0, 1) ** 1.6 * alpha
    img[:] = img * (1 - a[..., None]) + hexc(color) * a[..., None]


def grain(img, amt=3.0):
    n = rng.normal(0, amt, (H, W, 1)).astype(np.float32)
    img += n


def save(img, name):
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(f"{OUT}/{name}.jpg", quality=93, subsampling=0)


# content slides: the contact section's two pools (violet top-right, blue bottom-left)
im = base(); glow(im, "#6A3FE6", 1.02, -0.05, 0.62, 0.95, 0.46); glow(im, "#3B5BFF", 0.08, 1.12, 0.5, 0.8, 0.26); grain(im); save(im, "content")

# hero / title: the story stage - a big violet glow high and centred, blue lift from below
im = base("#07031A"); glow(im, "#4E2BCC", 0.66, 0.28, 0.55, 0.75, 0.45); glow(im, "#905BF4", 0.92, 0.02, 0.3, 0.5, 0.14)
glow(im, "#3B5BFF", 0.45, 1.2, 0.8, 0.5, 0.20); grain(im); save(im, "hero")

# section divider: deeper, more saturated
im = base("#0C0426"); glow(im, "#6A3FE6", 0.85, 0.5, 0.7, 0.95, 0.55); glow(im, "#C084FC", 1.0, 0.0, 0.35, 0.6, 0.18)
glow(im, "#2438C8", 0.0, 1.0, 0.6, 0.8, 0.40); grain(im); save(im, "section")

# CTA band: the site's one bright moment - 100deg #4E2BCC 0 -> #9A66F8 9% -> #C58BFF 58% -> #D9B8FF 100%
t = ((xx / W) * np.cos(np.radians(10)) + (yy / H) * np.sin(np.radians(10)))
t = (t - t.min()) / (t.max() - t.min())
stops = [(0.0, "#4E2BCC"), (0.09, "#9A66F8"), (0.58, "#C58BFF"), (1.0, "#D9B8FF")]
im = np.zeros((H, W, 3), np.float32)
for c in range(3):
    im[..., c] = np.interp(t, [s[0] for s in stops], [hexc(s[1])[c] for s in stops])
glow(im, "#FFFFFF", 0.66, 0.08, 0.3, 0.5, 0.22); glow(im, "#3B5BFF", 0.14, 0.16, 0.4, 0.75, 0.15); glow(im, "#4E2BCC", 0.86, 0.88, 0.36, 0.64, 0.22)
grain(im, 2.0); save(im, "band")

# sample photo for the Image + Caption slide: violet gradient with the logo mark
im = base("#0C0426"); glow(im, "#6A3FE6", 0.5, 0.35, 0.8, 0.8, 0.8); glow(im, "#3B5BFF", 0.2, 1.0, 0.7, 0.7, 0.5); glow(im, "#C084FC", 0.9, 0.0, 0.5, 0.6, 0.35)
grain(im, 2.5)
art = Image.fromarray(np.clip(im, 0, 255).astype(np.uint8)).convert("RGBA")
logo = Image.open(Path(__file__).resolve().parents[1] / "assets" / "serfis-logo.png").convert("RGBA")
logo = logo.resize((560, 560), Image.LANCZOS)
art.alpha_composite(logo, ((W - 560) // 2, (H - 560) // 2))
art.convert("RGB").save(f"{OUT}/sample_image.jpg", quality=92)
print("ok", os.listdir(OUT))
