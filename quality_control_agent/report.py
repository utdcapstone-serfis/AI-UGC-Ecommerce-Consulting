"""Renders a list of QCEvaluation results as an HTML table."""

from __future__ import annotations

from html import escape

from .models import QCEvaluation, Verdict

_METRIC_COLUMNS = [
    ("duration", "Duration"),
    ("aspect_ratio", "Aspect Ratio"),
    ("hook", "Hook"),
    ("captions", "Captions"),
    ("safe_zone", "Safe Zone"),
    ("branding", "Branding"),
    ("voice_tone", "Voice/Tone"),
    ("audio_quality", "Audio Quality"),
    ("pacing", "Pacing"),
    ("cta", "CTA"),
]

_VERDICT_CLASS = {
    Verdict.PASS: "qc-verdict-pass",
    Verdict.FAIL: "qc-verdict-fail",
    Verdict.FLAG: "qc-verdict-flag",
    Verdict.UNMEASURED: "qc-verdict-unmeasured",
    Verdict.NOT_APPLICABLE: "qc-verdict-na",
}

TABLE_CSS = """
table.qc-report { border-collapse: collapse; width: 100%; font-family: system-ui, sans-serif; font-size: 14px; }
table.qc-report th, table.qc-report td { border: 1px solid rgba(128,128,128,0.35); padding: 8px 10px; text-align: left; vertical-align: top; }
table.qc-report th { background: rgba(128,128,128,0.12); }
table.qc-report td:first-child { font-weight: 600; }
.qc-verdict-pass { color: #1a7f37; font-weight: 600; }
.qc-verdict-fail { color: #cf222e; font-weight: 600; }
.qc-verdict-flag { color: #9a6700; font-weight: 600; }
.qc-verdict-unmeasured, .qc-verdict-na { color: #6e7781; font-style: italic; }
"""


def _cell_html(metric) -> str:
    if metric is None:
        return "—"
    label = metric.verdict.value.upper()
    if metric.score is not None:
        label += f" ({metric.score:.0f}/10)"
    css_class = _VERDICT_CLASS.get(metric.verdict, "")
    title_attr = f' title="{escape(metric.note)}"' if metric.note else ""
    return f'<span class="{css_class}"{title_attr}>{escape(label)}</span>'


def render_table_html(evaluations: list[QCEvaluation]) -> str:
    """Returns a `<style>` block plus a `<table>` — no `<html>/<head>/<body>`,
    so it can be embedded in a larger page (e.g. a published artifact) or
    wrapped by `render_standalone_report` below.
    """
    header_cells = "".join(f"<th>{label}</th>" for _, label in _METRIC_COLUMNS)

    rows = []
    for ev in evaluations:
        metric_cells = "".join(f"<td>{_cell_html(ev.metrics.get(key))}</td>" for key, _ in _METRIC_COLUMNS)

        score = ev.composite_score()
        score_text = f"{score:.1f}/10" if score is not None else "—"

        verdict = ev.final_verdict()
        verdict_class = "qc-verdict-pass" if verdict == "PASS" else "qc-verdict-fail"

        if ev.video_url:
            title_cell = f'<a href="{escape(ev.video_url)}" target="_blank" rel="noopener">{escape(ev.video_title)}</a>'
        else:
            title_cell = escape(ev.video_title)

        rows.append(
            "<tr>"
            f"<td>{title_cell}</td>"
            f"{metric_cells}"
            f"<td>{score_text}</td>"
            f'<td class="{verdict_class}">{escape(verdict)}</td>'
            "</tr>"
        )

    return (
        f"<style>{TABLE_CSS}</style>"
        '<table class="qc-report">'
        f"<thead><tr><th>Video</th>{header_cells}<th>Composite</th><th>Verdict</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def render_standalone_report(evaluations: list[QCEvaluation], title: str = "QC Evaluation Report") -> str:
    """A full, self-contained HTML document — for saving as a plain report file."""
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{escape(title)}</title></head><body>"
        f"<h1>{escape(title)}</h1>"
        f"{render_table_html(evaluations)}"
        "</body></html>"
    )
