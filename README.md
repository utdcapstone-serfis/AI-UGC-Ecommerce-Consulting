# Allison - Higgsfield (AI video and image ad generation)

## Video ad generation (Higgsfield)

`.claude/skills/higgsfield/` is a Claude Code Skill (not a Python agent) for
generating AI video/image ads via [Higgsfield](https://higgsfield.ai) -
Seedance, Kling, Wan, Genjutsu, and other model families. Needs two
credentials in `.env` (`HIGGSFIELD_API_KEY_ID` and
`HIGGSFIELD_API_KEY_SECRET` - note it's two separate values, not one). The
skill itself explains the request lifecycle, cost-estimation, and - most
importantly - to always confirm the exact request schema from the specific
model's own docs page rather than guessing, since it varies per model.

This is separate from the lead-gen pipeline above: it doesn't touch
`storage.py`'s leads table or get triggered by anything automatically. It's
a capability Claude can use when asked to generate ad creative, optionally
grounded in a specific lead's data if asked to make something for/about
that company.
