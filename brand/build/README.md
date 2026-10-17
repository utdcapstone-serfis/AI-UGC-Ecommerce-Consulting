# Rebuilding the Serfis PowerPoint template

These scripts generate `brand/Serfis_Template.pptx` (11 layouts, 13 sample slides) and `brand/Serfis_Agents_Slide.pptx` from the purple Serfis design
system (colors, fonts and components taken from the Serfis site artifact). Rebuilt output matches the committed files exactly (same slide and layout
counts and file sizes).

```
pip install python-pptx pillow numpy
python brand/build/make_backgrounds.py   # draws the dark-violet, section and bright-band backgrounds into brand/build/bg/ (git-ignored)
python brand/build/build_deck.py         # writes brand/Serfis_Template.pptx
python brand/build/agents_slide.py       # writes brand/Serfis_Agents_Slide.pptx (needs the template first)
```

Install the brand fonts before opening the decks: Unbounded, DM Sans, DM Mono, Fredoka (all free on Google Fonts).
The logo is `brand/assets/serfis-logo.png`. The older PDF generator was not kept (superseded by `docs/SYSTEM_GUIDE.md`).
